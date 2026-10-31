"""Annotatorlar orasidagi kelishuv va oltin standartga o'tkazish.

Span annotatsiyasida Cohen's kappa ma'nosiz (termin bo'lmagan "spanlar" sanab
bo'lmaydi), shuning uchun adabiyotdagi odatiy ko'rsatkich ishlatiladi: bir
annotatorni "oltin", ikkinchisini "bashorat" deb olingan **F1** (simmetrik:
qaysi tomon oltin bo'lishidan qatʼi nazar bir xil). Exact va partial F1, hamda
mos spanlarda lug'at shakli (``term``) qanchalik bir xil ekani hisoblanadi.

Faqat ikkala annotator ham belgilagan va matni bir xil paragraflar solishtiriladi.

    PYTHONPATH=backend python -m app.annotation.agreement compare A1 A2
    PYTHONPATH=backend python -m app.annotation.agreement promote A1 [--include-drafts] [--force]
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.annotation.workspace import check_annotator
from app.dataset.annotation import STATUS_REVIEWED, load_annotations
from app.dataset.sources import load_sources
from app.evaluation.metrics import Scores, Span, exact_scores, partial_scores
from app.nlp.normalize import normalize_form


@dataclass(frozen=True)
class AgreementReport:
    first: str
    second: str
    paragraphs: int
    exact: Scores
    partial: Scores
    same_term: int  # aynan mos spanlardan lug'at shakli ham bir xil bo'lganlari
    examples: list[dict[str, Any]]


def _load_dir(directory: Path) -> dict[str, Any]:
    records = {}
    for path in sorted(directory.glob("*.jsonl")):
        for record in load_annotations([path]):
            records[record.id] = record
    return records


def compare(annotations_dir: Path, first: str, second: str, max_examples: int = 20) -> AgreementReport:
    a = _load_dir(annotations_dir / check_annotator(first))
    b = _load_dir(annotations_dir / check_annotator(second))
    common = sorted(rid for rid in a if rid in b and a[rid].text == b[rid].text)

    pairs = []
    same_term = 0
    examples: list[dict[str, Any]] = []
    for rid in common:
        spans_a = [Span(s.start, s.end, s.term) for s in a[rid].terms]
        spans_b = [Span(s.start, s.end, s.term) for s in b[rid].terms]
        pairs.append((spans_a, spans_b))
        terms_b = {(s.start, s.end): s.term for s in spans_b}
        for s in spans_a:
            other = terms_b.get((s.start, s.end))
            if other is not None and normalize_form(other) == normalize_form(s.term or ""):
                same_term += 1
        keys_a = {(s.start, s.end) for s in spans_a}
        keys_b = {(s.start, s.end) for s in spans_b}
        for start, end in sorted(keys_a ^ keys_b):
            if len(examples) >= max_examples:
                break
            examples.append(
                {
                    "id": rid,
                    "surface": a[rid].text[start:end],
                    "only": first if (start, end) in keys_a else second,
                }
            )
    return AgreementReport(first, second, len(common), exact_scores(pairs), partial_scores(pairs), same_term, examples)


def promote(
    annotations_dir: Path,
    annotated_dir: Path,
    sources_path: Path,
    annotator: str,
    include_drafts: bool = False,
    force: bool = False,
) -> list[Path]:
    """Annotator yozuvlarini ``data/annotated/<doc_id>.jsonl`` ga (oltin standart) yozadi.

    Standart bo'yicha faqat ``reviewed`` yozuvlar o'tadi. Mavjud faylni ``force`` siz
    qayta yozmaydi (boshqa annotator yoki qo'lda tuzatilgan natija yo'qolmasin).
    """
    source_ids = {source.id for source in load_sources(sources_path)}
    written: list[Path] = []
    for path in sorted((annotations_dir / check_annotator(annotator)).glob("*.jsonl")):
        records = [
            r for r in load_annotations([path], source_ids) if include_drafts or r.status == STATUS_REVIEWED
        ]
        if not records:
            continue
        target = annotated_dir / path.name
        if target.exists() and not force:
            raise FileExistsError(f"{target} allaqachon bor (--force bilan qayta yozish mumkin)")
        lines = []
        for record in records:
            obj = {
                "id": record.id,
                "doc_id": record.doc_id,
                "text": record.text,
                "terms": [
                    {"start": s.start, "end": s.end, "term": s.term, "label": s.label, "surface": record.text[s.start : s.end]}
                    for s in record.terms
                ],
                "annotator": record.annotator,
                "status": record.status,
            }
            if record.notes:
                obj["notes"] = record.notes
            lines.append(json.dumps(obj, ensure_ascii=False))
        annotated_dir.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(target)
    return written


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Annotatorlar kelishuvi va oltin standartga o'tkazish")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    commands = parser.add_subparsers(dest="command", required=True)
    cmp = commands.add_parser("compare", help="ikki annotator kelishuvi (span F1)")
    cmp.add_argument("first")
    cmp.add_argument("second")
    pro = commands.add_parser("promote", help="annotator yozuvlarini data/annotated/ ga o'tkazish")
    pro.add_argument("annotator")
    pro.add_argument("--include-drafts", action="store_true")
    pro.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.command == "compare":
            report = compare(args.data_dir / "annotations", args.first, args.second)
            print(f"{report.first} ↔ {report.second}: {report.paragraphs} ta umumiy paragraf")
            if not report.paragraphs:
                return 0
            for name, scores in (("exact", report.exact), ("partial", report.partial)):
                print(f"  {name:<8} F1 = {_fmt(scores.f1)}  (P = {_fmt(scores.precision)}, R = {_fmt(scores.recall)}; "
                      f"{report.first}: {scores.gold} span, {report.second}: {scores.predicted} span)")
            matched = report.exact.correct_gold
            print(f"  aynan mos {matched} spandan lug'at shakli ham bir xil: {report.same_term}")
            for example in report.examples:
                print(f"    faqat {example['only']}: {example['surface']!r} ({example['id']})")
        else:
            written = promote(
                args.data_dir / "annotations",
                args.data_dir / "annotated",
                args.data_dir / "sources.json",
                args.annotator,
                args.include_drafts,
                args.force,
            )
            print(f"{len(written)} ta fayl yozildi: " + ", ".join(str(p) for p in written))
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
