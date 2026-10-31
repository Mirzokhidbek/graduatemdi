from __future__ import annotations

import pytest

from app.database.term_store import parse_terms
from app.dataset.bio import BEGIN, INSIDE, OUTSIDE, Edit, apply_edit, to_bio, validate_bio
from app.services.term_normalizer import TermNormalizer
from tests.conftest import make_entry


@pytest.fixture
def normalizer() -> TermNormalizer:
    entries = parse_terms(
        [
            make_entry("t1", "affiks", synonyms=["qoʻshimcha"]),
            make_entry("t2", "undosh tovush"),
            make_entry("t3", "fonema", status="approved", source="Darslik"),
        ]
    )
    vocabulary = ["kelishik", "boʻlak", "gap", "nutq", "soʻz", "birikma", "oʻrin", "ravish", "lingvistika", "tovush"]
    return TermNormalizer(entries, vocabulary)


@pytest.mark.parametrize(
    "surface, lemma, method",
    [
        ("Fonemalarning", "fonema", "dictionary"),
        ("qoʻshimchalari", "qoʻshimcha", "dictionary"),  # sinonim: o'z lug'at shakli, asosiy termin alohida
        ("undosh tovushlari", "undosh tovush", "dictionary"),
        ("kelishigi", "kelishik", "morphology"),  # g -> k tiklanadi
        ("oʻrni", "oʻrin", "morphology"),  # tushgan unli tiklanadi
        ("gap boʻlaklarini", "gap boʻlagi", "morphology"),  # izofa saqlanadi, k -> g
        ("soʻz birikmalari", "soʻz birikmasi", "morphology"),
        ("nutq tovushlari", "nutq tovushi", "morphology"),
        ("dialektografiyaga", "dialektografiya", "morphology"),  # korpusda yo'q o'zak, aniq kelishik
        ("lingvistika", "lingvistika", "unchanged"),  # "-i" + "-ka" emas
        ("Ravishlar", "ravish", "morphology"),
    ],
)
def test_normalize(normalizer, surface, lemma, method):
    result = normalizer.normalize(surface)
    assert (result.lemma, result.method) == (lemma, method)


def test_dictionary_result_carries_main_term_and_status(normalizer):
    synonym = normalizer.normalize("qoʻshimcha")
    assert (synonym.lemma, synonym.term, synonym.status) == ("qoʻshimcha", "affiks", "needs_review")
    approved = normalizer.normalize("fonemaga")
    assert (approved.term, approved.preferred_form, approved.status) == ("fonema", "fonema", "approved")
    # morfologiya natijasi meʼyoriy deb eʼlon qilinmaydi
    assert normalizer.normalize("kelishigi").status == "no_data"


def test_hyphen_inside_term_is_kept(normalizer):
    assert normalizer.normalize("kasb-hunar ravishlari").lemma == "kasb-hunar ravishi"


# --- BIO ------------------------------------------------------------------------


def test_bio_conversion_and_validation():
    obj = to_bio("Undosh tovushlar va fonema.", [(0, 16, "undosh tovush"), (20, 26, "fonema")])
    assert obj["tags"] == [BEGIN, INSIDE, OUTSIDE, BEGIN]
    assert validate_bio(obj) == []

    broken = dict(obj, tags=[INSIDE, INSIDE, OUTSIDE, BEGIN])
    problems = validate_bio(broken)
    assert any("I-TERM" in p for p in problems) and any("mos emas" in p for p in problems)

    shifted = dict(obj, terms=[{"start": 1, "end": 16, "term": "x", "surface": "ndosh tovushlar"}])
    assert any("so'z chegarasida" in p for p in validate_bio(shifted))


def test_review_edits():
    text = "Ravishlar gapda hol vazifasida keladi."
    spans = [(0, 9, "ravish")]
    added = apply_edit(text, spans, Edit(1, True, "gapda", "gap"))
    assert added == [(0, 9, "ravish"), (10, 15, "gap")]
    assert apply_edit(text, added, Edit(1, False, "gapda", None)) == spans
    with pytest.raises(ValueError):
        apply_edit(text, spans, Edit(1, True, "yoʻq", "x"))
