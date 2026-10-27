"""Ilova sozlamalari (muhit o'zgaruvchilaridan; namunasi ``.env.example`` da)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAX_TEXT_CHARS = 20_000


def _resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


@dataclass(frozen=True)
class Settings:
    terms_path: Path
    max_text_chars: int

    @classmethod
    def from_env(cls) -> "Settings":
        raw_limit = os.environ.get("UZTERM_MAX_TEXT_CHARS", str(DEFAULT_MAX_TEXT_CHARS))
        try:
            max_text_chars = int(raw_limit)
        except ValueError:
            raise ValueError(f"UZTERM_MAX_TEXT_CHARS butun son bo'lishi kerak: {raw_limit!r}") from None
        if max_text_chars < 1:
            raise ValueError("UZTERM_MAX_TEXT_CHARS musbat bo'lishi kerak")
        return cls(
            terms_path=_resolve(os.environ.get("UZTERM_TERMS_PATH", "data/terms.json")),
            max_text_chars=max_text_chars,
        )
