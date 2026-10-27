"""Termin nomzodlarini inson baholashi: shablon, baholarni o'qish, Precision@K, kappa.

Jarayon (``docs/data-annotation-guide.md``, 9-bo'lim):

1. ``template`` — bir nechta usul reytinglarining top-K nomzodlari birlashtiriladi
   (pooling). Ro'yxat **ko'r**: usul, o'rin, ball va lug'at belgisi
   ko'rsatilmaydi, nomzodlar alifbo tartibida. Har biriga korpusdan misol
   kontekst qo'shiladi. Mavjud fayl bo'lsa, baholar saqlanadi va faqat yangi
   nomzodlar qo'shiladi.
2. Baholovchi ``judgment`` ustunini to'ldiradi: ``1`` — termin, ``0`` — termin
   emas, ``?`` — noaniq, bo'sh — hali baholanmagan.
3. ``score`` — har bir reyting uchun Precision@K:
   - qatʼiy: faqat ``1`` termin hisoblanadi;
   - yumshoq: ``1`` va ``?`` termin hisoblanadi;
   top-K ichida baholanmagan nomzod bo'lsa, u termin emas deb sanaladi va
   alohida ko'rsatiladi (natija pastki chegara bo'ladi).
   Ikki va undan ortiq baho fayli berilsa, juft-juft Cohen's kappa
   (faqat ikkala tomon ``0``/``1`` qo'ygan nomzodlar bo'yicha).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from app.evaluation.errors import context_window
from app.nlp.normalize import is_word_end, is_word_start, normalize_text

RELEVANT = "1"
NOT_RELEVANT = "0"
UNSURE = "?"
VALUES = (RELEVANT, NOT_RELEVANT, UNSURE)
COLUMNS = ("candidate", "judgment", "notes", "frequency", "example")
DEFAULT_KS = (10, 20, 50, 100)


class JudgmentError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        details = "\n".join(f"- {p}" for p in problems)
        super().__init__(f"Baholar faylida xatolar:\n{details}")


@dataclass(frozen=True)
class RankedCandidate:
    candidate: str
    top_surface: str
    frequency: int


def load_ranking(path: str | Path) -> list[RankedCandidate]:
    """``app.nlp.candidates --output *.csv`` natijasini o'qiydi (reyting tartibida)."""
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"rank", "candidate", "top_surface", "frequency"} - set(reader.fieldnames or [])
        if missing:
            raise JudgmentError([f"{path}: reyting faylida ustunlar yo'q: {', '.join(sorted(missing))}"])
        rows = sorted(reader, key=lambda row: int(row["rank"]))
    return [RankedCandidate(r["candidate"], r["top_surface"], int(r["frequency"])) for r in rows]


def method_name(path: str | Path) -> str:
    stem = Path(path).stem
    return stem.removeprefix("candidates-")


def build_pool(rankings: Iterable[Sequence[RankedCandidate]], k: int) -> list[RankedCandidate]:
    """Har bir reytingning top-K nomzodlarini birlashtiradi; natija alifbo tartibida."""
    if k < 1:
        raise ValueError("k kamida 1 bo'lishi kerak")
    pool: dict[str, RankedCandidate] = {}
    for ranking in rankings:
        for item in ranking[:k]:
            pool.setdefault(item.candidate, item)
    return [pool[name] for name in sorted(pool)]


def find_example(surface: str, documents: Mapping[str, str]) -> str:
    """``surface`` ning butun so'z sifatida birinchi uchrashini kontekst bilan qaytaradi."""
    for doc_id in sorted(documents):
        text = documents[doc_id]
        normalized = normalize_text(text)
        index = text.find(surface)
        while index != -1:
            end = index + len(surface)
            if is_word_start(normalized, index) and is_word_end(normalized, end):
                return context_window(text, index, end, width=60)
            index = text.find(surface, index + 1)
    return ""


