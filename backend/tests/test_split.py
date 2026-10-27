from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.dataset import split as split_module
from app.dataset.annotation import AnnotatedRecord, AnnotatedSpan, validate_files
from app.dataset.split import (
    DEFAULT_RATIOS,
    SPLITS,
    TEST,
    TRAIN,
    VALIDATION,
    SplitError,
    assign_splits,
    build_splits,
    group_documents,
    load_manifest,
    manifest_to_dict,
    validate_ratios,
)


def rec(doc_id: str, number: int = 1, spans: int = 1, text: str | None = None, status="reviewed"):
    text = text or f"{doc_id} matni {number}: " + " ".join(["fonema"] * spans)
    words = []
    position = text.find("fonema")
    while position != -1 and len(words) < spans:
        words.append(AnnotatedSpan(position, position + 6, "fonema", "TERM"))
        position = text.find("fonema", position + 6)
    return AnnotatedRecord(f"{doc_id}-p{number:03d}", doc_id, text, tuple(words), "A1", status, None)


def docs(count: int, spans: int = 1) -> list[AnnotatedRecord]:
    return [rec(f"doc-{i:02d}", spans=spans) for i in range(count)]


# --- Nisbatlar ------------------------------------------------------------------


@pytest.mark.parametrize(
    "ratios",
    [(0.7, 0.2), (0.5, 0.5, 0.5), (-0.1, 0.6, 0.5), (0, 0.5, 0.5), (0.5, 0.5, 0), (float("nan"), 0.5, 0.5)],
)
def test_invalid_ratios(ratios):
    with pytest.raises(SplitError):
        validate_ratios(ratios)


def test_validation_ratio_may_be_zero():
    assert validate_ratios((0.8, 0, 0.2)) == (0.8, 0.0, 0.2)


# --- Guruhlash -------------------------------------------------------------------


def test_each_doc_is_own_group():
    records = [rec("b"), rec("a"), rec("a", 2)]
    groups = group_documents(records)
    assert [g.doc_ids for g in groups] == [("a",), ("b",)]
    assert [r.id for r in groups[0].records] == ["a-p001", "a-p002"]


def test_docs_with_duplicate_text_are_grouped():
    shared = "Fonema haqida umumiy matn."
    records = [
        rec("c", text=shared),
        rec("a"),
        rec("b", text="  FONEMA haqida\numumiy matn. "),  # registr va bo'shliq farqi
        rec("d"),
    ]
    groups = group_documents(records)
    assert [g.doc_ids for g in groups] == [("a",), ("b", "c"), ("d",)]


def test_duplicate_chain_merges_transitively():
    records = [rec("a", text="X matn."), rec("b", text="X matn."), rec("b", 2, text="Y matn."), rec("c", text="Y matn.")]
    [group] = group_documents(records)
    assert group.doc_ids == ("a", "b", "c")


def test_group_weight_counts_spans_with_minimum_one():
    [group] = group_documents([rec("a", spans=3), rec("a", 2, spans=2)])
    assert group.weight == 5
    [empty] = group_documents([rec("b", spans=0)])
    assert empty.weight == 1


# --- Taqsimlash ------------------------------------------------------------------


def test_every_doc_assigned_and_records_not_split_across_sets():
    records = [rec(f"d{i}", n) for i in range(20) for n in (1, 2)]
    assignments = assign_splits(group_documents(records), {})
    splits = build_splits(records, assignments)
    assert set(assignments) == {f"d{i}" for i in range(20)}
    doc_sets = {s: {r.doc_id for r in splits[s]} for s in SPLITS}
    assert not doc_sets[TRAIN] & doc_sets[VALIDATION]
    assert not doc_sets[TRAIN] & doc_sets[TEST]
    assert not doc_sets[VALIDATION] & doc_sets[TEST]
    assert sum(len(v) for v in splits.values()) == len(records)


def test_proportions_follow_ratios():
    assignments = assign_splits(group_documents(docs(100)), {}, DEFAULT_RATIOS)
    counts = {s: list(assignments.values()).count(s) for s in SPLITS}
    assert counts == {TRAIN: 70, VALIDATION: 15, TEST: 15}


