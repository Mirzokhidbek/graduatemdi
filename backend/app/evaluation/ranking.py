"""Termin nomzodlari reytingini baholash: Precision@K va qamrov.

Bu vazifa matndagi spanlarni aniqlashdan alohida baholanadi
(``docs/experiment-methodology.md``, 1-bo'lim).

- Precision@K = (birinchi K nomzod ichida maʼlum terminlar) / K;
  nomzodlar K tadan kam bo'lsa, maxraj — mavjud nomzodlar soni.
- Qamrov (coverage) = (reytingda uchragan maʼlum terminlar) / (barcha maʼlum terminlar).

"Maʼlum termin" ro'yxati to'liq emas: unda yo'q, lekin haqiqiy termin bo'lgan
nomzodlar ham xato deb sanaladi. Shuning uchun lug'atga nisbatan Precision@K —
**pastki chegara**; aniq qiymat uchun nomzodlarni inson baholashi kerak.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

Key = tuple[str, ...]


@dataclass(frozen=True)
class PrecisionAtK:
    k: int
    hits: int
    considered: int

    @property
    def precision(self) -> float | None:
        return self.hits / self.considered if self.considered else None


def precision_at_k(ranked: Sequence[Key], reference: set[Key], k: int) -> PrecisionAtK:
    if k < 1:
        raise ValueError("k kamida 1 bo'lishi kerak")
    top = ranked[:k]
    return PrecisionAtK(k=k, hits=sum(1 for key in top if key in reference), considered=len(top))


def coverage(ranked: Sequence[Key], reference: set[Key]) -> tuple[int, int]:
    """(reytingda topilgan maʼlum terminlar soni, barcha maʼlum terminlar soni)."""
    return len(reference & set(ranked)), len(reference)