def load_judgments(path: str | Path) -> dict[str, str]:
    """``{nomzod: baho}`` ni qaytaradi; bo'sh baho ``""``. Xatolar qator raqami bilan."""
    path = Path(path)
    problems: list[str] = []
    judgments: dict[str, str] = {}
    try:
        handle = path.open(encoding="utf-8-sig", newline="")
    except FileNotFoundError:
        raise JudgmentError([f"{path}: fayl topilmadi"]) from None
    with handle:
        reader = csv.DictReader(handle)
        missing = {"candidate", "judgment"} - set(reader.fieldnames or [])
        if missing:
            raise JudgmentError([f"{path}: ustunlar yo'q: {', '.join(sorted(missing))}"])
        for line, row in enumerate(reader, start=2):
            candidate = (row["candidate"] or "").strip()
            value = (row["judgment"] or "").strip()
            if not candidate:
                problems.append(f"{path}:{line}: 'candidate' bo'sh")
                continue
            if value and value not in VALUES:
                problems.append(f"{path}:{line}: '{candidate}' uchun noto'g'ri baho {value!r} (1, 0, ? yoki bo'sh)")
            if candidate in judgments:
                problems.append(f"{path}:{line}: '{candidate}' takrorlangan")
            judgments[candidate] = value
    if problems:
        raise JudgmentError(problems)
    return judgments


def write_template(
    path: str | Path,
    pool: Sequence[RankedCandidate],
    documents: Mapping[str, str],
) -> tuple[int, int]:
    """Shablonni yozadi. Mavjud fayldagi baho va izohlar saqlanadi.

    Qaytaradi: (yangi qo'shilgan nomzodlar, saqlangan eski qatorlar).
    """
    path = Path(path)
    existing: dict[str, dict[str, str]] = {}
    if path.exists():
        load_judgments(path)  # formatni tekshirish
        with path.open(encoding="utf-8-sig", newline="") as handle:
            existing = {row["candidate"].strip(): row for row in csv.DictReader(handle)}

    rows: dict[str, dict[str, str]] = {}
    for item in pool:
        old = existing.get(item.candidate, {})
        rows[item.candidate] = {
            "candidate": item.candidate,
            "judgment": (old.get("judgment") or "").strip(),
            "notes": old.get("notes") or "",
            "frequency": str(item.frequency),
            "example": old.get("example") or find_example(item.top_surface, documents),
        }
    # Pool'dan chiqib qolgan, lekin baholangan qatorlar ham yo'qolmasin.
    for name, old in existing.items():
        rows.setdefault(name, {column: old.get(column) or "" for column in COLUMNS})

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS))
        writer.writeheader()
        for name in sorted(rows):
            writer.writerow(rows[name])
    added = sum(1 for name in rows if name not in existing)
    return added, len(existing)


@dataclass(frozen=True)
class JudgedPrecision:
    k: int
    considered: int
    relevant: int
    unsure: int
    unjudged: int

    @property
    def strict(self) -> float | None:
        return self.relevant / self.considered if self.considered else None

    @property
    def lenient(self) -> float | None:
        return (self.relevant + self.unsure) / self.considered if self.considered else None


def judged_precision_at_k(ranked: Sequence[str], judgments: Mapping[str, str], k: int) -> JudgedPrecision:
    if k < 1:
        raise ValueError("k kamida 1 bo'lishi kerak")
    top = ranked[:k]
    values = [judgments.get(candidate, "") for candidate in top]
    return JudgedPrecision(
        k=k,
        considered=len(top),
        relevant=values.count(RELEVANT),
        unsure=values.count(UNSURE),
        unjudged=values.count(""),
    )


@dataclass(frozen=True)
class Agreement:
    common: int  # ikkala tomon 0/1 qo'ygan nomzodlar
    agreed: int
    kappa: float | None


