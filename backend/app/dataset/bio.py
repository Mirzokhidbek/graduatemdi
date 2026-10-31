"""BIO formatidagi dataset: span annotatsiyadan BIO ga o'tkazish, tekshirish va 100 gaplik to'plam.

BIO yozuvi (JSONL, bir qatorda bitta gap)::

    {"id": "bio-001", "source_id": "uzwiki-1739-p001", "doc_id": "uzwiki-1739",
     "text": "Tilshunoslik yoki Lingvistika tillarni oʻrganuvchi fandir.",
     "tokens": ["Tilshunoslik", "yoki", "Lingvistika", "tillarni", "oʻrganuvchi", "fandir"],
     "offsets": [[0, 12], [13, 17], ...],
     "tags": ["B-TERM", "O", "B-TERM", "O", "O", "O"],
     "terms": [{"start": 0, "end": 12, "term": "tilshunoslik", "surface": "Tilshunoslik"}, ...],
     "status": "reviewed", "annotator": "claude", "review": "o'zgarishsiz"}

``tags`` va ``terms`` bir-biridan kelib chiqadi; ``validate_bio`` ularning mosligini,
BIO qoidasini (``I`` faqat ``B``/``I`` dan keyin), tokenlar matndagi joyiga mosligini
tekshiradi. Tokenlar ``app.nlp.tokenize`` bo'yicha (harflar va so'z ichidagi apostrof).

    PYTHONPATH=backend python -m app.dataset.bio sample     # 100 gaplik to'plam -> data/bio/sentences-100.jsonl
    PYTHONPATH=backend python -m app.dataset.bio export data/processed/silver/train.jsonl -o data/processed/bio/train.jsonl
    PYTHONPATH=backend python -m app.dataset.bio validate data/bio/sentences-100.jsonl
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from app.dataset.annotation import AnnotatedRecord, load_annotations
from app.nlp.clean import split_sentences
from app.nlp.normalize import is_word_end, is_word_start, normalize_text
from app.nlp.tokenize import tokenize

OUTSIDE, BEGIN, INSIDE = "O", "B-TERM", "I-TERM"
TAGS = (OUTSIDE, BEGIN, INSIDE)


def to_bio(text: str, spans: Iterable[tuple[int, int, str]]) -> dict[str, Any]:
    """Matn va ``(start, end, term)`` spanlardan BIO yozuvining asosiy qismi."""
    tokens = tokenize(text)
    tags = [OUTSIDE] * len(tokens)
    terms = []
    for start, end, term in sorted(spans):
        inside = [i for i, t in enumerate(tokens) if t.start >= start and t.end <= end]
        for k, i in enumerate(inside):
            tags[i] = BEGIN if k == 0 else INSIDE
        terms.append({"start": start, "end": end, "term": term, "surface": text[start:end]})
    return {
        "text": text,
        "tokens": [t.text for t in tokens],
        "offsets": [[t.start, t.end] for t in tokens],
        "tags": tags,
        "terms": terms,
    }


def validate_bio(obj: dict[str, Any]) -> list[str]:
    """Bitta BIO yozuvidagi muammolar ro'yxati (bo'sh — yaroqli)."""
    problems: list[str] = []
    text, tokens, offsets, tags = obj.get("text"), obj.get("tokens"), obj.get("offsets"), obj.get("tags")
    if not isinstance(text, str) or not text.strip():
        return ["'text' bo'sh"]
    if not (isinstance(tokens, list) and isinstance(offsets, list) and isinstance(tags, list)):
        return ["'tokens', 'offsets', 'tags' ro'yxat bo'lishi kerak"]
    if not len(tokens) == len(offsets) == len(tags):
        return [f"uzunliklar teng emas: tokens={len(tokens)}, offsets={len(offsets)}, tags={len(tags)}"]
    expected = tokenize(text)
    if [t.text for t in expected] != tokens or [[t.start, t.end] for t in expected] != offsets:
        problems.append("tokenlar matnni qayta tokenlashtirish natijasiga mos emas")
    for i, tag in enumerate(tags):
        if tag not in TAGS:
            problems.append(f"{i}-token: nomaʼlum teg {tag!r}")
        elif tag == INSIDE and (i == 0 or tags[i - 1] == OUTSIDE):
            problems.append(f"{i}-token ({tokens[i]!r}): I-TERM B-TERM/I-TERM dan keyin kelishi kerak")
    normalized = normalize_text(text)
    rebuilt = to_bio(text, [(t["start"], t["end"], t["term"]) for t in obj.get("terms", [])])
    for term in obj.get("terms", []):
        start, end = term["start"], term["end"]
        if text[start:end] != term.get("surface"):
            problems.append(f"'surface' matnga mos emas: {term.get('surface')!r}")
        if not (is_word_start(normalized, start) and is_word_end(normalized, end)):
            problems.append(f"span so'z chegarasida emas: {text[start:end]!r}")
        if not str(term.get("term", "")).strip():
            problems.append(f"{text[start:end]!r}: lug'at shakli bo'sh")
    if rebuilt["tags"] != tags:
        problems.append("'tags' va 'terms' bir-biriga mos emas")
    ordered = sorted((t["start"], t["end"]) for t in obj.get("terms", []))
    for (a, b), (c, d) in zip(ordered, ordered[1:]):
        if c < b:
            problems.append(f"spanlar ustma-ust tushadi: [{a}, {b}) va [{c}, {d})")
    return problems


def sentence_records(record: AnnotatedRecord) -> list[tuple[str, int, list[tuple[int, int, str]]]]:
    """Paragrafni gaplarga ajratadi; gap chegarasini kesib o'tgan span tashlab yuborilmaydi — gap birlashtiriladi."""
    out = []
    for start, end in split_sentences(record.text):
        spans = [(s.start - start, s.end - start, s.term) for s in record.terms if s.start >= start and s.end <= end]
        out.append((record.text[start:end], start, spans))
    return out


