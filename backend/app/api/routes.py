"""REST API endpointlari."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CheckTermsRequest,
    CheckTermsResponse,
    HealthOut,
    TermOut,
)
from app.services.analyzer import analyze_text, analyze_with_model
from app.services.detectors import DICTIONARY, LABELS, DetectorUnavailable

router = APIRouter(prefix="/api")

NOTE_DICTIONARY_ONLY = (
    "Lug'atga asoslangan usul: bazada yo'q terminlar topilmaydi."
)
NOTE_NEEDS_REVIEW = (
    "Ayrim meʼyoriy shakllar manba bilan tasdiqlanmagan — bular faqat tavsiya, tekshirish kerak."
)
NOTE_MODEL = (
    "{label} modeli: terminlarni kontekst bo'yicha aniqlaydi, shu jumladan lug'atda yo'qlarini ham. "
    "Natijalar AI annotatsiyasida o'qitilgan modelga tegishli — xato bo'lishi mumkin."
)
NOTE_NEW_TERMS = (
    "\"Yangi\" deb belgilangan terminlar lug'atda yo'q: lug'at shakli avtomatik taklif qilingan, "
    "termin ekanini va shaklini mutaxassis tekshirishi kerak."
)
NOTE_AMBIGUOUS = "Ayrim shakllar bir nechta terminga mos keldi — kontekst bo'yicha tekshirish kerak."


@router.get("/health", response_model=HealthOut)
def health(request: Request) -> HealthOut:
    state = request.app.state
    return HealthOut(
        terms_in_dictionary=len(state.entries),
        max_text_chars=state.settings.max_text_chars,
        methods=[m.to_dict() for m in state.detectors.methods()],
    )


@router.get("/terms", response_model=list[TermOut])
def terms(request: Request) -> list[TermOut]:
    return [TermOut(**asdict(entry)) for entry in request.app.state.entries]


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    state = request.app.state
    limit = state.settings.max_text_chars
    if len(payload.text) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Matn juda uzun: {len(payload.text)} belgi. Eng ko'pi {limit} belgi.",
        )

    if payload.method == DICTIONARY:
        matches = analyze_text(payload.text, state.matcher)
        notes = [NOTE_DICTIONARY_ONLY]
    else:
        detectors = state.detectors
        try:
            predict = detectors.predictor(payload.method)
        except DetectorUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
        normalizer = detectors.normalizer()
        matches = analyze_with_model(
            payload.text, predict(payload.text), state.matcher, payload.method,
            lambda surface: normalizer.normalize(surface).lemma,
        )
        notes = [NOTE_MODEL.format(label=LABELS[payload.method])]
        if any(not m["in_dictionary"] for m in matches):
            notes.append(NOTE_NEW_TERMS)
    if any(c["normalization"]["status"] != "approved" for m in matches for c in m["candidates"]):
        notes.append(NOTE_NEEDS_REVIEW)
    if any(m["ambiguous"] for m in matches):
        notes.append(NOTE_AMBIGUOUS)

    return AnalyzeResponse(
        method="dictionary_baseline" if payload.method == DICTIONARY else payload.method,
        text_length=len(payload.text),
        terms_in_dictionary=len(state.entries),
        matches=matches,
        notes=notes,
    )


NOTE_CHECK = (
    "Tekshiruv qoidaviy va tavsiya xarakterida: ISO 704 tamoyillari va oʻzbek imlo qoidalari (1995) "
    "bo'yicha ekspert eʼtiborini talab qiladigan joylar ko'rsatiladi."
)
MAX_TERM_CHARS = 200


def _checker(state):
    """Tekshiruvchi birinchi so'rovda quriladi (korpus lug'ati bilan, bo'lsa)."""
    checker = getattr(state, "checker", None)
    if checker is None:
        from app.nlp.tokenize import tokenize
        from app.norms.checker import TermChecker

        raw = state.settings.data_dir / "raw"
        vocabulary = [
            t.norm for p in sorted(raw.glob("*.txt")) for t in tokenize(p.read_text(encoding="utf-8"))
        ] if raw.is_dir() else []
        checker = state.checker = TermChecker(state.entries, vocabulary)
    return checker


@router.post("/check-terms", response_model=CheckTermsResponse)
def check_terms(payload: CheckTermsRequest, request: Request) -> CheckTermsResponse:
    too_long = [t for t in payload.terms if len(t) > MAX_TERM_CHARS]
    if too_long:
        raise HTTPException(status_code=413, detail=f"Termin juda uzun (eng ko'pi {MAX_TERM_CHARS} belgi).")
    checker = _checker(request.app.state)
    return CheckTermsResponse(results=[checker.check(t).to_dict() for t in payload.terms], note=NOTE_CHECK)


@router.get("/thesaurus")
def thesaurus(request: Request) -> dict:
    """Avtomatik qurilgan tezaurus (``python -m app.ontology.thesaurus`` natijasi, SKOS tuzilmasi)."""
    import json

    path = request.app.state.settings.data_dir.parent / "reports" / "thesaurus.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Tezaurus hali qurilmagan: python -m app.ontology.thesaurus")
    return json.loads(path.read_text(encoding="utf-8"))

