from __future__ import annotations

from collections import Counter

from app.dataset.annotation import AnnotatedRecord, AnnotatedSpan
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.patterns import MorphTagger
from app.variation.groups import bcubed, build_groups, choose_preferred
from app.variation.homonymy import GENERAL, TERM, HomonymClassifier, ambiguous_lemmas, occurrences
from app.variation.orthography import (
    canonical_form,
    edit_distance,
    has_mixed_script,
    likely_misspelling,
    skeleton,
    to_latin,
)
from app.variation.synonyms import KIND_DOUBLET, KIND_SYNONYM, SynonymExtractor, classify, is_international
from app.database.term_store import TermEntry


def make_entry(term: str, synonyms=(), status: str = "needs_review", source=None) -> TermEntry:
    return TermEntry(term, term, None, None, (), tuple(synonyms), term, status, source)

# --- orthography --------------------------------------------------------------------


def test_to_latin_follows_official_rules():
    assert to_latin("ўзак") == "oʻzak"
    assert to_latin("ғоя") == "gʻoya"
    assert to_latin("Шеър") == "Sheʼr"
    assert to_latin("ер") == "yer" and to_latin("поезд") == "poyezd" and to_latin("тема") == "tema"
    assert to_latin("цирк") == "sirk" and to_latin("акция") == "aksiya" and to_latin("милиция") == "militsiya"
    assert to_latin("Ўзбекистон") == "Oʻzbekiston"


def test_skeleton_unifies_spelling_variants():
    forms = ["oʻzak", "o'zak", "o`zak", "o‘zak", "ozak", "Oʻzak", "ўзак"]
    assert {skeleton(f) for f in forms} == {"ozak"}
    assert skeleton("kasb-hunar") == skeleton("kasbhunar")
    assert canonical_form("o'zak  so`z") == "oʻzak soʻz"


def test_mixed_script_detection():
    assert has_mixed_script("fonemа")  # oxirgi "а" kirill
    assert not has_mixed_script("fonema") and not has_mixed_script("фонема")


def test_edit_distance_and_misspelling():
    assert edit_distance("antonim", "atnonim") == 1  # o'rin almashish
    assert edit_distance("kitob", "kitob") == 0 and edit_distance("", "abc") == 3
    assert likely_misspelling("allofon", "alloton")
    assert likely_misspelling("leksikologiya", "leksikalogiya")
    assert not likely_misspelling("fonetik", "fonetika")  # yasalish, xato emas
    assert not likely_misspelling("fonologik", "fonologiya")
    assert not likely_misspelling("mahsullilik", "mahsulsizlik")  # zid maʼno
    assert not likely_misspelling("nutq payti", "nutq vaqti")  # qisqa so'z
    assert not likely_misspelling("gap", "kap")


# --- synonyms -----------------------------------------------------------------------


def test_international_word_heuristic():
    for word in ("lingvistika", "funksiya", "morfema", "intonatsiya", "ekstralingvistik", "deskriptiv"):
        assert is_international(word), word
    for word in ("tilshunoslik", "vazifa", "ohang", "qoʻshimcha", "nolisoniy", "tavsifiy"):
        assert not is_international(word), word
    assert classify(("lingvistika",), ("tilshunoslik",)) == KIND_DOUBLET
    assert classify(("ovoz",), ("shovqin",)) == KIND_SYNONYM


def test_synonym_extractor_cues_and_filters():
    docs = {
        "a": "Intonatsiya (ohang) gapning ohangidir. Tilshunoslik yoki lingvistika fani. "
             "Ikki yoki uch tovush. Feʼl (keldi) shakli. Supersegment (ustsegment) birliklar."
    }
    lem = CorpusLemmatizer({"intonatsiya", "ohang", "tilshunoslik", "lingvistika", "tovush", "supersegment"})
    known = {("intonatsiya",), ("tilshunoslik",), ("supersegment",)}
    pairs = {(" ".join(p.left), " ".join(p.right)): p for p in SynonymExtractor(MorphTagger(lem), known).extract(docs)}
    assert ("intonatsiya", "ohang") in pairs and pairs[("intonatsiya", "ohang")].kind == KIND_DOUBLET
    assert ("lingvistika", "tilshunoslik") in pairs and pairs[("lingvistika", "tilshunoslik")].cues["or"] == 1
    assert ("supersegment", "ustsegment") in pairs
    assert not any("keldi" in key for pair in pairs for key in pair)  # fe'l misol, sinonim emas
    assert not any("uch" in pair for pair in pairs)  # maʼlum termin yo'q


