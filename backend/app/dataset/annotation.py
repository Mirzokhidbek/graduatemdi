"""Inson annotatsiyasi (JSONL) formatini o'qish va tekshirish.

Format va qoidalar ``docs/data-annotation-guide.md`` da tasvirlangan.
Xatolar (errors) faylni yaroqsiz qiladi; ogohlantirishlar (warnings) esa
inson e'tiborini talab qiladigan, lekin formatni buzmaydigan holatlar.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from app.nlp.normalize import is_word_end, is_word_start, normalize_form, normalize_text

LABELS = ("TERM",)
STATUS_DRAFT = "draft"
STATUS_REVIEWED = "reviewed"
RECORD_STATUSES = (STATUS_DRAFT, STATUS_REVIEWED)

_RECORD_FIELDS = frozenset({"id", "doc_id", "text", "terms", "annotator", "status", "notes"})
_SPAN_FIELDS = frozenset({"start", "end", "term", "label", "surface"})


@dataclass(frozen=True)
class AnnotatedSpan:
    start: int
    end: int
    term: str
    label: str


@dataclass(frozen=True)
class AnnotatedRecord:
    id: str
    doc_id: str
    text: str
    terms: tuple[AnnotatedSpan, ...]
    annotator: str | None
    status: str
    notes: str | None


@dataclass(frozen=True)
class Issue:
    location: str  # "fayl:qator" yoki "fayl:qator terms[i]"
    message: str

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


@dataclass
class ValidationReport:
    records: list[AnnotatedRecord] = field(default_factory=list)
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class AnnotationError(ValueError):
    def __init__(self, errors: list[Issue]) -> None:
        self.errors = errors
        details = "\n".join(f"- {issue}" for issue in errors)
        super().__init__(f"Annotatsiyada xatolar topildi:\n{details}")


def duplicate_key(text: str) -> str:
    """Takroriy matnlarni aniqlash kaliti: registr, apostrof va bo'shliq farqlari hisobga olinmaydi."""
    return normalize_form(text)


def record_to_dict(record: AnnotatedRecord) -> dict[str, Any]:
    """Yozuvni JSONL formatidagi obyektga qaytaradi (``surface`` bilan)."""
    obj: dict[str, Any] = {
        "id": record.id,
        "doc_id": record.doc_id,
        "text": record.text,
        "terms": [
            {
                "start": span.start,
                "end": span.end,
                "term": span.term,
                "label": span.label,
                "surface": record.text[span.start : span.end],
            }
            for span in record.terms
        ],
    }
    if record.annotator is not None:
        obj["annotator"] = record.annotator
    obj["status"] = record.status
    if record.notes is not None:
        obj["notes"] = record.notes
    return obj


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _optional_str(obj: dict[str, Any], key: str, problems: list[str]) -> str | None:
    value = obj.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        problems.append(f"'{key}' matn yoki null bo'lishi kerak")
        return None
    return value.strip() or None


def _parse_span(
    span: Any, text: str, normalized: str, where: str, errors: list[Issue]
) -> AnnotatedSpan | None:
    if not isinstance(span, dict):
        errors.append(Issue(where, "span JSON obyekt bo'lishi kerak"))
        return None

    problems: list[str] = []
    unknown = sorted(set(span) - _SPAN_FIELDS)
    if unknown:
        problems.append(f"nomaʼlum maydon(lar): {', '.join(unknown)}")

    start, end = span.get("start"), span.get("end")
    positions_ok = _is_int(start) and _is_int(end)
    if not positions_ok:
        problems.append("'start' va 'end' butun son bo'lishi kerak")
    elif not 0 <= start < end <= len(text):
        problems.append(f"noto'g'ri interval [{start}, {end}): 0 <= start < end <= {len(text)} bo'lishi kerak")
        positions_ok = False

    term = span.get("term")
    if not isinstance(term, str) or not any(ch.isalnum() for ch in term):
        problems.append("'term' bo'sh bo'lmagan matn bo'lishi kerak")

    label = span.get("label")
    if label not in LABELS:
        problems.append(f"'label' quyidagilardan biri bo'lishi kerak: {', '.join(LABELS)}")

    if positions_ok:
        surface = text[start:end]
        if not (surface[0].isalnum() and surface[-1].isalnum()):
            problems.append(
                f"span harf yoki raqam bilan boshlanib, tugashi kerak: {surface!r}"
            )
        if not is_word_start(normalized, start):
            problems.append(f"span so'z o'rtasidan boshlanadi: {surface!r}")
        if not is_word_end(normalized, end):
            problems.append(f"span so'z o'rtasida tugaydi: {surface!r}")
        if "surface" in span and span["surface"] != surface:
            problems.append(
                f"'surface' matndagi shaklga mos emas: {span['surface']!r} != {surface!r}"
            )

    if problems:
        errors.extend(Issue(where, p) for p in problems)
        return None
    return AnnotatedSpan(start=start, end=end, term=term.strip(), label=label)


