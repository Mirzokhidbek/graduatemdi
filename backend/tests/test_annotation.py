from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.dataset import validate
from app.dataset.annotation import (
    AnnotationError,
    ValidationReport,
    load_annotations,
    parse_record,
    validate_files,
)
from app.dataset.sources import SourceRegistryError, load_sources, parse_sources
from app.nlp.normalize import is_word_end, is_word_start, normalize_text

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "docs" / "examples"


def span(text: str, piece: str, term: str | None = None, **extra) -> dict:
    start = text.index(piece)
    return {"start": start, "end": start + len(piece), "term": term or piece.lower(),
            "label": "TERM", **extra}


def record(text: str = "Fonema va morfema.", terms=None, **fields) -> dict:
    if terms is None:
        terms = [span(text, "Fonema")]
    return {"id": "r1", "doc_id": "d1", "text": text, "terms": terms, **fields}


def check(obj) -> ValidationReport:
    report = ValidationReport()
    parsed = parse_record(obj, "f:1", report)
    assert (parsed is None) == bool(report.errors)
    return report


def error_messages(obj) -> list[str]:
    return [issue.message for issue in check(obj).errors]


def write_jsonl(path: Path, objs) -> Path:
    path.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in objs) + "\n", encoding="utf-8")
    return path


# --- So'z chegarasi yordamchilari ---------------------------------------


@pytest.mark.parametrize(
    ("text", "index", "start_ok", "end_ok"),
    [
        ("fonema", 0, True, False),
        ("fonema", 6, False, True),
        ("a fonema", 2, True, False),
        ("polifonema", 4, False, False),
        ("soʻz", 3, False, False),  # apostrofdan keyingi "z"
        ("soʻz", 2, False, False),  # apostrof oldi
        ("'fonema'", 1, True, False),
        ("'fonema'", 7, False, True),
    ],
)
def test_word_boundaries(text, index, start_ok, end_ok):
    normalized = normalize_text(text)
    assert is_word_start(normalized, index) is start_ok
    assert is_word_end(normalized, index) is end_ok


# --- To'g'ri yozuvlar ---------------------------------------------------


def test_valid_record():
    report = ValidationReport()
    parsed = parse_record(record(status="reviewed", annotator="A1"), "f:1", report)
    assert report.errors == [] and report.warnings == []
    assert parsed.status == "reviewed"
    assert parsed.terms[0].start == 0 and parsed.terms[0].end == 6


def test_record_without_terms_is_valid():
    assert check(record(terms=[])).errors == []


def test_defaults():
    report = ValidationReport()
    parsed = parse_record(record(), "f:1", report)
    assert parsed.status == "draft"
    assert parsed.annotator is None and parsed.notes is None


def test_inflected_multiword_and_apostrophe_spans_valid():
    text = "«Qoʻshma gaplarning», soʻz turkumi."
    terms = [
        span(text, "Qoʻshma gaplarning", "qoʻshma gap", surface="Qoʻshma gaplarning"),
        span(text, "soʻz turkumi"),
    ]
    assert check(record(text, terms)).errors == []


def test_spans_are_sorted():
    text = "Fonema va morfema."
    report = ValidationReport()
    parsed = parse_record(record(text, [span(text, "morfema"), span(text, "Fonema")]), "f:1", report)
    assert [s.term for s in parsed.terms] == ["fonema", "morfema"]


# --- Yozuv darajasidagi xatolar ------------------------------------------


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"id": ""}, "'id'"),
        ({"id": 5}, "'id'"),
        ({"doc_id": None}, "'doc_id'"),
        ({"text": ""}, "'text'"),
        ({"text": "  \n"}, "'text'"),
        ({"terms": None}, "'terms'"),
        ({"terms": {}}, "'terms'"),
        ({"status": "done"}, "'status'"),
        ({"annotator": 1}, "'annotator'"),
        ({"extra": 1}, "nomaʼlum maydon"),
    ],
)
def test_invalid_record_fields(changes, expected):
    messages = error_messages({**record(), **changes})
    assert any(expected in m for m in messages), messages