def test_balancing_uses_span_weight():
    records = [rec("big", spans=10)] + [rec(f"s{i}", spans=1) for i in range(10)]
    assignments = assign_splits(group_documents(records), {}, (0.5, 0, 0.5))
    weight = {s: 0 for s in SPLITS}
    for record in records:
        weight[assignments[record.doc_id]] += len(record.terms)
    assert weight == {TRAIN: 10, VALIDATION: 0, TEST: 10}


def test_deterministic_and_independent_of_input_order():
    records = docs(30)
    first = assign_splits(group_documents(records), {})
    second = assign_splits(group_documents(list(reversed(records))), {})
    assert first == second


def test_few_docs_fill_train_first():
    assert assign_splits(group_documents(docs(1)), {}) == {"doc-00": TRAIN}


def test_frozen_assignments_are_kept_when_dataset_grows():
    initial = docs(20)
    frozen = assign_splits(group_documents(initial), {})
    # Yangi manbalar tartibda oldin turadi: qayta taqsimlansa,
    # eski manbalarning to'plami o'zgarardi (20 ta manba 14/3/3 ga aniq bo'linadi,
    # shuning uchun 5 ta yangi manba olinadi: taqsimot naqshi siljiydi).
    grown = initial + [rec(f"aaa-{i:02d}") for i in range(5)]
    updated = assign_splits(group_documents(grown), frozen)
    assert {d: updated[d] for d in frozen} == frozen
    assert all(f"aaa-{i:02d}" in updated for i in range(5))
    fresh = assign_splits(group_documents(grown), {})
    assert any(fresh[d] != frozen[d] for d in frozen), "test sharti: qayta taqsimlash farq qilishi kerak"


def test_frozen_docs_absent_from_dataset_are_kept():
    updated = assign_splits(group_documents([rec("a")]), {"old": TEST})
    assert updated["old"] == TEST


def test_new_doc_with_duplicate_text_inherits_frozen_split():
    records = [rec("a", text="Umumiy matn."), rec("b", text="Umumiy matn.")]
    updated = assign_splits(group_documents(records), {"a": TEST})
    assert updated == {"a": TEST, "b": TEST}


def test_duplicate_text_across_frozen_splits_is_error():
    records = [rec("a", text="Umumiy matn."), rec("b", text="Umumiy matn.")]
    with pytest.raises(SplitError, match="turli to'plamlarda"):
        assign_splits(group_documents(records), {"a": TRAIN, "b": TEST})


def test_frozen_weight_counts_towards_balance():
    frozen = {f"t{i}": TRAIN for i in range(7)}
    records = [rec(d) for d in frozen] + [rec(f"n{i}") for i in range(3)]
    updated = assign_splits(group_documents(records), frozen, (0.7, 0.15, 0.15))
    new = [updated[f"n{i}"] for i in range(3)]
    assert TRAIN not in new[:2]  # train allaqachon to'lgan


# --- Manifest --------------------------------------------------------------------


def test_manifest_roundtrip(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest_to_dict({"b": TEST, "a": TRAIN}, (0.8, 0.1, 0.1))), encoding="utf-8")
    assignments, ratios = load_manifest(path)
    assert assignments == {"a": TRAIN, "b": TEST}
    assert ratios == (0.8, 0.1, 0.1)


def test_missing_manifest_is_empty(tmp_path):
    assert load_manifest(tmp_path / "yoq.json") == ({}, None)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("{", "JSON xatosi"),
        ("[]", "'assignments'"),
        ('{"version": 1, "assignments": []}', "'assignments'"),
        ('{"version": 2, "assignments": {}}', "versiyasi"),
        ('{"version": 1, "assignments": {"a": "dev"}}', "noto'g'ri to'plam"),
        ('{"version": 1, "assignments": {}}', "'ratios'"),
        ('{"version": 1, "assignments": {}, "ratios": {"train": 1}}', "'ratios'"),
        ('{"version": 1, "assignments": {}, "ratios": {"train": "x", "validation": 0, "test": 0}}', "'ratios'"),
    ],
)
def test_invalid_manifest(tmp_path, content, expected):
    path = tmp_path / "manifest.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SplitError) as exc_info:
        load_manifest(path)
    assert any(expected in p for p in exc_info.value.problems), exc_info.value.problems


