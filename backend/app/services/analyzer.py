"""Matn tahlili: termin aniqlash natijalarini eksport qilinadigan ko'rinishga keltirish."""

from __future__ import annotations

from typing import Any

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
    }


def analyze_text(text: str, matcher: DictionaryMatcher) -> list[dict[str, Any]]:
    return [match_to_dict(match) for match in matcher.find(text)]
