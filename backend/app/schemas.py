"""API so'rov va javoblari uchun Pydantic modellari."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DetectionMethod = Literal["dictionary", "crf", "crf_gazetteer", "transformer"]


class AnalyzeRequest(BaseModel):
    text: str = Field(description="Tahlil qilinadigan matn (oʻzbek lotin yozuvi)")
    method: DetectionMethod = Field(default="dictionary", description="Aniqlash usuli (GET /api/health -> methods)")


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
    method: Literal["dictionary_exact", "dictionary_inflected", "crf", "crf_gazetteer", "transformer"]
    confidence: float | None = Field(description="Faqat model haqiqatan hisoblaganda; lug'at usulida null")
    ambiguous: bool
    review_required: bool
    candidates: list[CandidateOut]
    lemma: str | None = Field(description="Lug'at shakli; lug'atda yo'q termin uchun morfologik taklif")
    in_dictionary: bool = Field(description="Termin bazada bormi; false — model topgan yangi termin nomzodi")
    related_terms: list[str] = Field(description="Yangi termin ichidagi yoki u bilan kesishgan lug'at terminlari")


class AnalyzeResponse(BaseModel):
    method: Literal["dictionary_baseline", "crf", "crf_gazetteer", "transformer"] = "dictionary_baseline"
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


class MethodOut(BaseModel):
    id: DetectionMethod
    label: str
    description: str
    available: bool
    reason: str | None = Field(description="Mavjud bo'lmasa — sababi")
    test_f1: float | None = Field(description="Test exact F1 (reports/, kumush maʼlumot)")


class HealthOut(BaseModel):
    status: Literal["ok"] = "ok"
    terms_in_dictionary: int
    max_text_chars: int
    methods: list[MethodOut] = []


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


class CheckTermsRequest(BaseModel):
    terms: list[str] = Field(min_length=1, max_length=200, description="Tekshiriladigan terminlar (1–200 ta)")


class FindingOut(BaseModel):
    rule: str
    basis: str = Field(description="Qoida manbasi: ISO 704:2022, imlo qoidalari (1995) yoki lug'at shakli")
    severity: Literal["ok", "info", "warning", "error"]
    message: str
    suggestion: str | None


class CheckResultOut(BaseModel):
    term: str
    severity: Literal["ok", "info", "warning", "error"]
    suggestion: str | None = Field(description="Imlo va lug'at shakli tuzatishlari qo'llangan shakl")
    findings: list[FindingOut]


class CheckTermsResponse(BaseModel):
    results: list[CheckResultOut]
    note: str

