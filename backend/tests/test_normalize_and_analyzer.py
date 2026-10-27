from __future__ import annotations

import json

import pytest

from app import cli
from app.database.term_store import parse_terms
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.nlp.normalize import normalize_form, normalize_text
from app.services.analyzer import analyze_text
from tests.conftest import make_entry


@pytest.mark.parametrize("text", ["", "Oʻzbek", "İstanbul ẞ ǅ", "MAʼNO’", "a\nb\t c"])
def test_normalization_preserves_length(text):
    assert len(normalize_text(text)) == len(text)


def test_normalize_form():
    assert normalize_form("  Qoʻshma \n GAP ") == "qo'shma gap"


def test_analyzer_output_for_needs_review_term(matcher):
    [result] = analyze_text("Fonemalar", matcher)
    assert result["surface"] == "Fonemalar"
    assert result["base_surface"] == "Fonema"
    assert (result["start"], result["end"]) == (0, 9)
    assert result["term"] == "fonema"
    assert result["method"] == "dictionary_inflected"
    assert result["confidence"] is None
    assert result["review_required"] is True
    [candidate] = result["candidates"]
    assert candidate["normalization"]["status"] == "needs_review"
    assert candidate["normalization"]["label"].startswith("Tavsiya")
    assert candidate["normalization"]["surface_matches_preferred"] is True


def test_approved_term_is_reported_with_source():
    entries = parse_terms(
        [
            make_entry(
                "a", "affiks", synonyms=["qoʻshimcha"], status="approved", source="Test manbasi"
            )
        ]
    )
    [result] = analyze_text("qoʻshimcha", DictionaryMatcher(entries))
    normalization = result["candidates"][0]["normalization"]
    assert normalization["status"] == "approved"
    assert "Test manbasi" in normalization["label"]
    assert normalization["preferred_form"] == "affiks"
    assert normalization["surface_matches_preferred"] is False
    assert result["review_required"] is False


def test_missing_preferred_form_is_not_invented():
    entries = parse_terms([{"id": "a", "term": "fonema"}])
    [result] = analyze_text("fonema", DictionaryMatcher(entries))
    normalization = result["candidates"][0]["normalization"]
    assert normalization["status"] == "no_data"
    assert normalization["preferred_form"] is None


def test_ambiguous_match_requires_review():
    entries = parse_terms(
        [
            make_entry("a", "ot", status="approved", source="A"),
            make_entry("b", "ot", status="approved", source="B"),
        ]
    )
    [result] = analyze_text("ot", DictionaryMatcher(entries))
    assert result["ambiguous"] is True
    assert result["term"] is None
    assert result["review_required"] is True


def test_cli_outputs_json(capsys):
    exit_code = cli.main(["Fonema va soʻz turkumi."])
    assert exit_code == 0
    results = json.loads(capsys.readouterr().out)
    assert [r["term"] for r in results] == ["fonema", "soʻz turkumi"]


def test_cli_reports_broken_database(tmp_path, capsys):
    path = tmp_path / "terms.json"
    path.write_text('[{"id": "a"}]', encoding="utf-8")
    assert cli.main(["--terms", str(path), "fonema"]) == 1
    assert "'term'" in capsys.readouterr().err
