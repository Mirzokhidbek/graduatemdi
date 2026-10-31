"""Usullarni bir xil to'plamda solishtirish: lug'at baseline'lari va CRF (metodika, 3–4-bo'limlar).

Tartib (``docs/experiment-methodology.md``):
1. CRF giperparametrlari (c1, c2) faqat **validation** bo'yicha tanlanadi;
2. tanlangan konfiguratsiya train'da o'qitiladi va **test** bir marta baholanadi;
3. har bir usul uchun exact va partial P/R/F1, exact mosliklarda lug'at shakli aniqligi.

Maʼlumot: standart bo'yicha AI (Claude) annotatsiyasi — "kumush" to'plam. Natija
inson oltin standarti emas va hisobotda shunday belgilanadi.

    PYTHONPATH=backend python -m app.models.experiment --data data/processed/silver --output reports/experiment-silver.json
"""

from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
from typing import Callable, Sequence

from app.database.term_store import load_terms
from app.dataset.annotation import AnnotatedRecord, load_annotations
from app.evaluation.evaluate import predict as dictionary_predict
from app.evaluation.metrics import Span, exact_scores, partial_scores
from app.models.crf import CrfConfig, TermCrf, build_lemmatizer, save_meta
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.nlp.normalize import normalize_form

Predictor = Callable[[str], list[Span]]
C1_GRID = (0.01, 0.1, 0.5)
C2_GRID = (0.01, 0.05, 0.2)


def score(records: Sequence[AnnotatedRecord], predict: Predictor) -> dict:
    pairs = []
    matched = term_ok = 0
    for record in records:
        gold = [Span(s.start, s.end, s.term) for s in record.terms]
        predicted = predict(record.text)
        pairs.append((gold, predicted))
        by_key = {(p.start, p.end): p for p in predicted}
        for span in gold:
            hit = by_key.get((span.start, span.end))
            if hit is not None:
                matched += 1
                term_ok += hit.term is not None and normalize_form(hit.term) == normalize_form(span.term)
    return {
        "exact": exact_scores(pairs).to_dict(),
        "partial": partial_scores(pairs).to_dict(),
        "term_accuracy": term_ok / matched if matched else None,
    }


def per_record_counts(records: Sequence[AnnotatedRecord], predict: Predictor) -> list[tuple[int, int, int]]:
    """Har bir yozuv uchun (to'g'ri, bashorat, oltin) — exact mezon."""
    counts = []
    for record in records:
        gold = {(s.start, s.end) for s in record.terms}
        predicted = {(p.start, p.end) for p in predict(record.text)}
        counts.append((len(gold & predicted), len(predicted), len(gold)))
    return counts


def _f1(counts: Sequence[tuple[int, int, int]]) -> float:
    correct = sum(c[0] for c in counts)
    predicted = sum(c[1] for c in counts)
    gold = sum(c[2] for c in counts)
    if not predicted or not gold or not correct:
        return 0.0
    precision, recall = correct / predicted, correct / gold
    return 2 * precision * recall / (precision + recall)


def bootstrap(
    counts_by_method: dict[str, list[tuple[int, int, int]]], baseline: str, samples: int = 2000, seed: int = 13
) -> dict:
    """Yozuvlar bo'yicha bootstrap: har bir usulning exact F1 uchun 95% ishonch oralig'i va baseline'dan
    farqning oralig'i (bir xil qayta tanlanmalarda — juftlangan)."""
    import random

    rng = random.Random(seed)
    n = len(next(iter(counts_by_method.values())))
    f1s: dict[str, list[float]] = {name: [] for name in counts_by_method}
    deltas: dict[str, list[float]] = {name: [] for name in counts_by_method if name != baseline}
    for _ in range(samples):
        idx = [rng.randrange(n) for _ in range(n)]
        values = {name: _f1([c[i] for i in idx]) for name, c in counts_by_method.items()}
        for name, value in values.items():
            f1s[name].append(value)
        for name in deltas:
            deltas[name].append(values[name] - values[baseline])

    def interval(values: list[float]) -> list[float]:
        ordered = sorted(values)
        return [round(ordered[int(0.025 * len(ordered))], 4), round(ordered[int(0.975 * len(ordered)) - 1], 4)]

    return {
        "samples": samples,
        "unit": "yozuv (paragraf)",
        "f1_ci95": {name: interval(v) for name, v in f1s.items()},
        "baseline": baseline,
        "delta_vs_baseline_ci95": {name: interval(v) for name, v in deltas.items()},
    }


def unseen_recall(train: Sequence[AnnotatedRecord], test: Sequence[AnnotatedRecord], predict: Predictor) -> dict:
    """Train'da hech uchramagan lug'at shakllari bo'yicha recall: usul yangi terminni topa oladimi."""
    seen = {normalize_form(s.term) for r in train for s in r.terms}
    total = found = 0
    for record in test:
        keys = {(p.start, p.end) for p in predict(record.text)}
        for span in record.terms:
            if normalize_form(span.term) in seen:
                continue
            total += 1
            found += (span.start, span.end) in keys
    return {"gold": total, "found": found, "recall": found / total if total else None}