def cohen_kappa(first: Mapping[str, str], second: Mapping[str, str]) -> Agreement:
    binary = (RELEVANT, NOT_RELEVANT)
    common = [c for c in first if first[c] in binary and second.get(c) in binary]
    n = len(common)
    if n == 0:
        return Agreement(0, 0, None)
    agreed = sum(1 for c in common if first[c] == second[c])
    p_observed = agreed / n
    p1 = sum(1 for c in common if first[c] == RELEVANT) / n
    p2 = sum(1 for c in common if second[c] == RELEVANT) / n
    p_expected = p1 * p2 + (1 - p1) * (1 - p2)
    kappa = None if p_expected == 1 else (p_observed - p_expected) / (1 - p_expected)
    return Agreement(n, agreed, kappa)


def _fmt(value: float | None, lower_bound: bool = False) -> str:
    if value is None:
        return "—"
    return ("≥" if lower_bound else "") + f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    import argparse
    import itertools
    import sys

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Termin nomzodlarini inson baholashi")
    commands = parser.add_subparsers(dest="command", required=True)

    template = commands.add_parser("template", help="baholash shablonini yaratish yoki yangilash")
    template.add_argument("--rankings", type=Path, nargs="+", required=True, help="reyting CSV fayllari")
    template.add_argument("--k", type=int, default=100, help="har bir reytingdan nechta nomzod olish")
    template.add_argument("--corpus", type=Path, nargs="*", help="misol kontekst uchun matnlar (standart: data/raw/*.txt)")
    template.add_argument("--output", type=Path, required=True, help="baholar CSV fayli")

    score = commands.add_parser("score", help="baholardan Precision@K va kelishuvni hisoblash")
    score.add_argument("--rankings", type=Path, nargs="+", required=True)
    score.add_argument("--judgments", type=Path, nargs="+", required=True)
    score.add_argument("--k", type=int, nargs="+", default=list(DEFAULT_KS))

    args = parser.parse_args(argv)
    try:
        rankings = {method_name(path): load_ranking(path) for path in args.rankings}

        if args.command == "template":
            corpus = args.corpus or sorted((REPO_ROOT / "data" / "raw").glob("*.txt"))
            documents = {path.stem: path.read_text(encoding="utf-8") for path in corpus}
            pool = build_pool(rankings.values(), args.k)
            added, kept = write_template(args.output, pool, documents)
            print(f"{args.output}: {len(pool)} nomzod pool'da ({', '.join(rankings)} reytinglaridan top-{args.k}); "
                  f"yangi qo'shildi: {added}, avvalgi qatorlar saqlandi: {kept}")
            return 0

        judgments = {path.stem: load_judgments(path) for path in args.judgments}
    except (JudgmentError, ValueError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1

    for judge, values in judgments.items():
        judged = sum(1 for v in values.values() if v)
        print(f"\nBaholovchi fayli: {judge} ({judged}/{len(values)} baholangan)")
        print(f"  {'usul':<10} {'K':>4} {'qatʼiy':>8} {'yumshoq':>8}   termin / ? / baholanmagan")
        for method, ranking in rankings.items():
            names = [item.candidate for item in ranking]
            for k in args.k:
                result = judged_precision_at_k(names, values, k)
                partial = result.unjudged > 0
                print(f"  {method:<10} {k:>4} {_fmt(result.strict, partial):>8} {_fmt(result.lenient, partial):>8}   "
                      f"{result.relevant} / {result.unsure} / {result.unjudged}")
        if any(judged_precision_at_k([i.candidate for i in r], values, max(args.k)).unjudged for r in rankings.values()):
            print("  Diqqat: top-K ichida baholanmagan nomzodlar bor — ular termin emas deb sanaldi, "
                  "shuning uchun '≥' bilan belgilangan qiymatlar pastki chegara.")

    for (name_a, a), (name_b, b) in itertools.combinations(judgments.items(), 2):
        agreement = cohen_kappa(a, b)
        print(f"\nKelishuv {name_a} ↔ {name_b}: umumiy {agreement.common}, mos {agreement.agreed}, "
              f"Cohen's kappa = {_fmt(agreement.kappa)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
