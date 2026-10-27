from __future__ import annotations

import pytest

from app.database.term_store import parse_terms
from app.nlp.dictionary_matcher import (
    METHOD_EXACT,
    METHOD_INFLECTED,
    MATCH_SYNONYM,
    MATCH_TERM,
    MATCH_VARIANT,
    DictionaryMatcher,
)
from tests.conftest import make_entry


def spans(matches):
    return [(m.start, m.end, m.surface) for m in matches]


def terms(matches):
    return [m.candidates[0].entry.term for m in matches]


# --- Katta-kichik harf ---------------------------------------------------


@pytest.mark.parametrize("surface", ["morfologiya", "Morfologiya", "MORFOLOGIYA", "MorFoLogiya"])
def test_case_insensitive_and_surface_preserved(matcher, surface):
    text = f"Bu {surface} haqida."
    [match] = matcher.find(text)
    assert (match.start, match.end) == (3, 3 + len(surface))
    assert match.surface == surface
    assert match.candidates[0].entry.term == "morfologiya"


# --- Ko'p so'zli terminlar -----------------------------------------------


def test_multiword_term(matcher):
    text = "Har bir soʻz turkumi oʻrganiladi."
    [match] = matcher.find(text)
    assert spans([match]) == [(8, 20, "soʻz turkumi")]


@pytest.mark.parametrize("gap", ["  ", "\t", "\n", " \n  "])
def test_multiword_term_with_irregular_whitespace(matcher, gap):
    text = f"qoʻshma{gap}gap"
    [match] = matcher.find(text)
    assert (match.start, match.end) == (0, len(text))
    assert match.surface == text


def test_multiword_term_requires_all_words(matcher):
    assert matcher.find("qoʻshma soʻz") == []


# --- Bir necha marta uchrash ---------------------------------------------


def test_repeated_term_positions(matcher):
    text = "fonema, fonema va yana fonema"
    assert spans(matcher.find(text)) == [
        (0, 6, "fonema"),
        (8, 14, "fonema"),
        (23, 29, "fonema"),
    ]


# --- Uzunroq termin ichidagi termin --------------------------------------


def test_longer_term_wins_over_nested_term(matcher):
    text = "Undosh tovush va tovush."
    matches = matcher.find(text)
    assert spans(matches) == [(0, 13, "Undosh tovush"), (17, 23, "tovush")]
    assert terms(matches) == ["undosh tovush", "tovush"]


def test_longer_term_wins_regardless_of_dictionary_order():
    entries = parse_terms([make_entry("a", "gap"), make_entry("b", "qoʻshma gap")])
    reversed_entries = list(reversed(entries))
    for ordered in (entries, reversed_entries):
        [match] = DictionaryMatcher(ordered).find("qoʻshma gap")
        assert match.candidates[0].entry.term == "qoʻshma gap"


def test_overlapping_terms_keep_longest():
    entries = parse_terms([make_entry("a", "sodda gap"), make_entry("b", "gap boʻlagi")])
    # "sodda gap boʻlagi": ikkala termin "gap" so'zida kesishadi, uzunrog'i qoladi.
    [match] = DictionaryMatcher(entries).find("sodda gap boʻlagi")
    assert match.candidates[0].entry.term == "gap boʻlagi"


# --- So'z chegarasi ------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "polifonema",  # termin so'z o'rtasida
        "fonemaz",  # ruxsat etilmagan davomi
        "fonema2",  # raqam bilan davom etadi
        "2fonema",
        "fonetik",  # termin qisqartirilgan
    ],
)
def test_term_inside_other_word_not_matched(matcher, text):
    assert matcher.find(text) == []


def test_apostrophe_inside_word_is_part_of_word():
    entries = parse_terms([make_entry("a", "so"), make_entry("b", "z")])
    assert DictionaryMatcher(entries).find("soʻz so'z") == []


# --- Topilmaydigan termin va bo'sh matn ----------------------------------


def test_no_terms_found(matcher):
    assert matcher.find("Bugun havo juda yaxshi.") == []


@pytest.mark.parametrize("text", ["", " ", "\n\t  \n"])
def test_empty_text(matcher, text):
    assert matcher.find(text) == []


def test_non_string_text_rejected(matcher):
    with pytest.raises(TypeError):
        matcher.find(None)


def test_empty_dictionary():
    assert DictionaryMatcher([]).find("fonema") == []


# --- Apostrof variantlari -------------------------------------------------


