from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.evaluation import judgments as judgments_module
from app.evaluation.judgments import (
    COLUMNS,
    JudgmentError,
    RankedCandidate,
    build_pool,
    cohen_kappa,
    find_example,
    judged_precision_at_k,
    load_judgments,
    load_ranking,
    method_name,
    write_template,
)


def ranked(*names):
    return [RankedCandidate(name, name, 10 - i) for i, name in enumerate(names)]


def write_ranking(path: Path, names) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["rank", "candidate", "score", "frequency", "top_surface"])
        writer.writeheader()
        for i, name in enumerate(names, start=1):
            writer.writerow({"rank": i, "candidate": name, "score": 1 / i, "frequency": 10 - i, "top_surface": name})
    return path


def write_judgments(path: Path, rows) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["candidate", "judgment", "notes"])
        writer.writerows(rows)
    return path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


# --- pool ----------------------------------------------------------------------------


def test_pool_unions_top_k_and_hides_order():
    pool = build_pool([ranked("c", "a", "x"), ranked("b", "a", "y")], k=2)
    assert [item.candidate for item in pool] == ["a", "b", "c"]


def test_pool_invalid_k():
    with pytest.raises(ValueError):
        build_pool([ranked("a")], k=0)


def test_load_ranking_sorts_by_rank(tmp_path):
    path = write_ranking(tmp_path / "candidates-cvalue.csv", ["a", "b"])
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    with path.open("w", encoding="utf-8", newline="") as handle:  # tartibni buzamiz
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(reversed(rows))
    assert [r.candidate for r in load_ranking(path)] == ["a", "b"]
    assert method_name(path) == "cvalue"


def test_load_ranking_missing_columns(tmp_path):
    path = tmp_path / "r.csv"
    path.write_text("candidate\nfonema\n", encoding="utf-8")
    with pytest.raises(JudgmentError, match="ustunlar"):
        load_ranking(path)


# --- misol kontekst ------------------------------------------------------------------


def test_find_example_requires_whole_word():
    documents = {"b": "Allofonlari bor.", "a": "Bu fonemaning allofonlar deyiladi."}
    assert find_example("allofonlar", documents) == "Bu fonemaning ⟦allofonlar⟧ deyiladi."
    assert find_example("fonema", {"d": "fonemalar, polifonema"}) == ""
    assert find_example("yo'q", {"d": "matn"}) == ""


# --- baholar fayli ------------------------------------------------------------------------


def test_load_judgments(tmp_path):
    path = write_judgments(tmp_path / "A1.csv", [["fonema", "1", ""], ["til", " 0 ", "umumiy"], ["shakl", "?", ""], ["gap", "", ""]])
    assert load_judgments(path) == {"fonema": "1", "til": "0", "shakl": "?", "gap": ""}


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([["fonema", "ha", ""]], "noto'g'ri baho"),
        ([["fonema", "1", ""], ["fonema", "0", ""]], "takrorlangan"),
        ([["", "1", ""]], "'candidate' bo'sh"),
    ],
)
def test_invalid_judgments(tmp_path, rows, expected):
    path = write_judgments(tmp_path / "A1.csv", rows)
    with pytest.raises(JudgmentError) as exc_info:
        load_judgments(path)
    assert any(expected in p for p in exc_info.value.problems), exc_info.value.problems


def test_invalid_judgment_reports_line_number(tmp_path):
    path = write_judgments(tmp_path / "A1.csv", [["fonema", "1", ""], ["til", "x", ""]])
    with pytest.raises(JudgmentError) as exc_info:
        load_judgments(path)
    assert exc_info.value.problems == [f"{path}:3: 'til' uchun noto'g'ri baho 'x' (1, 0, ? yoki bo'sh)"]


def test_judgments_missing_file_and_columns(tmp_path):
    with pytest.raises(JudgmentError, match="topilmadi"):
        load_judgments(tmp_path / "yoq.csv")
    path = tmp_path / "bad.csv"
    path.write_text("name\nfonema\n", encoding="utf-8")
    with pytest.raises(JudgmentError, match="ustunlar"):
        load_judgments(path)


# --- shablon ----------------------------------------------------------------------------------


def test_write_template_new_file(tmp_path):
    path = tmp_path / "judgments" / "A1.csv"
    added, kept = write_template(path, ranked("tovush", "fonema"), {"d": "Fonema va tovush."})
    assert (added, kept) == (2, 0)
    rows = read_rows(path)
    assert [r["candidate"] for r in rows] == ["fonema", "tovush"]
    assert list(rows[0]) == list(COLUMNS)
    assert rows[0]["judgment"] == "" and rows[1]["example"] == "Fonema va ⟦tovush⟧."


