from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.annotation.agreement import compare, promote
from app.core.config import Settings
from app.main import create_app
from tests.conftest import make_entry

TEXT = "Fonemalar va undosh tovush.\n\nBu paragrafda termin yo'q."


@pytest.fixture
def data_dir(tmp_path):
    data = tmp_path / "data"
    (data / "raw").mkdir(parents=True)
    (data / "raw" / "doc-1.txt").write_text(TEXT, encoding="utf-8")
    (data / "sources.json").write_text(
        json.dumps([{"id": "doc-1", "title": "Sinov hujjati", "rights": "test"}]), encoding="utf-8"
    )
    (data / "judgments").mkdir()
    (data / "judgments" / "candidates-A1.csv").write_text(
        "﻿candidate,judgment,notes,frequency,example\nfonema,,,3,…⟦fonema⟧…\nusul,,,2,…⟦usul⟧…\n",
        encoding="utf-8",
    )
    return data


@pytest.fixture
def client(tmp_path, data_dir):
    terms = tmp_path / "terms.json"
    terms.write_text(json.dumps([make_entry("t1", "fonema"), make_entry("t2", "tovush")]), encoding="utf-8")
    return TestClient(create_app(Settings(terms_path=terms, max_text_chars=1000, data_dir=data_dir)))


def test_document_list_and_suggestions(client):
    docs = client.get("/api/annotate/documents", params={"annotator": "A1"}).json()
    assert docs == [{"doc_id": "doc-1", "title": "Sinov hujjati", "paragraphs": 2, "annotated": 0, "reviewed": 0}]

    doc = client.get("/api/annotate/documents/doc-1", params={"annotator": "A1"}).json()
    first = doc["paragraphs"][0]
    assert first["id"] == "doc-1-p001"
    assert first["saved"] is None
    assert [(s["start"], s["end"], s["term"], s["source"]) for s in first["suggestions"]] == [
        (0, 9, "fonema", "dictionary"),
        (20, 26, "tovush", "dictionary"),
    ]


