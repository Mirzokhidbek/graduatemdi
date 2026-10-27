"""Annotatsiya fayllarini tekshirish.

Misollar (repo ildizidan):
    PYTHONPATH=backend python -m app.dataset.validate
    PYTHONPATH=backend python -m app.dataset.validate data/annotated/fayl.jsonl
    PYTHONPATH=backend python -m app.dataset.validate \\
        docs/examples/annotation.example.jsonl --sources docs/examples/sources.example.json

Xato bo'lsa, chiqish kodi 1 bo'ladi. Ogohlantirishlar chiqish kodiga taʼsir qilmaydi.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from app.dataset.annotation import validate_files
from app.dataset.sources import SourceRegistryError, load_sources

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ANNOTATED_DIR = REPO_ROOT / "data" / "annotated"
DEFAULT_SOURCES = REPO_ROOT / "data" / "sources.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UzTerm AI annotatsiya fayllarini tekshirish")
    parser.add_argument(
        "files", nargs="*", type=Path, help="JSONL fayllar (standart: data/annotated/*.jsonl)"
    )
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="manbalar reyestri")
    args = parser.parse_args(argv)

    try:
        sources = load_sources(args.sources)
    except SourceRegistryError as exc:
        print(exc, file=sys.stderr)
        return 1

    files = args.files or sorted(DEFAULT_ANNOTATED_DIR.glob("*.jsonl"))
    if not files:
        print(f"Annotatsiya fayllari topilmadi: {DEFAULT_ANNOTATED_DIR}/*.jsonl")
        return 0

    report = validate_files(files, {source.id for source in sources})

    statuses = Counter(record.status for record in report.records)
    labels = Counter(span.label for record in report.records for span in record.terms)
    print(f"Fayllar: {len(files)}")
    print(
        f"Yaroqli yozuvlar: {len(report.records)} "
        f"(reviewed: {statuses['reviewed']}, draft: {statuses['draft']})"
    )
    print(f"Manbalar (doc_id): {len({record.doc_id for record in report.records})}")
    print("Spanlar: " + (", ".join(f"{k}={v}" for k, v in sorted(labels.items())) or "0"))

    if report.warnings:
        print(f"\nOgohlantirishlar ({len(report.warnings)}):")
        for issue in report.warnings:
            print(f"  - {issue}")
    if report.errors:
        print(f"\nXatolar ({len(report.errors)}):", file=sys.stderr)
        for issue in report.errors:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    print("\nXato topilmadi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