# --- grouping and preferred form -----------------------------------------------------


def test_build_groups_merges_spelling_and_morphology_but_not_synonyms():
    forms = {"oʻzak": 5, "o'zak": 2, "oʻzaklar": 3, "affiks": 4, "qoʻshimcha": 6}
    lemma_of = {"oʻzaklar": "oʻzak"}
    entry = make_entry("affiks", synonyms=["qoʻshimcha"])
    groups = build_groups(forms, lemma_of, [entry])
    by_pref = {g.preferred: g for g in groups}
    assert set(by_pref["oʻzak"].members) == {"oʻzak", "o'zak", "oʻzaklar"}
    assert {t for *_, t in by_pref["oʻzak"].links} == {"orthographic", "morphological"}
    # sinonimlar bitta guruhga avtomatik qo'shilmaydi, faqat tekshiruv uchun bog'lanadi
    assert len(groups) == 3
    assert any(t == "synonym" for g in groups for *_, t in g.links)
    assert all(g.status == "needs_review" for g in groups)


def test_choose_preferred_rules():
    approved = make_entry("tilshunoslik", status="approved", source="Lugʻat, 2020")
    form, status, reasons = choose_preferred(Counter({"lingvistika": 9, "tilshunoslik": 1}), [approved])
    assert (form, status) == ("tilshunoslik", "approved") and "tasdiqlangan" in reasons[0]
    form, status, reasons = choose_preferred(Counter({"o'zak": 3, "oʻzak": 1}))
    assert form == "oʻzak" and status == "needs_review" and "imlo" in reasons[0]
    form, _, reasons = choose_preferred(Counter({"lingvistika": 2, "tilshunoslik": 5}))
    assert form == "tilshunoslik" and "ko'p qo'llangan" in reasons[0]
    form, _, reasons = choose_preferred(Counter({"leksik birlik": 2, "leksema": 2}))
    assert form == "leksema" and "qisqaroq" in reasons[0]


def test_bcubed():
    gold = {"a": "1", "b": "1", "c": "2"}
    assert bcubed({"a": "x", "b": "x", "c": "y"}, gold)["f1"] == 1.0
    split = bcubed({"a": "x", "b": "y", "c": "z"}, gold)
    assert split["precision"] == 1.0 and split["recall"] < 1.0
    merged = bcubed({"a": "x", "b": "x", "c": "x"}, gold)
    assert merged["recall"] == 1.0 and merged["precision"] < 1.0


# --- homonymy ------------------------------------------------------------------------


def _record(rid: str, text: str, terms: list[tuple[str, str]]) -> AnnotatedRecord:
    spans = []
    for surface, term in terms:
        start = text.index(surface)
        spans.append(AnnotatedSpan(start, start + len(surface), term, "TERM"))
    return AnnotatedRecord(rid, "d", text, tuple(spans), "t", "reviewed", None)


def test_homonymy_classifier_uses_context():
    train = [
        _record(f"t{i}", "Soʻzga qoʻshimcha qoʻshiladi.", [("qoʻshimcha", "qoʻshimcha")]) for i in range(4)
    ] + [_record(f"g{i}", "Bu haqda qoʻshimcha maʼlumot berildi.", []) for i in range(4)]
    lem = CorpusLemmatizer({"qo'shimcha", "so'z", "ma'lumot"})
    amb = ambiguous_lemmas(train, lem, min_count=4)
    assert set(amb) == {"qo'shimcha"} and amb["qo'shimcha"] == 0.5
    occ = occurrences(train, set(amb), lem)
    clf = HomonymClassifier().fit(occ)
    term = next(o for o in occ if o.label == TERM)
    general = next(o for o in occ if o.label == GENERAL)
    assert clf.predict(term) == TERM and clf.predict(general) == GENERAL
