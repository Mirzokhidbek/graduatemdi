from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.term_store import TermDatabaseError
from app.main import create_app
from tests.conftest import make_entry


@pytest.fixture
def terms_file(tmp_path):
    path = tmp_path / "terms.json"
    path.write_text(
        json.dumps(
            [
                make_entry("t1", "fonema", definition="Tovush birligi.", domain="fonetika"),
                make_entry("t2", "affiks", synonyms=["qoʻshimcha"], status="approved", source="Test manbasi"),
                make_entry("t3", "ot", domain="morfologiya"),
                make_entry("t4", "ot", domain="boshqa"),
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def client(terms_file):
    return TestClient(create_app(Settings(terms_path=terms_file, max_text_chars=50)))


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "terms_in_dictionary": 4, "max_text_chars": 50}


def test_terms_list(client):
    terms = client.get("/api/terms").json()
    assert [t["id"] for t in terms] == ["t1", "t2", "t3", "t4"]
    assert terms[1]["synonyms"] == ["qoʻshimcha"] and terms[1]["status"] == "approved"


def test_analyze(client):
    response = client.post("/api/analyze", json={"text": "Fonemalar va qoʻshimcha."})
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "dictionary_baseline"
    assert body["positions"] == "unicode_codepoints"
    assert body["text_length"] == 24
    first, second = body["matches"]
    assert (first["start"], first["end"], first["surface"], first["term"]) == (0, 9, "Fonemalar", "fonema")
    assert first["method"] == "dictionary_inflected" and first["confidence"] is None
    assert first["candidates"][0]["definition"] == "Tovush birligi."
    assert first["review_required"] is True
    assert second["candidates"][0]["match_type"] == "synonym"
    assert second["candidates"][0]["normalization"]["status"] == "approved"
    assert any("tekshirish kerak" in note for note in body["notes"])


def test_positions_are_codepoints_with_astral_characters(client):
    text = "😀 fonema"
    [match] = client.post("/api/analyze", json={"text": text}).json()["matches"]
    assert (match["start"], match["end"]) == (2, 8)
    assert text[match["start"] : match["end"]] == "fonema"


def test_ambiguous_note(client):
    body = client.post("/api/analyze", json={"text": "ot"}).json()
    [match] = body["matches"]
    assert match["ambiguous"] is True and match["term"] is None
    assert any("bir nechta" in note for note in body["notes"])


@pytest.mark.parametrize("text", ["", "   ", "Bugun havo yaxshi."])
def test_analyze_without_matches(client, text):
    body = client.post("/api/analyze", json={"text": text}).json()
    assert body["matches"] == []
    assert len(body["notes"]) == 1  # faqat lug'at usuli haqidagi izoh


def test_text_length_limit(client):
    assert client.post("/api/analyze", json={"text": "a" * 50}).status_code == 200
    response = client.post("/api/analyze", json={"text": "a" * 51})
    assert response.status_code == 413
    assert "51 belgi" in response.json()["detail"]


@pytest.mark.parametrize("payload", [{}, {"text": 5}, {"txt": "fonema"}, ["fonema"]])
def test_invalid_payload(client, payload):
    assert client.post("/api/analyze", json=payload).status_code == 422


def test_invalid_json_body(client):
    response = client.post("/api/analyze", content="{bad", headers={"content-type": "application/json"})
    assert response.status_code == 422


def test_broken_terms_database_prevents_startup(tmp_path):
    path = tmp_path / "terms.json"
    path.write_text('[{"id": "a"}]', encoding="utf-8")
    with pytest.raises(TermDatabaseError):
        create_app(Settings(terms_path=path, max_text_chars=10))


def test_unexpected_error_hides_internals(terms_file, monkeypatch):
    app = create_app(Settings(terms_path=terms_file, max_text_chars=50))

    def boom(text):
        raise RuntimeError("maxfiy ichki tafsilot")

    monkeypatch.setattr(app.state.matcher, "find", boom)
    response = TestClient(app, raise_server_exceptions=False).post("/api/analyze", json={"text": "fonema"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Serverda ichki xato yuz berdi."}
    assert "maxfiy" not in response.text


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("UZTERM_TERMS_PATH", str(tmp_path / "x.json"))
    monkeypatch.setenv("UZTERM_MAX_TEXT_CHARS", "123")
    settings = Settings.from_env()
    assert settings.terms_path == tmp_path / "x.json" and settings.max_text_chars == 123
    monkeypatch.setenv("UZTERM_TERMS_PATH", "data/terms.json")
    assert Settings.from_env().terms_path.is_absolute()


@pytest.mark.parametrize("value", ["abc", "0", "-5"])
def test_settings_invalid_limit(monkeypatch, value):
    monkeypatch.setenv("UZTERM_MAX_TEXT_CHARS", value)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_check_terms(client):
    body = client.post("/api/check-terms", json={"terms": ["Fonemalar", "фонема", "fonema"]}).json()
    first, cyrillic, clean = body["results"]
    assert first["suggestion"] == "fonema" and first["severity"] == "warning"
    assert {f["rule"] for f in first["findings"]} >= {"lowercase", "dictionary_form"}
    assert cyrillic["severity"] == "error" and cyrillic["suggestion"] == "fonema"
    assert clean["severity"] in ("ok", "info") and clean["suggestion"] is None
    assert "ISO 704" in body["note"]


def test_check_terms_validation(client):
    assert client.post("/api/check-terms", json={"terms": []}).status_code == 422
    assert client.post("/api/check-terms", json={"terms": ["a" * 201]}).status_code == 413



def test_thesaurus_endpoint(terms_file, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    client = TestClient(create_app(Settings(terms_path=terms_file, max_text_chars=50, data_dir=data_dir)))
    assert client.get("/api/thesaurus").status_code == 404
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "thesaurus.json").write_text(
        json.dumps({"concepts": [], "relations": [], "related": [], "summary": {}}), encoding="utf-8"
    )
    assert client.get("/api/thesaurus").json()["concepts"] == []