def test_missing_required_fields():
    messages = error_messages({})
    for key in ("'id'", "'doc_id'", "'text'", "'terms'"):
        assert any(key in m for m in messages)


def test_record_must_be_object():
    assert error_messages(["fonema"]) == ["yozuv JSON obyekt bo'lishi kerak"]


# --- Span xatolari ---------------------------------------------------------


TEXT = "Fonema va polifonema, soʻz."


@pytest.mark.parametrize(
    ("bad_span", "expected"),
    [
        ({"start": 0, "end": 0}, "noto'g'ri interval"),
        ({"start": 3, "end": 2}, "noto'g'ri interval"),
        ({"start": -1, "end": 6}, "noto'g'ri interval"),
        ({"start": 0, "end": 999}, "noto'g'ri interval"),
        ({"start": "0", "end": 6}, "butun son"),
        ({"start": True, "end": 6}, "butun son"),
        ({"start": 0.0, "end": 6}, "butun son"),
        ({"term": ""}, "'term'"),
        ({"term": None}, "'term'"),
        ({"label": "term"}, "'label'"),
        ({"surface": "fonema"}, "'surface'"),
        ({"extra": 1}, "nomaʼlum maydon"),
        # So'z o'rtasi: "poli|fonema"
        ({"start": 14, "end": 20}, "so'z o'rtasidan boshlanadi"),
        # "Fonem|a"
        ({"start": 0, "end": 5}, "so'z o'rtasida tugaydi"),
        # "so|ʻz": apostrof so'z ichida
        ({"start": 22, "end": 24}, "so'z o'rtasida tugaydi"),
        # bo'shliq va tinish belgisi bilan
        ({"start": 0, "end": 7}, "harf yoki raqam"),
        ({"start": 14, "end": 21}, "harf yoki raqam"),
    ],
)
def test_invalid_spans(bad_span, expected):
    base = {"start": 0, "end": 6, "term": "fonema", "label": "TERM"}
    messages = error_messages(record(TEXT, [{**base, **bad_span}]))
    assert any(expected in m for m in messages), messages


def test_span_must_be_object():
    messages = error_messages(record(TEXT, ["Fonema"]))
    assert messages == ["span JSON obyekt bo'lishi kerak"]


def test_overlapping_spans_rejected():
    text = "undosh tovush"
    terms = [span(text, "undosh tovush"), span(text, "tovush")]
    assert any("ustma-ust" in m for m in error_messages(record(text, terms)))


def test_adjacent_spans_allowed():
    text = "fonema-morfema"
    terms = [span(text, "fonema"), span(text, "morfema")]
    assert check(record(text, terms)).errors == []


def test_error_location_points_to_span():
    report = check(record(TEXT, [{"start": 0, "end": 6, "term": "fonema", "label": "X"}]))
    assert report.errors[0].location == "f:1 terms[0]"


def test_non_nfc_text_warns():
    text = "Fonema va ŏ"  # birikma belgi (NFD)
    report = check(record(text))
    assert report.errors == []
    assert any("NFC" in w.message for w in report.warnings)


# --- Fayl darajasidagi tekshiruvlar ---------------------------------------


def test_validate_files_ok(tmp_path):
    path = write_jsonl(tmp_path / "a.jsonl", [record(), record(text="Morfema.", terms=[], id="r2")])
    report = validate_files([path], {"d1"})
    assert report.ok and len(report.records) == 2


def test_blank_lines_skipped_and_line_numbers_reported(tmp_path):
    path = tmp_path / "a.jsonl"
    path.write_text(json.dumps(record()) + "\n\n{bad json\n", encoding="utf-8")
    report = validate_files([path])
    assert len(report.records) == 1
    [error] = report.errors
    assert error.location == f"{path}:3"
    assert "JSON xatosi" in error.message


def test_duplicate_ids_across_files(tmp_path):
    a = write_jsonl(tmp_path / "a.jsonl", [record()])
    b = write_jsonl(tmp_path / "b.jsonl", [record(text="Morfema.", terms=[])])
    report = validate_files([a, b])
    assert any("takrorlangan" in e.message for e in report.errors)
    assert len(report.records) == 1


