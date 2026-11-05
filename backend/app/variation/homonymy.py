"""Terminologik omonimiya: so'z matnda termin maʼnosidami yoki umumiy maʼnodami (3.1-bo'lim).

*qoʻshimcha* — "affiks" maʼnosida termin, "qoʻshimcha maʼlumot" birikmasida esa termin
emas. *gap*, *ega*, *kesim*, *ot*, *asos*, *belgi* ham shunday. Lug'at aniqlagichi
bunday so'zni har doim termin deb oladi (yoki umuman olmaydi).

**Model.** Har bir uchrash uchun kontekst xususiyatlari bo'yicha ko'p nomli
naiv Bayes klassifikatori (Laplace silliqlash bilan):

    P(c | x) ∝ P(c | lemma) · Π_f P(f | c),   c ∈ {termin, umumiy}

Xususiyatlar: so'z lemmasi, ±1 va ±2 qo'shni so'zlar (lemma), o'ngdagi qo'shni
so'z qo'shimcha olganmi, so'z gap boshidami. P(c | lemma) — shu lemma bo'yicha
train'dagi termin ulushi (silliqlangan).

**Maʼlumot.** Annotatsiyadan avtomatik olinadi: train'da kamida ``min_count`` marta
uchragan va ham termin, ham termin emas deb belgilangan bir so'zli lemmalar
("noaniq lemmalar"). So'zning uchrashi termin spani bilan aynan mos kelsa — termin,
hech qanday spanga tegmasa — umumiy; ko'p so'zli termin ichida bo'lsa, hisobga olinmaydi.

**Taqqoslash.** (1) har doim termin (lug'at usuli), (2) lemma bo'yicha ko'pchilik sinf.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence

from app.dataset.annotation import AnnotatedRecord
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.stopwords import STOPWORDS
from app.nlp.tokenize import Token, tokenize

TERM, GENERAL = "term", "general"


@dataclass(frozen=True)
class Occurrence:
    lemma: str
    features: tuple[str, ...]
    label: str | None  # None — ko'p so'zli termin ichida (o'qitish/baholashda ishlatilmaydi)
    record_id: str
    start: int


def _features(tokens: Sequence[Token], i: int, lemmatizer: CorpusLemmatizer) -> tuple[str, ...]:
    lemma = lemmatizer.lemma(tokens[i].norm)
    feats = [f"w={lemma}"]
    for offset in (-2, -1, 1, 2):
        j = i + offset
        if 0 <= j < len(tokens):
            word = tokens[j].norm
            feats.append(f"{offset:+d}:{lemmatizer.lemma(word)}")
            if word in STOPWORDS:
                feats.append(f"{offset:+d}:FUNC")
        else:
            feats.append(f"{offset:+d}:<chet>")
    if i + 1 < len(tokens):
        nxt = tokens[i + 1].norm
        feats.append(f"+1:suffixed={lemmatizer.lemma(nxt) != nxt}")
    feats.append(f"own_suffix={lemmatizer.lemma(tokens[i].norm) != tokens[i].norm}")
    feats.append(f"capital={tokens[i].text[:1].isupper()}")
    return tuple(feats)


def occurrences(
    records: Iterable[AnnotatedRecord], lemmas: set[str], lemmatizer: CorpusLemmatizer
) -> list[Occurrence]:
    found = []
    for record in records:
        tokens = tokenize(record.text)
        spans = [(s.start, s.end) for s in record.terms]
        for i, token in enumerate(tokens):
            lemma = lemmatizer.lemma(token.norm)
            if lemma not in lemmas:
                continue
            if (token.start, token.end) in spans:
                label = TERM
            elif any(s < token.end and token.start < e for s, e in spans):
                label = None
            else:
                label = GENERAL
            found.append(Occurrence(lemma, _features(tokens, i, lemmatizer), label, record.id, token.start))
    return found


def ambiguous_lemmas(
    records: Iterable[AnnotatedRecord], lemmatizer: CorpusLemmatizer, min_count: int = 5, min_share: float = 0.1
) -> dict[str, float]:
    """Train'da ham termin, ham umumiy maʼnoda uchragan bir so'zli lemmalar -> termin ulushi."""
    records = list(records)
    single = {
        lemmatizer.lemma(tokenize(s.term)[0].norm)
        for r in records
        for s in r.terms
        if len(tokenize(s.term)) == 1
    }
    counts: dict[str, Counter] = defaultdict(Counter)
    for occ in occurrences(records, single, lemmatizer):
        if occ.label is not None:
            counts[occ.lemma][occ.label] += 1
    result = {}
    for lemma, c in counts.items():
        total = c[TERM] + c[GENERAL]
        share = c[TERM] / total if total else 0.0
        if total >= min_count and min_share <= share <= 1 - min_share:
            result[lemma] = share
    return result


class HomonymClassifier:
    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self.prior: dict[str, Counter] = {}
        self.feature_counts: dict[str, Counter] = {TERM: Counter(), GENERAL: Counter()}
        self.class_totals: Counter = Counter()
        self.vocabulary: set[str] = set()

    def fit(self, data: Iterable[Occurrence]) -> "HomonymClassifier":
        prior: dict[str, Counter] = defaultdict(Counter)
        for occ in data:
            if occ.label is None:
                continue
            prior[occ.lemma][occ.label] += 1
            self.feature_counts[occ.label].update(occ.features)
            self.class_totals[occ.label] += len(occ.features)
            self.vocabulary.update(occ.features)
        self.prior = dict(prior)
        return self

    def log_odds(self, occ: Occurrence) -> float:
        """log P(termin | x) − log P(umumiy | x)."""
        p = self.prior.get(occ.lemma, Counter())
        score = math.log((p[TERM] + self.alpha) / (p[GENERAL] + self.alpha))
        v = len(self.vocabulary) + 1
        for f in occ.features:
            if f not in self.vocabulary:
                continue
            pt = (self.feature_counts[TERM][f] + self.alpha) / (self.class_totals[TERM] + self.alpha * v)
            pg = (self.feature_counts[GENERAL][f] + self.alpha) / (self.class_totals[GENERAL] + self.alpha * v)
            score += math.log(pt / pg)
        return score

    def predict(self, occ: Occurrence) -> str:
        return TERM if self.log_odds(occ) >= 0 else GENERAL


def evaluate(classifier: HomonymClassifier, data: Sequence[Occurrence]) -> dict:
    labelled = [o for o in data if o.label is not None]
    if not labelled:
        return {"occurrences": 0}

    def accuracy(predict) -> float:
        return sum(predict(o) == o.label for o in labelled) / len(labelled)

    def term_f1(predict) -> float | None:
        tp = sum(predict(o) == TERM and o.label == TERM for o in labelled)
        fp = sum(predict(o) == TERM and o.label == GENERAL for o in labelled)
        fn = sum(predict(o) == GENERAL and o.label == TERM for o in labelled)
        return 2 * tp / (2 * tp + fp + fn) if tp else 0.0

    majority = {lemma: (TERM if c[TERM] >= c[GENERAL] else GENERAL) for lemma, c in classifier.prior.items()}
    methods = {
        "always_term": lambda o: TERM,
        "lemma_majority": lambda o: majority.get(o.lemma, TERM),
        "naive_bayes": classifier.predict,
    }
    by_lemma: dict[str, Counter] = defaultdict(Counter)
    for o in labelled:
        by_lemma[o.lemma]["n"] += 1
        by_lemma[o.lemma]["term"] += o.label == TERM
        by_lemma[o.lemma]["nb_ok"] += classifier.predict(o) == o.label
    return {
        "occurrences": len(labelled),
        "term_share": sum(o.label == TERM for o in labelled) / len(labelled),
        "accuracy": {name: accuracy(fn) for name, fn in methods.items()},
        "term_f1": {name: term_f1(fn) for name, fn in methods.items()},
        "by_lemma": {lemma: dict(c) for lemma, c in sorted(by_lemma.items(), key=lambda kv: -kv[1]["n"])},
    }
