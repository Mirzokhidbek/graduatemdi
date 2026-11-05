from __future__ import annotations

from collections import Counter

from app.nlp.lemmatize import CorpusLemmatizer
from app.ontology.thesaurus import Relation, ThesaurusBuilder, transitive_reduction

VOCAB = {
    "tovush", "undosh", "gap", "so'z", "yordamchi", "ko'makchi", "yuklama", "bo'lak", "kesim", "soha",
    "fonetika", "fonologiya", "sintaksis", "turkum", "mustaqil", "ot",
}
TERMS = [
    "tovush", "undosh tovush", "jarangli undosh tovush", "gap", "sodda gap", "yordamchi soʻz", "koʻmakchi",
    "yuklama", "kesim", "bosh boʻlak", "fonetika", "fonologiya", "sintaksis", "soʻz turkumi", "mustaqil soʻz turkumi", "ot",
]


def builder() -> ThesaurusBuilder:
    return ThesaurusBuilder(CorpusLemmatizer(VOCAB), TERMS)


def test_head_hierarchy_uses_longest_known_suffix():
    pairs = {(n, b) for n, b, _ in builder().head_relations()}
    assert ("jarangli undosh tovush", "undosh tovush") in pairs
    assert ("undosh tovush", "tovush") in pairs
    assert ("jarangli undosh tovush", "tovush") not in pairs  # faqat eng yaqin jins
    assert ("sodda gap", "gap") in pairs


def test_definitions_extract_genus():
    docs = {
        "a": "Koʻmakchi — yordamchi soʻzlarning bir turi. Kesim — gapning bosh boʻlaklaridan biri. "
             "Ot — mustaqil soʻz turkumlaridan biri.\nShevalar — lingvistik geografiya tomonidan oʻrganiladi."
    }
    b = builder()
    pairs = {(b.label(n), b.label(g)) for n, g, _ in b.definition_relations(docs)}
    assert ("koʻmakchi", "yordamchi soʻz") in pairs
    assert ("kesim", "bosh boʻlak") in pairs
    assert ("ot", "mustaqil soʻz turkumi") in pairs
    assert not any(n == "shevalar" for n, _ in pairs)  # fe'l bilan tugaydi — taʼrif emas


def test_patterns_such_as_and_divided():
    docs = {
        "a": "Fonetika, fonologiya va sintaksis kabi sohalar rivojlandi. "
             "Xona, noma kabi soʻzlar qoʻshib yoziladi. Gaplar 3 turga boʻlinadi: sodda gap va qoʻshma gap."
    }
    b = builder()
    pairs = {(b.label(n), b.label(g)) for n, g, _ in b.pattern_relations(docs)}
    assert {("fonetika", "soha"), ("fonologiya", "soha"), ("sintaksis", "soha")} <= pairs
    assert ("sodda gap", "gap") in pairs
    assert not any(n in ("xona", "noma") for n, _ in pairs)  # misollar, termin emas


def test_build_reduces_transitive_links_and_exports_skos():
    b = builder()
    docs = {"a": "Undosh tovush — tovush. Jarangli undosh tovush — tovush."}
    thesaurus = b.build(docs, paragraphs=[{"tovush", "undosh tovush"}] * 3 + [{"gap"}], alt_labels={"tovush": ["ovoz"]})
    assert ("jarangli undosh tovush", "tovush") not in thesaurus.relations
    assert thesaurus.broader("jarangli undosh tovush") == ["undosh tovush"]
    assert thesaurus.cycles() == []
    ttl = thesaurus.to_turtle()
    assert "skos:broader" in ttl and 'skos:altLabel "ovoz"@uz' in ttl


def test_transitive_reduction_moves_evidence():
    rel = {
        ("a", "b"): Relation("a", "b", Counter(head=1), ["e1"]),
        ("b", "c"): Relation("b", "c", Counter(head=1)),
        ("a", "c"): Relation("a", "c", Counter(definition=1), ["e2"]),
    }
    assert transitive_reduction(rel) == [("a", "c")]
    assert rel[("a", "b")].sources == Counter(head=1, definition=1) and "e2" in rel[("a", "b")].evidence
