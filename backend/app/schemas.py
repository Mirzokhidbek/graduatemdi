"""API so'rov va javoblari uchun Pydantic modellari."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(description="Tahlil qilinadigan matn (oʻzbek lotin yozuvi)")


class NormalizationOut(BaseModel):
    preferred_form: str | None
    status: Literal["approved", "needs_review", "no_data"]
    label: str
    surface_matches_preferred: bool | None


class CandidateOut(BaseModel):
    term_id: str
    term: str
    matched_form: str
    match_type: Literal["term", "variant", "synonym"]
    domain: str | None
    definition: str | None
    status: Literal["approved", "needs_review"]
    source: str | None
    normalization: NormalizationOut


class MatchOut(BaseModel):
    surface: str
    base_surface: str
    suffix: str
    start: int = Field(description="Boshlanish, Unicode belgilari bo'yicha (Python indeksi)")
    end: int = Field(description="Tugash (eksklyuziv), Unicode belgilari bo'yicha")
    term: str | None = Field(description="Asosiy termin; bir nechta yozuvga mos kelsa null")
    method: Literal["dictionary_exact", "dictionary_inflected"]
    confidence: float | None = Field(description="Faqat model haqiqatan hisoblaganda; lug'at usulida null")
    ambiguous: bool
    review_required: bool
    candidates: list[CandidateOut]


class AnalyzeResponse(BaseModel):
    method: Literal["dictionary_baseline"] = "dictionary_baseline"
    positions: Literal["unicode_codepoints"] = "unicode_codepoints"
    text_length: int
    terms_in_dictionary: int
    matches: list[MatchOut]
    notes: list[str]


class TermOut(BaseModel):
    id: str
    term: str
    definition: str | None
    domain: str | None
    variants: list[str]
    synonyms: list[str]
    preferred_form: str | None
    status: Literal["approved", "needs_review"]
    source: str | None


class HealthOut(BaseModel):
    status: Literal["ok"] = "ok"
    terms_in_dictionary: int
    max_text_chars: int


# --- annotatsiya ish joyi -----------------------------------------------------


class AnnotationDocumentSummary(BaseModel):
    doc_id: str
    title: str
    paragraphs: int
    annotated: int = Field(description="Shu annotator saqlagan paragraflar")
    reviewed: int = Field(description="Ulardan 'reviewed' holatidagilari")


class SpanIn(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    term: str = Field(min_length=1, max_length=200)
    label: Literal["TERM"] = "TERM"


class SpanOut(SpanIn):
    surface: str


class SuggestionOut(BaseModel):
    start: int
    end: int
    term: str | None
    source: Literal["dictionary", "ai", "model"]


class SavedParagraph(BaseModel):
    terms: list[SpanOut]
    status: Literal["draft", "reviewed"]
    notes: str | None


class ParagraphOut(BaseModel):
    id: str
    text: str
    saved: SavedParagraph | None
    suggestions: list[SuggestionOut]


class AnnotationDocumentOut(BaseModel):
    doc_id: str
    title: str
    annotator: str
    paragraphs: list[ParagraphOut]


class SaveParagraphIn(BaseModel):
    terms: list[SpanIn] = Field(max_length=500)
    status: Literal["draft", "reviewed"] = "draft"
    notes: str | None = Field(default=None, max_length=2000)


class SavedRecordOut(BaseModel):
    id: str
    doc_id: str
    text: str
    terms: list[SpanOut]
    annotator: str | None = None
    status: Literal["draft", "reviewed"]
    notes: str | None = None


class JudgmentRow(BaseModel):
    candidate: str
    judgment: Literal["1", "0", "?", ""]
    notes: str
    frequency: str
    example: str


class JudgmentIn(BaseModel):
    candidate: str = Field(min_length=1, max_length=200)
    judgment: Literal["1", "0", "?", ""]
    notes: str | None = Field(default=None, max_length=500)