@dataclass(frozen=True)
class Edit:
    number: int
    add: bool
    surface: str
    term: str | None


def parse_review(text: str) -> list[Edit]:
    edits = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        number, sign, rest = line.split(" ", 2)
        surface, _, term = rest.partition("|")
        edits.append(Edit(int(number), sign == "+", surface.strip(), term.strip() or None))
    return edits


def apply_edit(text: str, spans: list[tuple[int, int, str]], edit: Edit) -> list[tuple[int, int, str]]:
    target = normalize_text(edit.surface)
    normalized = normalize_text(text)
    position = normalized.find(target)
    while position != -1 and not (is_word_start(normalized, position) and is_word_end(normalized, position + len(target))):
        position = normalized.find(target, position + 1)
    if position == -1:
        raise ValueError(f"{edit.number:03d}: {edit.surface!r} gapda topilmadi")
    start, end = position, position + len(target)
    if edit.add:
        kept = [s for s in spans if s[1] <= start or s[0] >= end]
        return sorted(kept + [(start, end, edit.term or edit.surface.lower())])
    remaining = [s for s in spans if (s[0], s[1]) != (start, end)]
    if len(remaining) == len(spans):
        raise ValueError(f"{edit.number:03d}: olib tashlanadigan {edit.surface!r} belgilanmagan")
    return remaining


def sample_sentences(records_by_doc: dict[str, list[AnnotatedRecord]], size: int = 100) -> list[tuple[str, str, str, list]]:
    """Barcha hujjatlardan navbatma-navbat, hujjat ichida bir tekis tarqatib ``size`` ta gap tanlaydi (deterministik).

    Faqat 6–40 tokenli gaplar, bibliografiya qatorlari chiqarib tashlanadi.
    """
    candidates: dict[str, list] = {}
    for doc_id in sorted(records_by_doc):
        for record in records_by_doc[doc_id]:
            for text, _, spans in sentence_records(record):
                if not 6 <= len(tokenize(text)) <= 40 or any(m in text for m in ("==", "Ad.:", "Obsheye", "M., 19")):
                    continue
                candidates.setdefault(doc_id, []).append((record.id, doc_id, text, spans))
    picked: list = []
    docs = sorted(candidates)
    round_ = 0
    while len(picked) < size and any(round_ < len(candidates[d]) for d in docs):
        for doc_id in docs:
            items = candidates[doc_id]
            if round_ < len(items):
                item = items[(round_ * 7) % len(items)]
                if item not in picked:
                    picked.append(item)
                if len(picked) == size:
                    break
        round_ += 1
    return picked


