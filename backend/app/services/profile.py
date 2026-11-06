"""Termin profili: bitta termin haqida barcha modullar natijasi bir joyda.

- **lug'at** — bazadagi yozuv (taʼrif, holat, variant va sinonimlar);
- **meʼyor tekshiruvi** — ISO 704 va imlo qoidalari (``app.norms.checker``);
- **tezaurus** — jins, turlar va assotsiativ terminlar (``reports/thesaurus.json``);
- **ekvivalentlar** — ruscha/inglizcha muqobillar va etimologiya
  (``data/multilingual/*.csv``; manbasi va tekshirilganligi bilan).

Fayllar bo'lmasa, tegishli bo'lim bo'sh qaytadi — profil baribir ishlaydi.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.database.term_store import TermEntry
from app.nlp.normalize import normalize_form

EQUIVALENT_SOURCES = (
    # (fayl, manba nomi, tekshirilganmi)
    ("wikipedia-langlinks.csv", "Vikipediya (tillararo havolalar)", False),
    ("equivalents-silver.csv", "Claude tuzgan ro'yxat (kumush)", False),
)


def _key(text: str) -> str:
    return normalize_form(text)


class ProfileBuilder:
    def __init__(self, entries: list[TermEntry], checker, data_dir: Path, reports_dir: Path) -> None:
        self.checker = checker
        self.by_form: dict[str, TermEntry] = {}
        for entry in entries:
            for form in (entry.term, *entry.variants, *entry.synonyms):
                self.by_form.setdefault(_key(form), entry)
        self.concepts: dict[str, dict] = {}
        self.related: dict[str, list[dict]] = {}
        path = reports_dir / "thesaurus.json"
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.concepts = {_key(c["label"]): c for c in data.get("concepts", [])}
            for item in data.get("related", []):
                self.related.setdefault(_key(item["a"]), []).append({"term": item["b"], "pmi": item["pmi"]})
                self.related.setdefault(_key(item["b"]), []).append({"term": item["a"], "pmi": item["pmi"]})
        self.equivalents: dict[str, list[dict]] = {}
        multilingual = data_dir / "multilingual"
        for name, source, verified in EQUIVALENT_SOURCES:
            path = multilingual / name
            if not path.is_file():
                continue
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    for lang in ("ru", "en"):
                        value = (row.get(lang) or "").strip()
                        if value:
                            self._add_equivalent(row["uz"], lang, value, source, verified)
        path = multilingual / "etymons.csv"
        if path.is_file():
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if row.get("foreign"):
                        self._add_equivalent(row["uz"], row["lang"], row["foreign"], "korpusdagi etimologik izoh", False,
                                             gloss=row.get("gloss") or None)

    def _add_equivalent(self, uz: str, lang: str, value: str, source: str, verified: bool, gloss=None) -> None:
        items = self.equivalents.setdefault(_key(uz), [])
        if any(i["lang"] == lang and _key(i["value"]) == _key(value) for i in items):
            return
        items.append({"lang": lang, "value": value, "source": source, "verified": verified, "gloss": gloss})

    def profile(self, term: str) -> dict[str, Any]:
        key = _key(term)
        entry = self.by_form.get(key)
        concept = self.concepts.get(key) or (self.concepts.get(_key(entry.term)) if entry else None)
        lookup = [key] + ([_key(entry.term)] if entry and _key(entry.term) != key else [])
        equivalents = [e for k in lookup for e in self.equivalents.get(k, [])]
        return {
            "term": term,
            "dictionary": None if entry is None else {
                "id": entry.id,
                "term": entry.term,
                "definition": entry.definition,
                "status": entry.status,
                "source": entry.source,
                "preferred_form": entry.preferred_form,
                "variants": list(entry.variants),
                "synonyms": list(entry.synonyms),
            },
            "check": self.checker.check(term).to_dict(),
            "thesaurus": {
                "broader": concept["broader"] if concept else [],
                "narrower": concept["narrower"] if concept else [],
                "related": [r["term"] for r in sorted(self.related.get(key, []), key=lambda r: -r["pmi"])][:8],
            },
            "equivalents": equivalents,
        }
