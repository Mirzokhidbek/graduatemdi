"""Meʼyor tekshiruvchisini baholash (3.2-bo'lim, 3.5–3.6-jadvallar).

Inson tomonidan belgilangan "meʼyorga zid terminlar" to'plami hali yo'q. Shuning uchun
imlo va lug'at shakli qoidalari **sintetik buzilishlar** bilan baholanadi:
bazadagi har bir termin (to'g'ri shakl deb olinadi) bitta turdagi xato bilan buziladi
va quyidagilar o'lchanadi:

- **aniqlash** (recall): tekshiruvchi kutilgan qoidani ``warning``/``error`` bilan belgiladimi;
- **tuzatish**: taklif qilingan shakl asl terminga tengmi;
- **yolg'on signal**: buzilmagan terminlarda imlo/shakl qoidalari ogohlantirish berish ulushi.

ISO 704 tamoyillari (bir maʼnolilik, sinonimsizlik, tizimlilik) bo'yicha natijalar
ekspert bahosi bilan solishtiriladi: ``data/judgments/term-check-review.csv``
(tasodifiy 100 ta termin, ``expert`` ustuni to'ldirilgach — Cohen's kappa).

    PYTHONPATH=backend python -m app.norms.experiment
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Callable

from app.database.term_store import load_terms
from app.nlp.normalize import normalize_form
from app.nlp.tokenize import tokenize
from app.norms.checker import ERROR, WARNING, TermChecker
from app.variation.experiment import to_cyrillic

_LOOKALIKE = {"a": "а", "o": "о", "e": "е", "p": "р", "x": "х", "y": "у"}


def _mixed(term: str) -> str | None:
    for i, ch in enumerate(term):
        if ch in _LOOKALIKE:
            return term[:i] + _LOOKALIKE[ch] + term[i + 1 :]
    return None


def _apostrophe(term: str) -> str | None:
    return term.replace("ʻ", "'").replace("ʼ", "'") if ("ʻ" in term or "ʼ" in term) else None


def _plural_case(term: str) -> str | None:
    if " " in term or not term[-1:].isalpha():
        return None
    return term + "larning"


def _locative(term: str) -> str | None:
    if " " in term or not term[-1:].isalpha():
        return None
    return term + "da"


def _capital(term: str) -> str | None:
    return term[:1].upper() + term[1:] if term[:1].islower() else None


def _spacing(term: str) -> str | None:
    if "-" in term:
        return term.replace("-", " - ", 1)
    return term.replace(" ", "  ", 1) if " " in term else None


CORRUPTIONS: dict[str, tuple[Callable[[str], str | None], str]] = {
    "kirill yozuvi": (to_cyrillic, "script"),
    "aralash yozuv": (_mixed, "script"),
    "norasmiy apostrof": (_apostrophe, "apostrophe"),
    "ko'plik + qaratqich (-larning)": (_plural_case, "dictionary_form"),
    "o'rin-payt (-da)": (_locative, "dictionary_form"),
    "bosh harf": (_capital, "lowercase"),
    "ortiqcha bo'shliq": (_spacing, "spacing"),
}
FORM_RULES = ("script", "alphabet", "apostrophe", "ts_rule", "spacing", "dictionary_form")


def run(terms_path: Path, raw_dir: Path) -> dict:
    entries = load_terms(terms_path)
    vocabulary = [t.norm for p in sorted(raw_dir.glob("*.txt")) for t in tokenize(p.read_text(encoding="utf-8"))]
    checker = TermChecker(entries, vocabulary)
    clean_terms = [e.term for e in entries]

    false_alarm = defaultdict(int)
    for term in clean_terms:
        for f in checker.check(term).findings:
            if f.rule in FORM_RULES and f.severity in (WARNING, ERROR):
                false_alarm[f.rule] += 1

    corruption = {}
    for name, (corrupt, rule) in CORRUPTIONS.items():
        total = detected = corrected = 0
        misses = []
        for term in clean_terms:
            broken = corrupt(term)
            if not broken or broken == term:
                continue
            total += 1
            result = checker.check(broken)
            hit = any(f.rule == rule and f.severity != "ok" for f in result.findings)
            detected += hit
            fixed = result.suggestion
            ok = fixed is not None and normalize_form(fixed) == normalize_form(term)
            corrected += ok
            if not ok and len(misses) < 5:
                misses.append({"term": term, "corrupted": broken, "suggestion": fixed})
        corruption[name] = {
            "rule": rule,
            "items": total,
            "detected": detected / total if total else None,
            "corrected": corrected / total if total else None,
            "examples_not_corrected": misses,
        }
    return {
        "terms": len(clean_terms),
        "clean_false_alarm_rate": sum(false_alarm.values()) / len(clean_terms),
        "clean_false_alarms_by_rule": dict(false_alarm),
        "corruption": corruption,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Meʼyor tekshiruvchisini sintetik xatolar bilan baholash")
    parser.add_argument("--terms", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports" / "term-check-synthetic.json")
    args = parser.parse_args(argv)

    report = run(args.terms, args.raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Terminlar: {report['terms']}; toza terminlarda yolg'on signal: {report['clean_false_alarm_rate']:.3f} "
          f"{report['clean_false_alarms_by_rule']}")
    print(f"\n{'buzilish':<32} {'qoida':<16} {'soni':>5} {'aniqlandi':>10} {'tuzatildi':>10}")
    for name, r in report["corruption"].items():
        print(f"{name:<32} {r['rule']:<16} {r['items']:>5} {r['detected']:>10.3f} {r['corrected']:>10.3f}")
    print(f"\nHisobot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
