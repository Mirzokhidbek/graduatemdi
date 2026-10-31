"""Terminlarni meʼyorlashtirish: matndagi shakl -> lug'at shakli -> meʼyoriy shakl (5-bosqich).

Algoritm (birinchi ishlagan qoida natijani beradi):

1. **Lug'at.** Shakl lug'atdagi termin, variant yoki sinonimga (qo'shimchalari va
   tovush o'zgarishlari bilan) to'liq mos kelsa — lug'at yozuvi: ``term``,
   ``preferred_form`` va holati (``approved`` / ``needs_review``).
2. **Morfologiya.** Lug'atda yo'q bo'lsa, oxirgi so'zdan qo'shimchalar zanjiri ajratiladi
   (ko'plik + egalik + kelishik + ``-dagi/-ki`` + yuklama). O'zak korpusda yoki lug'atda
   mustaqil so'z sifatida uchragan bo'lishi kerak. Tovush o'zgarishi teskari tiklanadi:
   ``kelishigi -> kelishik``, ``qishlogʻi -> qishloq``, ``oʻrni -> oʻrin``.
   **Izofa.** Ko'p so'zli terminda oxirgi so'zdagi III shaxs egalik qo'shimchasi
   (``-i/-si``) ko'pincha birikmaning o'ziga tegishli: *soʻz birikmasi*, *gap boʻlagi*,
   *kelishik qoʻshimchasi*. Shuning uchun u saqlanadi (ko'plik va kelishik olib
   tashlanadi). Istisno: birinchi so'z sifat bo'lsa (*undosh tovushlari* ->
   *undosh tovush*). Sifat deb ``-ik, -iy, -li, -siz, -gan, -vchi`` bilan
   tugaydigan yoki ``ATTRIBUTIVE`` ro'yxatidagi so'zlar olinadi.
3. Natija kichik harfda, apostroflar rasmiy shaklda (``oʻ``, ``gʻ``, ``ʼ``).

Morfologiya bilan topilgan shakl **meʼyoriy deb eʼlon qilinmaydi**: holati ``no_data``,
ya'ni "lug'atda yo'q, tekshirish kerak" (loyiha qoidasi, ``docs/project-plan.md``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.database.term_store import TermEntry
from app.nlp.clean import canonical_apostrophes
from app.nlp.dictionary_matcher import (
    ATTRIBUTIVE_SUFFIXES,
    CASE_SUFFIXES,
    PARTICLE_SUFFIXES,
    PLURAL_SUFFIXES,
    POSSESSIVE_SUFFIXES,
    DictionaryMatcher,
)
from app.nlp.normalize import normalize_form, normalize_text
from app.nlp.tokenize import tokenize

METHOD_DICTIONARY = "dictionary"
METHOD_MORPHOLOGY = "morphology"
METHOD_UNCHANGED = "unchanged"

# Ko'p so'zli terminlarda aniqlovchi vazifasida keladigan, lekin sifat qo'shimchasi bilan
# tugamaydigan so'zlar (izofa emas: "undosh tovushlari" -> "undosh tovush").
ATTRIBUTIVE = frozenset(
    normalize_form(w)
    for w in (
        "undosh", "unli", "sodda", "qoʻshma", "ergash", "bosh", "yordamchi", "mustaqil", "asosiy", "umumiy",
        "xususiy", "amaliy", "nazariy", "tarixiy", "qiyosiy", "yasama", "koʻchma", "teng", "zidlovchi",
        "ergashtiruvchi", "biriktiruvchi", "ayiruvchi", "jarangli", "jarangsiz", "lablangan", "lablanmagan",
        "choʻziq", "qisqa", "kuchli", "kuchsiz", "oddiy", "orttirma", "ozaytirma", "atoqli", "turdosh",
        "modal", "taqlid", "undov", "ikkinchi", "uchinchi", "birinchi", "eski", "yangi", "oʻz", "majhul",
    )
)
# nisbiy sifat (grammatik, fonetik, tarixiy), -li/-siz, sifatdosh -gan/-vchi; "-lik" otlari emas
ADJECTIVE_ENDINGS = ("tik", "gik", "sik", "nik", "kik", "rik", "iy", "viy", "li", "siz", "gan", "kan", "qan", "vchi")


def _alternation(parts: Iterable[str]) -> str:
    return "|".join(re.escape(p) for p in sorted(parts, key=len, reverse=True))


_SUFFIX = re.compile(
    rf"(?P<plural>{_alternation(PLURAL_SUFFIXES)})?(?P<poss>{_alternation(POSSESSIVE_SUFFIXES)})?"
    rf"(?P<case>{_alternation(CASE_SUFFIXES)})?(?P<attr>{_alternation(ATTRIBUTIVE_SUFFIXES)})?"
    rf"(?P<particle>{_alternation(PARTICLE_SUFFIXES)})?"
)


@dataclass(frozen=True)
class Normalized:
    surface: str
    lemma: str  # matndagi so'zning lug'at shakli (sinonim bo'lsa — sinonimning o'zi: "qoʻshimcha")
    term: str | None  # lug'atdagi asosiy termin ("affiks"); lug'atda yo'q bo'lsa None
    preferred_form: str | None
    status: str  # approved | needs_review | no_data
    method: str  # dictionary | morphology | unchanged
    entry_id: str | None = None


def _is_vowel(ch: str) -> bool:
    return ch in "aeiou"


def _syllables(word: str) -> int:
    return sum(_is_vowel(ch) for ch in word)


def _fits(stem: str, match: re.Match[str]) -> bool:
    """Fonotaktika: jo'nalish kelishigi -ka faqat k dan, -qa faqat q dan keyin (tilakka, tuproqqa);
    egalik yoki ko'plik qo'shimchasidan keyin ham faqat -ga ("uyiga"). Shu sababli
    "lingvistika" -> "lingvist" + "i" + "ka" bo'linishi rad etiladi."""
    case = match.group("case") or ""
    if case not in ("ka", "qa"):
        return True
    before = stem + (match.group("plural") or "") + (match.group("poss") or "")
    return before.endswith(case[0])


