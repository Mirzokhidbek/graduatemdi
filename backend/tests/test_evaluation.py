from __future__ import annotations

import json

import pytest

from app.database.term_store import parse_terms
from app.dataset.annotation import AnnotatedRecord, AnnotatedSpan
from app.evaluation import evaluate
from app.evaluation.errors import (
    AMBIGUOUS,
    BOUNDARY,
    FALSE_POSITIVE,
    MISSED,
    TERM_MISMATCH,
    classify_errors,
    context_window,
)
from app.evaluation.evaluate import evaluate_records
from app.evaluation.metrics import Scores, Span, exact_scores, partial_scores
from app.nlp.dictionary_matcher import DictionaryMatcher
from tests.conftest import make_entry

# --- Scores -----------------------------------------------------------------


def test_scores_values():
    scores = Scores(correct_predicted=3, predicted=4, correct_gold=3, gold=6)
    assert scores.precision == 0.75
    assert scores.recall == 0.5
    assert scores.f1 == pytest.approx(2 * 0.75 * 0.5 / 1.25)


def test_scores_undefined_when_denominator_zero():
    no_predictions = Scores(0, 0, 0, 5)
    assert no_predictions.precision is None
    assert no_predictions.recall == 0.0
    assert no_predictions.f1 is None
    no_gold = Scores(0, 3, 0, 0)
    assert no_gold.recall is None and no_gold.f1 is None


def test_f1_zero_when_nothing_correct():
    assert Scores(0, 2, 0, 2).f1 == 0.0


# --- exact / partial -----------------------------------------------------------


def test_exact_scores_hand_computed():
    pairs = [
        ([Span(0, 6), Span(10, 17)], [Span(0, 6), Span(10, 15), Span(20, 25)]),
        ([Span(0, 4)], []),
        ([], [Span(3, 8)]),
    ]
    scores = exact_scores(pairs)
    assert (scores.correct_predicted, scores.predicted, scores.gold) == (1, 4, 3)
    assert scores.precision == pytest.approx(1 / 4)
    assert scores.recall == pytest.approx(1 / 3)


def test_partial_scores_hand_computed():
    pairs = [
        # 10-15 oltin 10-17 ga tegadi; 20-25 hech narsaga tegmaydi
        ([Span(0, 6), Span(10, 17)], [Span(0, 6), Span(10, 15), Span(20, 25)]),
        # bitta keng bashorat ikkita oltin spanga tegadi
        ([Span(0, 4), Span(5, 9)], [Span(2, 7)]),
    ]
    scores = partial_scores(pairs)
    assert (scores.correct_predicted, scores.predicted) == (3, 4)
    assert (scores.correct_gold, scores.gold) == (4, 4)


def test_adjacent_spans_do_not_overlap():
    assert not Span(0, 5).overlaps(Span(5, 9))
    assert Span(0, 5).overlaps(Span(4, 9))


# --- Xato toifalari -----------------------------------------------------------


def categories(errors):
    return [e.category for e in errors]


def test_error_categories():
    text = "fonema va morfologiya hamda soʻz turkumi, sintaksis"
    gold = [
        Span(0, 6, "fonema"),  # aniq, lug'at shakli to'g'ri — xato emas
        Span(10, 21, "morfologiya"),  # aniq, lekin boshqa termin -> term_mismatch
        Span(28, 40, "soʻz turkumi"),  # bashorat faqat "turkumi" -> boundary
        Span(42, 51, "sintaksis"),  # topilmagan -> missed
    ]
    predicted = [
        Span(0, 6, "fonema"),
        Span(10, 21, "morfema"),
        Span(33, 40, "turkum"),
        Span(22, 27, "hamda"),  # false positive
    ]
    errors = classify_errors("r1", text, gold, predicted, lambda term: term == "sintaksis")
    assert categories(errors) == [TERM_MISMATCH, FALSE_POSITIVE, BOUNDARY, MISSED]
    missed = errors[-1]
    assert missed.in_dictionary is True
    assert missed.gold.term == "sintaksis"


def test_ambiguous_prediction():
    errors = classify_errors("r1", "ot", [Span(0, 2, "ot")], [Span(0, 2, None)], lambda _: True)
    assert categories(errors) == [AMBIGUOUS]


def test_term_comparison_ignores_apostrophe_variants():
    errors = classify_errors("r1", "oʻzak", [Span(0, 5, "o'zak")], [Span(0, 5, "oʻzak")], lambda _: True)
    assert errors == []


def test_one_prediction_spanning_two_gold_terms_is_boundary_for_both():
    text = "fonema morfema"
    gold = [Span(0, 6, "fonema"), Span(7, 14, "morfema")]
    errors = classify_errors("r1", text, gold, [Span(0, 14, "x")], lambda _: True)
    assert categories(errors) == [BOUNDARY, BOUNDARY]


def test_missed_not_in_dictionary():
    [error] = classify_errors("r1", "fonema", [Span(0, 6, "fonema")], [], lambda _: False)
    assert error.category == MISSED and error.in_dictionary is False


