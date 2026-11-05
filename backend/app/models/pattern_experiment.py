"""Lingvistik, statistik va gibrid termin aniqlash modellarini span darajasida solishtirish (2.1-bo'lim).

Usullar:

- ``pattern`` — faqat leksik-grammatik qolip (``app.nlp.patterns``): qolipga mos har bir
  zanjir termin deb olinadi;
- ``pattern+<ball>`` — gibrid: qolip zanjiri faqat uning statistik bali (C-value, NC-value
  yoki Weirdness) chegaradan yuqori bo'lsa olinadi; aks holda zanjirning bosh so'z bilan
  tugaydigan qisqaroq qismi tekshiriladi;
- solishtirish uchun: train lug'ati, CRF va CRF + gazetteer (``models/*.crfsuite``,
  ``app.models.experiment`` o'qitgan).

Statistik ballar butun soha korpusi (``data/raw``) bo'yicha **belgisiz** hisoblanadi —
annotatsiya ishlatilmaydi. Chegara (θ) faqat **validation** bo'yicha tanlanadi
(nomzodlar ballarining kvantillari to'ri), test bir marta baholanadi.

    PYTHONPATH=backend python -m app.models.pattern_experiment
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Callable, Mapping, Sequence

from app.database.term_store import load_terms
from app.dataset.annotation import load_annotations
from app.evaluation.evaluate import predict as dictionary_predict
from app.models.experiment import Predictor, bootstrap, per_record_counts, score, unseen_recall
from app.nlp.candidates import (
    Key,
    c_values,
    contrast_frequencies,
    extract_candidates,
    nc_values,
    weirdness_scores,
)
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.patterns import MorphTagger, PatternExtractor
from app.nlp.tokenize import tokenize

QUANTILES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)


def statistical_scores(
    documents: Mapping[str, str], contrast: Mapping[str, str], lemmatizer: CorpusLemmatizer
) -> dict[str, dict[Key, float]]:
    candidates = extract_candidates(documents, lemmatizer=lemmatizer)
    tokens = sum(len(tokenize(text)) for text in documents.values())
    scores = {"cvalue": c_values(candidates), "ncvalue": nc_values(candidates)}
    if contrast:
        counts, contrast_tokens = contrast_frequencies(contrast, set(candidates), lemmatizer)
        scores["weirdness"] = weirdness_scores(candidates, tokens, counts, contrast_tokens)
    return scores


def thresholds(values: Sequence[float]) -> list[float]:
    ordered = sorted(values)
    if not ordered:
        return [-math.inf]
    return sorted({-math.inf, *(ordered[int(q * (len(ordered) - 1))] for q in QUANTILES[1:])})


def tune_threshold(
    dev, tagger: MorphTagger, table: Mapping[Key, float]
) -> tuple[float, list[dict], Callable[[Key], bool]]:
    """Validation exact F1 bo'yicha eng yaxshi chegara."""
    base = PatternExtractor(tagger)
    keys = {s.key for record in dev for s in base.candidates(record.text)}
    grid = thresholds([table[k] for k in keys if k in table])
    trials, best = [], None
    for theta in grid:
        keep = (lambda t: lambda key: table.get(key, -math.inf) >= t)(theta)
        f1 = score(dev, PatternExtractor(tagger, keep).extract)["exact"]["f1"] or 0.0
        trials.append({"threshold": None if theta == -math.inf else theta, "validation_exact_f1": f1})
        if best is None or f1 > best[0]:
            best = (f1, theta, keep)
    assert best is not None
    return best[1], trials, best[2]