class TermNormalizer:
    def __init__(self, entries: Iterable[TermEntry], vocabulary: Iterable[str] = ()) -> None:
        entries = list(entries)
        self.matcher = DictionaryMatcher(entries)
        words = {normalize_form(w) for w in vocabulary}
        for entry in entries:
            for form in (entry.term, *entry.variants, *entry.synonyms):
                words.update(normalize_form(form).split(" "))
        self.vocabulary = frozenset(words)

    # --- 1. lug'at -------------------------------------------------------------

    def _from_dictionary(self, surface: str) -> Normalized | None:
        matches = self.matcher.find(surface)
        if len(matches) != 1 or matches[0].start != 0 or matches[0].end != len(surface.rstrip()):
            return None
        match = matches[0]
        candidate = match.candidates[0]
        lemma = canonical_apostrophes(candidate.matched_form.lower())
        if match.ambiguous:
            return Normalized(surface, lemma, None, None, "needs_review", METHOD_DICTIONARY, None)
        entry = candidate.entry
        return Normalized(surface, lemma, entry.term, entry.preferred_form, entry.status, METHOD_DICTIONARY, entry.id)

    # --- 2. morfologiya ---------------------------------------------------------

    def split_word(self, word: str) -> tuple[str, re.Match[str] | None]:
        """So'zni o'zak + qo'shimchalarga ajratadi; o'zak lug'at/korpusda bo'lishi kerak (eng qisqa)."""
        for cut in range(3, len(word)):
            stem, rest = word[:cut], word[cut:]
            match = _SUFFIX.fullmatch(rest)
            if not match or not rest or not _fits(stem, match):
                continue
            for candidate in self._restore(stem, rest):
                if candidate in self.vocabulary:
                    return candidate, match
        # O'zak korpusda yo'q (yangi termin): faqat ko'plik/kelishik qo'shimchasi aniq bo'lsa va
        # o'zak kamida 5 harf bo'lsa ajratiladi ("dialektografiyaga" -> "dialektografiya").
        for cut in range(5, len(word)):
            rest = word[cut:]
            match = _SUFFIX.fullmatch(rest)
            if not match or len(rest) < 2 or not _fits(word[:cut], match):
                continue
            # ko'plik/kelishik, yoki unlidan keyingi -si (terminologiyasi -> terminologiya)
            if match.group("plural") or match.group("case") or (rest == "si" and _is_vowel(word[cut - 1]) and cut >= 6):
                return word[:cut], match
        return word, None

    def _restore(self, stem: str, rest: str) -> list[str]:
        """Tovush o'zgarishini teskari tiklash: unli bilan boshlanuvchi egalik oldida."""
        options = [stem]
        if rest[:1] == "i":
            if stem.endswith("g'"):
                options.append(stem[:-2] + "q")
            elif stem.endswith("g"):
                options.append(stem[:-1] + "k")
            if len(stem) >= 3 and not _is_vowel(stem[-1]) and not _is_vowel(stem[-2]):
                for vowel in ("i", "u"):
                    options.append(stem[:-1] + vowel + stem[-1])
        return options

    @staticmethod
    def _attributive(word: str) -> bool:
        return word in ATTRIBUTIVE or (len(word) > 4 and word.endswith(ADJECTIVE_ENDINGS))

    @staticmethod
    def _izofa(stem: str) -> str:
        """III shaxs egalik qo'shimchasini o'zakka qo'shadi: unlidan keyin -si, undoshdan keyin -i;
        ko'p bo'g'inli so'zda k -> g, q -> gʻ (boʻlak -> boʻlagi, qishloq -> qishlogʻi)."""
        if _is_vowel(stem[-1]):
            return stem + "si"
        if _syllables(stem) >= 2 and stem.endswith("k"):
            return stem[:-1] + "gi"
        if _syllables(stem) >= 2 and stem.endswith("q"):
            return stem[:-1] + "g'i"
        return stem + "i"

    def _from_morphology(self, surface: str) -> Normalized:
        words = [t.norm for t in tokenize(surface)]
        if not words:
            return Normalized(surface, surface, None, None, "no_data", METHOD_UNCHANGED)
        last = words[-1]
        stem, suffix = self.split_word(last)
        method = METHOD_MORPHOLOGY if suffix is not None else METHOD_UNCHANGED
        lemma_last = stem
        if suffix is not None and len(words) > 1 and suffix.group("poss") in ("i", "si"):
            if not self._attributive(words[-2]):
                lemma_last = self._izofa(stem)
        # birikmaning ichki so'zlari va ular orasidagi belgilar (defis) o'zgarmaydi:
        # faqat oxirgi so'z almashtiriladi ("kasb-hunar leksikasi", "fonemalar almashinuvi")
        tokens = tokenize(surface)
        head = normalize_text(surface[: tokens[-1].start]).lower()
        lemma = canonical_apostrophes(" ".join((head + lemma_last).split()))
        return Normalized(surface, lemma, None, None, "no_data", method)

    def normalize(self, surface: str) -> Normalized:
        return self._from_dictionary(surface) or self._from_morphology(surface)


def build_normalizer(entries: Iterable[TermEntry], texts: Iterable[str]) -> TermNormalizer:
    vocabulary = {token.norm for text in texts for token in tokenize(normalize_text(text))}
    return TermNormalizer(entries, vocabulary)