def test_save_validates_and_writes_jsonl(client, data_dir):
    url = "/api/annotate/documents/doc-1/paragraphs/doc-1-p001"
    bad = client.put(url, params={"annotator": "A1"}, json={"terms": [{"start": 0, "end": 5, "term": "fonema"}]})
    assert bad.status_code == 400
    assert "so'z o'rtasida tugaydi" in bad.json()["detail"]
    assert not (data_dir / "annotations" / "A1" / "doc-1.jsonl").exists()

    good = client.put(
        url,
        params={"annotator": "A1"},
        json={"terms": [{"start": 13, "end": 26, "term": "undosh tovush"}, {"start": 0, "end": 9, "term": "fonema"}], "status": "reviewed"},
    )
    assert good.status_code == 200
    assert [t["surface"] for t in good.json()["terms"]] == ["Fonemalar", "undosh tovush"]

    empty = client.put(
        "/api/annotate/documents/doc-1/paragraphs/doc-1-p002", params={"annotator": "A1"}, json={"terms": []}
    )
    assert empty.status_code == 200

    lines = (data_dir / "annotations" / "A1" / "doc-1.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["id"] for line in lines] == ["doc-1-p001", "doc-1-p002"]
    assert client.get("/api/annotate/documents", params={"annotator": "A1"}).json()[0]["annotated"] == 2
    # boshqa annotator birinchisining belgilarini ko'rmaydi
    other = client.get("/api/annotate/documents/doc-1", params={"annotator": "A2"}).json()
    assert other["paragraphs"][0]["saved"] is None


def test_overlapping_spans_are_refused(client):
    response = client.put(
        "/api/annotate/documents/doc-1/paragraphs/doc-1-p001",
        params={"annotator": "A1"},
        json={"terms": [{"start": 13, "end": 26, "term": "undosh tovush"}, {"start": 20, "end": 26, "term": "tovush"}]},
    )
    assert response.status_code == 400
    assert "ustma-ust" in response.json()["detail"]


@pytest.mark.parametrize("annotator", ["../etc", "", "1abc", "a" * 17, "A 1"])
def test_unsafe_annotator_codes_are_refused(client, annotator):
    response = client.get("/api/annotate/documents/doc-1", params={"annotator": annotator})
    assert response.status_code == 400


def test_unknown_document_and_paragraph(client):
    assert client.get("/api/annotate/documents/..%2Fsecret", params={"annotator": "A1"}).status_code == 404
    assert client.get("/api/annotate/documents/nope", params={"annotator": "A1"}).status_code == 404
    missing = client.put(
        "/api/annotate/documents/doc-1/paragraphs/doc-1-p099", params={"annotator": "A1"}, json={"terms": []}
    )
    assert missing.status_code == 404


def test_saving_can_be_turned_off(tmp_path, data_dir):
    terms = tmp_path / "terms.json"
    terms.write_text(json.dumps([make_entry("t1", "fonema")]), encoding="utf-8")
    client = TestClient(
        create_app(Settings(terms_path=terms, max_text_chars=1000, data_dir=data_dir, annotation_enabled=False))
    )
    response = client.put(
        "/api/annotate/documents/doc-1/paragraphs/doc-1-p001", params={"annotator": "A1"}, json={"terms": []}
    )
    assert response.status_code == 403


def test_ai_annotation_is_offered_as_suggestion(client, data_dir):
    ai_dir = data_dir / "annotations" / "claude"
    ai_dir.mkdir(parents=True)
    record = {"id": "doc-1-p001", "doc_id": "doc-1", "text": "Fonemalar va undosh tovush.", "status": "draft",
              "terms": [{"start": 13, "end": 26, "term": "undosh tovush", "label": "TERM"}]}
    (ai_dir / "doc-1.jsonl").write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    doc = client.get("/api/annotate/documents/doc-1", params={"annotator": "A1"}).json()
    assert (13, 26, "undosh tovush", "ai") in [
        (s["start"], s["end"], s["term"], s["source"]) for s in doc["paragraphs"][0]["suggestions"]
    ]


def test_judgments_are_saved_per_annotator(client, data_dir):
    rows = client.get("/api/judgments/A2").json()
    assert [r["candidate"] for r in rows] == ["fonema", "usul"]
    saved = client.put("/api/judgments/A2", json={"candidate": "fonema", "judgment": "1", "notes": "aniq"})
    assert saved.status_code == 200
    assert client.put("/api/judgments/A2", json={"candidate": "fonema", "judgment": "x"}).status_code == 422
    assert client.put("/api/judgments/A2", json={"candidate": "yo'q", "judgment": "1"}).status_code == 404
    content = (data_dir / "judgments" / "candidates-A2.csv").read_text(encoding="utf-8-sig")
    assert "fonema,1,aniq,3" in content
    # A1 shabloni o'zgarmagan
    assert "fonema,,," in (data_dir / "judgments" / "candidates-A1.csv").read_text(encoding="utf-8-sig")


def test_agreement_and_promote(client, data_dir):
    url = "/api/annotate/documents/doc-1/paragraphs/doc-1-p001"
    client.put(url, params={"annotator": "A1"}, json={
        "terms": [{"start": 0, "end": 9, "term": "fonema"}, {"start": 13, "end": 26, "term": "undosh tovush"}],
        "status": "reviewed"})
    client.put(url, params={"annotator": "A2"}, json={"terms": [{"start": 0, "end": 9, "term": "fonema"}]})

    report = compare(data_dir / "annotations", "A1", "A2")
    assert report.paragraphs == 1
    assert report.exact.f1 == pytest.approx(2 / 3)
    assert report.same_term == 1
    assert report.examples == [{"id": "doc-1-p001", "surface": "undosh tovush", "only": "A1"}]

    written = promote(data_dir / "annotations", data_dir / "annotated", data_dir / "sources.json", "A1")
    assert [p.name for p in written] == ["doc-1.jsonl"]
    with pytest.raises(FileExistsError):
        promote(data_dir / "annotations", data_dir / "annotated", data_dir / "sources.json", "A1")
    # A2 ning yozuvi draft: standart bo'yicha o'tmaydi
    assert promote(data_dir / "annotations", data_dir / "annotated2", data_dir / "sources.json", "A2") == []
