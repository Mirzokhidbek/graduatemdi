"""Tajribalarni taqqoslash jadvali: ``reports/*.json`` dan Markdown (6-bosqich).

    PYTHONPATH=backend python -m app.evaluation.report   # -> docs/experiments-table.md
"""

from __future__ import annotations

import json
from pathlib import Path

NAMES = {
    "dictionary_seed": "Lug'at (15 termin)",
    "dictionary_train": "Lug'at (train, 450 termin)",
    "crf": "CRF",
    "crf_gazetteer": "CRF + gazetteer",
    "transformer": "Transformer",
    "lowercase": "O'zgarishsiz (kichik harf)",
    "corpus_lemmatizer": "Korpus lemmatizatori",
    "dictionary": "Faqat lug'at",
    "dictionary_morphology": "Lug'at + morfologik qoidalar",
}


def _f(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def detection_table(report: dict, split: str = "test") -> list[str]:
    rows = ["| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |", "|---|---|---|---|---|---|---|"]
    boot = report.get("test_bootstrap", {}).get("f1_ci95", {}) if split == "test" else {}
    best = max(report[split].values(), key=lambda r: r["exact"]["f1"] or 0)
    for name, result in report[split].items():
        exact = result["exact"]
        ci = boot.get(name)
        f1 = _f(exact["f1"])
        if result is best:
            f1 = f"**{f1}**"
        rows.append(
            f"| {NAMES.get(name, name)} | {_f(exact['precision'])} | {_f(exact['recall'])} | {f1} | "
            f"{f'[{ci[0]:.3f}, {ci[1]:.3f}]' if ci else '—'} | {_f(result['partial']['f1'])} | {_f(result['term_accuracy'])} |"
        )
    return rows


def normalization_table(results: dict[str, dict]) -> list[str]:
    columns = list(results)
    rows = ["| Usul | " + " | ".join(columns) + " |", "|---" * (len(columns) + 1) + "|"]
    for method in next(iter(results.values()))["methods"]:
        cells = [f"{_f(results[c]['methods'][method]['accuracy'])} ({results[c]['methods'][method]['correct']}/{results[c]['spans']})"
                 for c in columns]
        rows.append(f"| {NAMES.get(method, method)} | " + " | ".join(cells) + " |")
    return rows


def build(reports_dir: Path) -> str:
    silver = json.loads((reports_dir / "experiment-silver.json").read_text(encoding="utf-8"))
    test2_path = reports_dir / "experiment-silver-test2.json"
    lines = [
        "# Tajribalarni taqqoslash jadvali",
        "",
        "> Avtomatik yaratilgan: `PYTHONPATH=backend python -m app.evaluation.report`.",
        "> Barcha natijalar **AI annotatsiyasi** (kumush maʼlumot) bo'yicha, inson oltin standarti emas.",
        "",
        f"Maʼlumot: train {silver['records']['train']} / validation {silver['records']['validation']} / "
        f"test {silver['records']['test']} paragraf; termin spanlari: train {silver['spans']['train']}, "
        f"validation {silver['spans']['validation']}, test {silver['spans']['test']}.",
        "",
        "## 1. Terminlarni aniqlash — test (ro'yxat usulidagi belgilar)",
        "",
        *detection_table(silver, "test"),
        "",
        "## 2. Terminlarni aniqlash — validation",
        "",
        *detection_table(silver, "validation"),
    ]
    if test2_path.exists():
        test2 = json.loads(test2_path.read_text(encoding="utf-8"))
        lines += [
            "",
            "## 3. Terminlarni aniqlash — test (uchrash-ma-uchrash qayta belgilangan, `claude2`)",
            "",
            *detection_table(test2, "test"),
        ]
    lines += ["", "## 4. Yangi terminlar (test, train'da uchramagan)", "", "| Usul | Topildi | Recall |", "|---|---|---|"]
    for name, r in silver["test_unseen_terms"].items():
        lines.append(f"| {NAMES.get(name, name)} | {r['found']}/{r['gold']} | {_f(r['recall'])} |")

    norm = {}
    for label, file in (("test", "normalization-test.json"), ("test (claude2)", "normalization-test2.json")):
        path = reports_dir / file
        if path.exists():
            norm[label] = json.loads(path.read_text(encoding="utf-8"))
    if norm:
        lines += [
            "",
            "## 5. Meʼyorlashtirish (oltin spanlar uchun lug'at shakli aniqligi)",
            "",
            *normalization_table(norm),
            "",
            (
                "Morfologik qoidalardagi `-ka` fonotaktika qoidasi va `-im`/`-ing` (I/II shaxs birlik egaligi) "
                "qoidasi test xatolari tahlilidan keyin qo'shilgan (test bo'yicha sozlangan). Undan oldin: "
                "test 0.861, test (claude2) 0.849; validation ikkala qoidada ham o'zgarmagan (0.936)."
            ),
        ]
    for label, file in (("test", "experiment-transformer.json"), ("test, claude2", "experiment-transformer-test2.json")):
        transformer_path = reports_dir / file
        if not transformer_path.exists():
            continue
        tr = json.loads(transformer_path.read_text(encoding="utf-8"))
        boot = tr["test_bootstrap"]
        lines += [
            "",
            f"## 6. Transformer — {label} (`{tr['model']}`, eng yaxshi epoxa: {tr['best_epoch']})",
            "",
            *detection_table(tr, "test"),
            "",
            f"`{boot['baseline']}` dan farqning 95 % oralig'i: "
            + "; ".join(f"{NAMES.get(n, n)} [{ci[0]:+.3f}, {ci[1]:+.3f}]" for n, ci in boot["delta_vs_baseline_ci95"].items())
            + ".",
            "",
            "Train'da uchramagan terminlar: "
            + "; ".join(f"{NAMES.get(n, n)} {r['found']}/{r['gold']}" for n, r in tr["test_unseen_terms"].items())
            + ".",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Tajribalar jadvali")
    parser.add_argument("--reports", type=Path, default=REPO_ROOT / "reports")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "docs" / "experiments-table.md")
    args = parser.parse_args(argv)
    args.output.write_text(build(args.reports), encoding="utf-8")
    print(f"Yozildi: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
