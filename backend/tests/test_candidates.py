from __future__ import annotations

import csv
import json
import math

import pytest

from app.evaluation.ranking import coverage, precision_at_k
from app.nlp import candidates as candidates_module
from app.nlp.candidates import (
    Candidate,
    build_lemmatizer,
    c_values,
    extract_candidates,
    lemmatize_form,
    rank,
    tfidf_scores,
)
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.tokenize import phrases, tokenize
from tests.conftest import make_entry

# --- tokenize ---------------------------------------------------------------------


def test_tokenize_keeps_inner_apostrophe_and_positions():
    text = "Soʻz va maʼno, 2024-yil «fonema»."
    tokens = tokenize(text)
    assert [t.text for t in tokens] == ["Soʻz", "va", "maʼno", "yil", "fonema"]
    assert [t.norm for t in tokens] == ["so'z", "va", "ma'no", "yil", "fonema"]
    for token in tokens:
        assert text[token.start : token.end] == token.text


def test_phrases_split_on_punctuation_not_on_whitespace():
    text = "unli tovush,\nundosh\ntovush (fonema) va-morfema"
    assert [[t.norm for t in p] for p in phrases(text)] == [
        ["unli", "tovush"],
        ["undosh", "tovush"],
        ["fonema"],
        ["va"],
        ["morfema"],
    ]


def test_tokenize_empty():
    assert tokenize("") == [] and phrases("  ,. 12") == []


# --- lemmatize -----------------------------------------------------------------------


def test_lemmatizer_requires_attested_stem():
    lemmatizer = CorpusLemmatizer({"fonema", "fonemalar", "bola"})
    assert lemmatizer.lemma("fonemalarning") == "fonema"  # eng qisqa o'zak
    assert lemmatizer.lemma("fonemaga") == "fonema"
    assert lemmatizer.lemma("morfemalar") == "morfemalar"  # "morfema" korpusda yo'q
    assert lemmatizer.lemma("bolalar") == "bola"
    assert lemmatizer.lemma("fonemaz") == "fonemaz"  # "z" qo'shimcha emas


def test_lemmatizer_min_stem():
    lemmatizer = CorpusLemmatizer({"ot", "un"})
    assert lemmatizer.lemma("otga") == "otga"
    assert lemmatizer.lemma("unga") == "unga"


# --- extract_candidates -------------------------------------------------------------------


def test_extract_candidates_counts_and_surfaces():
    documents = {
        "d1": "Undosh tovush va undosh tovushlar. Tovush!",
        "d2": "Undosh tovushning belgisi.",
    }
    found = extract_candidates(documents, max_words=2)
    pair = found[("undosh", "tovush")]
    assert pair.frequency == 3
    assert pair.documents == {"d1", "d2"}
    assert pair.surfaces == {"Undosh tovush": 1, "undosh tovushlar": 1, "Undosh tovushning": 1}
    assert found[("tovush",)].frequency == 4
    assert found[("tovush",)].doc_frequency == 2


def test_candidates_do_not_start_or_end_with_stopword_or_cross_punctuation():
    found = extract_candidates({"d": "fonema va morfema, sintaksis bilan"}, max_words=3)
    assert set(found) == {("fonema",), ("morfema",), ("sintaksis",), ("fonema", "va", "morfema")}


def test_only_last_word_is_lemmatized():
    found = extract_candidates({"d": "tilning tovushlari. Til va tovush."}, max_words=2)
    assert ("tilning", "tovush") in found
    assert ("til", "tovush") not in found


def test_short_candidates_dropped():
    assert extract_candidates({"d": "ot u"}) == {}


def test_invalid_max_words():
    with pytest.raises(ValueError):
        extract_candidates({"d": "fonema"}, max_words=0)


# --- ballar ------------------------------------------------------------------------------


def make(key, frequency, docs=("d",)):
    return Candidate(tuple(key), frequency, set(docs))


def test_c_value_hand_computed():
    pool = {
        ("undosh", "tovush"): make(("undosh", "tovush"), 3),
        ("unli", "tovush"): make(("unli", "tovush"), 1),
        ("tovush",): make(("tovush",), 5),
        ("fonema",): make(("fonema",), 4),
    }
    scores = c_values(pool)
    # tovush ikki nomzod ichida: (3 + 1) / 2 = 2
    assert scores[("tovush",)] == pytest.approx(math.log2(2) * (5 - 2))
    assert scores[("fonema",)] == pytest.approx(math.log2(2) * 4)
    assert scores[("undosh", "tovush")] == pytest.approx(math.log2(3) * 3)


def test_c_value_three_word_containment():
    pool = {
        ("a", "b", "c"): make(("a", "b", "c"), 2),
        ("b", "c"): make(("b", "c"), 4),
        ("a", "c"): make(("a", "c"), 3),  # uzluksiz qism emas
    }
    scores = c_values(pool)
    assert scores[("b", "c")] == pytest.approx(math.log2(3) * (4 - 2))
    assert scores[("a", "c")] == pytest.approx(math.log2(3) * 3)