@pytest.mark.parametrize("apostrophe", ["'", "`", "ʻ", "ʼ", "‘", "’", "´"])
def test_apostrophe_variants(matcher, apostrophe):
    text = f"o{apostrophe}zak"
    [match] = matcher.find(text)
    assert match.surface == text
    assert match.candidates[0].entry.term == "oʻzak"


def test_tutuq_belgisi_variants(matcher):
    for text in ("maʼno", "ma'no", "ma’no", "MAʼNO"):
        [match] = matcher.find(text)
        assert match.candidates[0].entry.term == "maʼno"


def test_dictionary_written_with_plain_apostrophe_matches_official_letter():
    entries = parse_terms([make_entry("a", "o'zak")])
    [match] = DictionaryMatcher(entries).find("Oʻzak")
    assert match.surface == "Oʻzak"


def test_quotes_around_term_are_not_part_of_term(matcher):
    text = "'fonema' va ‘morfologiya’"
    assert spans(matcher.find(text)) == [(1, 7, "fonema"), (13, 24, "morfologiya")]


# --- Matn boshi va oxiri --------------------------------------------------


def test_term_is_whole_text(matcher):
    assert spans(matcher.find("fonema")) == [(0, 6, "fonema")]


def test_term_at_start_and_end(matcher):
    text = "Fonema va morfologiya"
    assert spans(matcher.find(text)) == [(0, 6, "Fonema"), (10, 21, "morfologiya")]


# --- Tinish belgilari va qator tashlash ----------------------------------


def test_punctuation_and_newlines(matcher):
    text = "(fonema),\n«morfologiya»;\r\nfonetika!\t“tovush”?"
    matches = matcher.find(text)
    assert terms(matches) == ["fonema", "morfologiya", "fonetika", "tovush"]
    for match in matches:
        assert text[match.start : match.end] == match.surface


def test_hyphenated_neighbour_is_boundary(matcher):
    assert terms(matcher.find("fonema-tovush")) == ["fonema", "tovush"]


# --- Qo'shimchali shakllar -----------------------------------------------


@pytest.mark.parametrize(
    ("text", "suffix"),
    [
        ("fonemalar", "lar"),
        ("fonemalarning", "larning"),
        ("fonemani", "ni"),
        ("morfologiyaning", "ning"),
        ("fonetikaga", "ga"),
        ("fonemadagi", "dagi"),
        ("fonemalaridan", "laridan"),
    ],
)
def test_inflected_forms(matcher, text, suffix):
    [match] = matcher.find(text)
    assert match.surface == text
    assert match.suffix == suffix
    assert match.method == METHOD_INFLECTED


def test_inflected_multiword_term(matcher):
    text = "Soʻz turkumining belgilari."
    [match] = matcher.find(text)
    assert match.surface == "Soʻz turkumining"
    assert match.base_surface == "Soʻz turkumi"
    assert match.suffix == "ning"
    assert match.candidates[0].entry.term == "soʻz turkumi"


def test_known_limitation_inflection_inside_lemma(matcher):
    # "soʻz turkumi" -> "soʻz turkumlari": qo'shimcha egalik qo'shimchasidan
    # oldin qo'shiladi. Baseline buni bilmaydi; hujjatlashtirilgan cheklov.
    assert matcher.find("soʻz turkumlari") == []


def test_limitation_can_be_covered_by_dictionary_variant():
    entries = parse_terms(
        [make_entry("a", "soʻz turkumi", variants=["soʻz turkumlari"])]
    )
    [match] = DictionaryMatcher(entries).find("soʻz turkumlarini")
    assert match.candidates[0].match_type == MATCH_VARIANT
    assert match.suffix == "ni"


def test_exact_form_method(matcher):
    [match] = matcher.find("fonema")
    assert match.method == METHOD_EXACT
    assert match.suffix == ""
    assert match.base_surface == "fonema"


# --- Variant, sinonim va omonimlar ---------------------------------------


def test_match_types(matcher):
    matches = matcher.find("affiks, affix, qoʻshimcha")
    assert [m.candidates[0].match_type for m in matches] == [
        MATCH_TERM,
        MATCH_VARIANT,
        MATCH_SYNONYM,
    ]
    assert all(m.candidates[0].entry.term == "affiks" for m in matches)
    assert [m.candidates[0].matched_form for m in matches] == ["affiks", "affix", "qoʻshimcha"]


def test_same_form_in_two_entries_is_ambiguous():
    entries = parse_terms(
        [
            make_entry("a", "ot", domain="morfologiya"),
            make_entry("b", "ot", domain="umumiy"),
        ]
    )
    [match] = DictionaryMatcher(entries).find("ot")
    assert match.ambiguous
    assert {c.entry.id for c in match.candidates} == {"a", "b"}
