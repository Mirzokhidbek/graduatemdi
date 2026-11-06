"""Ekvivalentlar manbalari: korpusdagi etimologik izohlar, Wikidata/Vikipediya va embedding modeli (3.3-bo'lim).

1. ``extract_etymons`` — ensiklopedik matndagi izohlar: *Fonema (yun. phonema — tovush)*,
   *Undosh (lotincha: consonans — undosh tovush)*. Natija: (oʻzbekcha termin, til, asl so'z).
2. ``fetch_langlinks`` — oʻzbekcha Vikipediya maqolasining ruscha va inglizcha
   maqolalari nomi (``langlinks`` API). **Internet talab qiladi**; bu loyihaning ishlab
   chiqish muhitida Vikipediya yopiq bo'lgani uchun Colab yoki lokal kompyuterda ishga
   tushiriladi. Natija avtomatik tasdiqlanmaydi: ``needs_review``.
3. ``sentence_encoder`` — LaBSE (``sentence-transformers``) asosidagi encoder; o'rnatilmagan
   bo'lsa ``None``.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Callable, Iterable, Mapping, Sequence

LANG_CODES = {
    "lotincha": "la", "lot.": "la", "lotinchada": "la", "yunoncha": "grc", "yun.": "grc",
    "qadimgi yunoncha": "grc", "inglizcha": "en", "ingl.": "en", "ruscha": "ru", "fransuzcha": "fr",
    "fr.": "fr", "nemischa": "de", "arabcha": "ar", "arab.": "ar", "forscha": "fa",
}
_ETYMON = re.compile(
    r"(?P<term>[^\W\d_]+(?:['ʻʼ][^\W\d_]+)*(?:\s+[^\W\d_]+(?:['ʻʼ][^\W\d_]+)*)?)\s*\(\s*"
    r"(?P<lang>qadimgi yunoncha|lotinchada|lotincha|yunoncha|inglizcha|ruscha|fransuzcha|nemischa|arabcha|forscha"
    r"|lot\.|yun\.|ingl\.|fr\.|arab\.)\s*:?\s*(?P<body>[^)]{1,120})\)",
    re.IGNORECASE,
)
_FOREIGN = re.compile(r"[„“\"«]?([^\s—–,;„“\"«»]+(?:[-‐][^\s—–,;]+)?)")


def extract_etymons(documents: Mapping[str, str]) -> list[dict]:
    found = []
    for doc_id, text in documents.items():
        for m in _ETYMON.finditer(text):
            body = m.group("body").strip()
            parts = re.split(r"(?:^|\s+)[—–-]\s+", body, maxsplit=1)
            foreign = parts[0].strip(" „“\"«»") or None
            gloss = parts[1].strip() if len(parts) > 1 else None
            found.append({
                "uz": m.group("term").split()[-1].lower(),  # qavsdan oldingi so'z: "Tilshunoslikda affiks (...)"
                "lang": LANG_CODES.get(m.group("lang").lower(), m.group("lang").lower()),
                "foreign": foreign,
                "gloss": gloss,
                "doc_id": doc_id,
            })
    return found


Fetcher = Callable[[str], dict]


USER_AGENT = "UzTerm-research/0.1 (https://github.com/Mirzokhidbek/graduatemdi)"


def _http_json(url: str, retries: int = 5) -> dict:
    """Vikipediya API: 429/503 da kutib qayta urinadi (Retry-After yoki eksponensial)."""
    import time
    import urllib.error

    for attempt in range(retries):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 — faqat Vikipediya API
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == retries - 1:
                raise
            wait = float(exc.headers.get("Retry-After") or 2 ** (attempt + 1))
            time.sleep(min(wait, 60))
    raise RuntimeError("unreachable")


def fetch_langlinks(
    titles: Iterable[str],
    langs: Sequence[str] = ("ru", "en"),
    fetch: Fetcher = _http_json,
    batch: int = 40,
    pause: float = 1.0,
) -> dict[str, dict[str, str]]:
    """Oʻzbekcha Vikipediya sarlavhasi -> {til: shu tildagi maqola nomi}."""
    titles = list(dict.fromkeys(titles))
    result: dict[str, dict[str, str]] = {}
    import time

    for i in range(0, len(titles), batch):
        chunk = titles[i : i + batch]
        # Har bir til alohida so'raladi (lllang): bitta maqolaga bitta havola, natija kesilmaydi.
        for lang in langs:
            if pause:
                time.sleep(pause)
            params = {
                "action": "query", "format": "json", "prop": "langlinks", "redirects": "1",
                "lllang": lang, "lllimit": "max", "titles": "|".join(chunk), "maxlag": "5",
            }
            data = fetch("https://uz.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params))
            query = data.get("query", {})
            back = {r["to"]: r["from"] for r in query.get("redirects", [])}
            back.update({n["to"]: n["from"] for n in query.get("normalized", [])})
            for page in query.get("pages", {}).values():
                title = back.get(page.get("title"), page.get("title"))
                for ll in page.get("langlinks", []):
                    if ll["lang"] == lang:
                        result.setdefault(title, {})[lang] = ll.get("*") or ll.get("title")
    return result


def sentence_encoder(model_name: str = "sentence-transformers/LaBSE"):
    """LaBSE encoder (normalizatsiyalangan vektorlar) yoki kutubxona/tarmoq bo'lmasa ``None``."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    model = SentenceTransformer(model_name)

    def encode(texts: Sequence[str]):
        return model.encode(list(texts), normalize_embeddings=True, batch_size=64).tolist()

    return encode