# --- CLI ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path):
    def write_dataset(doc_ids, *, draft_ids=()):
        sources = [{"id": d, "title": d, "rights": "test"} for d in [*doc_ids, *draft_ids]]
        (tmp_path / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
        lines = []
        for doc_id in doc_ids:
            lines.append({"id": f"{doc_id}-p001", "doc_id": doc_id, "text": f"{doc_id}: fonema.",
                          "terms": [{"start": len(doc_id) + 2, "end": len(doc_id) + 8, "term": "fonema", "label": "TERM"}],
                          "status": "reviewed"})
        for doc_id in draft_ids:
            lines.append({"id": f"{doc_id}-p001", "doc_id": doc_id, "text": f"{doc_id} qoralama.", "terms": []})
        (tmp_path / "data.jsonl").write_text(
            "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in lines), encoding="utf-8"
        )

    def run(*extra):
        return split_module.main(
            [str(tmp_path / "data.jsonl"), "--sources", str(tmp_path / "sources.json"),
             "--manifest", str(tmp_path / "splits" / "manifest.json"),
             "--output-dir", str(tmp_path / "processed"), *extra]
        )

    return tmp_path, write_dataset, run


def read_manifest(root: Path) -> dict:
    return json.loads((root / "splits" / "manifest.json").read_text(encoding="utf-8"))


def test_cli_writes_manifest_and_valid_split_files(workspace, capsys):
    root, write_dataset, run = workspace
    write_dataset([f"doc-{i:02d}" for i in range(20)])
    assert run() == 0
    manifest = read_manifest(root)
    assert len(manifest["assignments"]) == 20
    assert manifest["ratios"] == dict(zip(SPLITS, DEFAULT_RATIOS))

    seen = set()
    for split in SPLITS:
        path = root / "processed" / f"{split}.jsonl"
        report = validate_files([path])
        assert report.ok, report.errors
        ids = {r.doc_id for r in report.records}
        assert all(manifest["assignments"][d] == split for d in ids)
        assert not ids & seen
        seen |= ids
    assert len(seen) == 20


def test_cli_rerun_keeps_frozen_test_set(workspace):
    root, write_dataset, run = workspace
    write_dataset([f"doc-{i:02d}" for i in range(20)])
    assert run() == 0
    before = read_manifest(root)["assignments"]
    write_dataset([f"doc-{i:02d}" for i in range(40)])
    assert run("--ratios", "0.5", "0.25", "0.25") == 0
    after = read_manifest(root)["assignments"]
    assert {d: after[d] for d in before} == before
    assert read_manifest(root)["ratios"] == {TRAIN: 0.5, VALIDATION: 0.25, TEST: 0.25}


def test_cli_skips_drafts_by_default(workspace, capsys):
    root, write_dataset, run = workspace
    write_dataset(["a", "b"], draft_ids=["c"])
    assert run() == 0
    assert "1 ta yozuv kiritilmadi" in capsys.readouterr().out
    assert set(read_manifest(root)["assignments"]) == {"a", "b"}
    assert run("--include-drafts") == 0
    assert set(read_manifest(root)["assignments"]) == {"a", "b", "c"}


def test_cli_dry_run_writes_nothing(workspace, capsys):
    root, write_dataset, run = workspace
    write_dataset(["a", "b", "c"])
    assert run("--dry-run") == 0
    assert "hech narsa yozilmadi" in capsys.readouterr().out
    assert not (root / "splits").exists() and not (root / "processed").exists()


def test_cli_rejects_invalid_annotation(workspace, capsys):
    root, write_dataset, run = workspace
    write_dataset(["a"])
    (root / "data.jsonl").write_text('{"id": "x"}\n', encoding="utf-8")
    assert run() == 1
    assert "avval tuzating" in capsys.readouterr().err
    assert not (root / "splits").exists()


def test_cli_rejects_bad_ratios(workspace, capsys):
    _, write_dataset, run = workspace
    write_dataset(["a"])
    assert run("--ratios", "0.5", "0.5", "0.5") == 1
    assert "yig'indisi" in capsys.readouterr().err


def test_cli_no_records(workspace, capsys):
    root, write_dataset, run = workspace
    write_dataset([], draft_ids=["a"])
    assert run() == 0
    assert "Ajratish uchun yozuv yo'q" in capsys.readouterr().out
    assert not (root / "splits").exists()
