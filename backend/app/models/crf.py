"""Termin aniqlash uchun CRF modeli (token classification, BIO teglar) — 4-bosqich.

Nega CRF: oʻzbek tili uchun tayyor transformer modelini (XLM-R, mBERT) bu muhitda
yuklab bo'lmadi, belgilangan maʼlumot ham kichik (~300 paragraf). CRF (Lafferty va
boshq., 2001) — kichik datasetlarda termin va nomlangan obyektlarni aniqlashda
keng ishlatiladigan, natijasi tushuntiriladigan klassik model; transformer bilan
keyingi solishtirish uchun ham kuchli asos (baseline).

Xususiyatlar (har bir token uchun, ±2 qo'shni bilan):
- so'zning o'zi (kichik harf), korpus lemmatizatori bo'yicha o'zagi;
- oxirgi 2–5 va boshidagi 3 harf (qo'shimcha va yunon-lotin o'zaklari: -logiya, -ema, fono-);
- registr, uzunlik, apostrof va defis;
- ixtiyoriy **gazetteer**: token train lug'ati moslashtirgichi topgan spanning
  boshi/ichi ekanligi (``--gazetteer``). Lug'at faqat train to'plamidan.

Spanlar so'z chegarasida bo'ladi, shuning uchun BIO token darajasida aniq.

    PYTHONPATH=backend python -m app.models.crf train data/processed/silver/train.jsonl \\
        --dev data/processed/silver/validation.jsonl --model models/crf.crfsuite [--gazetteer data/terms.json]
    PYTHONPATH=backend python -m app.models.crf evaluate data/processed/silver/test.jsonl --model models/crf.crfsuite
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pycrfsuite

from app.dataset.annotation import AnnotatedRecord
from app.evaluation.metrics import Span
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.tokenize import Token, tokenize

OUTSIDE, BEGIN, INSIDE = "O", "B-TERM", "I-TERM"


@dataclass(frozen=True)
class CrfConfig:
    c1: float = 0.1
    c2: float = 0.05
    max_iterations: int = 200


def bio_labels(tokens: Sequence[Token], spans: Iterable[tuple[int, int]]) -> list[str]:
    labels = [OUTSIDE] * len(tokens)
    for start, end in spans:
        inside = [i for i, t in enumerate(tokens) if t.start >= start and t.end <= end]
        for position, index in enumerate(inside):
            labels[index] = BEGIN if position == 0 else INSIDE
    return labels


def spans_from_labels(tokens: Sequence[Token], labels: Sequence[str]) -> list[tuple[int, int]]:
    """BIO -> [start, end); yetim ``I`` yangi span boshlaydi (odatiy "lenient" dekodlash)."""
    spans: list[tuple[int, int]] = []
    current: list[int] | None = None
    for token, label in zip(tokens, labels):
        if label == BEGIN or (label == INSIDE and current is None):
            if current:
                spans.append((current[0], current[1]))
            current = [token.start, token.end]
        elif label == INSIDE and current is not None:
            current[1] = token.end
        else:
            if current:
                spans.append((current[0], current[1]))
            current = None
    if current:
        spans.append((current[0], current[1]))
    return spans


def gazetteer_tags(text: str, tokens: Sequence[Token], matcher: DictionaryMatcher | None) -> list[str]:
    if matcher is None:
        return [OUTSIDE] * len(tokens)
    return bio_labels(tokens, [(m.start, m.end) for m in matcher.find(text)])


def _shape(word: str) -> str:
    if word.isupper():
        return "UPPER"
    if word[:1].isupper():
        return "Title"
    return "lower"


def token_features(
    tokens: Sequence[Token], index: int, lemmatizer: CorpusLemmatizer, gazetteer: Sequence[str]
) -> list[str]:
    def describe(offset: int) -> list[str]:
        j = index + offset
        if j < 0:
            return [f"{offset}:BOS"]
        if j >= len(tokens):
            return [f"{offset}:EOS"]
        word = tokens[j].norm
        features = [f"{offset}:w={word}", f"{offset}:lemma={lemmatizer.lemma(word)}", f"{offset}:gaz={gazetteer[j]}"]
        if abs(offset) <= 1:
            features += [f"{offset}:suf3={word[-3:]}", f"{offset}:shape={_shape(tokens[j].text)}"]
        return features

    word = tokens[index].norm
    features = [
        "bias",
        f"suf2={word[-2:]}",
        f"suf3={word[-3:]}",
        f"suf4={word[-4:]}",
        f"suf5={word[-5:]}",
        f"pre3={word[:3]}",
        f"len={min(len(word), 12)}",
        f"apostrophe={chr(39) in word}",
    ]
    for offset in (-2, -1, 0, 1, 2):
        features += describe(offset)
    if index > 0:
        features.append(f"-1|0={tokens[index - 1].norm}|{word}")
    if index + 1 < len(tokens):
        features.append(f"0|+1={word}|{tokens[index + 1].norm}")
    return features


class TermCrf:
    def __init__(self, lemmatizer: CorpusLemmatizer, matcher: DictionaryMatcher | None = None) -> None:
        self.lemmatizer = lemmatizer
        self.matcher = matcher
        self.tagger: pycrfsuite.Tagger | None = None

    def sequence(self, text: str) -> tuple[list[Token], list[list[str]]]:
        tokens = tokenize(text)
        gazetteer = gazetteer_tags(text, tokens, self.matcher)
        return tokens, [token_features(tokens, i, self.lemmatizer, gazetteer) for i in range(len(tokens))]

    def train(self, records: Sequence[AnnotatedRecord], model_path: Path, config: CrfConfig = CrfConfig()) -> None:
        trainer = pycrfsuite.Trainer(verbose=False)
        for record in records:
            tokens, features = self.sequence(record.text)
            if tokens:
                trainer.append(features, bio_labels(tokens, [(s.start, s.end) for s in record.terms]))
        trainer.set_params(
            {
                "c1": config.c1,
                "c2": config.c2,
                "max_iterations": config.max_iterations,
                "feature.possible_transitions": True,
            }
        )
        model_path.parent.mkdir(parents=True, exist_ok=True)
        trainer.train(str(model_path))
        self.load(model_path)

    def load(self, model_path: Path) -> "TermCrf":
        self.tagger = pycrfsuite.Tagger()
        self.tagger.open(str(model_path))
        return self

    def predict_spans(self, text: str) -> list[tuple[int, int]]:
        if self.tagger is None:
            raise RuntimeError("model yuklanmagan")
        tokens, features = self.sequence(text)
        if not tokens:
            return []
        return spans_from_labels(tokens, self.tagger.tag(features))

    def predict(self, text: str) -> list[Span]:
        """Spanlar va lug'at shakli taklifi: lug'atda bo'lsa uning termini, aks holda lemmatizatsiya."""
        found = {(m.start, m.end): m for m in self.matcher.find(text)} if self.matcher else {}
        spans = []
        for start, end in self.predict_spans(text):
            match = found.get((start, end))
            if match is not None and not match.ambiguous:
                term = match.candidates[0].entry.term
            else:
                words = [t.norm for t in tokenize(text[start:end])]
                term = " ".join([*words[:-1], self.lemmatizer.lemma(words[-1])]) if words else None
            spans.append(Span(start, end, term))
        return spans


