"""Matndan sinonim va dublet juftlarini ajratish (3.1-bo'lim).

Ilmiy matnda muallif ko'pincha terminning muqobilini o'zi beradi:

- qavs ichida: *arabistika (arabshunoslik)*, *nolisoniy (ekstralingvistik)*,
  *kvaziomonimlar (soxta omonimlar)*;
- *yoki* bog'lovchisi bilan: *Tilshunoslik yoki Lingvistika*;
- izoh bilan: *X, yaʼni Y*; *X boshqacha aytganda Y*.

Ikkala tomon ham leksik-grammatik qolipga (``app.nlp.patterns``) mos bo'lishi, 1–3
so'zdan iborat bo'lishi va bir-biriga teng bo'lmasligi kerak. Qavs ichida ko'pincha
misol (*feʼl (keldi)*) yoki izoh keladi, shuning uchun juftning **kamida bir tomoni
maʼlum termin** (lug'at yoki train annotatsiyasi) bo'lishi, ikkinchisi esa atoqli ot
(bosh harf bilan, gap boshida emas) yoki birinchisining qismi bo'lmasligi talab qilinadi. Natija — **nomzod**
juftlar, ular avtomatik ravishda lug'atga kiritilmaydi.

Juft turi:

- ``doublet`` — bir tomoni xalqaro (o'zlashma) termin, ikkinchisi o'zbekcha:
  *lingvistika ~ tilshunoslik*, *funksiya ~ vazifa*. Bu terminologiyadagi **dubletlik**;
- ``synonym`` — qolgan juftlar.

O'zlashma so'z belgilari (``is_international``) — yunon-lotin va rus-yevropa
qo'shimchalari va harf birikmalari (*-iya, -ika, -izm, -tsiya, -logiya, ts, f*).
Bu taxminiy qoida: *tavsifiy* (arabcha o'zlashma) o'zbekcha deb olinadi, chunki
u o'zbek tilida o'zlashib bo'lgan.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from app.nlp.normalize import normalize_text
from app.nlp.patterns import MorphTagger, matches_pattern
from app.nlp.tokenize import tokenize

KIND_DOUBLET = "doublet"
KIND_SYNONYM = "synonym"

INTERNATIONAL_ENDINGS = (
    "iya", "ika", "izm", "ist", "tsiya", "logiya", "grafiya", "fon", "ema", "ent", "ant", "ator", "ment",
    "ura", "tiv", "tsion", "al", "lingvistik", "tik", "gik", "fik", "nik", "rik", "sik", "or", "um", "us", "is",
)
INTERNATIONAL_PREFIXES = (
    "ekstra", "kvazi", "inter", "trans", "mikro", "makro", "neo", "proto", "para", "meta", "sotsio",
    "etno", "psixo", "neyro", "geo", "anti", "de", "re", "fono", "morfo", "lingvo",
)
NATIVE_ENDINGS = ("lik", "shunoslik", "chi", "siz", "ish", "uv", "lash", "dosh", "iy", "viy", "aviy", "gan", "li")
_INTERNATIONAL_LETTERS = re.compile(r"ts|ks|(?<![aeiou])f(?![aeiou])")  # undoshlar orasidagi f: morfema, sfera


def is_international(word: str) -> bool:
    """So'z xalqaro (yunon-lotin, yevropa) o'zlashma bo'lishi mumkinmi (taxminiy)."""
    w = normalize_text(word).replace("'", "")
    if len(w) < 4:
        return False
    if w.endswith(NATIVE_ENDINGS) and not w.endswith(("tsiya", "logiya", "ika", "iya")):
        return bool(_INTERNATIONAL_LETTERS.search(w)) and not w.endswith(("lik", "shunoslik"))
    return w.endswith(INTERNATIONAL_ENDINGS) or w.startswith(INTERNATIONAL_PREFIXES) or bool(
        _INTERNATIONAL_LETTERS.search(w)
    )