def parse_record(obj: Any, location: str, report: ValidationReport) -> AnnotatedRecord | None:
    """Bitta yozuvni tekshiradi; xato va ogohlantirishlarni ``report`` ga qo'shadi."""
    if not isinstance(obj, dict):
        report.errors.append(Issue(location, "yozuv JSON obyekt bo'lishi kerak"))
        return None

    problems: list[str] = []
    unknown = sorted(set(obj) - _RECORD_FIELDS)
    if unknown:
        problems.append(f"nomaʼlum maydon(lar): {', '.join(unknown)}")

    for key in ("id", "doc_id"):
        value = obj.get(key)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"'{key}' majburiy va bo'sh bo'lmagan matn bo'lishi kerak")

    text = obj.get("text")
    if not isinstance(text, str) or not text.strip():
        problems.append("'text' majburiy va bo'sh bo'lmagan matn bo'lishi kerak")
        text = None

    raw_terms = obj.get("terms")
    if not isinstance(raw_terms, list):
        problems.append("'terms' ro'yxat bo'lishi kerak (termin bo'lmasa — [])")
        raw_terms = None

    status = obj.get("status", STATUS_DRAFT)
    if status not in RECORD_STATUSES:
        problems.append(f"'status' quyidagilardan biri bo'lishi kerak: {', '.join(RECORD_STATUSES)}")

    annotator = _optional_str(obj, "annotator", problems)
    notes = _optional_str(obj, "notes", problems)

    errors_before = len(report.errors)
    report.errors.extend(Issue(location, p) for p in problems)

    spans: list[AnnotatedSpan] = []
    if text is not None and raw_terms is not None:
        if unicodedata.normalize("NFC", text) != text:
            report.warnings.append(
                Issue(location, "matn Unicode NFC shaklida emas; pozitsiyalar boshqa vositalarda siljishi mumkin")
            )
        normalized = normalize_text(text)
        for index, raw_span in enumerate(raw_terms):
            span = _parse_span(raw_span, text, normalized, f"{location} terms[{index}]", report.errors)
            if span is not None:
                spans.append(span)

        spans.sort(key=lambda s: (s.start, s.end))
        for previous, current in zip(spans, spans[1:]):
            if current.start < previous.end:
                report.errors.append(
                    Issue(
                        location,
                        f"spanlar ustma-ust tushadi: [{previous.start}, {previous.end}) "
                        f"va [{current.start}, {current.end})",
                    )
                )

    if len(report.errors) > errors_before:
        return None
    return AnnotatedRecord(
        id=obj["id"].strip(),
        doc_id=obj["doc_id"].strip(),
        text=text,
        terms=tuple(spans),
        annotator=annotator,
        status=status,
        notes=notes,
    )


def validate_files(
    paths: Iterable[str | Path], source_ids: set[str] | None = None
) -> ValidationReport:
    """JSONL fayllarni tekshiradi.

    ``source_ids`` berilsa, har bir ``doc_id`` manbalar reyestrida borligi
    tekshiriladi.
    """
    report = ValidationReport()
    first_seen_id: dict[str, str] = {}
    first_seen_text: dict[str, tuple[str, str]] = {}  # normallashtirilgan matn -> (joy, id)

    for path in paths:
        path = Path(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            report.errors.append(Issue(str(path), "fayl topilmadi"))
            continue
        except UnicodeDecodeError:
            report.errors.append(Issue(str(path), "fayl UTF-8 kodlashda emas"))
            continue

        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            location = f"{path}:{line_number}"
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                report.errors.append(Issue(location, f"JSON xatosi: {exc.msg}"))
                continue

            record = parse_record(obj, location, report)
            if record is None:
                continue

            if record.id in first_seen_id:
                report.errors.append(
                    Issue(location, f"'id' takrorlangan: {record.id} (avval: {first_seen_id[record.id]})")
                )
                continue
            first_seen_id[record.id] = location

            if source_ids is not None and record.doc_id not in source_ids:
                report.errors.append(
                    Issue(location, f"'doc_id' manbalar reyestrida yo'q: {record.doc_id}")
                )
                continue

            text_key = duplicate_key(record.text)
            if text_key in first_seen_text:
                other_location, other_id = first_seen_text[text_key]
                report.warnings.append(
                    Issue(
                        location,
                        f"matn takrorlangan ({other_location}, id={other_id}); "
                        "to'plamlar orasida sizib kirishga olib kelishi mumkin",
                    )
                )
            else:
                first_seen_text[text_key] = (location, record.id)

            report.records.append(record)

    return report


def load_annotations(
    paths: Iterable[str | Path], source_ids: set[str] | None = None
) -> list[AnnotatedRecord]:
    """Yaroqli yozuvlarni qaytaradi; bitta xato bo'lsa ham ``AnnotationError``."""
    report = validate_files(paths, source_ids)
    if not report.ok:
        raise AnnotationError(report.errors)
    return report.records
