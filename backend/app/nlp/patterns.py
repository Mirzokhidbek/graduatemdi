"""Leksik-grammatik qoliplarga asoslangan (lingvistik) termin aniqlash modeli (2.1-bo'lim).

Oʻzbek tili uchun ochiq va tekshirilgan POS-tegger yo'q. Shuning uchun so'z turkumi
**morfologik qoidalar** bilan taxminiy aniqlanadi (``MorphTagger``):

- ``FUNC`` — yordamchi so'z (``stopwords.STOPWORDS``);
- ``VERB`` — fe'l, sifatdosh, ravishdosh shakli (*-adi, -gan, -moq, -ib, ...*);
- ``ADJ``  — sifat: nisbiy sifat qo'shimchalari (*-tik, -iy, -li, -siz, -vchi*) yoki
  terminlarda aniqlovchi bo'lib keladigan so'zlar ro'yxati (*undosh, sodda, qoʻshma, ...*);
- ``NOUN`` — qolgan so'zlar (harakat nomi *-sh/-ish/-uv* ham ot hisoblanadi).

**Termin qolipi** (Justeson, Katz, 1995 qolipining oʻzbek tiliga moslamasi):

    T = (ADJ | NOUN₀)* NOUN

- oxirgi so'z (bosh so'z) — ot, istalgan qo'shimcha bilan (*tovushlarning*);
- undan oldingi so'zlar — sifat yoki **qo'shimchasiz** ot (*soʻz turkumi*,
  *kelishik qoʻshimchasi*). Oʻzbek tilida aniqlovchi ot qo'shimcha olmaydi; qaratqich
  (*-ning*) yoki boshqa kelishikdagi so'z birikmani bo'ladi: *gapning boʻlagi*
  termin emas, *gap boʻlagi* termin;
- 1–4 so'z, tinish belgisi kesib o'tilmaydi.

Ikki qo'llanish:

1. ``matches_pattern(key)`` — statistik nomzodlar uchun filtr (gibrid model:
   qolip + C-value / Weirdness).
2. ``PatternExtractor.extract(text)`` — matndan spanlarni to'g'ridan-to'g'ri ajratish.
   Har bir iborada eng uzun mos keladigan zanjir olinadi. ``keep`` funksiyasi berilsa
   (masalan, statistik ball chegarasi), faqat u ma'qullagan spanlar qoladi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from app.evaluation.metrics import Span
from app.nlp.clean import canonical_apostrophes
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.normalize import normalize_form
from app.nlp.stopwords import STOPWORDS
from app.nlp.tokenize import Token, phrases, tokenize

NOUN, ADJ, VERB, FUNC = "NOUN", "ADJ", "VERB", "FUNC"
MAX_WORDS = 4

# Fe'l shakllari: zamon/shaxs, sifatdosh, ravishdosh, harakat nomi -moq, majhul/orttirma nisbatdagi shakllar.
VERB_ENDINGS = (
    "adi", "aydi", "ydi", "moqda", "moq", "yapti", "gan", "kan", "qan", "ilgan", "ingan", "ladi",
    "ib", "ganda", "gach", "guncha", "maydi", "mas", "sin", "lmaydi", "ilmaydi", "ishadi",
    "yotgan", "ayotgan", "gani", "ganligi",
)
# Nisbiy sifat, -li/-siz, sifatdosh -vchi; -lik otlari bundan mustasno.
ADJ_ENDINGS = ("tik", "gik", "sik", "nik", "kik", "rik", "iy", "viy", "li", "siz", "vchi", "uvchi")
NOUN_ENDINGS = ("lik", "chilik", "shunoslik", "ish", "uv", "ov", "ma", "iya", "ika", "izm", "ema", "logiya")
# Terminlarda aniqlovchi bo'lib keladigan, sifat qo'shimchasisiz so'zlar.
ATTRIBUTIVE = frozenset(
    normalize_form(w)
    for w in (
        "undosh", "unli", "sodda", "qoʻshma", "ergash", "bosh", "yordamchi", "mustaqil", "asosiy", "umumiy",
        "xususiy", "amaliy", "nazariy", "tarixiy", "qiyosiy", "yasama", "koʻchma", "teng", "zidlovchi",
        "ergashtiruvchi", "biriktiruvchi", "ayiruvchi", "jarangli", "jarangsiz", "lablangan", "lablanmagan",
        "choʻziq", "qisqa", "kuchli", "kuchsiz", "oddiy", "orttirma", "ozaytirma", "atoqli", "turdosh",
        "modal", "taqlid", "undov", "ikkinchi", "uchinchi", "birinchi", "eski", "yangi", "majhul",
        "toʻliq", "toʻliqsiz", "chiziqli", "ochiq", "yopiq", "keng", "tor", "old", "orqa", "quyi", "yuqori",
    )
)
# Qo'shimchasiz ko'rinsa ham termin qismi bo'lmaydigan so'zlar (ravish, olmosh, son).
NON_TERM = frozenset(
    normalize_form(w)
    for w in (
        "koʻra", "xos", "oid", "doir", "boshqa", "oʻzaro", "ayniqsa", "odatda", "hatto", "ham", "deyarli",
        "bir", "ikki", "uch", "toʻrt", "besh", "olti", "yetti", "sakkiz", "toʻqqiz", "oʻn", "yuz", "ming",
        "biror", "hech", "har", "qachon", "qayer", "shuning", "keyingi", "oldingi", "avval", "ilgari",
        "tomon", "qadar", "sari", "uchun", "kabi", "singari", "bilan", "orasida", "sababli",
    )
)


class MorphTagger:
    """Qoidaviy so'z turkumi aniqlagichi (taxminiy)."""

    def __init__(self, lemmatizer: CorpusLemmatizer, stopwords: frozenset[str] = STOPWORDS) -> None:
        self.lemmatizer = lemmatizer
        self.stopwords = stopwords

    def tag(self, word: str) -> str:
        if word in self.stopwords or word in NON_TERM or self.lemmatizer.lemma(word) in self.stopwords:
            return FUNC
        if word in ATTRIBUTIVE:
            return ADJ
        if len(word) > 4 and word.endswith(NOUN_ENDINGS):
            return NOUN
        if len(word) > 4 and word.endswith(VERB_ENDINGS):
            return VERB
        if len(word) > 4 and word.endswith(ADJ_ENDINGS):
            return ADJ
        return NOUN

    def bare(self, word: str) -> bool:
        """So'z qo'shimchasiz (aniqlovchi ot bo'la oladi)."""
        return self.lemmatizer.lemma(word) == word

    def can_modify(self, word: str) -> bool:
        tag = self.tag(word)
        return tag == ADJ or (tag == NOUN and self.bare(word))

    def can_head(self, word: str) -> bool:
        return self.tag(word) == NOUN and self.tag(self.lemmatizer.lemma(word)) == NOUN


