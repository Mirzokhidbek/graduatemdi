"""Lug'atga asoslangan termin aniqlagich (baseline).

Algoritm:
1. Matn va lug'at shakllari ``normalize`` moduli orqali normallashtiriladi
   (registr va apostrof farqlari tenglashtiriladi, uzunlik saqlanadi).
2. Har bir lug'at shakli (termin, variant, sinonim) uchun regex tuziladi:
   so'z chegarasida boshlanadi, ko'p so'zli shakllarda so'zlar orasida
   istalgan bo'shliq (probel, tab, qator tashlash) bo'lishi mumkin,
   oxirgi so'zdan keyin cheklangan qo'shimchalar ro'yxatidan biri kelishi mumkin.
3. Barcha nomzodlar ichidan uzunroq moslik qisqaroq va ustma-ust
   tushadigan moslikdan ustun qo'yiladi.

Cheklovlar ``docs/project-plan.md`` faylida hujjatlashtirilgan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.database.term_store import TermEntry
from app.nlp.normalize import normalize_form, normalize_text

METHOD_EXACT = "dictionary_exact"
METHOD_INFLECTED = "dictionary_inflected"

MATCH_TERM = "term"
MATCH_VARIANT = "variant"
MATCH_SYNONYM = "synonym"


def _alternatives(options: Iterable[str]) -> str:
    # Uzunroq variant birinchi tursin, aks holda "da" "dan"dan oldin ushlanadi.
    ordered = sorted(options, key=len, reverse=True)
    return "(?:" + "|".join(re.escape(option) for option in ordered) + ")?"


# Ot so'z turkumiga qo'shiladigan eng ko'p uchraydigan qo'shimchalar
# (ko'plik + egalik + kelishik + -dagi/-ki + yuklama tartibida).
# Bu to'liq morfologik tahlil emas. Unli bilan boshlanuvchi egalik qo'shimchasi
# oldidagi eng ko'p uchraydigan tovush o'zgarishlari ``stem_alternations`` da.
PLURAL_SUFFIXES = ("lar",)
POSSESSIVE_SUFFIXES = ("imiz", "ingiz", "miz", "ngiz", "ing", "im", "ng", "m", "si", "i")
CASE_SUFFIXES = ("gacha", "dagi", "ning", "dan", "ni", "ga", "ka", "qa", "da")
ATTRIBUTIVE_SUFFIXES = ("ki",)
PARTICLE_SUFFIXES = ("dir", "dek", "mi")

SUFFIX_PATTERN = "".join(
    _alternatives(group)
    for group in (
        PLURAL_SUFFIXES,
        POSSESSIVE_SUFFIXES,
        CASE_SUFFIXES,
        ATTRIBUTIVE_SUFFIXES,
        PARTICLE_SUFFIXES,
    )
)

# unli bilan boshlanadigan egalik qo'shimchalari: tovush o'zgargan o'zakdan keyin faqat shular keladi
VOWEL_POSSESSIVE_SUFFIXES = ("imiz", "ingiz", "ing", "im", "i")
_AFTER_POSSESSIVE = "".join(
    _alternatives(group) for group in (CASE_SUFFIXES, ATTRIBUTIVE_SUFFIXES, PARTICLE_SUFFIXES)
)
ALTERED_SUFFIX_PATTERN = (
    "(?:" + "|".join(re.escape(s) for s in sorted(VOWEL_POSSESSIVE_SUFFIXES, key=len, reverse=True)) + ")"
    + _AFTER_POSSESSIVE
)

# o'rin -> o'rni, burun -> burni: oxirgi bo'g'indagi tor unli tushadi
_ELISION = re.compile(r"^(?P<head>.*[^aeiou'])(?P<vowel>[iu])(?P<tail>[^aeiou' ])$")


def stem_alternations(word: str) -> list[str]:
    """Unli bilan boshlanuvchi egalik qo'shimchasi oldida o'zgargan o'zaklar (normallashgan shaklda).

    - jarangsizlanish: ``k -> g`` (yurak -> yuragi, kelishik -> kelishigi),
      ``q -> g'`` (qishloq -> qishlog'i);
    - tor unli tushishi: ``o'rin -> o'rni``, ``burun -> burni``.

    Bu hodisalar leksik: har bir so'zda bo'lavermaydi. Lekin o'zgargan o'zak faqat
    ``-i/-im/-ing/...`` bilan birga qidiriladi va butun o'zak mos kelishi kerak, shuning
    uchun noto'g'ri moslik ehtimoli kichik. Bir bo'g'inli so'zlarga qo'llanmaydi.
    """
    if len(word) < 4:
        return []
    alternatives: list[str] = []
    if word.endswith("k"):
        alternatives.append(word[:-1] + "g")
    elif word.endswith("q"):
        alternatives.append(word[:-1] + "g'")
    match = _ELISION.match(word)
    if match and any(ch in "aeiou" for ch in match.group("head")):
        alternatives.append(match.group("head") + match.group("tail"))
    return alternatives


_LETTER = r"[^\W\d_]"
_ALNUM = r"[^\W_]"
# Oldida harf/raqam yoki so'z ichidagi apostrof (masalan, "so'z"dagi) bo'lmasin.
_START_BOUNDARY = rf"(?<!{_ALNUM})(?<!{_LETTER}')"
# Keyin harf/raqam yoki so'zni davom ettiruvchi apostrof kelmasin.
_END_BOUNDARY = rf"(?!{_ALNUM})(?!'{_LETTER})"


@dataclass(frozen=True)
class TermCandidate:
    entry: TermEntry
    matched_form: str  # lug'atdagi qaysi shakl bilan mos keldi (asl yozilishda)
    match_type: str  # "term" | "variant" | "synonym"


@dataclass(frozen=True)
class TermMatch:
    start: int
    end: int
    surface: str  # matndagi to'liq shakl, qo'shimcha bilan
    base_surface: str  # matndagi shakl, qo'shimchasiz
    suffix: str
    candidates: tuple[TermCandidate, ...]

    @property
    def method(self) -> str:
        return METHOD_INFLECTED if self.suffix else METHOD_EXACT

    @property
    def ambiguous(self) -> bool:
        return len(self.candidates) > 1


@dataclass(frozen=True)
class _RawMatch:
    start: int
    end: int
    base_end: int
    candidates: tuple[TermCandidate, ...]


def _compile_form(normalized_form: str) -> list[re.Pattern[str]]:
    """Shakl uchun regexlar: odatiy qo'shimchalar bilan, va tovush o'zgargan o'zak bilan."""
    words = normalized_form.split(" ")
    head = "".join(re.escape(word) + r"\s+" for word in words[:-1])
    patterns = [
        re.compile(f"{_START_BOUNDARY}(?P<base>{head}{re.escape(words[-1])})(?P<suffix>{SUFFIX_PATTERN}){_END_BOUNDARY}")
    ]
    for stem in stem_alternations(words[-1]):
        patterns.append(
            re.compile(f"{_START_BOUNDARY}(?P<base>{head}{re.escape(stem)})(?P<suffix>{ALTERED_SUFFIX_PATTERN}){_END_BOUNDARY}")
        )
    return patterns


