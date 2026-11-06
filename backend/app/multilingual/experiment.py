"""Ko'p tilli moslashtirish tajribasi (3.3-bo'lim, 3.7–3.8-jadvallar).

1. Ruscha va inglizcha terminlardan oʻzbekcha ekvivalentni topish:
   ``data/multilingual/equivalents-silver.csv`` (120 ta uz–ru–en uchligi; Claude tuzgan,
   ekspert tekshiruvi kerak — "kumush" maʼlumot). Nomzodlar — lug'at (450) va shu ro'yxatdagi
   barcha oʻzbekcha terminlar. Acc@1, Acc@5, MRR; xalqaro va oʻzbekcha (native) terminlar alohida.
2. Bir nechta oʻzbekcha muqobili bor manba terminlar uchun meʼyoriy muqobilni tanlash
   (3.1.4-qoidalar: tasdiqlangan → lug'atdagi meʼyoriy shakl → korpus chastotasi → qisqalik).
3. Korpusdagi etimologik izohlar -> ``data/multilingual/etymons.csv``.

    PYTHONPATH=backend python -m app.multilingual.experiment            # kognat modeli (oflayn)
    PYTHONPATH=backend python -m app.multilingual.experiment --encoder  # + LaBSE (internet, GPU tavsiya)
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from app.database.term_store import load_terms
from app.multilingual.align import Aligner, CascadeAligner, gold_by_source, load_gold, ranking_metrics
from app.multilingual.sources import extract_etymons, sentence_encoder
from app.nlp.candidates import build_lemmatizer, extract_candidates, lemmatize_form
from app.variation.groups import choose_preferred

KINDS = ("international", "native", None)


def evaluate(aligner: Aligner, rows, lang: str) -> dict:
    out = {}
    for kind in KINDS:
        gold = gold_by_source(rows, lang, kind)
        sources = list(gold)
        ranked = [[c.uz for c in cands] for cands in aligner.rank(sources, lang, top=5)]
        out[kind or "all"] = ranking_metrics(ranked, [gold[s] for s in sources])
    return out


def abstention(aligner: Aligner, rows, lang: str, thresholds=(0.5, 0.6, 0.7, 0.8)) -> list[dict]:
    """Ishonch chegarasi: eng yaxshi nomzod bali θ dan past bo'lsa, model javob bermaydi.
    Qamrov (javob berilganlar ulushi) va javob berilganlar orasidagi aniqlik."""
    gold = gold_by_source(rows, lang)
    sources = list(gold)
    top = [cands[0] for cands in aligner.rank(sources, lang, top=1)]
    out = []
    for theta in thresholds:
        answered = [(s, c) for s, c in zip(sources, top) if c.score >= theta]
        correct = sum(c.uz in gold[s] for s, c in answered)
        out.append({
            "threshold": theta,
            "coverage": len(answered) / len(sources) if sources else 0.0,
            "precision": correct / len(answered) if answered else None,
            "answered": len(answered),
        })
    return out


def errors(aligner: Aligner, rows, lang: str, limit: int = 15) -> list[dict]:
    gold = gold_by_source(rows, lang)
    sources = list(gold)
    result = []
    for source, cands in zip(sources, aligner.rank(sources, lang, top=3)):
        if cands and cands[0].uz not in gold[source]:
            result.append({"source": source, "gold": sorted(gold[source]), "top3": [c.uz for c in cands]})
    return result[:limit]


def preferred_choices(rows, documents, entries) -> list[dict]:
    """Bir nechta oʻzbekcha muqobili bor (ruscha bo'yicha) terminlar uchun tavsiya."""
    lemmatizer = build_lemmatizer(documents)
    freq = {c.key: c.frequency for c in extract_candidates(documents, lemmatizer=lemmatizer).values()}
    choices = []
    for ru, uz_forms in gold_by_source(rows, "ru").items():
        if len(uz_forms) < 2:
            continue
        counts = Counter({uz: freq.get(lemmatize_form(uz, lemmatizer), 0) for uz in uz_forms})
        preferred, status, reasons = choose_preferred(counts, entries)
        choices.append({"ru": ru, "uz": dict(counts), "preferred": preferred, "status": status, "reasons": reasons})
    return choices


def main(argv: list[str] | None = None) -> int:
    import argparse

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Ko'p tilli terminlarni moslashtirish tajribasi")
    parser.add_argument("--gold", type=Path, default=REPO_ROOT / "data" / "multilingual" / "equivalents-silver.csv")
    parser.add_argument("--terms", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--encoder", action="store_true", help="LaBSE embedding modeli (sentence-transformers)")
    parser.add_argument("--weight", type=float, default=0.5, help="gibrid: embedding og'irligi")
    parser.add_argument("--etymons", type=Path, default=REPO_ROOT / "data" / "multilingual" / "etymons.csv")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports" / "multilingual.json")
    args = parser.parse_args(argv)

    rows = load_gold(args.gold)
    entries = load_terms(args.terms)
    targets = [e.term for e in entries] + [r["uz"] for r in rows]
    documents = {p.stem: p.read_text(encoding="utf-8") for p in sorted(args.raw.glob("*.txt"))}

    models = {"cognate": Aligner(targets)}
    if args.encoder:
        encoder = sentence_encoder()
        if encoder is None:
            print("sentence-transformers o'rnatilmagan: pip install sentence-transformers")
            return 1
        models["semantic"] = Aligner(targets, encoder, weight=1.0)
        models["hybrid"] = Aligner(targets, encoder, weight=args.weight)
        models["cascade"] = CascadeAligner(models["cognate"], models["semantic"], threshold=0.7)

    report = {
        "gold": {"file": args.gold.name, "rows": len(rows), "kinds": dict(Counter(r["kind"] for r in rows)),
                 "note": "Claude tuzgan, ekspert tekshiruvi kerak (kumush maʼlumot)"},
        "candidates": len(set(targets)),
        "results": {name: {lang: evaluate(m, rows, lang) for lang in ("ru", "en")} for name, m in models.items()},
        "errors_cognate": {lang: errors(models["cognate"], rows, lang) for lang in ("ru", "en")},
        "abstention_cognate": {lang: abstention(models["cognate"], rows, lang) for lang in ("ru", "en")},
        "preferred": preferred_choices(rows, documents, entries),
    }
    etymons = extract_etymons(documents)
    report["etymons"] = len(etymons)
    args.etymons.parent.mkdir(parents=True, exist_ok=True)
    with args.etymons.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["uz", "lang", "foreign", "gloss", "doc_id"])
        writer.writeheader()
        writer.writerows(etymons)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Oltin (kumush) juftlar: {len(rows)}, nomzodlar: {report['candidates']}")
    print(f"{'model':<10} {'til':<4} {'turi':<14} {'n':>4} {'Acc@1':>6} {'Acc@5':>6} {'MRR':>6}")
    for name, by_lang in report["results"].items():
        for lang, by_kind in by_lang.items():
            for kind, m in by_kind.items():
                print(f"{name:<10} {lang:<4} {kind:<14} {m['n']:>4} {m['acc@1']:>6.3f} {m['acc@5']:>6.3f} {m['mrr']:>6.3f}")
    print("\nKognat modeli, ishonch chegarasi bilan (barcha terminlar):")
    for lang, items in report["abstention_cognate"].items():
        for a in items:
            prec = "—" if a["precision"] is None else f"{a['precision']:.3f}"
            print(f"   {lang} θ={a['threshold']:.1f}: qamrov {a['coverage']:.3f}, aniqlik {prec}")
    print("\nMeʼyoriy muqobil tanlash:")
    for c in report["preferred"]:
        print(f"   {c['ru']}: {c['uz']} -> {c['preferred']} ({'; '.join(c['reasons'])})")
    print(f"\nEtimologik izohlar: {len(etymons)} -> {args.etymons}\nHisobot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
