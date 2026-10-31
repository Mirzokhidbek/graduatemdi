"""Uchrash-ma-uchrash (kontekstga qarab) qilingan annotatsiyani JSONL ga aylantirish.

``silver.py`` dagi ro'yxat usulidan farqi: bu yerda har bir belgi alohida qaror —
annotator paragrafni o'qib, termin bo'lgan **har bir uchrashni** matndagi tartibda
yozadi; umumiy maʼnodagi uchrashlar shunchaki yozilmaydi. Matn qayta yozilmaydi
(nusxa xatolari bo'lmasin), belgilar asl matndan ketma-ket qidiriladi.

Fayl formati (``data/silver/<annotator>/<doc_id>.txt``)::

    # izoh
    @1                                  paragraf raqami (1 dan)
    Bogʻlovchi | bogʻlovchi             matndagi ko'rinish | lug'at shakli
    yordamchi soʻz                      lug'at shakli ko'rinish bilan bir xil bo'lsa
    @2
    ...

Qidiruv registr va apostrof farqisiz, so'z chegarasida, oldingi belgidan keyin
boshlanadi. Topilmagan belgi xato hisoblanadi.

    PYTHONPATH=backend python -m app.annotation.sequential claude2
"""

from __future__ import annotations

import json
from pathlib import Path

from app.annotation.workspace import check_annotator
from app.dataset.annotation import STATUS_DRAFT, ValidationReport, parse_record, record_to_dict
from app.dataset.inline import prepare_source, split_paragraphs
from app.nlp.normalize import is_word_end, is_word_start, normalize_text


class SequentialError(ValueError):
    pass


def parse_marks(text: str, source: str = "<fayl>") -> dict[int, list[tuple[str, str]]]:
    marks: dict[int, list[tuple[str, str]]] = {}
    current: int | None = None
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            current = int(line[1:])
            marks.setdefault(current, [])
            continue
        if current is None:
            raise SequentialError(f"{source}:{number}: '@N' paragraf raqamidan oldin belgi")
        surface, _, term = line.partition("|")
        surface, term = surface.strip(), term.strip()
        marks[current].append((surface, term or " ".join(surface.lower().split())))
    return marks


def find_after(text: str, surface: str, position: int) -> tuple[int, int] | None:
    normalized = normalize_text(text)
    target = normalize_text(surface)
    start = normalized.find(target, position)
    while start != -1:
        end = start + len(target)
        if is_word_start(normalized, start) and is_word_end(normalized, end):
            return start, end
        start = normalized.find(target, start + 1)
    return None


def apply_marks(doc_id: str, source: str, marks: dict[int, list[tuple[str, str]]], annotator: str) -> list[dict]:
    paragraphs = split_paragraphs(prepare_source(source))
    unknown = [n for n in marks if not 1 <= n <= len(paragraphs)]
    if unknown:
        raise SequentialError(f"{doc_id}: bunday paragraf yo'q: {unknown}")
    records = []
    report = ValidationReport()
    for number, paragraph in enumerate(paragraphs, start=1):
        spans = []
        position = 0
        for surface, term in marks.get(number, []):
            found = find_after(paragraph.text, surface, position)
            if found is None:
                raise SequentialError(f"{doc_id} @{number}: {surface!r} topilmadi (oldingi belgidan keyin)")
            spans.append({"start": found[0], "end": found[1], "term": term, "label": "TERM"})
            position = found[1]
        obj = {
            "id": f"{doc_id}-p{number:03d}",
            "doc_id": doc_id,
            "text": paragraph.text,
            "terms": spans,
            "annotator": annotator,
            "status": STATUS_DRAFT,
        }
        record = parse_record(obj, obj["id"], report)
        if record is None:
            raise SequentialError("; ".join(str(issue) for issue in report.errors))
        records.append(record_to_dict(record))
    return records


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Uchrash-ma-uchrash annotatsiyani JSONL ga aylantirish")
    parser.add_argument("annotator", help="annotator kodi; belgilar data/silver/<annotator>/ da")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    args = parser.parse_args(argv)

    try:
        annotator = check_annotator(args.annotator)
        out_dir = args.data_dir / "annotations" / annotator
        for path in sorted((args.data_dir / "silver" / annotator).glob("*.txt")):
            doc_id = path.stem
            marks = parse_marks(path.read_text(encoding="utf-8"), path.name)
            records = apply_marks(doc_id, (args.data_dir / "raw" / f"{doc_id}.txt").read_text(encoding="utf-8"), marks, annotator)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{doc_id}.jsonl").write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
            )
            print(f"{doc_id}: {len(records)} paragraf, {sum(len(r['terms']) for r in records)} termin")
    except (SequentialError, ValueError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