def build_sample(annotations_dir: Path, review_path: Path, size: int = 100) -> list[dict[str, Any]]:
    """AI annotatsiyasidan (test maqolalari uchun uchrash-ma-uchrash ``claude2``) 100 gap + qo'lda tekshiruv tuzatishlari."""
    records: dict[str, AnnotatedRecord] = {}
    for annotator in ("claude", "claude2"):  # claude2 ustun (keyin o'qiladi)
        for path in sorted((annotations_dir / annotator).glob("*.jsonl")):
            for record in load_annotations([path]):
                records[record.id] = record
    by_doc: dict[str, list[AnnotatedRecord]] = {}
    for record in sorted(records.values(), key=lambda r: r.id):
        by_doc.setdefault(record.doc_id, []).append(record)
    picked = sample_sentences(by_doc, size)
    edits: dict[int, list[Edit]] = {}
    for edit in parse_review(review_path.read_text(encoding="utf-8")):
        edits.setdefault(edit.number, []).append(edit)

    out = []
    for number, (source_id, doc_id, text, spans) in enumerate(picked, start=1):
        for edit in edits.get(number, []):
            spans = apply_edit(text, spans, edit)
        obj = {
            "id": f"bio-{number:03d}",
            "source_id": source_id,
            "doc_id": doc_id,
            **to_bio(text, spans),
            "annotator": records[source_id].annotator,
            "status": "reviewed",
            "review": "tuzatildi" if number in edits else "o'zgarishsiz",
        }
        problems = validate_bio(obj)
        if problems:
            raise ValueError(f"{obj['id']}: " + "; ".join(problems))
        out.append(obj)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys
    from collections import Counter

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="BIO dataset")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("sample", help="100 gaplik tekshirilgan to'plam")
    sample.add_argument("--size", type=int, default=100)
    sample.add_argument("-o", "--output", type=Path, default=REPO_ROOT / "data" / "bio" / "sentences-100.jsonl")
    export = commands.add_parser("export", help="span JSONL -> gap darajasidagi BIO JSONL")
    export.add_argument("files", nargs="+", type=Path)
    export.add_argument("-o", "--output", type=Path, required=True)
    check = commands.add_parser("validate", help="BIO JSONL ni tekshirish")
    check.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "sample":
            rows = build_sample(REPO_ROOT / "data" / "annotations", REPO_ROOT / "data" / "bio" / "review.txt", args.size)
        elif args.command == "export":
            rows = []
            for record in load_annotations(args.files):
                for k, (text, offset, spans) in enumerate(sentence_records(record), start=1):
                    rows.append({"id": f"{record.id}-s{k:02d}", "source_id": record.id, "doc_id": record.doc_id,
                                 "paragraph_offset": offset, **to_bio(text, spans),
                                 "annotator": record.annotator, "status": record.status})
        else:
            bad = 0
            total = 0
            tags: Counter = Counter()
            for path in args.files:
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    total += 1
                    tags.update(obj.get("tags", []))
                    for problem in validate_bio(obj):
                        bad += 1
                        print(f"{path}:{number} ({obj.get('id')}): {problem}")
            print(f"Gaplar: {total}, tokenlar: {sum(tags.values())}, teglar: {dict(tags)}; xatolar: {bad}")
            return 1 if bad else 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    terms = sum(len(r["terms"]) for r in rows)
    print(f"{args.output}: {len(rows)} gap, {terms} termin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