def test_unknown_doc_id(tmp_path):
    path = write_jsonl(tmp_path / "a.jsonl", [record()])
    report = validate_files([path], {"boshqa"})
    assert any("reyestrida yo'q" in e.message for e in report.errors)


def test_doc_id_not_checked_without_registry(tmp_path):
    path = write_jsonl(tmp_path / "a.jsonl", [record()])
    assert validate_files([path]).ok


def test_duplicate_text_warns(tmp_path):
    first = record()
    second = {**record(), "id": "r2", "doc_id": "d2", "text": "  FONEMA va\nmorfema. "}
    second["terms"] = [span(second["text"], "FONEMA", "fonema")]
    path = write_jsonl(tmp_path / "a.jsonl", [first, second])
    report = validate_files([path])
    assert report.ok
    assert any("takrorlangan" in w.message for w in report.warnings)


def test_missing_and_non_utf8_files(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_bytes("fonema".encode("utf-16"))
    report = validate_files([tmp_path / "yoq.jsonl", bad])
    assert [e.message for e in report.errors] == ["fayl topilmadi", "fayl UTF-8 kodlashda emas"]


def test_load_annotations_raises_on_errors(tmp_path):
    path = write_jsonl(tmp_path / "a.jsonl", [record(status="bad")])
    with pytest.raises(AnnotationError):
        load_annotations([path])


# --- Manbalar reyestri ------------------------------------------------------


def test_valid_source():
    [source] = parse_sources([{"id": "d1", "title": "Kitob", "rights": "CC BY 4.0", "year": 2020}])
    assert source.year == 2020 and source.author is None


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"title": "Kitob", "rights": "CC BY"}, "'id'"),
        ({"id": "d1", "rights": "CC BY"}, "'title'"),
        ({"id": "d1", "title": "Kitob"}, "'rights'"),
        ({"id": "d1", "title": "Kitob", "rights": "  "}, "'rights'"),
        ({"id": "d1", "title": "Kitob", "rights": "CC BY", "year": "2020"}, "'year'"),
        ({"id": "d1", "title": "Kitob", "rights": "CC BY", "year": True}, "'year'"),
        ({"id": "d1", "title": "Kitob", "rights": "CC BY", "author": 1}, "'author'"),
        ({"id": "d1", "title": "Kitob", "rights": "CC BY", "licence": "x"}, "nomaʼlum maydon"),
    ],
)
def test_invalid_sources(item, expected):
    with pytest.raises(SourceRegistryError) as exc_info:
        parse_sources([item])
    assert any(expected in p for p in exc_info.value.problems), exc_info.value.problems


def test_duplicate_source_ids():
    item = {"id": "d1", "title": "Kitob", "rights": "CC BY"}
    with pytest.raises(SourceRegistryError, match="takrorlangan"):
        parse_sources([item, item])


def test_project_sources_file_is_valid():
    load_sources(REPO_ROOT / "data" / "sources.json")


# --- Namunalar va CLI ------------------------------------------------------


def test_documentation_examples_are_valid():
    sources = load_sources(EXAMPLES / "sources.example.json")
    report = validate_files([EXAMPLES / "annotation.example.jsonl"], {s.id for s in sources})
    assert report.ok, report.errors
    assert report.warnings == []
    assert len(report.records) == 2


def test_cli_ok(capsys):
    exit_code = validate.main(
        [str(EXAMPLES / "annotation.example.jsonl"), "--sources", str(EXAMPLES / "sources.example.json")]
    )
    assert exit_code == 0
    assert "Xato topilmadi" in capsys.readouterr().out


def test_cli_reports_errors(tmp_path, capsys):
    sources = tmp_path / "sources.json"
    sources.write_text("[]", encoding="utf-8")
    path = write_jsonl(tmp_path / "a.jsonl", [record()])
    assert validate.main([str(path), "--sources", str(sources)]) == 1
    assert "reyestrida yo'q" in capsys.readouterr().err


def test_cli_broken_sources(tmp_path, capsys):
    sources = tmp_path / "sources.json"
    sources.write_text("{", encoding="utf-8")
    assert validate.main(["--sources", str(sources)]) == 1
    assert "JSON xatosi" in capsys.readouterr().err
