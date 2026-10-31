"""O'qitilgan CRF modelini ilovaga ulash (annotatsiya takliflari uchun).

Model ixtiyoriy: fayl yoki ``python-crfsuite`` bo'lmasa, ilova modelsiz ishlaydi.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger("uzterm")

SpanPredictor = Callable[[str], list[tuple[int, int, str | None]]]


def load_predictor(model_path: Path, raw_dir: Path) -> SpanPredictor | None:
    if not model_path.is_file():
        return None
    try:
        from app.models.crf import TermCrf, build_lemmatizer
    except ImportError:
        logger.warning("python-crfsuite o'rnatilmagan: model takliflari o'chiq")
        return None
    lemmatizer = build_lemmatizer(p.read_text(encoding="utf-8") for p in sorted(raw_dir.glob("*.txt")))
    model = TermCrf(lemmatizer).load(model_path)

    def predict(text: str) -> list[tuple[int, int, str | None]]:
        return [(span.start, span.end, span.term) for span in model.predict(text)]

    return predict
