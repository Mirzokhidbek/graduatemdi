"""Inline belgilangan matndan JSONL annotatsiya yaratish.

Annotator oddiy matn faylida terminlarni qo'sh kvadrat qavsga oladi:

    [[Fonemalar|fonema]] va [[unli tovush]] haqida.

- ``[[ko'rinish|termin]]`` — matndagi shakl va lug'at shakli;
- ``[[ko'rinish]]`` — lug'at shakli ko'rinishning kichik harfli nusxasi.

Bo'sh qator bilan ajratilgan har bir paragraf alohida yozuv bo'ladi.
Pozitsiyalar avtomatik hisoblanadi va natija ``annotation`` modulidagi
qoidalar bilan tekshiriladi; xatolar asl fayldagi qator:ustun bilan ko'rsatiladi.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.dataset.annotation import (
    LABELS,
    RECORD_STATUSES,
    STATUS_DRAFT,
    AnnotatedRecord,
    Issue,
    ValidationReport,
    parse_record,
)

OPEN = "[["
CLOSE = "]]"
SEPARATOR = "|"

_MARK = re.compile(r"\[\[(.*?)\]\]", re.DOTALL)
_SPAN_LOCATION = re.compile(r" terms\[(\d+)\]$")


@dataclass(frozen=True)
class Paragraph:
    offset: int  # manba matnidagi boshlanish pozitsiyasi
    text: str  # belgilari bilan


@dataclass(frozen=True)
class ConversionResult:
    records: list[AnnotatedRecord]
    objects: list[dict[str, Any]]  # JSONL ga yoziladigan obyektlar
    errors: list[Issue]

    @property
    def ok(self) -> bool:
        return not self.errors


def _line_col(source: str, offset: int) -> str:
    line = source.count("\n", 0, offset) + 1
    column = offset - (source.rfind("\n", 0, offset) + 1) + 1
    return f"{line}:{column}"


def _issue_position(issue: Issue) -> tuple[int, int]:
    line, column = issue.location.rsplit(":", 2)[-2:]
    return int(line), int(column)


def prepare_source(source: str) -> str:
    """Qator oxirlarini ``\\n`` ga va Unicode'ni NFC shakliga keltiradi."""
    return unicodedata.normalize("NFC", source.replace("\r\n", "\n").replace("\r", "\n"))


def split_paragraphs(source: str) -> list[Paragraph]:
    """Bo'sh (yoki faqat bo'shliqli) qatorlar bo'yicha paragraflarga ajratadi."""
    paragraphs: list[Paragraph] = []
    start: int | None = None
    end = 0
    offset = 0
    for line in source.split("\n"):
        line_end = offset + len(line)
        if line.strip():
            if start is None:
                start = offset
            end = line_end
        elif start is not None:
            paragraphs.append(Paragraph(start, source[start:end]))
            start = None
        offset = line_end + 1
    if start is not None:
        paragraphs.append(Paragraph(start, source[start:end]))

    # Paragraf boshidagi va oxiridagi bo'shliqlarni olib tashlaymiz.
    trimmed = []
    for paragraph in paragraphs:
        leading = len(paragraph.text) - len(paragraph.text.lstrip())
        trimmed.append(Paragraph(paragraph.offset + leading, paragraph.text.strip()))
    return trimmed


def parse_inline(
    marked: str,
) -> tuple[str, list[dict[str, Any]], list[int], list[tuple[int, str]]]:
    """Belgilangan matnni toza matn va spanlarga ajratadi.

    Qaytaradi: (toza matn, spanlar, har bir spanning belgili matndagi
    pozitsiyasi, [(belgili matndagi pozitsiya, xato xabari)]).
    """
    pieces: list[str] = []
    spans: list[dict[str, Any]] = []
    span_offsets: list[int] = []
    problems: list[tuple[int, str]] = []
    plain_length = 0
    position = 0

    def check_stray(start: int, end: int) -> None:
        chunk = marked[start:end]
        for token, message in ((OPEN, "yopilmagan '[['"), (CLOSE, "ochilmagan ']]'")):
            index = chunk.find(token)
            if index != -1:
                problems.append((start + index, message))

    for match in _MARK.finditer(marked):
        check_stray(position, match.start())
        pieces.append(marked[position : match.start()])
        plain_length += match.start() - position

        inner = match.group(1)
        problems_before = len(problems)
        if OPEN in inner:
            problems.append((match.start(), "ichma-ich '[[' ruxsat etilmaydi"))
            surface, term = inner, None
        else:
            parts = inner.split(SEPARATOR)
            if len(parts) > 2:
                problems.append((match.start(), f"bitta belgida faqat bitta '{SEPARATOR}' bo'lishi mumkin"))
            surface = parts[0]
            term = parts[1].strip() if len(parts) > 1 else surface.lower()
            if not surface.strip():
                problems.append((match.start(), "belgi ichida matn yo'q: '[[]]'"))
            elif len(parts) > 1 and not term:
                problems.append((match.start(), f"'{SEPARATOR}' dan keyin termin yozilmagan"))

        # Xato belgi spanga aylanmaydi, lekin qolgan belgilar tekshirilaveradi.
        if len(problems) == problems_before:
            spans.append(
                {
                    "start": plain_length,
                    "end": plain_length + len(surface),
                    "term": term,
                    "label": LABELS[0],
                    "surface": surface,
                }
            )
            span_offsets.append(match.start())
        pieces.append(surface)
        plain_length += len(surface)
        position = match.end()

    check_stray(position, len(marked))
    pieces.append(marked[position:])
    return "".join(pieces), spans, span_offsets, problems


