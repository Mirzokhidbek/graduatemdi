from __future__ import annotations

from app.multilingual.align import (
    Aligner,
    CascadeAligner,
    cognate_similarity,
    gold_by_source,
    key_en,
    key_ru,
    key_uz,
    preferred_equivalent,
    ranking_metrics,
)
from app.multilingual.sources import extract_etymons, fetch_langlinks
from app.database.term_store import TermEntry


def test_phonetic_keys_meet_across_languages():
    assert key_ru("фонема") == key_en("phoneme") == key_uz("fonema") == "fonema"
    assert key_ru("интонация") == key_en("intonation") == key_uz("intonatsiya")
    assert key_en("morphology") == key_uz("morfologiya")
    assert key_en("phonetics") == key_uz("fonetika")
    assert key_en("archiphoneme") == key_uz("arxifonema")
    assert cognate_similarity("аффикс", "ru", "affiks") == 1.0
    assert cognate_similarity("syntax", "en", "sintaksis") > 0.7
    assert cognate_similarity("языкознание", "ru", "tilshunoslik") < 0.3


def test_aligner_ranks_and_semantic_encoder_is_pluggable():
    targets = ["fonema", "fonetika", "tilshunoslik", "lingvistika"]
    [top] = Aligner(targets).rank(["phoneme"], "en", top=2)
    assert top[0].uz == "fonema" and top[0].semantic is None

    vectors = {"languages science": [1.0, 0.0], "tilshunoslik": [1.0, 0.1], "fonema": [0.0, 1.0],
               "fonetika": [0.0, 1.0], "lingvistika": [0.9, 0.2]}
    encoder = lambda texts: [vectors[t] for t in texts]  # noqa: E731
    [top] = Aligner(targets, encoder, weight=1.0).rank(["languages science"], "en", top=1)
    assert top[0].uz == "tilshunoslik" and top[0].semantic > 0.99


def test_ranking_metrics():
    ranked = [["a", "b"], ["x", "y", "z"], ["q"]]
    gold = [{"a"}, {"z"}, {"none"}]
    m = ranking_metrics(ranked, gold)
    assert m["acc@1"] == 1 / 3 and m["acc@5"] == 2 / 3 and abs(m["mrr"] - (1 + 1 / 3) / 3) < 1e-9


def test_gold_grouping_keeps_several_uzbek_answers():
    rows = [
        {"uz": "ohang", "ru": "интонация", "en": "intonation", "kind": "native"},
        {"uz": "intonatsiya", "ru": "интонация", "en": "intonation", "kind": "international"},
    ]
    assert gold_by_source(rows, "ru") == {"интонация": {"ohang", "intonatsiya"}}
    assert gold_by_source(rows, "en", "native") == {"intonation": {"ohang"}}


def test_preferred_equivalent_lists_dictionary_alternatives():
    entry = TermEntry("t1", "tilshunoslik", None, None, (), ("lingvistika",), "tilshunoslik", "needs_review", None)
    result = preferred_equivalent("lingvistika", [entry])
    assert result["preferred"] == "tilshunoslik" and result["alternatives"] == ["tilshunoslik"]
    assert result["status"] == "needs_review"
    assert preferred_equivalent("fonema", [entry])["status"] == "no_data"


def test_extract_etymons():
    docs = {"d": "Fonema (yun. phonema — tovush) — eng kichik birlik. Tilshunoslikda affiks (lotinchada „biriktirilgan“)."
                 " Imlo (arab. – toʻgʻri yozish)."}
    found = {(e["uz"], e["lang"]): e for e in extract_etymons(docs)}
    assert found[("fonema", "grc")]["foreign"] == "phonema" and found[("fonema", "grc")]["gloss"] == "tovush"
    assert ("affiks", "la") in found
    assert found[("imlo", "ar")]["foreign"] is None and found[("imlo", "ar")]["gloss"] == "toʻgʻri yozish"


def test_fetch_langlinks_with_fake_api():
    calls = []

    def fake(url):
        calls.append(url)
        return {"query": {
            "normalized": [{"from": "fonema", "to": "Fonema"}],
            "pages": {
                "1": {"title": "Fonema", "langlinks": [{"lang": "ru", "*": "Фонема"}, {"lang": "en", "*": "Phoneme"},
                                                        {"lang": "de", "*": "Phonem"}]},
                "2": {"title": "Yoʻq", "missing": ""},
            }}}

    links = fetch_langlinks(["fonema", "Yoʻq"], fetch=fake, pause=0)
    assert links == {"fonema": {"ru": "Фонема", "en": "Phoneme"}}
    assert len(calls) == 2 and "lllang=ru" in calls[0] and "lllang=en" in calls[1]


def test_cascade_uses_cognate_when_confident_else_semantic():
    targets = ["fonema", "tilshunoslik", "lingvistika"]
    vectors = {"phoneme": [0.0, 1.0], "linguistics science": [1.0, 0.0], "fonema": [0.0, 1.0],
               "tilshunoslik": [1.0, 0.0], "lingvistika": [0.6, 0.4]}
    encoder = lambda texts: [vectors[t] for t in texts]  # noqa: E731
    cascade = CascadeAligner(Aligner(targets), Aligner(targets, encoder, weight=1.0), threshold=0.7)
    first, second = cascade.rank(["phoneme", "linguistics science"], "en", top=1)
    assert first[0].uz == "fonema" and first[0].semantic is None  # kognat ishonchli
    assert second[0].uz == "tilshunoslik" and second[0].semantic is not None  # semantik model