def test_tfidf_hand_computed():
    pool = {("a",): make(("a",), 6, docs=("d1", "d2")), ("b",): make(("b",), 6, docs=("d1",))}
    scores = tfidf_scores(pool, n_documents=3)
    assert scores[("a",)] == pytest.approx(6 * (math.log(4 / 3) + 1))
    assert scores[("b",)] == pytest.approx(6 * (math.log(4 / 2) + 1))
    assert scores[("b",)] > scores[("a",)]


def test_rank_orders_and_filters():
    pool = {
        ("a",): make(("a",), 1),
        ("b",): make(("b",), 5),
        ("c",): make(("c",), 5),
        ("d",): make(("d",), 9),
    }
    ranked = rank(pool, "frequency", n_documents=1, min_frequency=2)
    assert [c.text for c, _ in ranked] == ["d", "b", "c"]  # teng ballda alifbo tartibi


def test_rank_min_frequency_applies_before_c_value_nesting():
    pool = {("x", "y"): make(("x", "y"), 1), ("y",): make(("y",), 4)}
    [(only, score)] = rank(pool, "cvalue", n_documents=1, min_frequency=2)
    assert only.key == ("y",) and score == pytest.approx(4.0)


def test_rank_invalid_method():
    with pytest.raises(ValueError):
        rank({}, "bm25", n_documents=1)


# --- Precision@K ----------------------------------------------------------------------


def test_precision_at_k():
    ranked = [("a",), ("b",), ("c",), ("d",)]
    reference = {("b",), ("d",), ("z",)}
    result = precision_at_k(ranked, reference, 2)
    assert (result.hits, result.considered, result.precision) == (1, 2, 0.5)
    assert precision_at_k(ranked, reference, 10).considered == 4
    assert precision_at_k([], reference, 5).precision is None
    assert coverage(ranked, reference) == (2, 3)
    with pytest.raises(ValueError):
        precision_at_k(ranked, reference, 0)


def test_lemmatize_form_matches_candidate_keys():
    documents = {"d": "Soʻz turkumlari va soʻz turkum."}
    lemmatizer = build_lemmatizer(documents)
    assert lemmatize_form("Soʻz turkumi", lemmatizer) == ("so'z", "turkum")
    assert ("so'z", "turkum") in extract_candidates(documents, lemmatizer=lemmatizer)
    assert lemmatize_form("...", lemmatizer) == ()


# --- CLI ------------------------------------------------------------------------------------


@pytest.fixture
def corpus(tmp_path):
    (tmp_path / "a.txt").write_text("Undosh tovush va unli tovush. Undosh tovushlar.", encoding="utf-8")
    (tmp_path / "b.txt").write_text("Fonema va undosh tovush. Fonemalar.", encoding="utf-8")
    terms = tmp_path / "terms.json"
    terms.write_text(json.dumps([make_entry("t1", "undosh tovush"), make_entry("t2", "fonema")]), encoding="utf-8")
    return tmp_path, terms


def run(tmp_path, terms, *extra):
    return candidates_module.main(
        [str(tmp_path / "a.txt"), str(tmp_path / "b.txt"), "--terms", str(terms), *extra]
    )


def test_cli_prints_ranking_and_precision(corpus, capsys):
    tmp_path, terms = corpus
    assert run(tmp_path, terms, "--reference-terms", str(terms), "--top", "3") == 0
    out = capsys.readouterr().out
    assert "Hujjatlar: 2" in out
    assert "undosh tovush" in out
    assert "Precision@10" in out and "Qamrov: 2/2" in out


def test_cli_writes_csv_and_json(corpus):
    tmp_path, terms = corpus
    assert run(tmp_path, terms, "--output", str(tmp_path / "out.csv"), "--method", "frequency") == 0
    rows = list(csv.DictReader((tmp_path / "out.csv").open(encoding="utf-8")))
    assert rows[0]["rank"] == "1" and "candidate" in rows[0]
    assert run(tmp_path, terms, "--output", str(tmp_path / "out.json")) == 0
    payload = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert payload["method"] == "cvalue" and payload["documents"] == 2
    top = {row["candidate"]: row for row in payload["candidates"]}
    assert top["undosh tovush"]["in_dictionary"] is True


def test_cli_reference_from_annotations(corpus, capsys):
    tmp_path, terms = corpus
    gold = tmp_path / "gold.jsonl"
    gold.write_text(json.dumps({
        "id": "r", "doc_id": "d", "text": "Fonemalar", "status": "reviewed",
        "terms": [{"start": 0, "end": 9, "term": "fonema", "label": "TERM"}],
    }) + "\n", encoding="utf-8")
    assert run(tmp_path, terms, "--reference-annotations", str(gold)) == 0
    assert "Maʼlum terminlar ro'yxati: 1 ta" in capsys.readouterr().out


def test_cli_no_files(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("app.dataset.validate.REPO_ROOT", tmp_path)
    assert candidates_module.main([]) == 1
    assert "topilmadi" in capsys.readouterr().err
