"""Lug'at baseline'ini inson belgilagan yozuvlarda baholash.

Misollar (repo ildizidan):
    PYTHONPATH=backend python -m app.evaluation.evaluate data/processed/validation.jsonl
    PYTHONPATH=backend python -m app.evaluation.evaluate data/processed/validation.jsonl \\
        --output reports/baseline-validation.json

Test to'plami (``test.jsonl``) faqat yakuniy baholash uchun ishlatiladi.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from app.dataset.annotation import STATUS_REVIEWED, AnnotatedRecord, validate_files
from app.database.term_store import TermDatabaseError, load_terms
from app.evaluation.errors import CATEGORIES, MISSED, ErrorCase, classify_errors
from app.evaluation.metrics import Scores, Span, exact_scores, partial_scores
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.nlp.normalize import normalize_form

METHOD_NAME = "dictionary_baseline"


@dataclass(frozen=True)
class EvaluationResult:
    records: int
    exact: Scores
    partial: Scores
    exact_matches: int
    term_correct: int  # aniq mosliklar ichida lug'at shakli to'g'ri topilgani
    errors: list[tuple[ErrorCase, str]]  # (xato, yozuv matni)

    @property
    def term_accuracy(self) -> float | None:
        return self.term_correct / self.exact_matches if self.exact_matches else None

    def error_counts(self) -> dict[str, int]:
        counts = Counter(case.category for case, _ in self.errors)
        return {category: counts.get(category, 0) for category in CATEGORIES}

    def missed_in_dictionary(self) -> int:
        return sum(1 for case, _ in self.errors if case.category == MISSED and case.in_dictionary)


def predict(matcher: DictionaryMatcher, text: str) -> list[Span]:
    return [
        Span(match.start, match.end, None if match.ambiguous else match.candidates[0].entry.term)
        for match in matcher.find(text)
    ]


def evaluate_records(records: Sequence[AnnotatedRecord], matcher: DictionaryMatcher) -> EvaluationResult:
    pairs = []
    errors: list[tuple[ErrorCase, str]] = []
    exact_matches = term_correct = 0

    for record in records:
        gold = [Span(s.start, s.end, s.term) for s in record.terms]
        predicted = predict(matcher, record.text)
        pairs.append((gold, predicted))

        predicted_by_key = {(p.start, p.end): p for p in predicted}
        for span in gold:
            hit = predicted_by_key.get((span.start, span.end))
            if hit is not None:
                exact_matches += 1
                if hit.term is not None and normalize_form(hit.term) == normalize_form(span.term):
                    term_correct += 1

        errors.extend(
            (case, record.text)
            for case in classify_errors(record.id, record.text, gold, predicted, matcher.has_form)
        )

    return EvaluationResult(
        records=len(records),
        exact=exact_scores(pairs),
        partial=partial_scores(pairs),
        exact_matches=exact_matches,
        term_correct=term_correct,
        errors=errors,
    )


def result_to_dict(result: EvaluationResult) -> dict[str, Any]:
    return {
        "records": result.records,
        "exact": result.exact.to_dict(),
        "partial": result.partial.to_dict(),
        "term_on_exact_matches": {
            "accuracy": result.term_accuracy,
            "correct": result.term_correct,
            "total": result.exact_matches,
        },
        "errors": {
            "counts": result.error_counts(),
            "missed_in_dictionary": result.missed_in_dictionary(),
            "cases": [case.to_dict(text) for case, text in result.errors],
        },
    }


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def _print_summary(result: EvaluationResult, examples: int) -> None:
    print(f"Yozuvlar: {result.records}")
    print(f"{'mezon':<8} {'precision':>10} {'recall':>10} {'f1':>10}   (to'g'ri/bashorat, to'g'ri/oltin)")
    for name, scores in (("exact", result.exact), ("partial", result.partial)):
        print(
            f"{name:<8} {_fmt(scores.precision):>10} {_fmt(scores.recall):>10} {_fmt(scores.f1):>10}"
            f"   ({scores.correct_predicted}/{scores.predicted}, {scores.correct_gold}/{scores.gold})"
        )
    print(
        f"Aniq mosliklarda lug'at shakli to'g'ri: {_fmt(result.term_accuracy)} "
        f"({result.term_correct}/{result.exact_matches})"
    )

    counts = result.error_counts()
    print("\nXatolar: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    if counts[MISSED]:
        print(
            f"  topilmaganlardan {result.missed_in_dictionary()} tasi lug'atda bor "
            "(morfologiya yoki yozilish sababli topilmagan)"
        )
    if examples > 0:
        for category in CATEGORIES:
            cases = [(c, t) for c, t in result.errors if c.category == category][:examples]
            if cases:
                print(f"\n[{category}]")
                for case, _ in cases:
                    print(f"  {case.record_id}: {case.context}")


def main(argv: list[str] | None = None) -> int:
    from app.cli import _default_terms_path

    parser = argparse.ArgumentParser(description="Lug'at baseline'ini belgilangan yozuvlarda baholash")
    parser.add_argument("files", nargs="+", type=Path, help="JSONL fayllar (masalan, data/processed/validation.jsonl)")
    parser.add_argument("--terms", type=Path, default=None, help="terminlar bazasi (standart: data/terms.json)")
    parser.add_argument("--include-drafts", action="store_true", help="'draft' yozuvlarni ham baholash")
    parser.add_argument("--output", type=Path, help="JSON hisobot fayli")
    parser.add_argument("--examples", type=int, default=5, help="har bir xato toifasidan nechta misol ko'rsatish")
    args = parser.parse_args(argv)

    terms_path = args.terms or _default_terms_path()
    try:
        entries = load_terms(terms_path)
    except TermDatabaseError as exc:
        print(exc, file=sys.stderr)
        return 1

    report = validate_files(args.files)
    if not report.ok:
        print(f"Annotatsiyada xatolar ({len(report.errors)}):", file=sys.stderr)
        for issue in report.errors:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    if any(path.stem == "test" for path in args.files):
        print("Diqqat: test to'plami baholanmoqda. Undan faqat yakuniy natija uchun foydalaning, sozlash uchun emas.\n")

    records = [r for r in report.records if args.include_drafts or r.status == STATUS_REVIEWED]
    skipped = len(report.records) - len(records)
    if skipped:
        print(f"'draft' holatidagi {skipped} ta yozuv baholanmadi (--include-drafts bilan qo'shish mumkin).")
    if not records:
        print("Baholash uchun yozuv yo'q.")
        return 0

    result = evaluate_records(records, DictionaryMatcher(entries))
    _print_summary(result, args.examples)

    if args.output is not None:
        payload = {
            "method": METHOD_NAME,
            "terms_file": str(terms_path),
            "terms_count": len(entries),
            "files": [str(path) for path in args.files],
            "include_drafts": args.include_drafts,
            "skipped_drafts": skipped,
            **result_to_dict(result),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nHisobot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
