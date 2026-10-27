"""Oʻzbek lotin matni uchun sodda tokenizator.

Token — harflar ketma-ketligi; so'z ichidagi apostrof (``so'z``, ``ma'no``)
tokenning bir qismi. Raqamlar va tinish belgilari token emas.
Pozitsiyalar asl matnga nisbatan ``[start, end)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.nlp.normalize import normalize_text

_TOKEN = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")


@dataclass(frozen=True)
class Token:
    start: int
    end: int
    text: str  # asl matndagi ko'rinish
    norm: str  # normallashtirilgan (kichik harf, yagona apostrof)


def tokenize(text: str) -> list[Token]:
    normalized = normalize_text(text)
    return [
        Token(match.start(), match.end(), text[match.start() : match.end()], match.group())
        for match in _TOKEN.finditer(normalized)
    ]


def phrases(text: str) -> list[list[Token]]:
    """Tokenlarni tinish belgisisiz ketma-ketliklarga (iboralarga) ajratadi.

    Ikki qo'shni token orasida faqat bo'shliq bo'lsa, ular bitta iborada.
    Vergul, nuqta, qavs, chiziqcha va h.k. iborani bo'ladi.
    """
    groups: list[list[Token]] = []
    for token in tokenize(text):
        if groups:
            gap = text[groups[-1][-1].end : token.start]
            if gap and gap.isspace():
                groups[-1].append(token)
                continue
        groups.append([token])
    return groups
