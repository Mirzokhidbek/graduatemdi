"""Web interfeys orqali annotatsiya va nomzodlarni baholash uchun ish joyi.

Matnlar ``data/raw/<doc_id>.txt`` dan o'qiladi va inline vositasidagi kabi bo'sh
qator bo'yicha paragraflarga ajratiladi (``<doc_id>-p001``, ...). Shu sababli
web interfeysda yaratilgan yozuvlar ``app.dataset.inline`` natijasi bilan bir xil
``id`` va ``text`` ga ega.

Har bir annotatorning ishi alohida saqlanadi::

    data/annotations/<annotator>/<doc_id>.jsonl

Ikki annotator bir-birining belgilarini ko'rmaydi (kelishuvni o'lchash uchun
mustaqillik kerak). Oltin standart ``data/annotated/`` ga ``promote`` buyrug'i
bilan, faqat ``reviewed`` yozuvlardan o'tkaziladi (``app.annotation.agreement``).

Takliflar (pre-annotation) annotatorga **taklif** sifatida ko'rsatiladi: ular
avtomatik saqlanmaydi, har birini annotator qabul qiladi yoki rad etadi.
"""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from app.dataset.annotation import (
    STATUS_DRAFT,
    AnnotatedRecord,
    Issue,
    ValidationReport,
    parse_record,
    record_to_dict,
)
from app.dataset.inline import prepare_source, split_paragraphs
from app.dataset.sources import SourceDocument, load_sources
from app.evaluation.judgments import COLUMNS, VALUES, load_judgments
from app.nlp.dictionary_matcher import DictionaryMatcher

# Annotator kodi fayl yo'lining bir qismi bo'ladi: faqat xavfsiz belgilar.
ANNOTATOR_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,15}$")
DOC_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")

# AI tomonidan belgilangan (inson tekshirmagan) yozuvlar shu annotator kodi ostida.
AI_ANNOTATOR = "claude"

SUGGEST_DICTIONARY = "dictionary"
SUGGEST_AI = "ai"
SUGGEST_MODEL = "model"


class WorkspaceError(ValueError):
    """Foydalanuvchi so'rovidagi xato (400)."""


class NotFound(LookupError):
    """Hujjat, paragraf yoki fayl topilmadi (404)."""


@dataclass(frozen=True)
class Suggestion:
    start: int
    end: int
    term: str | None
    source: str  # dictionary | ai | model


SpanPredictor = Callable[[str], list[tuple[int, int, str | None]]]


def check_annotator(annotator: str) -> str:
    if not ANNOTATOR_PATTERN.match(annotator or ""):
        raise WorkspaceError("Annotator kodi lotin harfi bilan boshlanib, 1–16 ta harf, raqam, '_' yoki '-' bo'lishi kerak.")
    return annotator


def check_doc_id(doc_id: str) -> str:
    if not DOC_ID_PATTERN.match(doc_id or ""):
        raise NotFound(doc_id)
    return doc_id


