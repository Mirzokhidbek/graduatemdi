"""Korpusga tayangan sodda lemmatizator (faqat qo'shimchani ajratish).

So'z ``o'zak + qo'shimchalar`` ko'rinishida yoyiladi, bunda:
- qo'shimchalar zanjiri ``dictionary_matcher.SUFFIX_PATTERN`` ga to'liq mos;
- o'zak kamida ``min_stem`` harfdan iborat;
- o'zak korpusda **alohida so'z sifatida** uchragan (lug'at yo'qligi sababli
  shu dalil talab qilinadi; aks holda "bola" -> "bo" + "la" kabi xato bo'linishlar ko'payadi).

Bir nechta variant bo'lsa, eng qisqa o'zak olinadi (``fonemalarning`` ->
``fonemalar`` ham, ``fonema`` ham bo'lishi mumkin — ``fonema`` tanlanadi).
Istisno: 1-/2-shaxs birlik egaligi (``-im``, ``-ing``) ilmiy matnda deyarli
uchramaydi (``-imiz`` esa uchraydi: *tilimiz*). Shuning uchun so'zning o'zi korpusda
bo'lsa, bunday bo'linish olinmaydi (``kesim`` -> ``kesim``, ``kes`` + ``-im`` emas).
Tovush o'zgarishlari (``o'rin -> o'rni``) hisobga olinmaydi.
"""

from __future__ import annotations

import re
from typing import Iterable

from app.nlp.dictionary_matcher import SUFFIX_PATTERN

_SUFFIXES = re.compile(SUFFIX_PATTERN)
# I/II shaxs birlik egaligi (mening/sening). Ensiklopedik matnda deyarli uchramaydi.
PERSONAL_POSSESSIVES = ("ing", "im")


class CorpusLemmatizer:
    def __init__(self, vocabulary: Iterable[str], min_stem: int = 3) -> None:
        self._vocabulary = frozenset(vocabulary)
        self._min_stem = min_stem
        self._cache: dict[str, str] = {}

    def lemma(self, word: str) -> str:
        if word not in self._cache:
            self._cache[word] = self._lemma(word)
        return self._cache[word]

    def _lemma(self, word: str) -> str:
        personal = None
        for cut in range(self._min_stem, len(word)):
            stem, suffix = word[:cut], word[cut:]
            if stem in self._vocabulary and _SUFFIXES.fullmatch(suffix):
                if not personal_possessive(suffix):
                    return stem
                personal = personal or stem
        if personal is not None and word not in self._vocabulary:
            return personal
        return word


def personal_possessive(suffix: str) -> bool:
    """Qo'shimcha zanjirini I/II shaxs birlik egaligi bilan o'qish mumkinmi (ko'plikdan keyin ham).

    Har qanday o'qilish hisobga olinadi: "imi" = "-im" + "-i"? yoki "-i" + "-mi" — ikkalasi ham
    "kesimi" ni "kes" ga tushirardi.
    """
    rest = suffix.removeprefix("lar")
    return any(rest.startswith(p) and _SUFFIXES.fullmatch(rest[len(p):]) for p in PERSONAL_POSSESSIVES)
