"""Sohaviy terminologik tezaurusni avtomatik shakllantirish (2.3-bo'lim).

Tezaurus — tushunchalar va ular orasidagi munosabatlar: tur–jins (``broader`` /
``narrower``, giponimiya), assotsiativ (``related``) va sinonimiya (``altLabel``).
Format — W3C SKOS (Simple Knowledge Organization System).

**Giponimiya (broader) uch manbadan olinadi:**

1. ``head`` — **bosh so'z ierarxiyasi.** Oʻzbek tilida aniqlovchi aniqlanmishdan oldin
   keladi, shuning uchun ko'p so'zli terminning oxirgi qismi uning jinsini bildiradi:
   *jarangli undosh tovush* ⊂ *undosh tovush* ⊂ *tovush*. Terminning eng uzun
   o'ng qismi (suffiksi) lug'atda termin bo'lsa, u ``broader`` deb olinadi.
2. ``definition`` — **taʼrif tahlili.** Ensiklopedik taʼrif "A — ... X" ko'rinishida;
   X — jins (*genus proximum*). X taʼrifning birinchi bo'lagidagi (``;`` yoki
   ``.`` gacha) oxirgi ot birikmasi:
   - *Fonetika — tilshunoslikning ... bo'limi* → *bo'lim*;
   - *Koʻmakchi — yordamchi soʻzlarning bir turi* → *yordamchi soʻz*;
   - *Ot — mustaqil soʻz turkumlaridan biri* → *mustaqil soʻz turkumi*.
3. ``pattern`` — **leksik-sintaktik qoliplar** (Hearst, 1992, oʻzbek tiliga moslama):
   - "A, B va C **kabi** X(lar)";
   - "X(lar) [N] **turga / xilga / guruhga boʻlinadi**: A, B va C";
   - "X**ning turlari**: A, B".

Har bir munosabat manbasi va matndagi dalil bilan saqlanadi. Bir nechta manba
tasdiqlagan munosabat ishonchliroq.

**Assotsiativ munosabat (related)** — bir paragrafda birga kelish bo'yicha PMI
(pointwise mutual information): PMI(a, b) = log₂ (p(a, b) / (p(a) · p(b))),
kamida ``min_cooc`` marta birga kelgan va giponimiya bilan bog'lanmagan juftlar.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Iterable, Mapping, Sequence

from app.nlp.clean import canonical_apostrophes
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.normalize import normalize_form, normalize_text
from app.nlp.patterns import FUNC, MorphTagger, PatternExtractor
from app.nlp.tokenize import tokenize

SOURCES = ("head", "definition", "pattern")
_WORD = r"[^\W\d_]+(?:['ʻʼ‘’`][^\W\d_]+)*"
_CHAIN = rf"{_WORD}(?:[ \t]+{_WORD}){{0,3}}"
_LIST = rf"{_CHAIN}(?:\s*,\s*{_CHAIN})*(?:\s*,?\s+(?:va|hamda|yoki)\s+{_CHAIN})?"
_NUMBER = r"(?:\d+|ikki|uch|toʻrt|to'rt|besh|olti|bir\s+necha)"

DEFINITION = re.compile(rf"(?:^|(?<=[.!?]\s))({_CHAIN})(?:\s*\([^)]*\))?\s+[—–-]\s+([^.;]+)")
SUCH_AS = re.compile(rf"({_LIST})\s+kabi\s+({_CHAIN})")
DIVIDED = re.compile(
    rf"({_CHAIN})\s+(?:{_NUMBER}\s+)?(?:tur|xil|guruh|qism)(?:lar)?(?:ga)\s+boʻlinadi\s*:\s*({_LIST})",
    re.IGNORECASE,
)
TYPES_OF = re.compile(rf"({_CHAIN})(?:ning)?\s+turlari\s*:\s*({_LIST})", re.IGNORECASE)
_ONE_OF = re.compile(r"(?:dan|lardan)\s+biri\s*$|\s+bir\s+turi\s*$")
_LIST_SPLIT = re.compile(r"\s*,\s*|\s+(?:va|hamda|yoki)\s+")
# Termin yasovchi qo'shimchalar: ro'yxatdagi so'z misol emas, soha/termin nomi ekanining belgisi.
# Juda umumiy "jinslar": "ilmiy, soxta kabi turlari", "tasdiq, inkor kabi maʼnolar" — giponimiya emas.
GENERIC_HYPERNYMS = frozenset(
    normalize_form(w) for w in ("tur", "xil", "guruh", "narsa", "masala", "xususiyat", "jarayon", "holat", "maʼno", "til")
)
TERM_ENDINGS = ("shunoslik", "logiya", "grafiya", "lingvistika", "ika", "iya", "ema", "izm", "lik", "fon")


@dataclass
class Relation:
    narrower: str
    broader: str
    sources: Counter = field(default_factory=Counter)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "narrower": self.narrower,
            "broader": self.broader,
            "sources": dict(self.sources),
            "evidence": self.evidence[:3],
        }


@dataclass
class Thesaurus:
    concepts: set[str]
    relations: dict[tuple[str, str], Relation]
    related: list[tuple[str, str, float, int]]  # (a, b, PMI, birga kelish soni)
    alt_labels: dict[str, set[str]] = field(default_factory=dict)

    def broader(self, concept: str) -> list[str]:
        return sorted(b for (n, b) in self.relations if n == concept)

    def narrower(self, concept: str) -> list[str]:
        return sorted(n for (n, b) in self.relations if b == concept)

    def roots(self) -> list[str]:
        has_parent = {n for n, _ in self.relations}
        children = {b for _, b in self.relations}
        return sorted(children - has_parent)

    def cycles(self) -> list[list[str]]:
        graph = defaultdict(list)
        for n, b in self.relations:
            graph[n].append(b)
        found, state = [], {}

        def visit(node: str, path: list[str]) -> None:
            state[node] = 1
            for nxt in graph[node]:
                if state.get(nxt) == 1:
                    found.append(path[path.index(nxt):] + [nxt] if nxt in path else [node, nxt])
                elif nxt not in state:
                    visit(nxt, path + [nxt])
            state[node] = 2

        for node in list(graph):
            if node not in state:
                visit(node, [node])
        return found

    def to_dict(self) -> dict:
        concepts = sorted(self.concepts | {c for pair in self.relations for c in pair})
        return {
            "concepts": [
                {
                    "label": c,
                    "broader": self.broader(c),
                    "narrower": self.narrower(c),
                    "alt_labels": sorted(self.alt_labels.get(c, ())),
                }
                for c in concepts
            ],
            "relations": [r.to_dict() for r in sorted(self.relations.values(), key=lambda r: (r.broader, r.narrower))],
            "related": [{"a": a, "b": b, "pmi": round(p, 3), "count": n} for a, b, p, n in self.related],
        }

    def to_turtle(self, base: str = "https://uzterm.local/concept/") -> str:
        def iri(label: str) -> str:
            slug = re.sub(r"[^\w]+", "_", normalize_form(label).replace("'", "")).strip("_")
            return f"<{base}{slug}>"

        def lit(text: str) -> str:
            return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"@uz'

        lines = [
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
            "",
            f"<{base}scheme> a skos:ConceptScheme ; skos:prefLabel \"Oʻzbek tilshunoslik terminlari\"@uz .",
            "",
        ]
        data = self.to_dict()
        for concept in data["concepts"]:
            parts = [f"{iri(concept['label'])} a skos:Concept", f"skos:inScheme <{base}scheme>",
                     f"skos:prefLabel {lit(concept['label'])}"]
            parts += [f"skos:altLabel {lit(a)}" for a in concept["alt_labels"]]
            parts += [f"skos:broader {iri(b)}" for b in concept["broader"]]
            parts += [f"skos:narrower {iri(n)}" for n in concept["narrower"]]
            lines.append(" ;\n    ".join(parts) + " .")
        for item in data["related"]:
            lines.append(f"{iri(item['a'])} skos:related {iri(item['b'])} .")
        return "\n".join(lines) + "\n"


def transitive_reduction(relations: dict[tuple[str, str], Relation]) -> list[tuple[str, str]]:
    """A ⊂ C ⊂ B bo'lsa, to'g'ridan-to'g'ri A ⊂ B ortiqcha: u olib tashlanadi, dalili A ⊂ C ga o'tadi.

    *mayl kategoriyasi ⊂ grammatik kategoriya ⊂ kategoriya* — *mayl kategoriyasi ⊂ kategoriya*
    (bosh so'z qoidasi) qoldirilmaydi. Olib tashlangan juftlar qaytariladi.
    """
    parents: dict[str, set[str]] = defaultdict(set)
    for n, b in relations:
        parents[n].add(b)

    def ancestors(node: str, seen: set[str]) -> set[str]:
        for parent in parents.get(node, ()):
            if parent not in seen:
                seen.add(parent)
                ancestors(parent, seen)
        return seen

    removed = []
    for n, b in list(relations):
        via = [c for c in parents[n] if c != b and b in ancestors(c, set())]
        if via:
            removed.append((n, b))
            dropped = relations.pop((n, b))
            keep = relations[(n, via[0])]
            keep.sources.update(dropped.sources)
            keep.evidence.extend(e for e in dropped.evidence if e not in keep.evidence)
            parents[n].discard(b)
    return removed


class ThesaurusBuilder:
    def __init__(self, lemmatizer: CorpusLemmatizer, terms: Iterable[str]) -> None:
        self.lemmatizer = lemmatizer
        self.tagger = MorphTagger(lemmatizer)
        self.extractor = PatternExtractor(self.tagger)
        self.display: dict[str, Counter] = defaultdict(Counter)
        for term in terms:
            key = self.key(term)
            if key:
                self.display[key][canonical_apostrophes(" ".join(term.lower().split()))] += 1
        self.terms = set(self.display)

    # --- yordamchi ------------------------------------------------------------------

    def key(self, phrase: str) -> str:
        """Ibora -> lug'at kaliti: kichik harf, oxirgi so'z lemmasi (izofa: so'zlar turkumi -> so'z turkumi)."""
        words = [t.norm for t in tokenize(phrase)]
        if not words:
            return ""
        lemmas = [*words[:-1], self.lemmatizer.lemma(words[-1])]
        if len(lemmas) >= 2:  # aniqlovchi ko'plikda: "soʻzlar turkumi" -> "soʻz turkumi"
            lemmas[-2] = self.lemmatizer.lemma(lemmas[-2]) if lemmas[-2].endswith("lar") else lemmas[-2]
        return " ".join(lemmas)

    def label(self, key: str) -> str:
        """Ko'rsatish uchun lug'at shakli (izofa bilan: "soʻz birikmasi"), lug'atda bo'lmasa — kalit."""
        forms = self.display.get(key)
        return forms.most_common(1)[0][0] if forms else canonical_apostrophes(key)

    def _last_chain(self, text: str, strict: bool = False, min_letters: int = 3) -> str | None:
        """Matndagi oxirgi ot birikmasi. ``strict``: undan keyin faqat yordamchi so'zlar bo'lishi mumkin
        (taʼrif ot bilan tugaydi; "... tomonidan oʻrganiladi" — taʼrif emas)."""
        spans = self.extractor.candidates(text)
        if not spans:
            return None
        last = spans[-1]
        tail = [t.norm for t in tokenize(text[last.end:])]
        allowed = (FUNC,) if strict else (FUNC, "VERB")
        if any(self.tagger.tag(w) not in allowed for w in tail):
            return None
        key = self.key(text[last.start : last.end])
        return key if len(key.replace(" ", "")) >= min_letters else None

    def _first_chain(self, text: str) -> str | None:
        spans = self.extractor.candidates(text)
        return self.key(spans[0].surface) if spans else None

    def _term_like(self, key: str) -> bool:
        return key in self.terms or key.split()[-1].endswith(TERM_ENDINGS) and len(key) >= 6

    def _known(self, key: str) -> bool:
        return key in self.terms

    def _specific(self, key: str) -> str:
        """Jins sifatida eng uzun, lug'atda bor o'ng qism (bo'lmasa — o'zi)."""
        words = key.split()
        for i in range(len(words)):
            tail = " ".join(words[i:])
            if tail in self.terms:
                return tail
        return key

    # --- manbalar ---------------------------------------------------------------------

    def head_relations(self) -> list[tuple[str, str, str]]:
        found = []
        for term in self.terms:
            words = term.split()
            for i in range(1, len(words)):
                tail = " ".join(words[i:])
                if tail in self.terms:
                    found.append((term, tail, term))
                    break
        return found

    def definition_relations(self, documents: Mapping[str, str]) -> list[tuple[str, str, str]]:
        found = []
        for text in documents.values():
            for paragraph in text.split("\n"):
                for match in DEFINITION.finditer(paragraph.strip()):
                    definiendum = self._last_chain(match.group(1), min_letters=2)  # "Ot", "Gap"
                    body = normalize_text(match.group(2)).strip()
                    body = _ONE_OF.sub("", body)
                    genus = self._last_chain(body, strict=True)
                    if not definiendum or not genus or genus == definiendum:
                        continue
                    # Jins (yoki uning bosh so'zi) va taʼriflanuvchi maʼlum terminlar bo'lsin.
                    if not self._known(definiendum) or not (self._known(genus) or self._known(genus.split()[-1])):
                        continue
                    found.append((definiendum, self._specific(genus), match.group(0)[:160]))
        return found

    def pattern_relations(self, documents: Mapping[str, str]) -> list[tuple[str, str, str]]:
        found = []
        for text in documents.values():
            for regex, hyper_group, list_group in ((SUCH_AS, 2, 1), (DIVIDED, 1, 2), (TYPES_OF, 1, 2)):
                for match in regex.finditer(text):
                    hyper = self._first_chain(match.group(hyper_group)) if regex is SUCH_AS else self._last_chain(
                        match.group(hyper_group)
                    )
                    if not hyper or hyper in GENERIC_HYPERNYMS:
                        continue
                    items = [i for i in _LIST_SPLIT.split(match.group(list_group)) if i.strip()]
                    hypos = [self._first_chain(i) if regex is not SUCH_AS else self._last_chain(i) for i in items]
                    # Giponim termin bo'lsin: lug'atda bor yoki termin yasovchi qo'shimchali
                    # (imlo qoidalaridagi "xona, noma kabi soʻzlar" — misollar, termin emas).
                    hypos = [h for h in hypos if h and h != hyper and self._term_like(h)]
                    if not hypos:
                        continue
                    for hypo in hypos:
                        found.append((hypo, self._specific(hyper), match.group(0)[:160]))
        return found

    def related(
        self, paragraphs: Sequence[set[str]], exclude: set[tuple[str, str]], min_cooc: int = 3, top: int = 300
    ) -> list[tuple[str, str, float, int]]:
        n = len(paragraphs)
        single, pair = Counter(), Counter()
        for terms in paragraphs:
            single.update(terms)
            pair.update(tuple(sorted(p)) for p in combinations(sorted(terms), 2))
        scored = []
        for (a, b), c in pair.items():
            if c < min_cooc or (a, b) in exclude or (b, a) in exclude:
                continue
            pmi = math.log2(c * n / (single[a] * single[b]))
            if pmi > 0:
                scored.append((self.label(a), self.label(b), pmi, c))
        return sorted(scored, key=lambda x: (-x[2], -x[3], x[0]))[:top]

    def build(
        self,
        documents: Mapping[str, str],
        paragraphs: Sequence[set[str]] = (),
        alt_labels: Mapping[str, Iterable[str]] | None = None,
    ) -> Thesaurus:
        relations: dict[tuple[str, str], Relation] = {}
        for source, items in (
            ("head", self.head_relations()),
            ("definition", self.definition_relations(documents)),
            ("pattern", self.pattern_relations(documents)),
        ):
            for narrower, broader, evidence in items:
                if narrower == broader:
                    continue
                key = (self.label(narrower), self.label(broader))
                rel = relations.setdefault(key, Relation(*key))
                rel.sources[source] += 1
                if evidence not in rel.evidence:
                    rel.evidence.append(evidence)
        # ikki tomonlama munosabat (A ⊂ B va B ⊂ A) — kamroq dalillisi olib tashlanadi
        for a, b in list(relations):
            if (b, a) in relations and (a, b) in relations:
                weaker = min(((a, b), (b, a)), key=lambda k: (sum(relations[k].sources.values()), k))
                relations.pop(weaker)
        transitive_reduction(relations)
        exclude = {(normalize_form(n), normalize_form(b)) for n, b in relations}
        related = self.related(paragraphs, exclude) if paragraphs else []
        alts = {self.label(self.key(k)): {canonical_apostrophes(v) for v in vs} for k, vs in (alt_labels or {}).items()}
        return Thesaurus({self.label(t) for t in self.terms}, relations, related, alts)


def build_from_repository(raw_dir, annotation_files, terms_path) -> tuple[Thesaurus, "ThesaurusBuilder"]:
    """Repozitoriy maʼlumotlaridan tezaurus: korpus, annotatsiyadagi terminlar va lug'at."""
    from pathlib import Path

    from app.database.term_store import load_terms
    from app.dataset.annotation import load_annotations

    documents = {p.stem: p.read_text(encoding="utf-8") for p in sorted(Path(raw_dir).glob("*.txt"))}
    lemmatizer = CorpusLemmatizer(t.norm for text in documents.values() for t in tokenize(text))
    records = load_annotations(list(annotation_files)) if annotation_files else []
    entries = load_terms(terms_path)
    terms = [e.term for e in entries] + [s.term for r in records for s in r.terms]
    builder = ThesaurusBuilder(lemmatizer, terms)
    paragraphs = [{builder.key(s.term) for s in r.terms} for r in records]
    alt = {e.term: [*e.synonyms, *e.variants] for e in entries if e.synonyms or e.variants}
    return builder.build(documents, paragraphs, alt), builder


def main(argv: list[str] | None = None) -> int:
    import argparse
    import csv
    import json
    import random
    from pathlib import Path

    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Terminologik tezaurusni (SKOS) avtomatik qurish")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--annotations", type=Path, nargs="*",
                        default=sorted((REPO_ROOT / "data" / "annotations" / "claude").glob("*.jsonl")))
    parser.add_argument("--terms", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports" / "thesaurus.json")
    parser.add_argument("--turtle", type=Path, default=REPO_ROOT / "reports" / "thesaurus.ttl")
    parser.add_argument("--review", type=Path, default=REPO_ROOT / "data" / "judgments" / "thesaurus-review.csv")
    parser.add_argument("--sample-per-source", type=int, default=40)
    args = parser.parse_args(argv)

    thesaurus, _ = build_from_repository(args.raw, args.annotations, args.terms)
    data = thesaurus.to_dict()
    by_source = Counter(src for r in thesaurus.relations.values() for src in r.sources)
    multi = sum(len(r.sources) > 1 for r in thesaurus.relations.values())
    with_parent = {n for n, _ in thesaurus.relations}
    summary = {
        "concepts": len(data["concepts"]),
        "dictionary_terms": len(thesaurus.concepts),
        "broader_relations": len(thesaurus.relations),
        "by_source": dict(by_source),
        "confirmed_by_several_sources": multi,
        "terms_with_broader": len(with_parent & thesaurus.concepts),
        "roots": len(thesaurus.roots()),
        "cycles": thesaurus.cycles(),
        "related_pairs": len(thesaurus.related),
    }
    data["summary"] = summary
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.turtle.write_text(thesaurus.to_turtle(), encoding="utf-8")

    existing = {}
    if args.review.is_file():
        with args.review.open(encoding="utf-8-sig", newline="") as handle:
            existing = {(r["narrower"], r["broader"]): r for r in csv.DictReader(handle)}
    rng = random.Random(13)
    sample = []
    for source in SOURCES:
        items = sorted(
            (r for r in thesaurus.relations.values() if source in r.sources), key=lambda r: (r.narrower, r.broader)
        )
        sample += rng.sample(items, min(args.sample_per_source, len(items)))
    seen = set()
    with args.review.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["narrower", "broader", "sources", "judgment", "notes", "evidence"])
        writer.writeheader()
        for r in sample:
            if (r.narrower, r.broader) in seen:
                continue
            seen.add((r.narrower, r.broader))
            old = existing.get((r.narrower, r.broader), {})
            writer.writerow({
                "narrower": r.narrower, "broader": r.broader, "sources": "+".join(sorted(r.sources)),
                "judgment": old.get("judgment", ""), "notes": old.get("notes", ""),
                "evidence": (r.evidence[0] if r.evidence else "")[:200],
            })
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Tezaurus: {args.output}, {args.turtle}; ekspert namunasi: {args.review} ({len(seen)} ta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

