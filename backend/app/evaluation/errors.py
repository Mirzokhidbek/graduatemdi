"""Xato tahlili: har bir xatoni toifaga ajratish va misol bilan saqlash.

Toifalar:
- ``missed`` — oltin span, unga hech qanday bashorat tegmagan
  (``in_dictionary`` — lug'at shakli bazada bormi);
- ``false_positive`` — bashorat, hech qanday oltin spanga tegmagan;
- ``boundary`` — bashorat oltin span bilan kesishadi, lekin chegaralari boshqa;
- ``term_mismatch`` — span aynan to'g'ri, lekin lug'at shakli boshqa;
- ``ambiguous`` — span aynan to'g'ri, lekin bashorat bir nechta yozuvga mos
  kelgani uchun lug'at shakli tanlanmagan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from app.evaluation.metrics import Span
from app.nlp.normalize import normalize_form

MISSED = "missed"
FALSE_POSITIVE = "false_positive"
BOUNDARY = "boundary"
TERM_MISMATCH = "term_mismatch"
AMBIGUOUS = "ambiguous"
CATEGORIES = (MISSED, FALSE_POSITIVE, BOUNDARY, TERM_MISMATCH, AMBIGUOUS)

CONTEXT_CHARS = 40


@dataclass(frozen=True)
class ErrorCase:
    category: str
    record_id: str
    gold: Span | None
    predicted: Span | None
    context: str
    in_dictionary: bool | None = None  # faqat ``missed`` uchun

    def to_dict(self, text: str) -> dict[str, Any]:
        def span_dict(span: Span | None) -> dict[str, Any] | None:
            if span is None:
                return None
            return {"start": span.start, "end": span.end, "surface": text[span.start : span.end], "term": span.term}

        result = {
            "category": self.category,
            "record_id": self.record_id,
            "gold": span_dict(self.gold),
            "predicted": span_dict(self.predicted),
            "context": self.context,
        }
        if self.in_dictionary is not None:
            result["in_dictionary"] = self.in_dictionary
        return result


def context_window(text: str, start: int, end: int, width: int = CONTEXT_CHARS) -> str:
    """Spanni ``⟦ ⟧`` ichida ko'rsatuvchi qisqa kontekst (qator tashlashlar probelga)."""
    left = max(0, start - width)
    right = min(len(text), end + width)
    snippet = (
        ("…" if left > 0 else "")
        + text[left:start]
        + "⟦"
        + text[start:end]
        + "⟧"
        + text[end:right]
        + ("…" if right < len(text) else "")
    )
    return " ".join(snippet.split())


def classify_errors(
    record_id: str,
    text: str,
    gold_spans: Sequence[Span],
    predicted_spans: Sequence[Span],
    in_dictionary: Callable[[str], bool],
) -> list[ErrorCase]:
    errors: list[ErrorCase] = []
    # Oltin spanlar ustma-ust tushmaydi (validator kafolatlaydi).
    predicted_by_key = {(p.start, p.end): p for p in predicted_spans}

    for gold in gold_spans:
        exact = predicted_by_key.get((gold.start, gold.end))
        if exact is not None:
            if exact.term is None:
                errors.append(
                    ErrorCase(AMBIGUOUS, record_id, gold, exact, context_window(text, gold.start, gold.end))
                )
            elif gold.term is not None and normalize_form(exact.term) != normalize_form(gold.term):
                errors.append(
                    ErrorCase(TERM_MISMATCH, record_id, gold, exact, context_window(text, gold.start, gold.end))
                )
            continue

        overlapping = [p for p in predicted_spans if p.overlaps(gold)]
        if not overlapping:
            errors.append(
                ErrorCase(
                    MISSED,
                    record_id,
                    gold,
                    None,
                    context_window(text, gold.start, gold.end),
                    in_dictionary=gold.term is not None and in_dictionary(gold.term),
                )
            )
        for predicted in overlapping:
            left = min(gold.start, predicted.start)
            right = max(gold.end, predicted.end)
            errors.append(ErrorCase(BOUNDARY, record_id, gold, predicted, context_window(text, left, right)))

    for predicted in predicted_spans:
        if not any(predicted.overlaps(g) for g in gold_spans):
            errors.append(
                ErrorCase(
                    FALSE_POSITIVE,
                    record_id,
                    None,
                    predicted,
                    context_window(text, predicted.start, predicted.end),
                )
            )

    return sorted(errors, key=lambda e: (e.gold or e.predicted).start)