def run(data_dir: Path, raw_dir: Path, contrast_dir: Path | None, train_terms: Path, model_dir: Path) -> dict:
    train = load_annotations([data_dir / "train.jsonl"])
    dev = load_annotations([data_dir / "validation.jsonl"])
    test = load_annotations([data_dir / "test.jsonl"])
    documents = {p.stem: p.read_text(encoding="utf-8") for p in sorted(raw_dir.glob("*.txt"))}
    contrast = (
        {p.stem: p.read_text(encoding="utf-8") for p in sorted(contrast_dir.glob("*.txt"))} if contrast_dir else {}
    )
    lemmatizer = CorpusLemmatizer(t.norm for text in documents.values() for t in tokenize(text))
    tagger = MorphTagger(lemmatizer)
    tables = statistical_scores(documents, contrast, lemmatizer)

    methods: dict[str, Predictor] = {"pattern": PatternExtractor(tagger).extract}
    tuning = {}
    for name, table in tables.items():
        theta, trials, keep = tune_threshold(dev, tagger, table)
        tuning[f"pattern+{name}"] = {"threshold": None if theta == -math.inf else theta, "trials": trials}
        methods[f"pattern+{name}"] = PatternExtractor(tagger, keep).extract

    references: dict[str, Predictor] = {
        "dictionary_train": lambda text: dictionary_predict(DictionaryMatcher(load_terms(train_terms)), text)
    }
    try:
        from app.models.crf import TermCrf

        for name, gazetteer in (("crf", None), ("crf_gazetteer", DictionaryMatcher(load_terms(train_terms)))):
            path = model_dir / f"{name.replace('_', '-')}.crfsuite"
            if path.is_file():
                references[name] = TermCrf(lemmatizer, gazetteer).load(path).predict
    except ImportError:  # python-crfsuite yo'q
        pass
    matcher = DictionaryMatcher(load_terms(train_terms))
    references["dictionary_train"] = lambda text: dictionary_predict(matcher, text)
    everything = {**methods, **references}

    return {
        "data": Path(os.path.relpath(data_dir, model_dir.parent)).as_posix(),
        "contrast_documents": len(contrast),
        "records": {"train": len(train), "validation": len(dev), "test": len(test)},
        "tuning": tuning,
        "validation": {name: score(dev, predict) for name, predict in everything.items()},
        "test": {name: score(test, predict) for name, predict in everything.items()},
        "test_unseen_terms": {name: unseen_recall(train, test, predict) for name, predict in everything.items()},
        "test_bootstrap": bootstrap(
            {name: per_record_counts(test, predict) for name, predict in everything.items()}, baseline="pattern"
        ),
    }


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    import argparse

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Lingvistik / statistik / gibrid ATE modellarini solishtirish")
    parser.add_argument("--data", type=Path, default=REPO_ROOT / "data" / "processed" / "silver")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--contrast", type=Path, default=REPO_ROOT / "data" / "contrast" / "raw")
    parser.add_argument("--train-terms", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--models", type=Path, default=REPO_ROOT / "models")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports" / "experiment-patterns.json")
    args = parser.parse_args(argv)

    contrast = args.contrast if args.contrast and args.contrast.is_dir() else None
    report = run(args.data, args.raw, contrast, args.train_terms, args.models)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for split in ("validation", "test"):
        print(f"\n{split}:  {'usul':<20} {'P':>6} {'R':>6} {'F1':>6} | partial F1 | term acc")
        for name, result in report[split].items():
            exact = result["exact"]
            print(f"   {name:<20} {_fmt(exact['precision']):>6} {_fmt(exact['recall']):>6} {_fmt(exact['f1']):>6} | "
                  f"{_fmt(result['partial']['f1']):>10} | {_fmt(result['term_accuracy'])}")
    print("\nChegaralar (validation):", {k: v["threshold"] for k, v in report["tuning"].items()})
    print("\nTest: train'da uchramagan terminlar bo'yicha recall")
    for name, result in report["test_unseen_terms"].items():
        print(f"   {name:<20} {result['found']}/{result['gold']} = {_fmt(result['recall'])}")
    boot = report["test_bootstrap"]
    print("\nTest, exact F1 95% oraliq; pattern dan farq:")
    for name, (low, high) in boot["f1_ci95"].items():
        delta = boot["delta_vs_baseline_ci95"].get(name)
        extra = f"   farq: [{delta[0]:+.3f}, {delta[1]:+.3f}]" if delta else ""
        print(f"   {name:<20} [{low:.3f}, {high:.3f}]{extra}")
    print(f"\nHisobot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
