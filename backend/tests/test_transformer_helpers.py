"""Transformer modulining torch'siz yordamchilari: bo'laklash va subword teglarini moslash."""

from __future__ import annotations

import pytest
from app.models.transformer import (
    IGNORE,
    LABEL_ID,
    align_labels,
    chunk_words,
    word_predictions,
)


def test_chunk_words():
    assert chunk_words(0, 150) == []
    assert chunk_words(5, 150) == [(0, 5)]
    assert chunk_words(7, 3) == [(0, 3), (3, 6), (6, 7)]
    with pytest.raises(ValueError):
        chunk_words(5, 0)


def test_align_labels_first_subword_only():
    # [CLS] fonema-lar va undosh tov-ush [SEP]
    word_ids = [None, 0, 0, 1, 2, 3, 3, None]
    labels = align_labels(word_ids, ["B-TERM", "O", "B-TERM", "I-TERM"])
    assert labels == [IGNORE, LABEL_ID["B-TERM"], IGNORE, LABEL_ID["O"], LABEL_ID["B-TERM"],
                      LABEL_ID["I-TERM"], IGNORE, IGNORE]


def test_word_predictions_roundtrip_and_truncation():
    word_ids = [None, 0, 0, 1, 2, 3, 3, None]
    subword = [0, 1, 2, 0, 1, 2, 0, 0]  # ikkinchi subword'lar e'tiborga olinmaydi
    assert word_predictions(word_ids, subword, 4) == ["B-TERM", "O", "B-TERM", "I-TERM"]
    # max_length bilan kesilgan oxirgi so'z -> O
    assert word_predictions([None, 0, 1, None], [0, 1, 1, 0], 3) == ["B-TERM", "B-TERM", "O"]
