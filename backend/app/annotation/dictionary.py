"""Lug'atni (``data/terms.json``) annotatsiyadagi terminlar bilan to'ldirish — faqat **train** to'plamidan.

Metodika (``docs/experiment-methodology.md``, 2-bo'lim): lug'at test to'plamidagi
terminlar asosida to'ldirilmaydi, aks holda lug'at baseline'i sunʼiy yuqori natija
beradi. Shu sababli faqat manifestda ``train`` deb belgilangan manbalarning
annotatsiyalari olinadi. Qo'shilgan yozuvlar ``status: "needs_review"`` va manbasi
ko'rsatilgan holda yoziladi; taʼrif bo'sh qoladi (uni inson yozadi).

    PYTHONPATH=backend python -m app.annotation.dictionary --annotator claude [--dry-run]
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.annotation.workspace import check_annotator
from app.database.term_store import parse_terms
from app.dataset.annotation import load_annotations
from app.dataset.split import TRAIN, load_manifest
from app.nlp.normalize import normalize_form

# Ko'p maʼnoli so'zlar lug'atga qo'shilmaydi: lug'at aniqlagichi kontekstni bilmaydi va ular
# umumiy maʼnoda juda ko'p uchraydi ("sifatida", "ega boʻladi", "gap", "son", "lugʻat").
# Bunday so'zlarni kontekstga qarab ajratish modelning (CRF) vazifasi. Loyiha rejasidagi
# dastlabki qaror bilan bir xil (docs/project-plan.md, 1-bosqich cheklovlari, 5-band).
AMBIGUOUS = frozenset(
    normalize_form(word)
    for word in (
        "ot", "sifat", "son", "ega", "hol", "gap", "kesim", "zamon", "nisbat", "mayl", "daraja",
        "kategoriya", "harf", "matn", "lugʻat", "asos", "period", "ovoz", "shovqin", "uslub",
        "birlik", "ism", "qoʻshimcha", "ravish", "undov", "ibora", "atama", "termin", "segment",
    )
)


def train_terms(annotations_dir: Path, manifest_path: Path, annotator: str) -> Counter:
    assignments, _ = load_manifest(manifest_path)
    counts: Counter = Counter()
    for path in sorted((annotations_dir / check_annotator(annotator)).glob("*.jsonl")):
        if assignments.get(path.stem) != TRAIN:
            continue
        for record in load_annotations([path]):
            counts.update(span.term for span in record.terms)
    return counts


def merge(entries: list[dict[str, Any]], terms: Counter, source: str, min_count: int = 1) -> list[dict[str, Any]]:
    """Mavjud yozuvlarga yangi terminlarni qo'shadi (lug'atdagi biror shakl bilan mos kelsa — qo'shilmaydi)."""
    known = set()
    for entry in entries:
        for form in (entry["term"], *entry.get("variants", []), *entry.get("synonyms", [])):
            known.add(normalize_form(form))
    numbers = [int(e["id"].rsplit("-", 1)[-1]) for e in entries if e["id"].rsplit("-", 1)[-1].isdigit()]
    next_number = max(numbers, default=0) + 1
    added = []
    for term, count in sorted(terms.items(), key=lambda item: (-item[1], item[0])):
        if count < min_count or normalize_form(term) in known or normalize_form(term) in AMBIGUOUS:
            continue
        known.add(normalize_form(term))
        added.append(
            {
                "id": f"term-{next_number:04d}",
                "term": term,
                "definition": None,
                "domain": None,
                "variants": [],
                "synonyms": [],
                "preferred_form": term,
                "status": "needs_review",
                "source": source,
            }
        )
        next_number += 1
    return entries + added


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Lug'atni train to'plamidagi annotatsiya terminlari bilan to'ldirish")
    parser.add_argument("--annotator", default="claude")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--min-count", type=int, default=1, help="kamida necha marta belgilangan bo'lsin")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    terms_path = args.data_dir / "terms.json"
    try:
        entries = json.loads(terms_path.read_text(encoding="utf-8"))
        counts = train_terms(args.data_dir / "annotations", args.data_dir / "splits" / "manifest.json", args.annotator)
        source = (
            f"AI annotatsiyasi ({args.annotator}), train to'plami; inson tekshirmagan"
            if args.annotator == "claude"
            else f"annotator {args.annotator}, train to'plami"
        )
        merged = merge(entries, counts, source, args.min_count)
        parse_terms(merged)  # formatni tekshirish
    except (ValueError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"train terminlari: {len(counts)}, lug'atda bor edi: {len(entries)}, qo'shiladi: {len(merged) - len(entries)}")
    if not args.dry_run:
        terms_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Yozildi: {terms_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
