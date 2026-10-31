"""Annotatsiya va nomzodlarni baholash endpointlari (web interfeysdagi ish joyi)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.annotation.workspace import NotFound, Workspace, WorkspaceError
from app.evaluation.judgments import JudgmentError
from app.schemas import (
    AnnotationDocumentOut,
    AnnotationDocumentSummary,
    JudgmentIn,
    JudgmentRow,
    SaveParagraphIn,
    SavedRecordOut,
)

router = APIRouter(prefix="/api")

ANNOTATOR = Query(description="Annotator kodi, masalan A1 (shaxsiy maʼlumot emas)")


def _workspace(request: Request, writing: bool = False) -> Workspace:
    state = request.app.state
    if writing and not state.settings.annotation_enabled:
        raise HTTPException(status_code=403, detail="Annotatsiyani saqlash o'chirilgan (UZTERM_ANNOTATION=off).")
    return state.workspace


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFound):
        return HTTPException(status_code=404, detail="Topilmadi.")
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/annotate/documents", response_model=list[AnnotationDocumentSummary])
def documents(request: Request, annotator: str | None = Query(default=None)) -> list[AnnotationDocumentSummary]:
    try:
        return [AnnotationDocumentSummary(**doc) for doc in _workspace(request).documents(annotator)]
    except (WorkspaceError, NotFound) as exc:
        raise _handle(exc) from None


@router.get("/annotate/documents/{doc_id}", response_model=AnnotationDocumentOut)
def document(doc_id: str, request: Request, annotator: str = ANNOTATOR) -> AnnotationDocumentOut:
    try:
        return AnnotationDocumentOut(**_workspace(request).document(doc_id, annotator))
    except (WorkspaceError, NotFound) as exc:
        raise _handle(exc) from None


@router.put("/annotate/documents/{doc_id}/paragraphs/{record_id}", response_model=SavedRecordOut)
def save_paragraph(
    doc_id: str, record_id: str, payload: SaveParagraphIn, request: Request, annotator: str = ANNOTATOR
) -> SavedRecordOut:
    workspace = _workspace(request, writing=True)
    try:
        saved = workspace.save(
            doc_id,
            record_id,
            annotator,
            [term.model_dump() for term in payload.terms],
            payload.status,
            payload.notes,
        )
    except (WorkspaceError, NotFound) as exc:
        raise _handle(exc) from None
    return SavedRecordOut(**saved)


@router.get("/judgments/{annotator}", response_model=list[JudgmentRow])
def judgments(annotator: str, request: Request) -> list[JudgmentRow]:
    try:
        return [JudgmentRow(**row) for row in _workspace(request).judgment_rows(annotator)]
    except (WorkspaceError, NotFound, JudgmentError) as exc:
        raise _handle(exc) from None


@router.put("/judgments/{annotator}", response_model=JudgmentRow)
def save_judgment(annotator: str, payload: JudgmentIn, request: Request) -> JudgmentRow:
    workspace = _workspace(request, writing=True)
    try:
        return JudgmentRow(**workspace.save_judgment(annotator, payload.candidate, payload.judgment, payload.notes))
    except (WorkspaceError, NotFound, JudgmentError) as exc:
        raise _handle(exc) from None
