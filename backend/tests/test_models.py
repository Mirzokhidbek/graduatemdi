from __future__ import annotations

import json
from collections import Counter

import pytest

from app.annotation.dictionary import AMBIGUOUS, merge
from app.annotation.silver import LexiconError, annotate_paragraph, build_matcher, combine, parse_lexicon
from app.dataset.annotation import AnnotatedRecord, AnnotatedSpan
from app.models.crf import BEGIN, INSIDE, OUTSIDE, TermCrf, bio_labels, build_lemmatizer, spans_from_labels
from app.nlp.tokenize import tokenize


# --- AI annotatsiya ro'yxatlari -----------------------------------------------


def test_lexicon_annotates_with_exclusions():
    base = parse_lexicon("unli tovush = unli\nfonema\n!~ ga ega\n")
    local = parse_lexicon("ega\nsifat\n!= sifatida\n!~ phonema — tovush\n-fonema\n")
    lexicon = combine(base, local)
    matcher = build_matcher(lexicon)
    text = "Ega va sifat. Unlilar sifatida xususiyatga ega. Fonema (phonema — tovush)."
    spans = annotate_paragraph(text, matcher, lexicon)
    assert [(text[s["start"] : s["end"]], s["term"]) for s in spans] == [
        ("Ega", "ega"),
        ("sifat", "sifat"),
        ("Unlilar", "unli tovush"),
    ]


def test_form_owned_by_two_lemmas_is_an_error():
    with pytest.raises(LexiconError):
        build_matcher(parse_lexicon("unli tovush = unli\nunli\n"))


# --- lug'atni train terminlari bilan to'ldirish ---------------------------------


def test_merge_skips_known_and_ambiguous_terms():
    entries = [{"id": "term-0001", "term": "fonema", "variants": [], "synonyms": ["fonem"]}]
    merged = merge(entries, Counter({"fonema": 5, "fonem": 1, "sifat": 9, "kelishik": 2, "undosh tovush": 3}), "test")
    assert [e["term"] for e in merged] == ["fonema", "undosh tovush", "kelishik"]
    assert merged[1]["id"] == "term-0002" and merged[1]["status"] == "needs_review" and merged[1]["source"] == "test"
    assert "sifat" in AMBIGUOUS


# --- CRF -----------------------------------------------------------------------


def test_bio_round_trip():
    text = "Undosh tovushlar va fonema."
    tokens = tokenize(text)
    labels = bio_labels(tokens, [(0, 16), (20, 26)])
    assert labels == [BEGIN, INSIDE, OUTSIDE, BEGIN]
    assert spans_from_labels(tokens, labels) == [(0, 16), (20, 26)]
    # yetim I yangi span boshlaydi
    assert spans_from_labels(tokens, [OUTSIDE, INSIDE, OUTSIDE, OUTSIDE]) == [(7, 16)]


def _record(text: str, spans: list[tuple[int, int, str]]) -> AnnotatedRecord:
    return AnnotatedRecord(
        id=f"r{abs(hash(text))}", doc_id="d", text=text,
        terms=tuple(AnnotatedSpan(s, e, t, "TERM") for s, e, t in spans), annotator=None, status="draft", notes=None,
    )


def test_crf_learns_and_predicts(tmp_path):
    texts = [
        ("Fonema tilning birligi.", [(0, 6, "fonema")]),
        ("Morfema soʻz qismi.", [(0, 7, "morfema")]),
        ("Leksema lugʻat birligi.", [(0, 7, "leksema")]),
        ("Sintaksis gapni oʻrganadi.", [(0, 9, "sintaksis")]),
        ("Bu kitob yaxshi.", []),
        ("Ular uyga ketdi.", []),
    ] * 3
    records = [_record(t, s) for t, s in texts]
    model = TermCrf(build_lemmatizer(t for t, _ in texts))
    model.train(records, tmp_path / "m.crfsuite")
    predicted = model.predict("Grafema yozuv birligi.")
    # yangi so'z, lekin -ema qo'shimchasi va gapdagi o'rni bo'yicha termin deb topiladi
    assert [(p.start, p.end) for p in predicted] == [(0, 7)]
    assert model.predict("Ular uyga ketdi.") == []
