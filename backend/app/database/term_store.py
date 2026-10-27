"""Terminologik bazani (data/terms.json) yuklash va tekshirish.

Baza qatʼiy tekshiriladi: bitta yozuvda xato bo'lsa ham butun baza
yuklanmaydi va barcha topilgan muammolar bitta xatoda qaytariladi.
Bu noto'g'ri maʼlumotning jimgina tahlilga kirib ketishining oldini oladi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STATUS_APPROVED = "approved"
STATUS_NEEDS_REVIEW = "needs_review"
ALLOWED_STATUSES = (STATUS_APPROVED, STATUS_NEEDS_REVIEW)

_KNOWN_FIELDS = frozenset(
    {
        "id",
        "term",
        "definition",
        "domain",
        "variants",
        "synonyms",
        "preferred_form",
        "status",
        "source",
    }
)


@dataclass(frozen=True)
class TermEntry:
    id: str
    term: str
    definition: str | None
    domain: str | None
    variants: tuple[str, ...]
    synonyms: tuple[str, ...]
    preferred_form: str | None
    status: str
    source: str | None


class TermDatabaseError(ValueError):
    """Terminlar bazasi noto'g'ri formatda bo'lganda ko'tariladi."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        details = "\n".join(f"- {p}" for p in problems)
        super().__init__(f"Terminlar bazasida xatolar topildi:\n{details}")


def _is_valid_form(value: str) -> bool:
    return any(ch.isalnum() for ch in value)


def _required_form(item: dict[str, Any], key: str, problems: list[str]) -> str | None:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        problems.append(f"'{key}' majburiy va bo'sh bo'lmagan matn bo'lishi kerak")
        return None
    value = value.strip()
    if key != "id" and not _is_valid_form(value):
        problems.append(f"'{key}' kamida bitta harf yoki raqamdan iborat bo'lishi kerak")
        return None
    return value


def _optional_str(item: dict[str, Any], key: str, problems: list[str]) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        problems.append(f"'{key}' matn yoki null bo'lishi kerak")
        return None
    return value.strip() or None


def _form_list(item: dict[str, Any], key: str, problems: list[str]) -> tuple[str, ...]:
    value = item.get(key, [])
    if not isinstance(value, list):
        problems.append(f"'{key}' matnlar ro'yxati bo'lishi kerak")
        return ()
    forms: list[str] = []
    for index, form in enumerate(value):
        if not isinstance(form, str) or not _is_valid_form(form):
            problems.append(f"'{key}[{index}]' bo'sh bo'lmagan matn bo'lishi kerak")
            continue
        form = form.strip()
        if form not in forms:
            forms.append(form)
    return tuple(forms)


def parse_terms(raw: Any) -> list[TermEntry]:
    """JSON'dan o'qilgan maʼlumotni tekshirib, ``TermEntry`` ro'yxatiga aylantiradi."""
    if not isinstance(raw, list):
        raise TermDatabaseError(["Baza JSON massiv (ro'yxat) bo'lishi kerak"])

    problems: list[str] = []
    entries: list[TermEntry] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(raw):
        where = f"#{index}"
        if not isinstance(item, dict):
            problems.append(f"{where}: yozuv JSON obyekt bo'lishi kerak")
            continue

        item_problems: list[str] = []
        unknown = sorted(set(item) - _KNOWN_FIELDS)
        if unknown:
            item_problems.append(f"nomaʼlum maydon(lar): {', '.join(unknown)}")

        entry_id = _required_form(item, "id", item_problems)
        if entry_id is not None:
            where = f"#{index} ({entry_id})"
            if entry_id in seen_ids:
                item_problems.append(f"'id' takrorlangan: {entry_id}")
            seen_ids.add(entry_id)

        term = _required_form(item, "term", item_problems)
        definition = _optional_str(item, "definition", item_problems)
        domain = _optional_str(item, "domain", item_problems)
        preferred_form = _optional_str(item, "preferred_form", item_problems)
        source = _optional_str(item, "source", item_problems)
        variants = _form_list(item, "variants", item_problems)
        synonyms = _form_list(item, "synonyms", item_problems)

        status = item.get("status", STATUS_NEEDS_REVIEW)
        if status not in ALLOWED_STATUSES:
            item_problems.append(
                f"'status' quyidagilardan biri bo'lishi kerak: {', '.join(ALLOWED_STATUSES)}"
            )
        elif status == STATUS_APPROVED:
            # Tasdiqlangan termin manbasiz bo'lishi mumkin emas.
            if source is None:
                item_problems.append("'approved' holatidagi termin uchun 'source' majburiy")
            if preferred_form is None:
                item_problems.append(
                    "'approved' holatidagi termin uchun 'preferred_form' majburiy"
                )

        if item_problems:
            problems.extend(f"{where}: {p}" for p in item_problems)
            continue

        entries.append(
            TermEntry(
                id=entry_id,
                term=term,
                definition=definition,
                domain=domain,
                variants=variants,
                synonyms=synonyms,
                preferred_form=preferred_form,
                status=status,
                source=source,
            )
        )

    if problems:
        raise TermDatabaseError(problems)
    return entries


def load_terms(path: str | Path) -> list[TermEntry]:
    """JSON fayldan terminlar bazasini yuklaydi."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise TermDatabaseError([f"{path}: fayl topilmadi"]) from None
    except json.JSONDecodeError as exc:
        raise TermDatabaseError([f"{path}: JSON xatosi: {exc}"]) from None
    return parse_terms(raw)