def test_context_window():
    text = "a" * 50 + "fonema" + "b" * 50
    snippet = context_window(text, 50, 56, width=5)
    assert snippet == "…aaaaa⟦fonema⟧bbbbb…"
    assert context_window("fonema\nva", 0, 6) == "⟦fonema⟧ va"


# --- evaluate_records ---------------------------------------------------------------


@pytest.fixture
def matcher():
    entries = parse_terms(
        [
            make_entry("t1", "fonema"),
            make_entry("t2", "undosh tovush"),
            make_entry("t3", "tovush"),
            make_entry("t4", "ot"),
            make_entry("t5", "ot", domain="boshqa"),
        ]
    )
    return DictionaryMatcher(entries)


def record(text, spans, record_id="r1"):
    terms = []
    for surface, term in spans:
        start = text.index(surface)
        terms.append(AnnotatedSpan(start, start + len(surface), term, "TERM"))
    return AnnotatedRecord(record_id, "d1", text, tuple(terms), None, "reviewed", None)


def test_evaluate_records_end_to_end(matcher):
    records = [
        # fonemalar: aniq; undosh tovushlar: aniq; morfema: lug'atda yo'q -> missed
        record("Fonemalar, undosh tovushlar va morfema.", [("Fonemalar", "fonema"), ("undosh tovushlar", "undosh tovush"), ("morfema", "morfema")]),
        # "tovush" belgilanmagan -> false positive; "ot" noaniq
        record("Bu tovush emas, ot.", [("ot", "ot")], "r2"),
    ]
    result = evaluate_records(records, matcher)
    assert result.records == 2
    assert (result.exact.correct_predicted, result.exact.predicted, result.exact.gold) == (3, 4, 4)
    assert result.exact.precision == 0.75 and result.exact.recall == 0.75
    assert (result.term_correct, result.exact_matches) == (2, 3)
    assert result.error_counts() == {
        MISSED: 1, FALSE_POSITIVE: 1, BOUNDARY: 0, TERM_MISMATCH: 0, AMBIGUOUS: 1,
    }
    assert result.missed_in_dictionary() == 0


def test_evaluate_record_without_terms(matcher):
    result = evaluate_records([record("Bugun havo yaxshi.", [])], matcher)
    assert result.exact.precision is None and result.exact.recall is None
    assert result.term_accuracy is None


# --- CLI ------------------------------------------------------------------------------


@pytest.fixture
def files(tmp_path):
    terms = tmp_path / "terms.json"
    terms.write_text(json.dumps([make_entry("t1", "fonema")]), encoding="utf-8")
    data = tmp_path / "validation.jsonl"
    rows = [
        {"id": "r1", "doc_id": "d1", "text": "Fonemalar va morfema.", "status": "reviewed",
         "terms": [{"start": 0, "end": 9, "term": "fonema", "label": "TERM"},
                   {"start": 13, "end": 20, "term": "morfema", "label": "TERM"}]},
        {"id": "r2", "doc_id": "d1", "text": "fonema", "terms": []},
    ]
    data.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return tmp_path, terms, data


def test_cli_prints_and_writes_report(files, capsys):
    root, terms, data = files
    output = root / "reports" / "r.json"
    assert evaluate.main([str(data), "--terms", str(terms), "--output", str(output)]) == 0
    out = capsys.readouterr().out
    assert "1 ta yozuv baholanmadi" in out
    assert "exact        1.0000     0.5000" in out
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["method"] == "dictionary_baseline"
    assert report["records"] == 1 and report["skipped_drafts"] == 1
    assert report["exact"]["precision"] == 1.0 and report["exact"]["recall"] == 0.5
    assert report["errors"]["counts"]["missed"] == 1
    [case] = report["errors"]["cases"]
    assert case["gold"]["surface"] == "morfema" and case["in_dictionary"] is False


def test_cli_include_drafts(files, capsys):
    _, terms, data = files
    assert evaluate.main([str(data), "--terms", str(terms), "--include-drafts", "--examples", "0"]) == 0
    out = capsys.readouterr().out
    assert "Yozuvlar: 2" in out and "false_positive=1" in out


def test_cli_warns_on_test_split(files, capsys):
    root, terms, data = files
    test_file = root / "test.jsonl"
    test_file.write_text(data.read_text(encoding="utf-8"), encoding="utf-8")
    assert evaluate.main([str(test_file), "--terms", str(terms)]) == 0
    assert "test to'plami baholanmoqda" in capsys.readouterr().out


def test_cli_no_reviewed_records(tmp_path, files, capsys):
    _, terms, _ = files
    data = tmp_path / "drafts.jsonl"
    data.write_text(json.dumps({"id": "r", "doc_id": "d", "text": "fonema", "terms": []}) + "\n", encoding="utf-8")
    assert evaluate.main([str(data), "--terms", str(terms)]) == 0
    assert "Baholash uchun yozuv yo'q" in capsys.readouterr().out


def test_cli_invalid_annotation(tmp_path, files, capsys):
    _, terms, _ = files
    data = tmp_path / "bad.jsonl"
    data.write_text('{"id": "r"}\n', encoding="utf-8")
    assert evaluate.main([str(data), "--terms", str(terms)]) == 1
    assert "Annotatsiyada xatolar" in capsys.readouterr().err
