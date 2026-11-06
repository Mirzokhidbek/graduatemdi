"""Termin aniqlash usullari reyestri: lug'at, CRF, CRF + gazetteer, XLM-R transformer.

Har bir model **birinchi so'rovda** yuklanadi va keyin xotirada saqlanadi. Model fayli yoki
kutubxona (``python-crfsuite``, ``torch``/``transformers``) bo'lmasa, usul "mavjud emas" deb
ko'rsatiladi va sababi qaytariladi — server baribir ishlaydi.

Test natijalari (F1) ``reports/`` dagi tajriba hisobotlaridan olinadi va interfeysda usul
yonida ko'rsatiladi. Ular AI annotatsiyasi (kumush maʼlumot) bo'yicha.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.database.term_store import TermEntry
from app.evaluation.metrics import Span
from app.nlp.dictionary_matcher import DictionaryMatcher
from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.tokenize import tokenize

logger = logging.getLogger("uzterm")

DICTIONARY = "dictionary"
CRF = "crf"
CRF_GAZETTEER = "crf_gazetteer"
TRANSFORMER = "transformer"
METHODS = (DICTIONARY, CRF, CRF_GAZETTEER, TRANSFORMER)

LABELS = {
    DICTIONARY: "Lug'at",
    CRF: "CRF",
    CRF_GAZETTEER: "CRF + lug'at belgisi",
    TRANSFORMER: "XLM-R (transformer)",
}
DESCRIPTIONS = {
    DICTIONARY: "Faqat bazadagi terminlar; yangi terminlarni topmaydi.",
    CRF: "Statistik model; yangi terminlarni ham topadi.",
    CRF_GAZETTEER: "CRF lug'at belgisi bilan: aniqroq, lekin yangi terminlarni kam topadi.",
    TRANSFORMER: "Ko'p tilli neyron model: eng yuqori natija, yangi terminlarni ham topadi (sekinroq).",
}


class DetectorUnavailable(RuntimeError):
    """Usul tanlangan, lekin modeli yoki kutubxonasi yo'q."""


@dataclass(frozen=True)
class MethodInfo:
    id: str
    label: str
    description: str
    available: bool
    reason: str | None
    test_f1: float | None

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _report_f1(reports_dir: Path) -> dict[str, float]:
    """``reports/experiment-*.json`` dagi test exact F1 qiymatlari."""
    scores: dict[str, float] = {}
    for name, keys in (
        ("experiment-silver.json", {"dictionary_train": DICTIONARY, CRF: CRF, CRF_GAZETTEER: CRF_GAZETTEER}),
        ("experiment-transformer.json", {TRANSFORMER: TRANSFORMER}),
    ):
        path = reports_dir / name
        if not path.is_file():
            continue
        try:
            test = json.loads(path.read_text(encoding="utf-8")).get("test", {})
        except (OSError, ValueError):
            continue
        for key, method in keys.items():
            f1 = test.get(key, {}).get("exact", {}).get("f1")
            if f1 is not None:
                scores[method] = f1
    return scores


class DetectorRegistry:
    def __init__(
        self,
        matcher: DictionaryMatcher,
        entries: list[TermEntry],
        models_dir: Path,
        raw_dir: Path,
        reports_dir: Path,
    ) -> None:
        self.matcher = matcher
        self.entries = entries
        self.models_dir = models_dir
        self.raw_dir = raw_dir
        self.reports_dir = reports_dir
        self._loaded: dict[str, Callable[[str], list[Span]]] = {}
        self._lemmatizer: CorpusLemmatizer | None = None
        self._normalizer = None
        self._lock = threading.Lock()

    # --- mavjudlik ----------------------------------------------------------------

    def _paths(self) -> dict[str, Path]:
        return {
            CRF: self.models_dir / "crf.crfsuite",
            CRF_GAZETTEER: self.models_dir / "crf-gazetteer.crfsuite",
            TRANSFORMER: self.models_dir / "transformer",
        }

    def _reason(self, method: str) -> str | None:
        if method == DICTIONARY:
            return None
        path = self._paths()[method]
        if method in (CRF, CRF_GAZETTEER):
            if not _has_module("pycrfsuite"):
                return "python-crfsuite o'rnatilmagan (pip install -r requirements.txt)"
            if not path.is_file():
                return f"model fayli yo'q: {path.name} (python -m app.models.experiment)"
            return None
        if not _has_module("torch") or not _has_module("transformers"):
            return "torch va transformers o'rnatilmagan (pip install -r requirements-transformer.txt)"
        if not (path / "uzterm.json").is_file():
            return "model yo'q: models/transformer/ (Colab'da o'qitib, yuklab oling)"
        return None

    def methods(self) -> list[MethodInfo]:
        scores = _report_f1(self.reports_dir)
        result = []
        for method in METHODS:
            reason = self._reason(method)
            result.append(MethodInfo(method, LABELS[method], DESCRIPTIONS[method], reason is None, reason,
                                     scores.get(method)))
        return result

    # --- yuklash --------------------------------------------------------------------

    def lemmatizer(self) -> CorpusLemmatizer:
        if self._lemmatizer is None:
            texts = [p.read_text(encoding="utf-8") for p in sorted(self.raw_dir.glob("*.txt"))]
            self._lemmatizer = CorpusLemmatizer(t.norm for text in texts for t in tokenize(text))
        return self._lemmatizer

    def normalizer(self):
        """Lug'atda yo'q (yangi) terminlar uchun lug'at shakli: ``fonemalarning -> fonema``."""
        if self._normalizer is None:
            from app.services.term_normalizer import TermNormalizer

            texts = [p.read_text(encoding="utf-8") for p in sorted(self.raw_dir.glob("*.txt"))]
            self._normalizer = TermNormalizer(self.entries, (t.norm for text in texts for t in tokenize(text)))
        return self._normalizer

    def _load(self, method: str) -> Callable[[str], list[Span]]:
        path = self._paths()[method]
        if method in (CRF, CRF_GAZETTEER):
            from app.models.crf import TermCrf

            gazetteer = self.matcher if method == CRF_GAZETTEER else None
            return TermCrf(self.lemmatizer(), gazetteer).load(path).predict

        from app.models.transformer import TermTransformer, best_device

        model = TermTransformer.load(path, self.lemmatizer())
        try:
            model.model.to(best_device())
        except Exception:  # noqa: BLE001 — qurilmaga o'tkazib bo'lmasa, CPU'da qoladi
            logger.warning("Transformer CPU'da ishlaydi")
        return model.predict

    def predictor(self, method: str) -> Callable[[str], list[Span]]:
        if method not in METHODS or method == DICTIONARY:
            raise ValueError(f"nomaʼlum usul: {method}")
        reason = self._reason(method)
        if reason:
            raise DetectorUnavailable(f"{LABELS[method]} mavjud emas: {reason}")
        with self._lock:
            if method not in self._loaded:
                logger.info("Model yuklanmoqda: %s", method)
                try:
                    self._loaded[method] = self._load(method)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Modelni yuklab bo'lmadi: %s", method)
                    raise DetectorUnavailable(f"{LABELS[method]} modelini yuklab bo'lmadi") from exc
            return self._loaded[method]
