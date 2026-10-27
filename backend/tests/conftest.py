from __future__ import annotations

from typing import Any

import pytest

from app.database.term_store import parse_terms
from app.nlp.dictionary_matcher import DictionaryMatcher


def make_entry(entry_id: str, term: str, **fields: Any) -> dict[str, Any]:
    return {"id": entry_id, "term": term, "preferred_form": term, **fields}


# Testlar data/terms.json'ga bog'liq bo'lmasligi uchun alohida kichik baza.
TEST_TERMS = [
    make_entry("t1", "morfologiya"),
    make_entry("t2", "fonema"),
    make_entry("t3", "fonetika"),
    make_entry("t4", "tovush"),
    make_entry("t5", "undosh tovush", synonyms=["undosh"]),
    make_entry("t6", "soʻz turkumi"),
    make_entry("t7", "oʻzak"),
    make_entry("t8", "qoʻshma gap"),
    make_entry("t9", "maʼno"),
    make_entry("t10", "affiks", variants=["affix"], synonyms=["qoʻshimcha"]),
]


@pytest.fixture
def matcher() -> DictionaryMatcher:
    return DictionaryMatcher(parse_terms(TEST_TERMS))