def _entry_forms(entry: TermEntry) -> Iterable[tuple[str, str]]:
    yield entry.term, MATCH_TERM
    for variant in entry.variants:
        yield variant, MATCH_VARIANT
    for synonym in entry.synonyms:
        yield synonym, MATCH_SYNONYM


class DictionaryMatcher:
    def __init__(self, entries: Iterable[TermEntry]) -> None:
        # normallashtirilgan shakl -> {entry.id -> nomzod}
        index: dict[str, dict[str, TermCandidate]] = {}
        for entry in entries:
            for form, match_type in _entry_forms(entry):
                per_entry = index.setdefault(normalize_form(form), {})
                # Bir yozuvda shakl takrorlansa, termin > variant > sinonim ustun.
                per_entry.setdefault(entry.id, TermCandidate(entry, form, match_type))

        self._known_forms = frozenset(index)
        self._patterns = [
            (pattern, tuple(candidates.values()))
            for form, candidates in index.items()
            for pattern in _compile_form(form)
        ]

    def has_form(self, form: str) -> bool:
        """Shakl (termin, variant yoki sinonim) lug'atda bormi — registr va apostrofsiz."""
        return normalize_form(form) in self._known_forms

    def find(self, text: str) -> list[TermMatch]:
        if not isinstance(text, str):
            raise TypeError("text matn (str) bo'lishi kerak")
        if not text.strip():
            return []

        normalized = normalize_text(text)
        raw_matches: list[_RawMatch] = []
        for pattern, candidates in self._patterns:
            position = 0
            while (match := pattern.search(normalized, position)) is not None:
                raw_matches.append(
                    _RawMatch(match.start(), match.end(), match.end("base"), candidates)
                )
                # Ustma-ust tushadigan mosliklarni o'tkazib yubormaslik uchun
                # qidiruvni keyingi belgidan davom ettiramiz.
                position = match.start() + 1

        return [
            TermMatch(
                start=raw.start,
                end=raw.end,
                surface=text[raw.start : raw.end],
                base_surface=text[raw.start : raw.base_end],
                suffix=text[raw.base_end : raw.end],
                candidates=raw.candidates,
            )
            for raw in _select_non_overlapping(raw_matches)
        ]


def _select_non_overlapping(matches: list[_RawMatch]) -> list[_RawMatch]:
    """Uzun moslikni ustun qo'yib, ustma-ust tushmaydigan mosliklarni tanlaydi.

    Tartib: avval uzunroq span, teng bo'lsa qo'shimchasi qisqaroq
    (ya'ni lug'atdagi shakli uzunroq), keyin matnda oldinroq kelgani.
    """
    ordered = sorted(matches, key=lambda m: (-(m.end - m.start), m.end - m.base_end, m.start))
    selected: list[_RawMatch] = []
    for candidate in ordered:
        if all(candidate.end <= kept.start or candidate.start >= kept.end for kept in selected):
            selected.append(candidate)
    return sorted(selected, key=lambda m: m.start)
