"""Matn tahlili: termin aniqlash natijalarini eksport qilinadigan ko'rinishga keltirish."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from app.evaluation.metrics import Span

from app.nlp.dictionary_matcher import DictionaryMatcher, TermMatch
from app.services.normalization import NORM_APPROVED, recommend_preferred_form


def match_to_dict(match: TermMatch) -> dict[str, Any]:
    candidates = []
    for candidate in match.candidates:
        entry = candidate.entry
        candidates.append(
            {
                "term_id": entry.id,
                "term": entry.term,
                "matched_form": candidate.matched_form,
                "match_type": candidate.match_type,
                "domain": entry.domain,
                "definition": entry.definition,
                "status": entry.status,
                "source": entry.source,
                "normalization": recommend_preferred_form(entry, match.base_surface),
            }
        )

    review_required = match.ambiguous or any(
        c["normalization"]["status"] != NORM_APPROVED for c in candidates
    )
    return {
        "surface": match.surface,
        "base_surface": match.base_surface,
        "suffix": match.suffix,
        "start": match.start,
        "end": match.end,
        "term": None if match.ambiguous else match.candidates[0].entry.term,
        "method": match.method,
        # Lug'at usuli ehtimollik hisoblamaydi, shuning uchun ishonchlilik yo'q.
        "confidence": None,
        "ambiguous": match.ambiguous,
        "review_required": review_required,
        "candidates": candidates,
        "lemma": None if match.ambiguous else match.candidates[0].entry.term,
        "in_dictionary": True,
        "related_terms": [],
    }


def analyze_text(text: str, matcher: DictionaryMatcher) -> list[dict[str, Any]]:
    return [match_to_dict(match) for match in matcher.find(text)]


def analyze_with_model(
    text: str,
    spans: Iterable[Span],
    matcher: DictionaryMatcher,
    method: str,
    lemma_of: Callable[[str], str],
) -> list[dict[str, Any]]:
    """Model topgan spanlar. Span lug'at mosligi bilan aynan bir xil bo'lsa — lug'at maʼlumoti
    (termin, taʼrif, meʼyoriy shakl) qo'shiladi; aks holda bu **yangi termin nomzodi**: lug'atda
    yo'q, lug'at shakli morfologik tahlil bilan taklif qilinadi va tekshiruv talab qilinadi."""
    dictionary = matcher.find(text)
    exact = {(m.start, m.end): m for m in dictionary}
    result = []
    for span in sorted(spans, key=lambda s: s.start):
        match = exact.get((span.start, span.end))
        if match is not None:
            item = match_to_dict(match)
            item["method"] = method
            result.append(item)
            continue
        surface = text[span.start : span.end]
        related = sorted(
            {m.candidates[0].entry.term for m in dictionary
             if not m.ambiguous and m.start < span.end and span.start < m.end}
        )
        result.append(
            {
                "surface": surface,
                "base_surface": surface,
                "suffix": "",
                "start": span.start,
                "end": span.end,
                "term": None,
                "method": method,
                "confidence": None,
                "ambiguous": False,
                "review_required": True,
                "candidates": [],
                "lemma": lemma_of(surface),
                "in_dictionary": False,
                "related_terms": related,
            }
        )
    return result

