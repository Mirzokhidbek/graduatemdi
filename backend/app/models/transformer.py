"""Transformer (XLM-R / mBERT) asosida termin aniqlash: token classification.

CRF bilan bir xil sharoitda solishtirish uchun:
- so'zlar ``app.nlp.tokenize`` bo'yicha (CRF bilan bir xil), BIO teglar ``bio_labels`` bo'yicha;
- subword'larga bo'linganda teg faqat so'zning **birinchi** subword'iga beriladi, qolganlari
  yo'qotish (loss) hisobidan chiqariladi (-100);
- uzun paragraflar ``chunk_words`` so'zlik bo'laklarga ajratiladi (512 subword chegarasi);
- epoxa validation exact F1 bo'yicha tanlanadi, test bir marta baholanadi;
- metrikalar, bootstrap va yangi terminlar recall'i ``app.models.experiment`` dagi funksiyalar.

GPU kerak (Google Colab, T4: xlm-roberta-base uchun ~10 daqiqa). Ishga tushirish::

    pip install torch transformers
    PYTHONPATH=backend python -m app.models.transformer --model xlm-roberta-base
    # o'sha modelni qayta-belgilangan testda (o'qitmasdan):
    PYTHONPATH=backend python -m app.models.transformer --load \
        --test-files data/annotations/claude2/*.jsonl --output reports/experiment-transformer-test2.json

``torch`` va ``transformers`` faqat o'qitish/bashorat paytida import qilinadi, shuning uchun
qolgan loyiha (va ushbu moduldagi yordamchi funksiyalar testlari) ularsiz ishlaydi.
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.dataset.annotation import AnnotatedRecord
from app.evaluation.metrics import Span
from app.models.crf import bio_labels, spans_from_labels
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.tokenize import Token, tokenize

LABELS = ("O", "B-TERM", "I-TERM")
LABEL_ID = {label: i for i, label in enumerate(LABELS)}
IGNORE = -100


@dataclass
class TransformerConfig:
    model_name: str = "xlm-roberta-base"
    epochs: int = 10
    learning_rate: float = 3e-5
    batch_size: int = 8
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    chunk_words: int = 150
    max_length: int = 512
    seed: int = 13


# --- toza Python yordamchilar (torch'siz test qilinadi) -------------------------------------


def chunk_words(n_words: int, size: int) -> list[tuple[int, int]]:
    """So'zlar ketma-ketligini ``size`` so'zdan oshmaydigan, ustma-ust tushmaydigan bo'laklarga ajratadi."""
    if size < 1:
        raise ValueError("size >= 1 bo'lishi kerak")
    return [(start, min(start + size, n_words)) for start in range(0, n_words, size)]


def align_labels(word_ids: Sequence[int | None], word_labels: Sequence[str]) -> list[int]:
    """Subword'larga teg: so'zning birinchi subword'i — so'z tegi, qolgani va maxsus tokenlar — IGNORE."""
    aligned = []
    previous = None
    for word_id in word_ids:
        if word_id is None or word_id == previous:
            aligned.append(IGNORE)
        else:
            aligned.append(LABEL_ID[word_labels[word_id]])
        previous = word_id
    return aligned


def word_predictions(word_ids: Sequence[int | None], subword_labels: Sequence[int], n_words: int) -> list[str]:
    """Subword bashoratlaridan so'z teglari: har bir so'zning birinchi subword'i olinadi.

    ``max_length`` tufayli kesilgan so'zlar (bashorati yo'q) ``O`` deb olinadi.
    """
    labels = ["O"] * n_words
    seen: set[int] = set()
    for word_id, label in zip(word_ids, subword_labels):
        if word_id is None or word_id in seen:
            continue
        seen.add(word_id)
        labels[word_id] = LABELS[label]
    return labels


def encode_records(
    records: Sequence[AnnotatedRecord], tokenizer: Any, config: TransformerConfig
) -> list[dict[str, list[int]]]:
    """O'qitish namunalari: har bir paragraf bo'lagi — ``input_ids``, ``attention_mask``, ``labels``."""
    examples = []
    for record in records:
        tokens = tokenize(record.text)
        if not tokens:
            continue
        labels = bio_labels(tokens, [(s.start, s.end) for s in record.terms])
        for start, end in chunk_words(len(tokens), config.chunk_words):
            words = [t.text for t in tokens[start:end]]
            enc = tokenizer(words, is_split_into_words=True, truncation=True, max_length=config.max_length)
            examples.append(
                {
                    "input_ids": enc["input_ids"],
                    "attention_mask": enc["attention_mask"],
                    "labels": align_labels(enc.word_ids(), labels[start:end]),
                }
            )
    return examples


# --- model ---------------------------------------------------------------------------------


