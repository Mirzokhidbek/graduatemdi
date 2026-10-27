"""Meʼyoriy shakl bo'yicha tavsiya.

Tizim meʼyoriy shaklni o'zi belgilamaydi. U faqat bazadagi maʼlumotni
ko'rsatadi: termin manbasi bilan tasdiqlangan bo'lsa, "tasdiqlangan",
aks holda "tavsiya — tekshirish kerak" deb belgilanadi.
"""

from __future__ import annotations

from typing import Any

from app.database.term_store import STATUS_APPROVED, TermEntry
from app.nlp.normalize import normalize_form

NORM_APPROVED = "approved"
NORM_NEEDS_REVIEW = "needs_review"
NORM_NO_DATA = "no_data"


def recommend_preferred_form(entry: TermEntry, base_surface: str) -> dict[str, Any]:
    preferred = entry.preferred_form
    if preferred is None:
        return {
            "preferred_form": None,
            "status": NORM_NO_DATA,
            "label": "Bazada meʼyoriy shakl yo'q — tekshirish kerak",
            "surface_matches_preferred": None,
        }

    matches_preferred = normalize_form(base_surface) == normalize_form(preferred)
    if entry.status == STATUS_APPROVED:
        status, label = NORM_APPROVED, f"Tasdiqlangan meʼyoriy shakl (manba: {entry.source})"
    else:
        status, label = NORM_NEEDS_REVIEW, "Tavsiya — tekshirish kerak"
    return {
        "preferred_form": preferred,
        "status": status,
        "label": label,
        "surface_matches_preferred": matches_preferred,
    }