def convert_document(
    source: str,
    doc_id: str,
    *,
    source_name: str = "<matn>",
    annotator: str | None = None,
    status: str = STATUS_DRAFT,
) -> ConversionResult:
    """Inline belgilangan hujjatni JSONL yozuvlariga aylantiradi."""
    if status not in RECORD_STATUSES:
        raise ValueError(f"status quyidagilardan biri bo'lishi kerak: {', '.join(RECORD_STATUSES)}")

    source = prepare_source(source)
    errors: list[Issue] = []
    records: list[AnnotatedRecord] = []
    objects: list[dict[str, Any]] = []

    for number, paragraph in enumerate(split_paragraphs(source), start=1):
        text, spans, span_offsets, problems = parse_inline(paragraph.text)

        def where(offset_in_paragraph: int) -> str:
            return f"{source_name}:{_line_col(source, paragraph.offset + offset_in_paragraph)}"

        paragraph_errors = [Issue(where(offset), message) for offset, message in problems]

        obj: dict[str, Any] = {"id": f"{doc_id}-p{number:03d}", "doc_id": doc_id, "text": text, "terms": spans}
        if annotator is not None:
            obj["annotator"] = annotator
        obj["status"] = status

        report = ValidationReport()
        record = parse_record(obj, where(0), report)
        # Span xatolarini belgining asl fayldagi joyiga bog'laymiz.
        for issue in report.errors:
            span_match = _SPAN_LOCATION.search(issue.location)
            location = where(span_offsets[int(span_match.group(1))]) if span_match else issue.location
            paragraph_errors.append(Issue(location, issue.message))

        if paragraph_errors:
            errors.extend(sorted(paragraph_errors, key=_issue_position))
        elif record is not None:
            records.append(record)
            objects.append(obj)

    return ConversionResult(records=records, objects=objects, errors=errors)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import sys
    from pathlib import Path

    from app.dataset.sources import SourceRegistryError, load_sources
    from app.dataset.validate import DEFAULT_SOURCES

    parser = argparse.ArgumentParser(
        description="Inline belgilangan matndan ([[ko'rinish|termin]]) JSONL yaratish"
    )
    parser.add_argument("input", type=Path, help="belgilangan matn fayli (UTF-8)")
    parser.add_argument("--doc-id", required=True, help="data/sources.json dagi manba id si")
    parser.add_argument("-o", "--output", type=Path, help="JSONL fayl (berilmasa, stdout)")
    parser.add_argument("--annotator", help="annotator kodi, masalan A1")
    parser.add_argument("--status", choices=RECORD_STATUSES, default=STATUS_DRAFT)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="manbalar reyestri")
    parser.add_argument("--force", action="store_true", help="mavjud chiqish faylini qayta yozish")
    args = parser.parse_args(argv)

    try:
        source_ids = {source.id for source in load_sources(args.sources)}
    except SourceRegistryError as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.doc_id not in source_ids:
        print(
            f"'{args.doc_id}' manbalar reyestrida ({args.sources}) yo'q. "
            "Avval manba va foydalanish huquqini qayd qiling.",
            file=sys.stderr,
        )
        return 1

    if args.output is not None and args.output.exists() and not args.force:
        print(
            f"{args.output} allaqachon mavjud. Qo'lda kiritilgan o'zgarishlar yo'qolmasligi "
            "uchun qayta yozilmadi; kerak bo'lsa --force bering.",
            file=sys.stderr,
        )
        return 1

    try:
        source = args.input.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError) as exc:
        print(f"{args.input}: faylni o'qib bo'lmadi: {exc}", file=sys.stderr)
        return 1

    result = convert_document(
        source,
        args.doc_id,
        source_name=str(args.input),
        annotator=args.annotator,
        status=args.status,
    )
    if not result.ok:
        print(f"Xatolar ({len(result.errors)}), fayl yozilmadi:", file=sys.stderr)
        for issue in result.errors:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    lines = "".join(json.dumps(obj, ensure_ascii=False) + "\n" for obj in result.objects)
    span_count = sum(len(record.terms) for record in result.records)
    if args.output is None:
        sys.stdout.write(lines)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(lines, encoding="utf-8")
        print(f"{args.output}: {len(result.records)} ta yozuv, {span_count} ta span yozildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
