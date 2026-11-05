from __future__ import annotations

import math

from app.nlp.candidates import extract_candidates, rank
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.patterns import ADJ, FUNC, NOUN, VERB, MorphTagger, PatternExtractor, matches_pattern, tag_sequence

VOCAB = {
    "so'z", "turkum", "gap", "bo'lak", "tovush", "undosh", "fonema", "kelishik", "qo'shimcha", "til", "yasash",
}


def tagger() -> MorphTagger:
    return MorphTagger(CorpusLemmatizer(VOCAB))


def test_tagger_classes():
    t = tagger()
    assert t.tag("va") == FUNC and t.tag("ko'ra") == FUNC
    assert t.tag("yoziladi") == VERB and t.tag("o'rganadigan") == VERB
    assert t.tag("grammatik") == ADJ and t.tag("undosh") == ADJ and t.tag("leksik") == ADJ
    assert t.tag("tilshunoslik") == NOUN  # -lik ot, sifat emas
    assert t.tag("fonema") == NOUN and t.tag("yasash") == NOUN


def test_pattern_requires_bare_modifier_and_noun_head():
    t = tagger()
    assert matches_pattern(("so'z", "turkum"), t)  # Ot + Ot
    assert matches_pattern(("undosh", "tovush"), t)  # Sifat + Ot
    assert matches_pattern(("grammatik", "kategoriya"), t)
    assert not matches_pattern(("gapning", "bo'lak"), t)  # qaratqich birikmani bo'ladi
    assert not matches_pattern(("grammatik",), t)  # bosh so'z sifat
    assert not matches_pattern(("so'z", "yoziladi"), t)  # bosh so'z fe'l
    assert not matches_pattern(("a", "b", "c", "d", "e"), t)  # 4 so'zdan uzun
    assert tag_sequence(("undosh", "tovush"), t) == "ADJ+NOUN"


def test_extractor_finds_longest_chains_with_positions():
    text = "Jarangli undosh tovushlarning soni va gapning boʻlaklari yoziladi."
    spans = PatternExtractor(tagger()).candidates(text)
    surfaces = [s.surface for s in spans]
    assert "Jarangli undosh tovushlarning" in surfaces
    assert "soni" in surfaces  # yolg'iz ot ham qolipga mos
    assert "gapning" in surfaces and "boʻlaklari" in surfaces  # qaratqich birikmani bo'ladi
    for span in spans:
        assert text[span.start : span.end] == span.surface
    chain = next(s for s in spans if s.surface.startswith("Jarangli"))
    assert chain.words == ("jarangli", "undosh", "tovush")


def test_extractor_keep_falls_back_to_shorter_chain():
    text = "jarangli undosh tovushlar"
    keep = lambda key: key == ("undosh", "tovush")  # noqa: E731
    spans = PatternExtractor(tagger(), keep).extract(text)
    assert [(text[s.start : s.end], s.term) for s in spans] == [("undosh tovushlar", "undosh tovush")]
    assert PatternExtractor(tagger(), lambda key: False).extract(text) == []


def test_rank_with_pattern_filter():
    docs = {"a": "grammatik kategoriya va grammatik shakl. grammatik", "b": "grammatik kategoriya"}
    t = tagger()
    ranked = rank(extract_candidates(docs), "frequency", 2, min_frequency=1, keep=lambda k: matches_pattern(k, t))
    texts = [c.text for c, _ in ranked]
    assert "grammatik kategoriya" in texts and "grammatik" not in texts


def test_pattern_experiment_thresholds_grid():
    from app.models.pattern_experiment import thresholds

    grid = thresholds([1.0, 2.0, 3.0, 4.0])
    assert grid[0] == -math.inf and grid == sorted(grid) and 4.0 not in grid
    assert thresholds([]) == [-math.inf]
