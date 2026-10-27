"""Buyruq satri orqali matn tahlili.

Misollar (repo ildizidan):
    PYTHONPATH=backend python -m app.cli "Fonema va morfologiya haqida."
    PYTHONPATH=backend python -m app.cli --file matn.txt
    echo "Qoʻshma gaplar" | PYTHONPATH=backend python -m app.cli
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from app.database.term_store import TermDatabaseError, load_terms
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.services.analyzer import analyze_text

REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_terms_path() -> Path:
    path = Path(os.environ.get("UZTERM_TERMS_PATH", "data/terms.json"))
    return path if path.is_absolute() else REPO_ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UzTerm AI: lug'atga asoslangan termin aniqlash")
    parser.add_argument("text", nargs="?", help="tahlil qilinadigan matn")
    parser.add_argument("--file", type=Path, help="matn fayli (UTF-8)")
    parser.add_argument("--terms", type=Path, default=None, help="terminlar bazasi (JSON)")
    args = parser.parse_args(argv)

    if args.file is not None:
        text = args.file.read_text(encoding="utf-8")
    elif args.text is not None:
        text = args.text
    else:
        text = sys.stdin.read()

    try:
        entries = load_terms(args.terms or _default_terms_path())
    except TermDatabaseError as exc:
        print(exc, file=sys.stderr)
        return 1

    results = analyze_text(text, DictionaryMatcher(entries))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
