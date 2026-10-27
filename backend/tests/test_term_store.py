from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.database.term_store import (
    STATUS_NEEDS_REVIEW,
    TermDatabaseError,
    load_terms,
    parse_terms,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def problems_of(raw) -> list[str]:
    with pytest.raises(TermDatabaseError) as exc_info:
        parse_terms(raw)
    return exc_info.value.problems


def test_project_terms_file_is_valid():
    entries = load_terms(REPO_ROOT / "data" / "terms.json")
    assert entries
    # Manbasi ko'rsatilmagan namunaviy yozuvlar tasdiqlangan bo'lmasligi kerak.
    for entry in entries:
        if entry.source is None:
            assert entry.status == STATUS_NEEDS_REVIEW


def test_minimal_entry_gets_defaults():
    [entry] = parse_terms([{"id": "a", "term": " fonema "}])
    assert entry.term == "fonema"
    assert entry.variants == ()
    assert entry.synonyms == ()
    assert entry.status == STATUS_NEEDS_REVIEW
    assert entry.definition is None and entry.source is None and entry.preferred_form is None


def test_duplicate_variants_removed():
    [entry] = parse_terms([{"id": "a", "term": "affiks", "variants": ["affix", " affix "]}])
    assert entry.variants == ("affix",)


def test_root_must_be_list():
    assert problems_of({"id": "a", "term": "fonema"})


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"term": "fonema"}, "'id'"),
        ({"id": "", "term": "fonema"}, "'id'"),
        ({"id": "a"}, "'term'"),
        ({"id": "a", "term": "   "}, "'term'"),
        ({"id": "a", "term": "..."}, "'term'"),
        ({"id": "a", "term": 5}, "'term'"),
        ({"id": "a", "term": "fonema", "definition": 3}, "'definition'"),
        ({"id": "a", "term": "fonema", "variants": "fonem"}, "'variants'"),
        ({"id": "a", "term": "fonema", "synonyms": [""]}, "'synonyms[0]'"),
        ({"id": "a", "term": "fonema", "status": "ok"}, "'status'"),
        ({"id": "a", "term": "fonema", "varaints": []}, "nomaʼlum maydon"),
        (
            {"id": "a", "term": "fonema", "preferred_form": "fonema", "status": "approved"},
            "'source'",
        ),
        (
            {"id": "a", "term": "fonema", "source": "Lug'at, 2020", "status": "approved"},
            "'preferred_form'",
        ),
    ],
)
def test_invalid_entries_rejected(item, expected):
    problems = problems_of([item])
    assert any(expected in p for p in problems), problems


def test_non_object_entry_rejected():
    assert any("JSON obyekt" in p for p in problems_of(["fonema"]))


def test_duplicate_ids_rejected():
    problems = problems_of([{"id": "a", "term": "fonema"}, {"id": "a", "term": "morfema"}])
    assert any("takrorlangan" in p for p in problems)


def test_all_problems_reported_together():
    problems = problems_of([{"id": "a"}, {"id": "b", "term": "x", "status": "bad"}])
    assert len(problems) == 2
    assert problems[0].startswith("#0 (a)")
    assert problems[1].startswith("#1 (b)")


def test_approved_entry_with_source_is_valid():
    [entry] = parse_terms(
        [
            {
                "id": "a",
                "term": "fonema",
                "preferred_form": "fonema",
                "status": "approved",
                "source": "Test manbasi",
            }
        ]
    )
    assert entry.status == "approved"


def test_invalid_json_file(tmp_path):
    path = tmp_path / "terms.json"
    path.write_text("[{", encoding="utf-8")
    with pytest.raises(TermDatabaseError, match="JSON xatosi"):
        load_terms(path)


def test_missing_file(tmp_path):
    with pytest.raises(TermDatabaseError, match="fayl topilmadi"):
        load_terms(tmp_path / "yoq.json")


def test_load_valid_file(tmp_path):
    path = tmp_path / "terms.json"
    path.write_text(json.dumps([{"id": "a", "term": "oʻzak"}], ensure_ascii=False), encoding="utf-8")
    [entry] = load_terms(path)
    assert entry.term == "oʻzak"
