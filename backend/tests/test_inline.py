from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from app.dataset import inline
from app.dataset.annotation import validate_files
from app.dataset.inline import convert_document, parse_inline, split_paragraphs

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_SOURCES = REPO_ROOT / "docs" / "examples" / "sources.example.json"


def messages(result) -> list[str]:
    return [issue.message for issue in result.errors]


# --- parse_inline ------------------------------------------------------------


def test_plain_text_without_marks():
    text, spans, _, problems = parse_inline("Bugun havo yaxshi.")
    assert text == "Bugun havo yaxshi." and spans == [] and problems == []


def test_marks_are_removed_and_offsets_computed():
    text, spans, offsets, problems = parse_inline(
        "[[Fonemalar|fonema]] va [[unli tovush]]."
    )
    assert problems == []
    assert text == "Fonemalar va unli tovush."
    assert [(s["start"], s["end"], s["term"], s["surface"]) for s in spans] == [
        (0, 9, "fonema", "Fonemalar"),
        (13, 24, "unli tovush", "unli tovush"),
    ]
    for span in spans:
        assert text[span["start"] : span["end"]] == span["surface"]
    assert offsets == [0, 24]


def test_default_term_is_lowercased_surface():
    _, [span], _, _ = parse_inline("[[Oʻzak]]")
    assert span["term"] == "oʻzak"


def test_term_whitespace_trimmed():
    _, [span], _, _ = parse_inline("[[fonemalar| fonema ]]")
    assert span["term"] == "fonema"


def test_single_brackets_are_plain_text():
    text, spans, _, problems = parse_inline("[1] [[fonema]] [a]")
    assert problems == [] and text == "[1] fonema [a]" and len(spans) == 1


@pytest.mark.parametrize(
    ("marked", "expected"),
    [
        ("[[fonema", "yopilmagan '[['"),
        ("fonema]] va", "ochilmagan ']]'"),
        ("[[a [[b]] c]]", "ichma-ich"),
        ("[[]]", "matn yo'q"),
        ("[[  ]]", "matn yo'q"),
        ("[[a|b|c]]", "bitta '|'"),
        ("[[fonemalar|]]", "termin yozilmagan"),
        ("[[fonemalar| ]]", "termin yozilmagan"),
    ],
)
def test_markup_problems(marked, expected):
    _, _, _, problems = parse_inline(marked)
    assert any(expected in message for _, message in problems), problems


def test_bad_mark_does_not_become_span_but_text_kept():
    text, spans, _, problems = parse_inline("[[a|b|c]] va [[fonema]]")
    assert len(problems) == 1
    assert text == "a va fonema"
    assert [s["surface"] for s in spans] == ["fonema"]


# --- Paragraflar --------------------------------------------------------------


def test_split_paragraphs_with_offsets():
    source = "\n  Birinchi\nqator.\n\n \t\nIkkinchi.  \n\n\n"
    paragraphs = split_paragraphs(source)
    assert [p.text for p in paragraphs] == ["Birinchi\nqator.", "Ikkinchi."]
    for paragraph in paragraphs:
        assert source[paragraph.offset :].startswith(paragraph.text)


def test_empty_source():
    assert split_paragraphs("") == [] and split_paragraphs("\n \n") == []
    result = convert_document("\n\n", "d1")
    assert result.ok and result.records == []


# --- convert_document ----------------------------------------------------------


SOURCE = (
    "[[Fonetika]] boʻlimida [[unli|unli tovush]] va\n"
    "[[undosh tovushlar|undosh tovush]] oʻrganiladi.\n"
    "\n"
    "Bu paragrafda termin yoʻq.\n"
)


def test_convert_document():
    result = convert_document(SOURCE, "d1", annotator="A1", status="reviewed")
    assert result.ok
    first, second = result.objects
    assert first["id"] == "d1-p001" and second["id"] == "d1-p002"
    assert first["text"] == "Fonetika boʻlimida unli va\nundosh tovushlar oʻrganiladi."
    assert [t["term"] for t in first["terms"]] == ["fonetika", "unli tovush", "undosh tovush"]
    assert second["terms"] == []
    assert first["annotator"] == "A1" and first["status"] == "reviewed"
    assert [len(r.terms) for r in result.records] == [3, 0]


