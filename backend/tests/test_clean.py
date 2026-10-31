from __future__ import annotations

from app.nlp.clean import canonical_apostrophes, clean_text, split_sentences


def test_canonical_apostrophes():
    assert canonical_apostrophes("o'zak, g'oya, tog', ma'no, fe`l") == "oʻzak, gʻoya, togʻ, maʼno, feʼl"
    assert canonical_apostrophes("So‘z va ma’no") == "Soʻz va maʼno"
    # qo'shtirnoq vazifasidagi belgi o'zgarmaydi, uzunlik saqlanadi
    text = "'fonema' va o'rin"
    assert canonical_apostrophes(text) == "'fonema' va oʻrin"
    assert len(canonical_apostrophes(text)) == len(text)


def test_clean_text():
    raw = "== Tarix ==\r\nFonema[1]  —   tovush​ birligi.\n\n\n\nIkkinchi   paragraf, so'z."
    assert clean_text(raw) == "Fonema — tovush birligi.\n\nIkkinchi paragraf, soʻz."


def _sentences(text: str) -> list[str]:
    return [text[a:b] for a, b in split_sentences(text)]


def test_split_sentences_keeps_abbreviations():
    text = (
        "Fonologiya N. S. Trubetskoy asarlarida shakllandi. Mas. tol, sol soʻzlari. "
        "Mil. av. IV asrda Aristotel St.ni 7 ga boʻldi. Bu „termin“ deyiladi! Keyingi gap"
    )
    assert _sentences(text) == [
        "Fonologiya N. S. Trubetskoy asarlarida shakllandi.",
        "Mas. tol, sol soʻzlari.",
        "Mil. av. IV asrda Aristotel St.ni 7 ga boʻldi.",
        "Bu „termin“ deyiladi!",
        "Keyingi gap",
    ]


def test_split_sentences_positions_point_into_text():
    text = "  Birinchi gap.  Ikkinchi gap. "
    assert split_sentences(text) == [(2, 15), (17, 30)]
    assert [text[a:b] for a, b in split_sentences(text)] == ["Birinchi gap.", "Ikkinchi gap."]
