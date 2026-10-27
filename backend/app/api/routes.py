"""REST API endpointlari."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

from app.schemas import AnalyzeRequest, AnalyzeResponse, HealthOut, TermOut
from app.services.analyzer import analyze_text

router = APIRouter(prefix="/api")

NOTE_DICTIONARY_ONLY = (
    "Lug'atga asoslangan usul: bazada yo'q terminlar topilmaydi."
)
NOTE_NEEDS_REVIEW = (
    "Ayrim meʼyoriy shakllar manba bilan tasdiqlanmagan — bular faqat tavsiya, tekshirish kerak."
)
NOTE_AMBIGUOUS = "Ayrim shakllar bir nechta terminga mos keldi — kontekst bo'yicha tekshirish kerak."


@router.get("/health", response_model=HealthOut)
def health(request: Request) -> HealthOut:
    state = request.app.state
    return HealthOut(terms_in_dictionary=len(state.entries), max_text_chars=state.settings.max_text_chars)


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

    matches = analyze_text(payload.text, state.matcher)
    notes = [NOTE_DICTIONARY_ONLY]
    if any(c["normalization"]["status"] != "approved" for m in matches for c in m["candidates"]):
        notes.append(NOTE_NEEDS_REVIEW)
    if any(m["ambiguous"] for m in matches):
        notes.append(NOTE_AMBIGUOUS)

    return AnalyzeResponse(
        text_length=len(payload.text),
        terms_in_dictionary=len(state.entries),
        matches=matches,
        notes=notes,
    )
