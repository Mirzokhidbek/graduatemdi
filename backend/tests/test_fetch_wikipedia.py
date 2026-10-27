from __future__ import annotations

import json
from pathlib import Path

from app.dataset.fetch_wikipedia import (
    LICENSE,
    clean_extract,
    fetch_article,
    is_author_signature,
    save_article,
)
from app.dataset.inline import split_paragraphs
from app.dataset.sources import load_sources, parse_sources

REPO_ROOT = Path(__file__).resolve().parents[2]

LONG = "Fonema til tovush qurilishining maʼno farqlovchi eng kichik birligidir."
LONG2 = "Morfema maʼnoga ega boʻlgan eng kichik til birligi hisoblanadi va soʻz tarkibida keladi."


def test_clean_extract_removes_headings_short_lines_and_tail_sections():
    extract = "\n".join(
        [
            LONG,
            "",
            "== Tarixi ==",
            f"  {LONG2}   ",
            "rasm izohi",
            "== Adabiyotlar ==",
            "Kitob nomi, Toshkent, 1990, juda uzun bibliografik yozuv shu yerda davom etadi.",
        ]
    )
    assert clean_extract(extract) == f"{LONG}\n\n{LONG2}"


def test_clean_extract_drops_author_signature():
    assert clean_extract(f"{LONG}\nAbduvahob Madvaliyev, Ibodulla Mirzayev.") == LONG


def test_clean_extract_output_matches_inline_paragraphs():
    text = clean_extract(f"{LONG}\n\n\n{LONG2}")
    assert [p.text for p in split_paragraphs(text)] == [LONG, LONG2]


def test_author_signature_detection():
    assert is_author_signature("Abduvahob Madvaliyev, Ibodulla Mirzayev.")
    assert not is_author_signature("Fonema til birligi.")
    assert not is_author_signature("Toshkent")  # bitta so'z
    assert not is_author_signature(LONG)


def fake_fetcher(response):
    calls = []

    def fetch(params):
        calls.append(params)
        return response

    fetch.calls = calls
    return fetch


PAGE = {
    "query": {
        "pages": [
            {
                "pageid": 600493,
                "title": "Fonema",
                "extract": f"{LONG}\n== Manbalar ==\nxyz",
                "revisions": [{"revid": 6136445, "timestamp": "2026-05-21T08:02:44Z"}],
            }
        ]
    }
}


def test_fetch_article_parses_response():
    fetch = fake_fetcher(PAGE)
    article = fetch_article("fonema", fetch)
    assert fetch.calls[0]["titles"] == "fonema" and fetch.calls[0]["redirects"] == "1"
    assert article.doc_id == "uzwiki-600493"
    assert article.text == LONG
    assert article.revision_url.endswith("oldid=6136445")


def test_fetch_article_missing():
    assert fetch_article("Yoq", fake_fetcher({"query": {"pages": [{"title": "Yoq", "missing": True}]}})) is None
    assert fetch_article("Yoq", fake_fetcher({})) is None


def test_source_entry_is_valid_and_records_revision_and_license():
    article = fetch_article("Fonema", fake_fetcher(PAGE))
    [source] = parse_sources([article.to_source()])
    assert source.id == "uzwiki-600493"
    assert source.rights == LICENSE
    assert source.year == 2026
    assert "oldid=6136445" in source.url
    assert "action=history" in source.author


def test_save_article_writes_text_and_source_once(tmp_path):
    article = fetch_article("Fonema", fake_fetcher(PAGE))
    sources = tmp_path / "sources.json"
    assert save_article(article, tmp_path / "raw", sources) is True
    assert (tmp_path / "raw" / "uzwiki-600493.txt").read_text(encoding="utf-8") == LONG + "\n"
    assert save_article(article, tmp_path / "raw", sources) is False
    assert len(load_sources(sources)) == 1


def test_save_article_keeps_existing_sources(tmp_path):
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps([{"id": "d1", "title": "Kitob", "rights": "CC BY"}]), encoding="utf-8")
    save_article(fetch_article("Fonema", fake_fetcher(PAGE)), tmp_path / "raw", sources)
    assert [s.id for s in load_sources(sources)] == ["d1", "uzwiki-600493"]


def test_project_raw_files_have_registered_sources():
    source_ids = {source.id for source in load_sources(REPO_ROOT / "data" / "sources.json")}
    for directory in ("raw", "inline"):
        for path in (REPO_ROOT / "data" / directory).glob("*.txt"):
            assert path.stem in source_ids, f"{path} uchun manba yo'q"