def build_lemmatizer(texts: Iterable[str]) -> CorpusLemmatizer:
    return CorpusLemmatizer(token.norm for text in texts for token in tokenize(text))


def save_meta(model_path: Path, meta: dict) -> None:
    model_path.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _records_from(paths: Sequence[Path]) -> list[AnnotatedRecord]:
    from app.dataset.annotation import load_annotations

    return load_annotations(paths)


def main(argv: list[str] | None = None) -> int:
    """Buyruq satri: o'qitish, saqlash, qayta yuklab baholash va matnni tahlil qilish."""
    import argparse
    import sys

    from app.database.term_store import load_terms
    from app.dataset.validate import REPO_ROOT
    from app.evaluation.metrics import exact_scores, partial_scores

    parser = argparse.ArgumentParser(description="CRF termin aniqlagich")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw", help="lemmatizator lug'ati uchun matnlar")
    commands = parser.add_subparsers(dest="command", required=True)

    train = commands.add_parser("train", help="o'qitish va saqlash")
    train.add_argument("files", nargs="+", type=Path, help="span JSONL (masalan data/processed/silver/train.jsonl)")
    train.add_argument("--model", type=Path, required=True)
    train.add_argument("--gazetteer", type=Path, help="lug'at (terms.json) — gazetteer xususiyati uchun")
    train.add_argument("--c1", type=float, default=0.1)
    train.add_argument("--c2", type=float, default=0.01)
    train.add_argument("--iterations", type=int, default=200)

    evaluate = commands.add_parser("evaluate", help="saqlangan modelni yuklab baholash")
    evaluate.add_argument("files", nargs="+", type=Path)
    evaluate.add_argument("--model", type=Path, required=True)

    predict = commands.add_parser("predict", help="matndan terminlarni topish")
    predict.add_argument("text")
    predict.add_argument("--model", type=Path, required=True)
    args = parser.parse_args(argv)

    lemmatizer = build_lemmatizer(p.read_text(encoding="utf-8") for p in sorted(args.raw.glob("*.txt")))

    def gazetteer_for(model_path: Path) -> DictionaryMatcher | None:
        meta_path = model_path.with_suffix(".json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        name = meta.get("gazetteer")
        if not name:
            return None
        path = Path(name) if Path(name).is_absolute() else REPO_ROOT / "data" / Path(name).name
        return DictionaryMatcher(load_terms(path))

    if args.command == "train":
        matcher = DictionaryMatcher(load_terms(args.gazetteer)) if args.gazetteer else None
        records = _records_from(args.files)
        model = TermCrf(lemmatizer, matcher)
        model.train(records, args.model, CrfConfig(args.c1, args.c2, args.iterations))
        save_meta(args.model, {"c1": args.c1, "c2": args.c2, "max_iterations": args.iterations,
                               "train_records": len(records),
                               "gazetteer": args.gazetteer.name if args.gazetteer else None,
                               "data": [p.as_posix() for p in args.files]})
        print(f"Model saqlandi: {args.model} ({len(records)} yozuv)")
        return 0

    if not args.model.exists():
        print(f"Model topilmadi: {args.model}", file=sys.stderr)
        return 1
    model = TermCrf(lemmatizer, gazetteer_for(args.model)).load(args.model)
    if args.command == "predict":
        for span in model.predict(args.text):
            print(f"[{span.start}, {span.end})  {args.text[span.start:span.end]}  ->  {span.term}")
        return 0

    records = _records_from(args.files)
    pairs = [([Span(s.start, s.end, s.term) for s in r.terms], model.predict(r.text)) for r in records]
    for name, scores in (("exact", exact_scores(pairs)), ("partial", partial_scores(pairs))):
        print(f"{name:<8} P={scores.precision:.3f} R={scores.recall:.3f} F1={scores.f1:.3f} "
              f"(oltin {scores.gold}, bashorat {scores.predicted})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