class TermTransformer:
    """O'qitilgan model atrofidagi qobiq: ``predict(text) -> list[Span]`` (CRF bilan bir xil interfeys)."""

    def __init__(self, model: Any, tokenizer: Any, lemmatizer: CorpusLemmatizer, config: TransformerConfig) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.lemmatizer = lemmatizer
        self.config = config

    @classmethod
    def load(cls, path: Path, lemmatizer: CorpusLemmatizer) -> TermTransformer:
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        meta = json.loads((path / "uzterm.json").read_text(encoding="utf-8"))
        config = TransformerConfig(**meta["config"])
        model = AutoModelForTokenClassification.from_pretrained(path)
        return cls(model, AutoTokenizer.from_pretrained(path), lemmatizer, config)

    def save(self, path: Path, extra: dict | None = None) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        meta = {"config": asdict(self.config), **(extra or {})}
        (path / "uzterm.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _word_labels(self, tokens: Sequence[Token]) -> list[str]:
        import torch

        device = next(self.model.parameters()).device
        labels: list[str] = []
        for start, end in chunk_words(len(tokens), self.config.chunk_words):
            words = [t.text for t in tokens[start:end]]
            enc = self.tokenizer(
                words, is_split_into_words=True, truncation=True, max_length=self.config.max_length, return_tensors="pt"
            )
            with torch.no_grad():
                logits = self.model(
                    input_ids=enc["input_ids"].to(device), attention_mask=enc["attention_mask"].to(device)
                ).logits
            predicted = logits.argmax(-1)[0].tolist()
            labels += word_predictions(enc.word_ids(), predicted, end - start)
        return labels

    def predict_spans(self, text: str) -> list[tuple[int, int]]:
        tokens = tokenize(text)
        if not tokens:
            return []
        self.model.eval()
        return spans_from_labels(tokens, self._word_labels(tokens))

    def predict(self, text: str) -> list[Span]:
        """Spanlar va lug'at shakli taklifi (oxirgi so'z lemmatizatsiya qilinadi, CRF kabi)."""
        spans = []
        for start, end in self.predict_spans(text):
            words = [t.norm for t in tokenize(text[start:end])]
            term = " ".join([*words[:-1], self.lemmatizer.lemma(words[-1])]) if words else None
            spans.append(Span(start, end, term))
        return spans


def _set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def train(
    train_records: Sequence[AnnotatedRecord],
    dev_records: Sequence[AnnotatedRecord],
    lemmatizer: CorpusLemmatizer,
    config: TransformerConfig,
    output_dir: Path,
    model: Any = None,
    tokenizer: Any = None,
    log: Any = print,
) -> tuple[TermTransformer, list[dict]]:
    """O'qitadi, har epoxadan keyin validation exact F1 ni o'lchaydi va eng yaxshi epoxani saqlaydi.

    ``model``/``tokenizer`` berilmasa ``config.model_name`` dan yuklanadi (HuggingFace Hub).
    """
    import torch
    from torch.utils.data import DataLoader
    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        DataCollatorForTokenClassification,
        get_linear_schedule_with_warmup,
    )

    from app.models.experiment import score

    _set_seed(config.seed)
    if tokenizer is None:
        tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    if model is None:
        model = AutoModelForTokenClassification.from_pretrained(
            config.model_name,
            num_labels=len(LABELS),
            id2label=dict(enumerate(LABELS)),
            label2id=LABEL_ID,
        )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    examples = encode_records(train_records, tokenizer, config)
    generator = torch.Generator().manual_seed(config.seed)
    loader = DataLoader(
        examples,
        batch_size=config.batch_size,
        shuffle=True,
        generator=generator,
        collate_fn=DataCollatorForTokenClassification(tokenizer),
    )
    no_decay = ("bias", "LayerNorm.weight", "layer_norm.weight")
    groups = [
        {"params": [p for n, p in model.named_parameters() if not any(k in n for k in no_decay)],
         "weight_decay": config.weight_decay},
        {"params": [p for n, p in model.named_parameters() if any(k in n for k in no_decay)], "weight_decay": 0.0},
    ]
    optimizer = torch.optim.AdamW(groups, lr=config.learning_rate)
    total = len(loader) * config.epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, int(config.warmup_ratio * total), total)

    tagger = TermTransformer(model, tokenizer, lemmatizer, config)
    history: list[dict] = []
    best_f1 = -1.0
    for epoch in range(1, config.epochs + 1):
        model.train()
        started, loss_sum = time.time(), 0.0
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            loss_sum += loss.item()
        f1 = score(dev_records, tagger.predict)["exact"]["f1"] or 0.0
        history.append({"epoch": epoch, "loss": loss_sum / max(len(loader), 1), "validation_exact_f1": f1})
        log(f"epoxa {epoch:2d}: loss {history[-1]['loss']:.4f}, validation F1 {f1:.3f} ({time.time() - started:.0f} s)")
        if f1 > best_f1:
            best_f1 = f1
            tagger.save(output_dir, {"best_epoch": epoch, "history": history})
    best = TermTransformer.load(output_dir, lemmatizer)
    best.model.to(device)
    return best, history


