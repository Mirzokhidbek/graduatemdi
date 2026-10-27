"""Matn manbalari reyestri (data/sources.json).

Datasetdagi har bir yozuv shu reyestrdagi manbaga bog'lanadi. Foydalanish
huquqi (``rights``) majburiy: huquqi nomaʼlum matn datasetga kiritilmaydi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_KNOWN_FIELDS = frozenset(
    {"id", "title", "author", "publication", "year", "url", "rights", "notes"}
)
_REQUIRED_TEXT_FIELDS = ("id", "title", "rights")
_OPTIONAL_TEXT_FIELDS = ("author", "publication", "url", "notes")


@dataclass(frozen=True)
class SourceDocument:
    id: str
    title: str
    author: str | None
    publication: str | None
    year: int | None
    url: str | None
    rights: str
    notes: str | None


class SourceRegistryError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        details = "\n".join(f"- {p}" for p in problems)
        super().__init__(f"Manbalar reyestrida xatolar topildi:\n{details}")


def parse_sources(raw: Any) -> list[SourceDocument]:
    if not isinstance(raw, list):
        raise SourceRegistryError(["Reyestr JSON massiv (ro'yxat) bo'lishi kerak"])

    problems: list[str] = []
    sources: list[SourceDocument] = []
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

        values: dict[str, Any] = {}
        for key in _REQUIRED_TEXT_FIELDS:
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                item_problems.append(f"'{key}' majburiy va bo'sh bo'lmagan matn bo'lishi kerak")
                values[key] = None
            else:
                values[key] = value.strip()
        for key in _OPTIONAL_TEXT_FIELDS:
            value = item.get(key)
            if isinstance(value, str):
                values[key] = value.strip() or None
            else:
                if value is not None:
                    item_problems.append(f"'{key}' matn yoki null bo'lishi kerak")
                values[key] = None

        year = item.get("year")
        if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
            item_problems.append("'year' butun son yoki null bo'lishi kerak")
            year = None

        source_id = values["id"]
        if source_id is not None:
            where = f"#{index} ({source_id})"
            if source_id in seen_ids:
                item_problems.append(f"'id' takrorlangan: {source_id}")
            seen_ids.add(source_id)

        if item_problems:
            problems.extend(f"{where}: {p}" for p in item_problems)
            continue
        sources.append(SourceDocument(year=year, **values))

    if problems:
        raise SourceRegistryError(problems)
    return sources


def load_sources(path: str | Path) -> list[SourceDocument]:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SourceRegistryError([f"{path}: fayl topilmadi"]) from None
    except json.JSONDecodeError as exc:
        raise SourceRegistryError([f"{path}: JSON xatosi: {exc}"]) from None
    return parse_sources(raw)
