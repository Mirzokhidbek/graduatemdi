"""Ko'p tilli terminologik baza: ekvivalentlarni moslashtirish va meʼyoriy muqobilni tanlash (3.3-bo'lim).

Vazifa: ruscha yoki inglizcha termin berilganda, oʻzbekcha terminlar bazasidan uning
ekvivalentini topish (cross-lingual alignment) va bir nechta oʻzbekcha muqobil bo'lsa,
meʼyoriysini tavsiya qilish.

**1. Kognat modeli (qoidaviy, oflayn).** Xalqaro terminlar uch tilda umumiy yunon-lotin
o'zakdan: *фонема — phoneme — fonema*. Har bir til shakli umumiy "fonetik kalit"ga
keltiriladi va kalitlar Levenshtein masofasi bilan solishtiriladi:

    sim(a, b) = 1 − lev(key(a), key(b)) / max(|key(a)|, |key(b)|)

- rus tili: kirill → lotin transliteratsiya (*ц → c*, *х → h*, *ия → iya*);
- ingliz tili: yunon-lotin so'zlarining o'zbek tiliga moslashish qoidalari teskari
  qo'llanadi (*ph → f*, *-tion → -tsiya*, *-ology → -ologiya*, *-ics → -ika*,
  *-eme → -ema*, *-ism → -izm*, *-y → -iya*, *c → k/s*);
- oʻzbek tili: *oʻ, gʻ → o, g*, *x → h*, *q → k*, *ts → c*.

**2. Embedding modeli (ixtiyoriy).** Ko'p tilli jumla embeddinglari (LaBSE —
Feng va boshq., 2022) kosinus o'xshashligi. Oʻzbekcha (*tilshunoslik*) va xalqaro
(*linguistics*) terminlar o'rtasida kognat yo'q — ularni faqat semantik model
moslashtira oladi. Model ``sentence-transformers`` va internet talab qiladi
(Colab: ``notebooks/multilingual_colab.ipynb``).

**3. Gibrid:** ``score = w · cos + (1 − w) · sim``.

**4. Meʼyoriy muqobil.** Topilgan oʻzbekcha termin lug'atda sinonim yoki dublet bilan
bog'langan bo'lsa (*lingvistika ~ tilshunoslik*), barcha muqobillar qaytariladi va
3.1.4-bo'limdagi qoidalar bilan (tasdiqlangan → lug'atdagi meʼyoriy shakl → chastota)
bittasi tavsiya etiladi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from app.nlp.normalize import normalize_form
from app.variation.orthography import edit_distance

_RU = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}
# Ingliz tilidagi yunon-lotin terminlarining oʻzbekcha moslashuvi (so'z oxiri qoidalari birinchi).
_EN_SUFFIXES = [
    ("ology", "ologiya"), ("graphy", "grafiya"), ("onymy", "onimiya"), ("nymy", "nimiya"), ("tion", "ciya"),
    ("sion", "siya"), ("ics", "ika"), ("ism", "izm"), ("eme", "ema"), ("ure", "ura"), ("ity", "itet"),
    ("ic", "ik"), ("ive", "iv"), ("al", "al"), ("ia", "iya"), ("y", "iya"),
]
_EN_RULES = [
    ("ph", "f"), ("th", "t"), ("rh", "r"), ("ch", "h"), ("ck", "k"), ("qu", "kv"), ("x", "ks"), ("w", "v"),
    ("ce", "se"), ("ci", "si"), ("cy", "si"), ("c", "k"), ("y", "i"), ("ou", "u"),
]


def key_ru(term: str) -> str:
    return "".join(_RU.get(ch, ch) for ch in term.lower()).replace("iy ", "i ").strip()


def key_en(term: str) -> str:
    words = []
    for word in term.lower().split():
        for suffix, repl in _EN_SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                word = word[: -len(suffix)] + "§" + repl  # § — qo'shimcha chegarasi (qoidalar unga tegmaydi)
                break
        stem, _, tail = word.partition("§")
        for a, b in _EN_RULES:
            stem = stem.replace(a, b)
        words.append(stem + tail)
    return " ".join(words)


def key_uz(term: str) -> str:
    text = normalize_form(term).replace("o'", "o").replace("g'", "g").replace("'", "")
    for a, b in (("ts", "c"), ("x", "h"), ("q", "k"), ("sh", "sh")):
        text = text.replace(a, b)
    return text


KEYS: dict[str, Callable[[str], str]] = {"ru": key_ru, "en": key_en, "uz": key_uz}


def cognate_similarity(source: str, source_lang: str, target_uz: str) -> float:
    a, b = KEYS[source_lang](source), key_uz(target_uz)
    a, b = re.sub(r"(.)\1", r"\1", a), re.sub(r"(.)\1", r"\1", b)  # qo'sh harflar: affiks ~ afiks
    if not a or not b:
        return 0.0
    return 1 - edit_distance(a, b) / max(len(a), len(b))


@dataclass(frozen=True)
class Candidate:
    uz: str
    score: float
    cognate: float
    semantic: float | None


class Aligner:
    """Manba tildagi terminga oʻzbekcha nomzodlar reytingi."""

    def __init__(
        self,
        targets: Iterable[str],
        encoder: Callable[[Sequence[str]], Sequence[Sequence[float]]] | None = None,
        weight: float = 0.5,
    ) -> None:
        self.targets = sorted({t for t in targets if t})
        self.encoder = encoder
        self.weight = weight
        self._target_vectors = encoder(self.targets) if encoder else None

    def rank(self, sources: Sequence[str], lang: str, top: int = 5) -> list[list[Candidate]]:
        vectors = self.encoder(list(sources)) if self.encoder else None
        result = []
        for i, source in enumerate(sources):
            scored = []
            for j, target in enumerate(self.targets):
                cog = cognate_similarity(source, lang, target)
                sem = _cosine(vectors[i], self._target_vectors[j]) if vectors is not None else None
                score = cog if sem is None else self.weight * sem + (1 - self.weight) * cog
                scored.append(Candidate(target, score, cog, sem))
            scored.sort(key=lambda c: (-c.score, c.uz))
            result.append(scored[:top])
        return result


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def ranking_metrics(ranked: Sequence[Sequence[str]], gold: Sequence[set[str]]) -> dict:
    """Acc@1, Acc@5 va MRR (birinchi to'g'ri javobning teskari o'rni)."""
    n = len(gold)
    if not n:
        return {"n": 0}
    acc1 = acc5 = rr = 0.0
    for predicted, answers in zip(ranked, gold):
        norm = {normalize_form(a) for a in answers}
        positions = [i for i, p in enumerate(predicted) if normalize_form(p) in norm]
        if positions:
            first = positions[0]
            acc1 += first == 0
            acc5 += first < 5
            rr += 1 / (first + 1)
    return {"n": n, "acc@1": acc1 / n, "acc@5": acc5 / n, "mrr": rr / n}


def preferred_equivalent(uz_term: str, entries) -> dict:
    """Topilgan oʻzbekcha termin bilan bog'langan barcha muqobillar va tavsiya (3.1.4 qoidalari)."""
    from collections import Counter

    from app.variation.groups import choose_preferred

    norm = normalize_form(uz_term)
    entry = next(
        (e for e in entries if norm in {normalize_form(f) for f in (e.term, *e.variants, *e.synonyms)}), None
    )
    if entry is None:
        return {"found": uz_term, "alternatives": [], "preferred": uz_term, "status": "no_data",
                "reasons": ["lug'atda yo'q — tekshirish kerak"]}
    forms = Counter({entry.term: 1, **{s: 1 for s in entry.synonyms}})
    preferred, status, reasons = choose_preferred(forms, [entry])
    return {
        "found": uz_term,
        "alternatives": sorted(f for f in forms if normalize_form(f) != norm),
        "preferred": preferred,
        "status": status,
        "reasons": reasons,
    }


def load_gold(path) -> list[dict[str, str]]:
    import csv

    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def gold_by_source(rows: Iterable[Mapping[str, str]], lang: str, kind: str | None = None) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for row in rows:
        if kind and row["kind"] != kind:
            continue
        grouped.setdefault(row[lang], set()).add(row["uz"])
    return grouped