def run(
    data_dir: Path,
    raw_dir: Path,
    train_terms: Path,
    crf_dir: Path,
    config: TransformerConfig,
    output_dir: Path,
    test_files: Sequence[Path] = (),
    load: bool = False,
) -> dict:
    """Transformer'ni o'qitib (yoki ``load`` bo'lsa ``output_dir`` dan yuklab), uni lug'at va saqlangan
    CRF modellari bilan bir xil testda solishtiradi."""
    from app.database.term_store import load_terms
    from app.dataset.annotation import load_annotations
    from app.evaluation.evaluate import predict as dictionary_predict
    from app.models.crf import TermCrf, build_lemmatizer
    from app.models.experiment import bootstrap, per_record_counts, score, unseen_recall
    from app.nlp.dictionary_matcher import DictionaryMatcher

    train_records = load_annotations([data_dir / "train.jsonl"])
    dev = load_annotations([data_dir / "validation.jsonl"])
    test = load_annotations(list(test_files) or [data_dir / "test.jsonl"])
    lemmatizer = build_lemmatizer(p.read_text(encoding="utf-8") for p in sorted(raw_dir.glob("*.txt")))
    matcher = DictionaryMatcher(load_terms(train_terms))

    if load:
        import torch

        model = TermTransformer.load(output_dir, lemmatizer)
        model.model.to("cuda" if torch.cuda.is_available() else "cpu")
        config = model.config
        history = json.loads((output_dir / "uzterm.json").read_text(encoding="utf-8"))["history"]
    else:
        model, history = train(train_records, dev, lemmatizer, config, output_dir)
    methods = {
        "dictionary_train": lambda text: dictionary_predict(matcher, text),
        "crf": TermCrf(lemmatizer).load(crf_dir / "crf.crfsuite").predict,
        "crf_gazetteer": TermCrf(lemmatizer, matcher).load(crf_dir / "crf-gazetteer.crfsuite").predict,
        "transformer": model.predict,
    }
    return {
        "model": config.model_name,
        "config": asdict(config),
        "history": history,
        "best_epoch": max(history, key=lambda h: h["validation_exact_f1"])["epoch"],
        "split": data_dir.name,
        "test_files": [p.as_posix() for p in test_files] or None,
        "validation": {name: score(dev, predict) for name, predict in methods.items()},
        "test": {name: score(test, predict) for name, predict in methods.items()},
        "test_unseen_terms": {name: unseen_recall(train_records, test, p) for name, p in methods.items()},
        "test_bootstrap": bootstrap(
            {name: per_record_counts(test, predict) for name, predict in methods.items()}, baseline="crf_gazetteer"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Transformer termin aniqlagich (token classification)")
    parser.add_argument("--model", default=TransformerConfig.model_name, help="xlm-roberta-base, bert-base-multilingual-cased, ...")
    parser.add_argument("--epochs", type=int, default=TransformerConfig.epochs)
    parser.add_argument("--lr", type=float, default=TransformerConfig.learning_rate)
    parser.add_argument("--batch-size", type=int, default=TransformerConfig.batch_size)
    parser.add_argument("--seed", type=int, default=TransformerConfig.seed)
    parser.add_argument("--data", type=Path, default=REPO_ROOT / "data" / "processed" / "silver")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--terms", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--crf-dir", type=Path, default=REPO_ROOT / "models")
    parser.add_argument("--test-files", type=Path, nargs="*", default=[])
    parser.add_argument("--save", type=Path, default=REPO_ROOT / "models" / "transformer")
    parser.add_argument("--load", action="store_true", help="o'qitmasdan --save dagi modelni baholash")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports" / "experiment-transformer.json")
    args = parser.parse_args(argv)

    config = TransformerConfig(
        model_name=args.model, epochs=args.epochs, learning_rate=args.lr, batch_size=args.batch_size, seed=args.seed
    )
    report = run(args.data, args.raw, args.terms, args.crf_dir, config, args.save, args.test_files, load=args.load)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\nEng yaxshi epoxa (validation): {report['best_epoch']}")
    for split in ("validation", "test"):
        print(f"\n{split}:  usul                    P      R     F1 | partial F1")
        for name, r in report[split].items():
            e = r["exact"]
            print(f"   {name:18s} {e['precision']:.3f}  {e['recall']:.3f}  {e['f1']:.3f} |      {r['partial']['f1']:.3f}")
    print("\nTrain'da uchramagan terminlar (test):")
    for name, r in report["test_unseen_terms"].items():
        print(f"   {name:18s} {r['found']}/{r['gold']} = {r['recall']:.3f}")
    boot = report["test_bootstrap"]
    print("\nTest F1, 95% oraliq; crf_gazetteer dan farq:")
    for name, ci in boot["f1_ci95"].items():
        delta = boot["delta_vs_baseline_ci95"].get(name)
        print(f"   {name:18s} [{ci[0]:.3f}, {ci[1]:.3f}]" + (f"   farq: [{delta[0]:+.3f}, {delta[1]:+.3f}]" if delta else ""))
    print(f"\nHisobot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