def test_multiword_mark_across_line_break():
    result = convert_document("[[Qoʻshma\ngaplarning|qoʻshma gap]] tuzilishi", "d1")
    assert result.ok
    [span] = result.objects[0]["terms"]
    assert span["surface"] == "Qoʻshma\ngaplarning"


def test_crlf_and_nfc_normalized():
    nfd = unicodedata.normalize("NFD", "ŏ")
    assert len(nfd) == 2
    result = convert_document(f"[[fonema]] {nfd}\r\n\r\n[[morfema]]\r\n", "d1")
    assert result.ok
    assert [o["text"] for o in result.objects] == ["fonema ŏ", "morfema"]


def test_validation_errors_point_to_source_line_and_column():
    source = "Birinchi [[fonema]].\n\nIkkinchi\n[[fonem]]alar va [[ morfema]]."
    result = convert_document(source, "d1", source_name="f.txt")
    assert [str(issue) for issue in result.errors] == [
        "f.txt:4:1: span so'z o'rtasida tugaydi: 'fonem'",
        "f.txt:4:18: span harf yoki raqam bilan boshlanib, tugashi kerak: ' morfema'",
    ]
    # Xatosiz paragraf baribir qaytariladi, lekin CLI hech narsa yozmaydi.
    assert [r.id for r in result.records] == ["d1-p001"]


def test_markup_and_validation_errors_reported_together():
    result = convert_document("[[polifonem]]a va [[a|b|c]]", "d1")
    assert len(result.errors) == 2
    assert result.records == []


def test_invalid_status_rejected():
    with pytest.raises(ValueError):
        convert_document("fonema", "d1", status="done")


def test_converted_file_passes_validator(tmp_path):
    result = convert_document(SOURCE, "example-doc")
    path = tmp_path / "out.jsonl"
    path.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in result.objects), encoding="utf-8")
    report = validate_files([path], {"example-doc"})
    assert report.ok and report.warnings == [] and len(report.records) == 2


# --- CLI -------------------------------------------------------------------------


@pytest.fixture
def marked_file(tmp_path) -> Path:
    path = tmp_path / "doc.txt"
    path.write_text(SOURCE, encoding="utf-8")
    return path


def run(marked_file: Path, *extra: str) -> int:
    return inline.main(
        [str(marked_file), "--doc-id", "example-doc", "--sources", str(EXAMPLE_SOURCES), *extra]
    )


def test_cli_writes_output(marked_file, tmp_path, capsys):
    output = tmp_path / "annotated" / "doc.jsonl"
    assert run(marked_file, "-o", str(output), "--annotator", "A1") == 0
    assert "2 ta yozuv, 3 ta span" in capsys.readouterr().out
    lines = output.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["id"] for line in lines] == ["example-doc-p001", "example-doc-p002"]


def test_cli_stdout(marked_file, capsys):
    assert run(marked_file) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["doc_id"] == "example-doc"


def test_cli_refuses_to_overwrite(marked_file, tmp_path, capsys):
    output = tmp_path / "doc.jsonl"
    output.write_text("qo'lda tahrirlangan\n", encoding="utf-8")
    assert run(marked_file, "-o", str(output)) == 1
    assert "--force" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "qo'lda tahrirlangan\n"
    assert run(marked_file, "-o", str(output), "--force") == 0
    assert output.read_text(encoding="utf-8").startswith("{")


def test_cli_unknown_doc_id(marked_file, capsys):
    exit_code = inline.main(
        [str(marked_file), "--doc-id", "yoq", "--sources", str(EXAMPLE_SOURCES)]
    )
    assert exit_code == 1
    assert "reyestrida" in capsys.readouterr().err


def test_cli_errors_write_nothing(tmp_path, capsys):
    source = tmp_path / "doc.txt"
    source.write_text("[[fonem]]alar", encoding="utf-8")
    output = tmp_path / "doc.jsonl"
    assert run(source, "-o", str(output)) == 1
    assert "fayl yozilmadi" in capsys.readouterr().err
    assert not output.exists()


def test_cli_missing_input(tmp_path, capsys):
    assert run(tmp_path / "yoq.txt") == 1
    assert "o'qib bo'lmadi" in capsys.readouterr().err