def run(
    data_dir: Path, seed_terms: Path, train_terms: Path, raw_dir: Path, model_dir: Path, test_files: Sequence[Path] = ()
) -> dict:
    train = load_annotations([data_dir / "train.jsonl"])
    dev = load_annotations([data_dir / "validation.jsonl"])
    test = load_annotations(list(test_files) or [data_dir / "test.jsonl"])
    lemmatizer = build_lemmatizer(p.read_text(encoding="utf-8") for p in sorted(raw_dir.glob("*.txt")))
    seed_matcher = DictionaryMatcher(load_terms(seed_terms))
    train_matcher = DictionaryMatcher(load_terms(train_terms))

    def tune(gazetteer: DictionaryMatcher | None, name: str) -> tuple[TermCrf, CrfConfig, list[dict]]:
        trials = []
        best: tuple[float, CrfConfig] | None = None
        for c1, c2 in itertools.product(C1_GRID, C2_GRID):
            config = CrfConfig(c1=c1, c2=c2)
            model = TermCrf(lemmatizer, gazetteer)
            model.train(train, model_dir / f"{name}-tuning.crfsuite", config)
            f1 = score(dev, model.predict)["exact"]["f1"] or 0.0
            trials.append({"c1": c1, "c2": c2, "validation_exact_f1": f1})
            if best is None or f1 > best[0]:
                best = (f1, config)
        assert best is not None
        model = TermCrf(lemmatizer, gazetteer)
        model.train(train, model_dir / f"{name}.crfsuite", best[1])
        (model_dir / f"{name}-tuning.crfsuite").unlink(missing_ok=True)
        save_meta(
            model_dir / f"{name}.crfsuite",
            {
                "c1": best[1].c1,
                "c2": best[1].c2,
                "train_records": len(train),
                "gazetteer": str(train_terms.name) if gazetteer else None,
                "data": Path(os.path.relpath(data_dir, model_dir.parent)).as_posix(),
            },
        )
        return model, best[1], trials

    crf, crf_config, crf_trials = tune(None, "crf")
    crf_gaz, gaz_config, gaz_trials = tune(train_matcher, "crf-gazetteer")

    methods: dict[str, Predictor] = {
        "dictionary_seed": lambda text: dictionary_predict(seed_matcher, text),
        "dictionary_train": lambda text: dictionary_predict(train_matcher, text),
        "crf": crf.predict,
        "crf_gazetteer": crf_gaz.predict,
    }
    report = {
        "data": Path(os.path.relpath(data_dir, model_dir.parent)).as_posix(),
        "test_files": [Path(os.path.relpath(p, model_dir.parent)).as_posix() for p in test_files] or None,
        "records": {"train": len(train), "validation": len(dev), "test": len(test)},
        "spans": {
            "train": sum(len(r.terms) for r in train),
            "validation": sum(len(r.terms) for r in dev),
            "test": sum(len(r.terms) for r in test),
        },
        "tuning": {
            "crf": {"chosen": crf_config.__dict__, "trials": crf_trials},
            "crf_gazetteer": {"chosen": gaz_config.__dict__, "trials": gaz_trials},
        },
        "validation": {name: score(dev, predict) for name, predict in methods.items()},
        "test": {name: score(test, predict) for name, predict in methods.items()},
        "test_unseen_terms": {name: unseen_recall(train, test, predict) for name, predict in methods.items()},
        "test_bootstrap": bootstrap(
            {name: per_record_counts(test, predict) for name, predict in methods.items()}, baseline="dictionary_train"
        ),
    }
    return report


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    import argparse

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Lug'at baseline'lari va CRF'ni solishtirish")
    parser.add_argument("--data", type=Path, default=REPO_ROOT / "data" / "processed" / "silver")
    parser.add_argument("--seed-terms", type=Path, default=REPO_ROOT / "data" / "terms-seed.json")
    parser.add_argument("--train-terms", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--models", type=Path, default=REPO_ROOT / "models")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports" / "experiment-silver.json")
    parser.add_argument("--test-files", type=Path, nargs="*", default=[],
                        help="test to'plami o'rniga shu JSONL fayllar (masalan, boshqa annotatorning test belgilari)")
    args = parser.parse_args(argv)

    report = run(args.data, args.seed_terms, args.train_terms, args.raw, args.models, args.test_files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Yozuvlar: {report['records']}, spanlar: {report['spans']}")
    for split in ("validation", "test"):
        print(f"\n{split}:  {'usul':<18} {'P':>6} {'R':>6} {'F1':>6} | partial F1 | term acc")
        for name, result in report[split].items():
            exact = result["exact"]
            print(f"   {name:<18} {_fmt(exact['precision']):>6} {_fmt(exact['recall']):>6} {_fmt(exact['f1']):>6} | "
                  f"{_fmt(result['partial']['f1']):>10} | {_fmt(result['term_accuracy'])}")
    print("\nTest: train'da uchramagan terminlar bo'yicha recall")
    for name, result in report["test_unseen_terms"].items():
        print(f"   {name:<18} {result['found']}/{result['gold']} = {_fmt(result['recall'])}")
    boot = report["test_bootstrap"]
    print(f"\nTest, exact F1 95% ishonch oralig'i (bootstrap, {boot['samples']} ta qayta tanlanma):")
    for name, (low, high) in boot["f1_ci95"].items():
        delta = boot["delta_vs_baseline_ci95"].get(name)
        extra = f"   {boot['baseline']} dan farq: [{delta[0]:+.3f}, {delta[1]:+.3f}]" if delta else ""
        print(f"   {name:<18} [{low:.3f}, {high:.3f}]{extra}")
    print(f"\nHisobot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
