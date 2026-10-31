"""AI (Claude) annotatsiyasi: hujjatlarni o'qib tuzilgan termin ro'yxatlaridan JSONL yaratish.

Bu **oltin standart emas**. Natija ``data/annotations/claude/`` ga ``annotator:
"claude"``, ``status: "draft"`` bilan yoziladi va web interfeysda inson annotatorga
faqat **taklif** sifatida ko'rsatiladi. Baholashda u "kumush" (silver) maʼlumot
deb ataladi va inson tekshiruvidan o'tmaguncha natijalar shu belgi bilan beriladi.

Qanday tuzilgan: Claude har bir hujjatni o'qib, unda qaysi so'z va birikmalar
yo'riqnoma (``docs/data-annotation-guide.md``) bo'yicha termin ekanini,
qaysi uchrashlar esa termin emasligini (umumiy maʼnodagi qo'llanish, chet tilidagi
izoh, asar nomi) ro'yxatga yozgan. Ro'yxatlar ``data/silver/`` da:

- ``lexicon.txt`` — barcha hujjatlarga umumiy, bir maʼnoli terminlar;
- ``docs/<doc_id>.txt`` — shu hujjatga xos terminlar va istisnolar.

Qator formati::

    # izoh
    undosh tovush = undosh; undoshlar     lemma = matndagi qo'shimcha shakllar
    -sifat                                umumiy ro'yxatdagi lemmani shu hujjatda ishlatmaslik
    != sifatida                           shu ko'rinishdagi moslik termin emas (registr/apostrofsiz)
    !~ phonema — tovush                   shu parcha ichidagi mosliklar termin emas

Ro'yxat lug'at aniqlagichi (qo'shimchalar, tovush o'zgarishlari, uzun moslik
ustunligi) bilan matnga qo'llanadi. Lug'at shakli (``term``) — lemma.

    PYTHONPATH=backend python -m app.annotation.silver [--check]
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.annotation.workspace import AI_ANNOTATOR
from app.database.term_store import parse_terms
from app.dataset.annotation import STATUS_DRAFT, ValidationReport, parse_record, record_to_dict
from app.dataset.inline import prepare_source, split_paragraphs
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.nlp.normalize import normalize_form, normalize_text


@dataclass
class Lexicon:
    terms: dict[str, list[str]] = field(default_factory=dict)  # lemma -> qo'shimcha shakllar
    removed: set[str] = field(default_factory=set)
    excluded_surfaces: set[str] = field(default_factory=set)
    excluded_contexts: list[str] = field(default_factory=list)


class LexiconError(ValueError):
    pass


def parse_lexicon(text: str, source: str = "<ro'yxat>") -> Lexicon:
    lexicon = Lexicon()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split(" #", 1)[0].strip() if not raw.lstrip().startswith("!~") else raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!="):
            lexicon.excluded_surfaces.add(normalize_form(line[2:]))
        elif line.startswith("!~"):
            context = line[2:].strip()
            if not context:
                raise LexiconError(f"{source}:{number}: bo'sh kontekst")
            lexicon.excluded_contexts.append(normalize_text(context))
        elif line.startswith("-"):
            lexicon.removed.add(normalize_form(line[1:]))
        else:
            lemma, _, rest = line.partition("=")
            lemma = lemma.strip()
            if not lemma:
                raise LexiconError(f"{source}:{number}: lemma yo'q")
            variants = [v.strip() for v in rest.split(";") if v.strip()]
            lexicon.terms.setdefault(lemma, [])
            lexicon.terms[lemma] += [v for v in variants if v not in lexicon.terms[lemma]]
    return lexicon


def combine(base: Lexicon, local: Lexicon) -> Lexicon:
    terms = {lemma: list(forms) for lemma, forms in base.terms.items() if normalize_form(lemma) not in local.removed}
    for lemma, forms in local.terms.items():
        terms.setdefault(lemma, [])
        terms[lemma] += [f for f in forms if f not in terms[lemma]]
    return Lexicon(
        terms=terms,
        excluded_surfaces=base.excluded_surfaces | local.excluded_surfaces,
        excluded_contexts=base.excluded_contexts + local.excluded_contexts,
    )


def build_matcher(lexicon: Lexicon, source: str = "<ro'yxat>") -> DictionaryMatcher:
    owner: dict[str, str] = {}
    entries = []
    for number, (lemma, forms) in enumerate(sorted(lexicon.terms.items()), start=1):
        for form in (lemma, *forms):
            key = normalize_form(form)
            if key in owner and owner[key] != lemma:
                raise LexiconError(f"{source}: '{form}' ikki lemmaga tegishli: {owner[key]!r} va {lemma!r}")
            owner[key] = lemma
        entries.append({"id": f"s{number}", "term": lemma, "variants": forms})
    return DictionaryMatcher(parse_terms(entries))


def annotate_paragraph(text: str, matcher: DictionaryMatcher, lexicon: Lexicon) -> list[dict]:
    normalized = normalize_text(text)
    blocked: list[tuple[int, int]] = []
    for context in lexicon.excluded_contexts:
        start = normalized.find(context)
        while start != -1:
            blocked.append((start, start + len(context)))
            start = normalized.find(context, start + 1)
    spans = []
    for match in matcher.find(text):
        if normalize_form(match.surface) in lexicon.excluded_surfaces:
            continue
        if any(a <= match.start and match.end <= b for a, b in blocked):
            continue
        spans.append({"start": match.start, "end": match.end, "term": match.candidates[0].entry.term, "label": "TERM"})
    return spans


def annotate_document(doc_id: str, source: str, matcher: DictionaryMatcher, lexicon: Lexicon) -> list[dict]:
    records = []
    report = ValidationReport()
    for number, paragraph in enumerate(split_paragraphs(prepare_source(source)), start=1):
        obj = {
            "id": f"{doc_id}-p{number:03d}",
            "doc_id": doc_id,
            "text": paragraph.text,
            "terms": annotate_paragraph(paragraph.text, matcher, lexicon),
            "annotator": AI_ANNOTATOR,
            "status": STATUS_DRAFT,
        }
        record = parse_record(obj, obj["id"], report)
        if record is None:
            raise LexiconError("; ".join(str(issue) for issue in report.errors))
        records.append(record_to_dict(record))
    return records


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="AI (Claude) termin ro'yxatlaridan annotatsiya yaratish")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--check", action="store_true", help="faqat statistikani ko'rsatish, yozmaslik")
    args = parser.parse_args(argv)

    silver = args.data_dir / "silver"
    try:
        base = parse_lexicon((silver / "lexicon.txt").read_text(encoding="utf-8"), "lexicon.txt")
        out_dir = args.data_dir / "annotations" / AI_ANNOTATOR
        totals = {"docs": 0, "paragraphs": 0, "spans": 0}
        missing = []
        for raw in sorted((args.data_dir / "raw").glob("*.txt")):
            doc_id = raw.stem
            local_path = silver / "docs" / f"{doc_id}.txt"
            if not local_path.exists():
                missing.append(doc_id)
                continue
            lexicon = combine(base, parse_lexicon(local_path.read_text(encoding="utf-8"), local_path.name))
            records = annotate_document(doc_id, raw.read_text(encoding="utf-8"), build_matcher(lexicon, local_path.name), lexicon)
            spans = sum(len(r["terms"]) for r in records)
            totals["docs"] += 1
            totals["paragraphs"] += len(records)
            totals["spans"] += spans
            print(f"{doc_id}: {len(records)} paragraf, {spans} termin")
            if not args.check:
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / f"{doc_id}.jsonl").write_text(
                    "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
                )
    except (LexiconError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Jami: {totals['docs']} hujjat, {totals['paragraphs']} paragraf, {totals['spans']} termin")
    if missing:
        print(f"Ro'yxati yo'q hujjatlar ({len(missing)}): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