def test_write_template_preserves_existing_judgments(tmp_path):
    path = tmp_path / "A1.csv"
    write_template(path, ranked("fonema", "til"), {})
    rows = read_rows(path)
    rows[0]["judgment"], rows[0]["notes"] = "1", "aniq termin"
    rows[1]["judgment"] = "0"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS))
        writer.writeheader()
        writer.writerows(rows)

    # Yangi pool: "til" chiqib ketgan, "morfema" qo'shilgan.
    added, kept = write_template(path, ranked("fonema", "morfema"), {})
    assert (added, kept) == (1, 2)
    assert load_judgments(path) == {"fonema": "1", "morfema": "", "til": "0"}
    assert read_rows(path)[0]["notes"] == "aniq termin"


def test_write_template_refuses_broken_existing_file(tmp_path):
    path = write_judgments(tmp_path / "A1.csv", [["fonema", "ha", ""]])
    with pytest.raises(JudgmentError):
        write_template(path, ranked("fonema"), {})
    assert read_rows(path) == [{"candidate": "fonema", "judgment": "ha", "notes": ""}]  # fayl o'zgarmagan


# --- Precision@K ---------------------------------------------------------------------------


def test_judged_precision_at_k():
    values = {"a": "1", "b": "0", "c": "?", "d": "1"}
    result = judged_precision_at_k(["a", "b", "c", "d", "e"], values, 5)
    assert (result.relevant, result.unsure, result.unjudged, result.considered) == (2, 1, 1, 5)
    assert result.strict == pytest.approx(2 / 5)
    assert result.lenient == pytest.approx(3 / 5)
    assert judged_precision_at_k(["a"], values, 10).considered == 1
    assert judged_precision_at_k([], values, 10).strict is None
    with pytest.raises(ValueError):
        judged_precision_at_k(["a"], values, 0)


# --- kappa ----------------------------------------------------------------------------------


def test_cohen_kappa_hand_computed():
    # 10 ta umumiy, 8 tasida mos; ikkalasi ham 5 tadan "1" -> p_e = 0.5, kappa = 0.6
    first = dict(zip("abcdefghij", "1111100000"))
    second = dict(zip("abcdefghij", "1111000001"))
    agreement = cohen_kappa(first, second)
    assert (agreement.common, agreement.agreed) == (10, 8)
    assert agreement.kappa == pytest.approx(0.6)


def test_cohen_kappa_ignores_unsure_and_unjudged():
    first = {"a": "1", "b": "0", "c": "?", "d": ""}
    second = {"a": "1", "b": "0", "c": "1", "d": "0", "e": "1"}
    agreement = cohen_kappa(first, second)
    assert (agreement.common, agreement.agreed, agreement.kappa) == (2, 2, pytest.approx(1.0))


def test_cohen_kappa_undefined_cases():
    assert cohen_kappa({}, {}).kappa is None
    assert cohen_kappa({"a": "1", "b": "1"}, {"a": "1", "b": "1"}).kappa is None  # p_e = 1


# --- CLI ------------------------------------------------------------------------------------------


@pytest.fixture
def setup(tmp_path):
    corpus = tmp_path / "doc.txt"
    corpus.write_text("Fonema, til va tovush. Shakl.", encoding="utf-8")
    first = write_ranking(tmp_path / "candidates-cvalue.csv", ["til", "fonema", "tovush"])
    second = write_ranking(tmp_path / "candidates-tfidf.csv", ["fonema", "shakl", "til"])
    return tmp_path, corpus, first, second


def test_cli_template_and_score(setup, capsys):
    tmp_path, corpus, first, second = setup
    judgments = tmp_path / "A1.csv"
    assert judgments_module.main([
        "template", "--rankings", str(first), str(second), "--k", "2",
        "--corpus", str(corpus), "--output", str(judgments),
    ]) == 0
    assert "3 nomzod pool'da" in capsys.readouterr().out
    assert [r["candidate"] for r in read_rows(judgments)] == ["fonema", "shakl", "til"]

    write_judgments(judgments, [["fonema", "1", ""], ["shakl", "?", ""], ["til", "0", ""]])
    second_judge = write_judgments(tmp_path / "A2.csv", [["fonema", "1", ""], ["shakl", "1", ""], ["til", "1", ""]])
    assert judgments_module.main([
        "score", "--rankings", str(first), str(second),
        "--judgments", str(judgments), str(second_judge), "--k", "2", "3",
    ]) == 0
    out = capsys.readouterr().out
    assert "cvalue        2    0.500    0.500   1 / 0 / 0" in out
    assert "tfidf         2    0.500    1.000   1 / 1 / 0" in out
    # cvalue top-3 dagi "tovush" baholanmagan -> pastki chegara
    assert "cvalue        3   ≥0.333   ≥0.333   1 / 0 / 1" in out
    assert "Kelishuv A1 ↔ A2: umumiy 2, mos 1" in out


def test_cli_score_invalid_judgments(setup, capsys):
    tmp_path, _, first, _ = setup
    bad = write_judgments(tmp_path / "bad.csv", [["fonema", "yes", ""]])
    assert judgments_module.main(["score", "--rankings", str(first), "--judgments", str(bad)]) == 1
    assert "noto'g'ri baho" in capsys.readouterr().err