@dataclass
class PairCandidate:
    left: tuple[str, ...]
    right: tuple[str, ...]
    kind: str
    cues: Counter = field(default_factory=Counter)  # qavs | yoki | ya'ni
    examples: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return sum(self.cues.values())

    def to_dict(self) -> dict:
        return {
            "left": " ".join(self.left),
            "right": " ".join(self.right),
            "kind": self.kind,
            "count": self.count,
            "cues": dict(self.cues),
            "example": self.examples[0] if self.examples else None,
        }


_WORD = r"[^\W\d_]+(?:['ʻʼ‘’`][^\W\d_]+)*"
_CHAIN = rf"{_WORD}(?:[ \t]+{_WORD}){{0,2}}"
_PAREN = re.compile(rf"({_CHAIN})[ \t]*\(({_CHAIN})\)")
_OR = re.compile(rf"({_CHAIN})[ \t]+yoki[ \t]+({_CHAIN})")
_THAT_IS = re.compile(rf"({_CHAIN}),?[ \t]+(?:ya['ʻʼ‘’`]ni|boshqacha aytganda)[ \t]+({_CHAIN})")
CUES = (("paren", _PAREN), ("or", _OR), ("that_is", _THAT_IS))


class SynonymExtractor:
    def __init__(self, tagger: MorphTagger, known_terms: Iterable[tuple[str, ...]] = ()) -> None:
        self.tagger = tagger
        self.known_terms = frozenset(known_terms)

    def _key(self, words: list[str]) -> tuple[str, ...]:
        return (*words[:-1], self.tagger.lemmatizer.lemma(words[-1]))

    def _side(self, chunk: str, take_last: bool, in_parens: bool = False) -> list[tuple[str, ...]]:
        """Chap tomonda — oxirgi 1..3 so'z, o'ng tomonda — boshidagi 1..3 so'z; qolipga moslari."""
        tokens = tokenize(chunk)
        words = [t.norm for t in tokens]
        options = []
        for n in range(1, min(3, len(words)) + 1):
            part = words[-n:] if take_last else words[:n]
            first = tokens[-n] if take_last else tokens[0]
            if in_parens and first.text[:1].isupper():
                continue  # qavs ichidagi atoqli ot: (Kichik Osiyo), (Hamid Gʻulom)
            key = self._key(part)
            if matches_pattern(key, self.tagger) and sum(len(w) for w in key) >= 4:
                options.append(key)
        return options

    def _choose(self, left: list[tuple[str, ...]], right: list[tuple[str, ...]], cue: str):
        if not left or not right:
            return None
        # Qavs ichidagi ifoda butunligicha olinadi; chap tomonda uzunligi unga yaqin variant.
        r = right[-1] if cue == "paren" else right[0]
        known_left = [k for k in left if k in self.known_terms]
        l = known_left[-1] if known_left else min(left, key=lambda k: (abs(len(k) - len(r)), len(k)))
        return l, r

    def extract(self, documents: Mapping[str, str]) -> list[PairCandidate]:
        pairs: dict[tuple, PairCandidate] = {}
        for text in documents.values():
            for cue, pattern in CUES:
                for match in pattern.finditer(text):
                    if cue == "paren" and match.group(2).count(" ") > 2:
                        continue
                    chosen = self._choose(
                        self._side(match.group(1), True), self._side(match.group(2), False, cue == "paren"), cue
                    )
                    if chosen is None:
                        continue
                    left, right = chosen
                    if left == right or set(left) <= set(right) or set(right) <= set(left):
                        continue  # "feʼl shakl ~ shakl" — ichma-ich, sinonim emas
                    if not (left in self.known_terms or right in self.known_terms):
                        continue  # "ikki yoki uch", "feʼl (keldi)" kabi shovqin
                    key = tuple(sorted((left, right)))
                    kind = classify(left, right)
                    item = pairs.setdefault(key, PairCandidate(key[0], key[1], kind))
                    item.cues[cue] += 1
                    if len(item.examples) < 3:
                        item.examples.append(match.group(0))
        return sorted(pairs.values(), key=lambda p: (-p.count, p.left))


def classify(left: tuple[str, ...], right: tuple[str, ...]) -> str:
    a, b = is_international(left[-1]), is_international(right[-1])
    return KIND_DOUBLET if a != b else KIND_SYNONYM
