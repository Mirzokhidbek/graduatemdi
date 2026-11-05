"""Variantdorlik bo'yicha tajribalar (3.1-bo'lim, 3.2–3.5-jadvallar).

1. **Variantlarni guruhlash.** Oltin spanlarning matndagi shakllari (*fonemalarning,
   Fonema, fonemaga*) oltin lug'at shakli bo'yicha klasterlanadi. Usullar shu
   klasterlarni qanchalik tiklashi B-cubed P/R/F1 bilan o'lchanadi (shakllar
   chastotasi bilan tortilgan).
2. **Imlo shovqiniga chidamlilik (sintetik).** Test terminlariga sun'iy imlo variantlari
   qo'shiladi: apostrof almashtirish (*oʻ → o', o`, o‘*), apostrofni tushirib qoldirish,
   kirill yozuvi, bosh harf. Variant asl shakl bilan bitta guruhga tushgan ulush o'lchanadi.
3. **Sinonim va dubletlar.** Butun korpusdan juftlar ajratiladi va ekspert tekshiruvi
   uchun ``data/judgments/synonyms-review.csv`` ga yoziladi (mavjud baholar saqlanadi).
4. **Omonimiya.** ``homonymy`` klassifikatori validation va test'da.
5. **Guruhlar va meʼyoriy shakl.** Butun annotatsiya bo'yicha guruhlar va tavsiyalar —
   ``reports/variation-groups.json``.

    PYTHONPATH=backend python -m app.variation.experiment
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Callable, Mapping, Sequence

from app.database.term_store import load_terms
from app.dataset.annotation import AnnotatedRecord, load_annotations
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.normalize import normalize_form
from app.nlp.patterns import MorphTagger
from app.nlp.tokenize import tokenize
from app.services.term_normalizer import TermNormalizer
from app.variation.groups import bcubed, build_groups
from app.variation.homonymy import HomonymClassifier, ambiguous_lemmas, evaluate, occurrences
from app.variation.orthography import skeleton
from app.variation.synonyms import SynonymExtractor

_TO_CYRILLIC = [
    ("sh", "ш"), ("ch", "ч"), ("oʻ", "ў"), ("gʻ", "ғ"), ("yo", "ё"), ("yu", "ю"), ("ya", "я"), ("ye", "е"),
    ("ʼ", "ъ"), ("a", "а"), ("b", "б"), ("d", "д"), ("e", "е"), ("f", "ф"), ("g", "г"), ("h", "ҳ"), ("i", "и"),
    ("j", "ж"), ("k", "к"), ("l", "л"), ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"), ("q", "қ"), ("r", "р"),
    ("s", "с"), ("t", "т"), ("u", "у"), ("v", "в"), ("x", "х"), ("y", "й"), ("z", "з"),
]


def to_cyrillic(text: str) -> str:
    """Sintetik test uchun sodda lotin -> kirill (``ts``/``e`` nozik qoidalarisiz)."""
    out, i, low = [], 0, text.lower()
    while i < len(low):
        for latin, cyr in _TO_CYRILLIC:
            if low.startswith(latin, i):
                out.append(cyr)
                i += len(latin)
                break
        else:
            out.append(low[i])
            i += 1
    return "".join(out)


def noisy_variants(form: str) -> dict[str, str]:
    variants = {
        "apostrof (')": form.replace("ʻ", "'").replace("ʼ", "'"),
        "apostrof (`)": form.replace("ʻ", "`").replace("ʼ", "`"),
        "apostrof (‘’)": form.replace("ʻ", "‘").replace("ʼ", "’"),
        "apostrofsiz": form.replace("ʻ", "").replace("ʼ", ""),
        "bosh harf": form[:1].upper() + form[1:],
        "kirill": to_cyrillic(form),
    }
    return {kind: v for kind, v in variants.items() if v != form}


def gold_forms(records: Sequence[AnnotatedRecord]) -> tuple[Counter, dict[str, str]]:
    counts: Counter = Counter()
    gold: dict[str, str] = {}
    for record in records:
        for span in record.terms:
            surface = record.text[span.start : span.end]
            counts[surface] += 1
            gold.setdefault(surface, normalize_form(span.term))
    return counts, gold


def grouping_methods(lemmatizer: CorpusLemmatizer, normalizer: TermNormalizer) -> dict[str, Callable[[str], str]]:
    def corpus_lemma(form: str) -> str:
        words = [t.norm for t in tokenize(form)]
        return " ".join([*words[:-1], lemmatizer.lemma(words[-1])]) if words else form

    return {
        "exact": lambda f: f,
        "lowercase": lambda f: f.lower(),
        "skeleton": skeleton,
        "skeleton+corpus_lemmatizer": lambda f: skeleton(corpus_lemma(skeleton(f))),
        "skeleton+term_normalizer": lambda f: skeleton(normalizer.normalize(f).lemma),
    }


def evaluate_grouping(records, methods: Mapping[str, Callable[[str], str]]) -> dict:
    counts, gold = gold_forms(records)
    return {name: bcubed({f: fn(f) for f in counts}, gold, counts) for name, fn in methods.items()}


def evaluate_noise(records, methods: Mapping[str, Callable[[str], str]]) -> dict:
    canonical = sorted({normalize_form(s.term) for r in records for s in r.terms})
    canonical = [c for c in canonical if c]
    result = {}
    for name, fn in methods.items():
        by_kind: dict[str, list[int]] = {}
        for form in canonical:
            from app.nlp.clean import canonical_apostrophes

            original = canonical_apostrophes(form)
            for kind, variant in noisy_variants(original).items():
                by_kind.setdefault(kind, []).append(fn(variant) == fn(original))
        result[name] = {kind: sum(v) / len(v) for kind, v in by_kind.items() if v}
    return result


def update_review(path: Path, pairs) -> int:
    existing: dict[tuple[str, str], dict] = {}
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                existing[(row["left"], row["right"])] = row
    rows = []
    for pair in pairs:
        d = pair.to_dict()
        old = existing.get((d["left"], d["right"]), {})
        rows.append({
            "left": d["left"], "right": d["right"], "kind": d["kind"], "count": d["count"],
            "judgment": old.get("judgment", ""), "notes": old.get("notes", ""), "example": d["example"],
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["left", "right", "kind", "count", "judgment", "notes", "example"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def run(data_dir: Path, raw_dir: Path, terms_path: Path, review_path: Path) -> tuple[dict, dict]:
    split = {name: load_annotations([data_dir / f"{name}.jsonl"]) for name in ("train", "validation", "test")}
    documents = {p.stem: p.read_text(encoding="utf-8") for p in sorted(raw_dir.glob("*.txt"))}
    vocabulary = [t.norm for text in documents.values() for t in tokenize(text)]
    lemmatizer = CorpusLemmatizer(vocabulary)
    entries = load_terms(terms_path)
    normalizer = TermNormalizer(entries, vocabulary)
    methods = grouping_methods(lemmatizer, normalizer)

    tagger = MorphTagger(lemmatizer)
    known = set()
    for record in split["train"]:
        for span in record.terms:
            words = [t.norm for t in tokenize(span.term)]
            if words:
                known.add((*words[:-1], lemmatizer.lemma(words[-1])))
    for entry in entries:
        words = [t.norm for t in tokenize(entry.term)]
        if words:
            known.add((*words[:-1], lemmatizer.lemma(words[-1])))
    pairs = SynonymExtractor(tagger, known).extract(documents)
    reviewed = update_review(review_path, pairs)

    amb = ambiguous_lemmas(split["train"], lemmatizer)
    classifier = HomonymClassifier().fit(occurrences(split["train"], set(amb), lemmatizer))

    all_records = [r for records in split.values() for r in records]
    counts, _ = gold_forms(all_records)
    lemma_of = {form: normalizer.normalize(form).lemma for form in counts}
    groups = build_groups(
        counts, lemma_of, entries, [(" ".join(p.left), " ".join(p.right), p.kind) for p in pairs]
    )

    report = {
        "grouping": {name: evaluate_grouping(split[name], methods) for name in ("validation", "test")},
        "noise_robustness_test": evaluate_noise(split["test"], methods),
        "synonym_pairs": {
            "total": len(pairs),
            "by_kind": dict(Counter(p.kind for p in pairs)),
            "by_cue": dict(sum((p.cues for p in pairs), Counter())),
            "review_file": review_path.as_posix(),
            "review_rows": reviewed,
        },
        "homonymy": {
            "ambiguous_lemmas": amb,
            "validation": evaluate(classifier, occurrences(split["validation"], set(amb), lemmatizer)),
            "test": evaluate(classifier, occurrences(split["test"], set(amb), lemmatizer)),
        },
        "groups_summary": {
            "groups": len(groups),
            "forms": len(counts),
            "groups_with_several_forms": sum(len(g.members) > 1 for g in groups),
            "review_links": dict(Counter(t for g in groups for _, _, t in g.links if t not in ("orthographic", "morphological"))),
        },
    }
    details = {"pairs": [p.to_dict() for p in pairs], "groups": [g.to_dict() for g in groups]}
    return report, details


def _fmt(v) -> str:
    return "—" if v is None else f"{v:.3f}"


def main(argv: list[str] | None = None) -> int:
    import argparse

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Terminologik variantdorlik tajribalari (3.1-bo'lim)")
    parser.add_argument("--data", type=Path, default=REPO_ROOT / "data" / "processed" / "silver")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--terms", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--review", type=Path, default=REPO_ROOT / "data" / "judgments" / "synonyms-review.csv")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports" / "variation.json")
    parser.add_argument("--groups-output", type=Path, default=REPO_ROOT / "reports" / "variation-groups.json")
    args = parser.parse_args(argv)

    report, details = run(args.data, args.raw, args.terms, args.review)
    report["synonym_pairs"]["review_file"] = Path(args.review).relative_to(REPO_ROOT).as_posix() \
        if Path(args.review).is_relative_to(REPO_ROOT) else str(args.review)
    for path, payload in ((args.output, report), (args.groups_output, details)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for split, rows in report["grouping"].items():
        print(f"\nGuruhlash, {split} (B-cubed):  {'usul':<28} {'P':>6} {'R':>6} {'F1':>6}")
        for name, r in rows.items():
            print(f"   {name:<40} {_fmt(r['precision']):>6} {_fmt(r['recall']):>6} {_fmt(r['f1']):>6}")
    print("\nImlo shovqiniga chidamlilik (test, sintetik):")
    for name, kinds in report["noise_robustness_test"].items():
        print(f"   {name:<28} " + "  ".join(f"{k}={v:.2f}" for k, v in kinds.items()))
    sp = report["synonym_pairs"]
    print(f"\nSinonim/dublet juftlari: {sp['total']} {sp['by_kind']} {sp['by_cue']} -> {sp['review_file']}")
    for split in ("validation", "test"):
        h = report["homonymy"][split]
        print(f"Omonimiya, {split}: {h['occurrences']} uchrash; accuracy "
              + ", ".join(f"{k}={v:.3f}" for k, v in h["accuracy"].items()))
    print(f"\nGuruhlar: {report['groups_summary']}")
    print(f"Hisobotlar: {args.output}, {args.groups_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
