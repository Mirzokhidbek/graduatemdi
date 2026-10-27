"""Korpusga tayangan sodda lemmatizator (faqat qo'shimchani ajratish).

So'z ``o'zak + qo'shimchalar`` ko'rinishida yoyiladi, bunda:
- qo'shimchalar zanjiri ``dictionary_matcher.SUFFIX_PATTERN`` ga to'liq mos;
- o'zak kamida ``min_stem`` harfdan iborat;
- o'zak korpusda **alohida so'z sifatida** uchragan (lug'at yo'qligi sababli
  shu dalil talab qilinadi; aks holda "bola" -> "bo" + "la" kabi xato bo'linishlar ko'payadi).

Bir nechta variant bo'lsa, eng qisqa o'zak olinadi (``fonemalarning`` ->
``fonemalar`` ham, ``fonema`` ham bo'lishi mumkin — ``fonema`` tanlanadi).
Tovush o'zgarishlari (``o'rin -> o'rni``) hisobga olinmaydi.
"""

from __future__ import annotations

import re
from typing import Iterable

from app.nlp.dictionary_matcher import SUFFIX_PATTERN

_SUFFIXES = re.compile(SUFFIX_PATTERN)


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
        for cut in range(self._min_stem, len(word)):
            stem, suffix = word[:cut], word[cut:]
            if stem in self._vocabulary and _SUFFIXES.fullmatch(suffix):
                return stem
        return word