def matches_pattern(key: Iterable[str], tagger: MorphTagger) -> bool:
    """Nomzod kaliti (ichki so'zlar asl shaklda, oxirgisi lemma) termin qolipiga mosmi."""
    words = list(key)
    if not words or len(words) > MAX_WORDS:
        return False
    return all(tagger.can_modify(w) for w in words[:-1]) and tagger.can_head(words[-1])


def tag_sequence(key: Iterable[str], tagger: MorphTagger) -> str:
    """Tahlil uchun: ``ADJ+NOUN`` ko'rinishidagi qolip yozuvi."""
    return "+".join(tagger.tag(w) for w in key)


@dataclass(frozen=True)
class PatternSpan:
    start: int
    end: int
    words: tuple[str, ...]  # nomzod kaliti: ichki so'zlar + bosh so'z lemmasi
    surface: str

    @property
    def key(self) -> tuple[str, ...]:
        return self.words


class PatternExtractor:
    """Matndan qolipga mos eng uzun zanjirlarni ajratadi."""

    def __init__(
        self,
        tagger: MorphTagger,
        keep: Callable[[tuple[str, ...]], bool] | None = None,
        max_words: int = MAX_WORDS,
    ) -> None:
        self.tagger = tagger
        self.keep = keep
        self.max_words = max_words

    def _chains(self, phrase: list[Token]) -> Iterable[tuple[int, int]]:
        """Iboradagi [i, j] (j — bosh so'z) zanjirlar, chapdan o'ngga, kesishmaydi."""
        i, n = 0, len(phrase)
        while i < n:
            # i dan boshlab aniqlovchilar zanjiri, so'ng bosh so'z
            j = i
            while j < n and self.tagger.can_modify(phrase[j].norm):
                j += 1
            # bosh so'z: zanjirdan keyingi ot yoki zanjirning oxirgi oti
            if j < n and self.tagger.can_head(phrase[j].norm):
                head = j
            else:
                head = next((h for h in range(j - 1, i - 1, -1) if self.tagger.can_head(phrase[h].norm)), None)
            if head is None:
                i = max(j, i + 1)
                continue
            first = max(i, head - self.max_words + 1)
            yield first, head
            i = head + 1

    def candidates(self, text: str) -> list[PatternSpan]:
        found = []
        for phrase in phrases(text):
            for first, head in self._chains(phrase):
                key = self._key(phrase[first : head + 1])
                spans = [(first, key)]
                if self.keep is not None and not self.keep(key):
                    # uzun zanjir ma'qullanmasa, undagi qisqaroq (bosh so'z bilan tugaydigan) zanjirlar
                    spans = []
                    for start in range(first + 1, head + 1):
                        shorter = self._key(phrase[start : head + 1])
                        if self.keep(shorter):
                            spans = [(start, shorter)]
                            break
                for start, words in spans:
                    found.append(PatternSpan(phrase[start].start, phrase[head].end, words,
                                             text[phrase[start].start : phrase[head].end]))
        return found

    def _key(self, tokens: list[Token]) -> tuple[str, ...]:
        words = [t.norm for t in tokens]
        return (*words[:-1], self.tagger.lemmatizer.lemma(words[-1]))

    def extract(self, text: str) -> list[Span]:
        return [Span(s.start, s.end, canonical_apostrophes(" ".join(s.words))) for s in self.candidates(text)]


def build_tagger(texts: Iterable[str]) -> MorphTagger:
    vocabulary = (token.norm for text in texts for token in tokenize(text))
    return MorphTagger(CorpusLemmatizer(vocabulary))
