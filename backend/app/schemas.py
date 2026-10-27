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
