"""Oʻzbekcha Vikipediya maqolalarini dataset uchun yuklab olish.

Har bir maqola uchun:
- toza matn ``data/raw/<doc_id>.txt`` ga yoziladi (bo'limlar sarlavhalari,
  "Adabiyotlar"/"Manbalar" kabi bo'limlar olib tashlanadi, paragraflar bo'sh
  qator bilan ajratiladi — ``app.dataset.inline`` formatiga mos);
- manba ``data/sources.json`` ga qo'shiladi: sarlavha, aniq versiya (revid)
  havolasi va litsenziya (CC BY-SA 4.0, mualliflar — maqola tarixi).

Wikimedia API qoidalariga rioya qilinadi: so'rovlar ketma-ket, orasida
pauza bilan; 429 javobida ``Retry-After`` bo'yicha kutiladi.

Misol (repo ildizidan):
    PYTHONPATH=backend python -m app.dataset.fetch_wikipedia Fonetika Morfologiya
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

API_URL = "https://uz.wikipedia.org/w/api.php"
SITE_URL = "https://uz.wikipedia.org"
USER_AGENT = "UzTermAI-dataset/0.1 (MDI thesis research; https://github.com/Mirzokhidbek/graduatemdi)"
LICENSE = "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)"

# Matn bo'lmagan yoki dataset uchun keraksiz bo'limlar (shu sarlavhadan keyingi hammasi tashlanadi).
_STOP_SECTIONS = {
    "adabiyotlar",
    "adabiyot",
    "manbalar",
    "manba",
    "havolalar",
    "tashqi havolalar",
    "izohlar",
    "yana qarang",
    "qarang",
    "foydalanilgan adabiyotlar",
}
_HEADING = re.compile(r"^(=+)\s*(.*?)\s*\1\s*$")
_MIN_PARAGRAPH_CHARS = 40

Fetcher = Callable[[dict[str, str]], dict[str, Any]]


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class Article:
    title: str
    page_id: int
    revision_id: int
    timestamp: str
    text: str  # toza, paragraflari bo'sh qator bilan ajratilgan

    @property
    def doc_id(self) -> str:
        return f"uzwiki-{self.page_id}"

    @property
    def revision_url(self) -> str:
        return f"{SITE_URL}/w/index.php?oldid={self.revision_id}"

    @property
    def history_url(self) -> str:
        return f"{SITE_URL}/w/index.php?" + urllib.parse.urlencode({"title": self.title, "action": "history"})

    def to_source(self) -> dict[str, Any]:
        return {
            "id": self.doc_id,
            "title": f"Vikipediya: {self.title}",
            "author": f"Vikipediya mualliflari ({self.history_url})",
            "publication": "Oʻzbekcha Vikipediya",
            "year": int(self.timestamp[:4]),
            "url": self.revision_url,
            "rights": LICENSE,
            "notes": f"revid={self.revision_id}, versiya vaqti {self.timestamp}; matn tozalangan (sarlavhalar va adabiyotlar olib tashlangan)",
        }


def http_fetcher(delay: float = 3.0, max_retries: int = 4) -> Fetcher:
    """Wikimedia API'ga ketma-ket, pauza bilan so'rov yuboruvchi funksiya."""
    last_request = [0.0]

    def fetch(params: dict[str, str]) -> dict[str, Any]:
        url = API_URL + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
        for attempt in range(max_retries + 1):
            wait = last_request[0] + delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            last_request[0] = time.monotonic()
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 503) and attempt < max_retries:
                    retry_after = exc.headers.get("Retry-After", "")
                    time.sleep(int(retry_after) if retry_after.isdigit() else 30 * (attempt + 1))
                    continue
                raise FetchError(f"HTTP {exc.code}: {url}") from None
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < max_retries:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise FetchError(f"tarmoq xatosi: {exc}") from None
        raise FetchError(f"so'rov bajarilmadi: {url}")

    return fetch


def is_author_signature(line: str) -> bool:
    """Ensiklopediya maqolalari oxiridagi mualliflar imzosi: "Ism Familiya, Ism Familiya."."""
    words = line.rstrip(".").replace(",", " ").split()
    return 2 <= len(words) <= 10 and all(word[:1].isupper() for word in words)


def clean_extract(extract: str) -> str:
    """API ``explaintext`` natijasini paragraflarga ajratilgan toza matnga aylantiradi."""
    paragraphs: list[str] = []
    for line in unicodedata.normalize("NFC", extract).split("\n"):
        line = " ".join(line.split())
        heading = _HEADING.match(line)
        if heading:
            if heading.group(2).strip().lower() in _STOP_SECTIONS:
                break
            continue
        # Juda qisqa qatorlar (ro'yxat bandlari, rasm izohlari) olinmaydi.
        if len(line) >= _MIN_PARAGRAPH_CHARS and not is_author_signature(line):
            paragraphs.append(line)
    return "\n\n".join(paragraphs)


def fetch_article(title: str, fetch: Fetcher) -> Article | None:
    data = fetch(
        {
            "action": "query",
            "titles": title,
            "redirects": "1",
            "prop": "extracts|revisions",
            "explaintext": "1",
            "exsectionformat": "wiki",
            "rvprop": "ids|timestamp",
        }
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing") or "revisions" not in pages[0]:
        return None
    page = pages[0]
    revision = page["revisions"][0]
    return Article(
        title=page["title"],
        page_id=page["pageid"],
        revision_id=revision["revid"],
        timestamp=revision["timestamp"],
        text=clean_extract(page.get("extract", "")),
    )


def save_article(article: Article, raw_dir: Path, sources_path: Path) -> bool:
    """Matn va manbani saqlaydi. Manba avvaldan bo'lsa, hech narsa o'zgartirilmaydi (False)."""
    sources = json.loads(sources_path.read_text(encoding="utf-8")) if sources_path.exists() else []
    if any(source.get("id") == article.doc_id for source in sources):
        return False
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{article.doc_id}.txt").write_text(article.text + "\n", encoding="utf-8")
    sources.append(article.to_source())
    sources_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Oʻzbekcha Vikipediya maqolalarini yuklab olish")
    parser.add_argument("titles", nargs="+", help="maqola sarlavhalari")
    parser.add_argument("--raw-dir", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--sources", type=Path, default=REPO_ROOT / "data" / "sources.json")
    parser.add_argument("--delay", type=float, default=3.0, help="so'rovlar orasidagi pauza (soniya)")
    parser.add_argument("--min-chars", type=int, default=300, help="bundan qisqa matnli maqola olinmaydi")
    args = parser.parse_args(argv)

    fetch = http_fetcher(delay=args.delay)
    saved = 0
    for title in args.titles:
        try:
            article = fetch_article(title, fetch)
        except FetchError as exc:
            print(f"{title}: xato — {exc}", file=sys.stderr)
            continue
        if article is None:
            print(f"{title}: maqola topilmadi")
            continue
        if len(article.text) < args.min_chars:
            print(f"{article.title}: matn juda qisqa ({len(article.text)} belgi), olinmadi")
            continue
        if save_article(article, args.raw_dir, args.sources):
            saved += 1
            paragraphs = article.text.count("\n\n") + 1
            print(f"{article.title}: {article.doc_id}.txt ({paragraphs} paragraf, {len(article.text)} belgi, revid={article.revision_id})")
        else:
            print(f"{article.title}: {article.doc_id} avvaldan bor, o'tkazib yuborildi")
    print(f"\nSaqlandi: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
