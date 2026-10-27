"""Termin aniqlash sifatini o'lchash: Precision, Recall, F1.

Ikki mezon hisoblanadi (micro-average, ya'ni barcha yozuvlar spanlari birga):

- **exact** — bashorat qilingan ``[start, end)`` inson belgilagan span bilan
  aynan bir xil bo'lsa, to'g'ri hisoblanadi. Asosiy mezon.
- **partial** — kamida bitta belgi ustma-ust tushsa yetarli. Precision uchun
  oltin spanga tegadigan bashoratlar, Recall uchun esa bashorat tekkan oltin
  spanlar sanaladi. Bu yordamchi mezon: chegara xatolari qanchalik ko'p
  ekanini ko'rsatadi.

Maxraj 0 bo'lsa (masalan, bashorat yo'q), ko'rsatkich ``None`` bo'ladi —
0 yoki 1 deb to'qib qo'yilmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    term: str | None = None  # lug'at shakli; noaniq bashoratda None

    def overlaps(self, other: "Span") -> bool:
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class Scores:
    correct_predicted: int  # Precision surati
    predicted: int
    correct_gold: int  # Recall surati
    gold: int

    @property
    def precision(self) -> float | None:
        return self.correct_predicted / self.predicted if self.predicted else None

    @property
    def recall(self) -> float | None:
        return self.correct_gold / self.gold if self.gold else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None:
            return None
        return 0.0 if p + r == 0 else 2 * p * r / (p + r)

    def to_dict(self) -> dict[str, float | int | None]:
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "correct_predicted": self.correct_predicted,
            "predicted": self.predicted,
            "correct_gold": self.correct_gold,
            "gold": self.gold,
        }


Pair = tuple[Sequence[Span], Sequence[Span]]  # (oltin, bashorat) bitta yozuv uchun


def exact_scores(pairs: Iterable[Pair]) -> Scores:
    correct = predicted = gold = 0
    for gold_spans, predicted_spans in pairs:
        gold_keys = {(s.start, s.end) for s in gold_spans}
        predicted_keys = {(s.start, s.end) for s in predicted_spans}
        correct += len(gold_keys & predicted_keys)
        predicted += len(predicted_keys)
        gold += len(gold_keys)
    return Scores(correct, predicted, correct, gold)


def partial_scores(pairs: Iterable[Pair]) -> Scores:
    correct_predicted = correct_gold = predicted = gold = 0
    for gold_spans, predicted_spans in pairs:
        correct_predicted += sum(any(p.overlaps(g) for g in gold_spans) for p in predicted_spans)
        correct_gold += sum(any(g.overlaps(p) for p in predicted_spans) for g in gold_spans)
        predicted += len(predicted_spans)
        gold += len(gold_spans)
    return Scores(correct_predicted, predicted, correct_gold, gold)
