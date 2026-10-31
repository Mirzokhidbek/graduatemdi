"""Meʼyorlashtirish (lug'at shaklini topish) aniqligi.

Har bir oltin spanning matndagi ko'rinishi uchun usul lug'at shaklini bashorat qiladi;
``normalize_form`` (registr va apostrofsiz) bo'yicha oltin ``term`` ga teng bo'lsa — to'g'ri.

Usullar:
- ``lowercase`` — o'zgarishsiz (kichik harf): pastki chegara;
- ``corpus_lemmatizer`` — oxirgi so'zdan qo'shimchani korpus lug'ati bo'yicha ajratish (CRF ichidagi usul);
- ``dictionary`` — faqat lug'at; topilmasa o'zgarishsiz;
- ``dictionary_morphology`` — ``TermNormalizer``: lug'at, keyin morfologik qoidalar va izofa.

Lug'at faqat train to'plamidan, shuning uchun test bo'yicha natija adolatli.
Ellipsis (``unli`` -> ``unli tovush``) hech qaysi usul bilan tiklanmaydi va alohida sanaladi.

    PYTHONPATH=backend python -m app.evaluation.normalization data/processed/silver/test.jsonl
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Callable, Sequence

from app.dataset.annotation import AnnotatedRecord, load_annotations
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.normalize import normalize_form
from app.nlp.tokenize import tokenize
from app.services.term_normalizer import TermNormalizer

Method = Callable[[str], str]


def methods(normalizer: TermNormalizer, lemmatizer: CorpusLemmatizer) -> dict[str, Method]:
    def corpus(surface: str) -> str:
        words = [t.norm for t in tokenize(surface)]
        return " ".join([*words[:-1], lemmatizer.lemma(words[-1])]) if words else surface

    def dictionary(surface: str) -> str:
        hit = normalizer._from_dictionary(surface)  # noqa: SLF001 — usullarni alohida o'lchash uchun
        return hit.lemma if hit else surface.lower()

    return {
        "lowercase": lambda surface: surface.lower(),
        "corpus_lemmatizer": corpus,
        "dictionary": dictionary,
        "dictionary_morphology": lambda surface: normalizer.normalize(surface).lemma,
    }


def evaluate(records: Sequence[AnnotatedRecord], normalizer: TermNormalizer, lemmatizer: CorpusLemmatizer) -> dict:
    spans = [(r.text[s.start : s.end], s.term) for r in records for s in r.terms]
    # ellipsis: lug'at shaklida matnda yo'q so'z bor (unli -> unli tovush)
    elliptic = sum(len(normalize_form(term).split()) > len(normalize_form(surface).split()) for surface, term in spans)
    result: dict = {"spans": len(spans), "elliptic": elliptic, "methods": {}}
    for name, method in methods(normalizer, lemmatizer).items():
        correct = sum(normalize_form(method(surface)) == normalize_form(term) for surface, term in spans)
        result["methods"][name] = {"correct": correct, "accuracy": correct / len(spans) if spans else None}
    # to'liq usulda qaysi qadam ishladi va qanchalik to'g'ri
    by_step: Counter = Counter()
    ok_by_step: Counter = Counter()
    errors = []
    for surface, term in spans:
        out = normalizer.normalize(surface)
        by_step[out.method] += 1
        if normalize_form(out.lemma) == normalize_form(term):
            ok_by_step[out.method] += 1
        elif len(errors) < 25:
            errors.append({"surface": surface, "gold": term, "predicted": out.lemma, "step": out.method})
    result["steps"] = {step: {"spans": n, "correct": ok_by_step[step], "accuracy": ok_by_step[step] / n}
                       for step, n in by_step.items()}
    result["errors"] = errors
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    from app.database.term_store import load_terms
    from app.dataset.validate import REPO_ROOT
    from app.models.crf import build_lemmatizer
    from app.services.term_normalizer import build_normalizer

    parser = argparse.ArgumentParser(description="Meʼyorlashtirish aniqligi")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--terms", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    texts = [p.read_text(encoding="utf-8") for p in sorted((REPO_ROOT / "data" / "raw").glob("*.txt"))]
    normalizer = build_normalizer(load_terms(args.terms), texts)
    result = evaluate(load_annotations(args.files), normalizer, build_lemmatizer(texts))
    print(f"Spanlar: {result['spans']} (ellipsis, tiklab bo'lmaydi: {result['elliptic']})")
    for name, r in result["methods"].items():
        print(f"  {name:<22} {r['correct']:>4} / {result['spans']}  = {r['accuracy']:.3f}")
    print("To'liq usul, qadamlar bo'yicha:")
    for step, r in result["steps"].items():
        print(f"  {step:<12} {r['correct']:>4} / {r['spans']:<4} = {r['accuracy']:.3f}")
    for e in result["errors"][:12]:
        print(f"    {e['surface']!r:32} oltin {e['gold']!r:28} bashorat {e['predicted']!r} ({e['step']})")
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