def _write_atomic(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Yarim yozilgan fayl qolmasligi uchun: vaqtinchalik faylga yozib, keyin almashtiramiz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(content)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class Workspace:
    def __init__(
        self,
        data_dir: Path,
        matcher: DictionaryMatcher,
        model: SpanPredictor | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        self.annotations_dir = data_dir / "annotations"
        self.judgments_dir = data_dir / "judgments"
        self.sources_path = data_dir / "sources.json"
        self.matcher = matcher
        self.model = model

    # --- manbalar va paragraflar -------------------------------------------------

    def sources(self) -> dict[str, SourceDocument]:
        if not self.sources_path.exists():
            return {}
        return {source.id: source for source in load_sources(self.sources_path)}

    def doc_ids(self) -> list[str]:
        if not self.raw_dir.exists():
            return []
        return sorted(path.stem for path in self.raw_dir.glob("*.txt"))

    def paragraphs(self, doc_id: str) -> list[tuple[str, str]]:
        """``[(record_id, text), ...]`` — inline vositasi bilan bir xil bo'linish."""
        path = self.raw_dir / f"{check_doc_id(doc_id)}.txt"
        if not path.is_file():
            raise NotFound(doc_id)
        source = prepare_source(path.read_text(encoding="utf-8"))
        return [(f"{doc_id}-p{number:03d}", p.text) for number, p in enumerate(split_paragraphs(source), start=1)]

    # --- annotatsiyalar ---------------------------------------------------------

    def _annotation_path(self, annotator: str, doc_id: str) -> Path:
        return self.annotations_dir / check_annotator(annotator) / f"{check_doc_id(doc_id)}.jsonl"

    def load_records(self, annotator: str, doc_id: str) -> dict[str, dict[str, Any]]:
        path = self._annotation_path(annotator, doc_id)
        if not path.exists():
            return {}
        records: dict[str, dict[str, Any]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                records[obj["id"]] = obj
        return records

    def annotators(self) -> list[str]:
        if not self.annotations_dir.exists():
            return []
        return sorted(p.name for p in self.annotations_dir.iterdir() if p.is_dir() and ANNOTATOR_PATTERN.match(p.name))

    def suggestions(self, text: str, record_id: str, doc_id: str, annotator: str) -> list[Suggestion]:
        found: list[Suggestion] = [
            Suggestion(m.start, m.end, None if m.ambiguous else m.candidates[0].entry.term, SUGGEST_DICTIONARY)
            for m in self.matcher.find(text)
        ]
        if annotator != AI_ANNOTATOR:
            ai = self.load_records(AI_ANNOTATOR, doc_id).get(record_id)
            if ai and ai.get("text") == text:
                found += [Suggestion(s["start"], s["end"], s["term"], SUGGEST_AI) for s in ai["terms"]]
        if self.model is not None:
            found += [Suggestion(start, end, term, SUGGEST_MODEL) for start, end, term in self.model(text)]
        return sorted(found, key=lambda s: (s.start, s.end, s.source))

    def document(self, doc_id: str, annotator: str) -> dict[str, Any]:
        check_annotator(annotator)
        sources = self.sources()
        saved = self.load_records(annotator, doc_id)
        paragraphs = []
        for record_id, text in self.paragraphs(doc_id):
            record = saved.get(record_id)
            # matn o'zgargan bo'lsa (manba qayta yuklangan), eski belgilar ko'rsatilmaydi
            if record is not None and record.get("text") != text:
                record = None
            paragraphs.append(
                {
                    "id": record_id,
                    "text": text,
                    "saved": None
                    if record is None
                    else {"terms": record["terms"], "status": record.get("status", STATUS_DRAFT), "notes": record.get("notes")},
                    "suggestions": [s.__dict__ for s in self.suggestions(text, record_id, doc_id, annotator)],
                }
            )
        source = sources.get(doc_id)
        return {
            "doc_id": doc_id,
            "title": source.title if source else doc_id,
            "annotator": annotator,
            "paragraphs": paragraphs,
        }

    def documents(self, annotator: str | None = None) -> list[dict[str, Any]]:
        if annotator is not None:
            check_annotator(annotator)
        sources = self.sources()
        result = []
        for doc_id in self.doc_ids():
            paragraphs = self.paragraphs(doc_id)
            done = reviewed = 0
            if annotator is not None:
                texts = dict(paragraphs)
                for record_id, record in self.load_records(annotator, doc_id).items():
                    if texts.get(record_id) == record.get("text"):
                        done += 1
                        reviewed += record.get("status") == "reviewed"
            source = sources.get(doc_id)
            result.append(
                {
                    "doc_id": doc_id,
                    "title": source.title if source else doc_id,
                    "paragraphs": len(paragraphs),
                    "annotated": done,
                    "reviewed": reviewed,
                }
            )
        return result

    def save(
        self,
        doc_id: str,
        record_id: str,
        annotator: str,
        terms: list[dict[str, Any]],
        status: str,
        notes: str | None,
    ) -> dict[str, Any]:
        """Bitta paragrafni tekshirib saqlaydi; xato bo'lsa ``WorkspaceError`` (hech narsa yozilmaydi)."""
        check_annotator(annotator)
        texts = dict(self.paragraphs(doc_id))
        if record_id not in texts:
            raise NotFound(record_id)
        if doc_id not in self.sources():
            raise WorkspaceError(f"'{doc_id}' manbalar reyestrida (data/sources.json) yo'q.")

        obj: dict[str, Any] = {
            "id": record_id,
            "doc_id": doc_id,
            "text": texts[record_id],
            "terms": [
                {"start": t["start"], "end": t["end"], "term": t["term"], "label": t.get("label", "TERM")} for t in terms
            ],
            "annotator": annotator,
            "status": status,
        }
        if notes and notes.strip():
            obj["notes"] = notes.strip()
        report = ValidationReport()
        record = parse_record(obj, record_id, report)
        if record is None:
            raise WorkspaceError("; ".join(_issue_text(issue) for issue in report.errors))

        records = self.load_records(annotator, doc_id)
        records[record_id] = record_to_dict(record)
        order = {rid: index for index, (rid, _) in enumerate(self.paragraphs(doc_id))}
        lines = [
            json.dumps(records[rid], ensure_ascii=False)
            for rid in sorted(records, key=lambda rid: order.get(rid, len(order)))
        ]
        _write_atomic(self._annotation_path(annotator, doc_id), "\n".join(lines) + "\n")
        return records[record_id]

    # --- nomzodlarni baholash ---------------------------------------------------

    def _judgments_path(self, annotator: str) -> Path:
        return self.judgments_dir / f"candidates-{check_annotator(annotator)}.csv"

    def judgment_rows(self, annotator: str) -> list[dict[str, str]]:
        path = self._judgments_path(annotator)
        if not path.exists():
            # yangi baholovchi: AI fayli emas, bo'sh shablon (A1) asos qilinadi
            template = self.judgments_dir / "candidates-A1.csv"
            if not template.exists():
                raise NotFound(str(path))
            path = template
            blank = True
        else:
            blank = False
        load_judgments(path)  # format tekshiruvi
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = [{column: (row.get(column) or "") for column in COLUMNS} for row in csv.DictReader(handle)]
        if blank:
            for row in rows:
                row["judgment"] = row["notes"] = ""
        return rows

    def save_judgment(self, annotator: str, candidate: str, judgment: str, notes: str | None) -> dict[str, str]:
        if judgment not in (*VALUES, ""):
            raise WorkspaceError("Baho 1, 0, ? yoki bo'sh bo'lishi kerak.")
        rows = self.judgment_rows(annotator)
        for row in rows:
            if row["candidate"] == candidate:
                row["judgment"] = judgment
                row["notes"] = (notes or "").strip()
                break
        else:
            raise NotFound(candidate)
        lines: list[str] = []

        class _Sink:
            def write(self, chunk: str) -> None:
                lines.append(chunk)

        writer = csv.DictWriter(_Sink(), fieldnames=list(COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
        _write_atomic(self._judgments_path(annotator), "".join(lines), encoding="utf-8-sig")
        return next(row for row in rows if row["candidate"] == candidate)


def _issue_text(issue: Issue) -> str:
    # "doc-p001 terms[2]" -> "2-span: ..."; foydalanuvchiga fayl joyi emas, span raqami kerak
    match = re.search(r"terms\[(\d+)\]$", issue.location)
    return f"{int(match.group(1)) + 1}-belgi: {issue.message}" if match else issue.message


def records_from(objs: Iterable[dict[str, Any]]) -> list[AnnotatedRecord]:
    report = ValidationReport()
    records = [parse_record(obj, obj.get("id", "?"), report) for obj in objs]
    return [r for r in records if r is not None]
