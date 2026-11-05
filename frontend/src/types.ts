// Backend javoblari (backend/app/schemas.py bilan mos).

export type NormalizationStatus = "approved" | "needs_review" | "no_data";
export type MatchType = "term" | "variant" | "synonym";
export type Method = "dictionary_exact" | "dictionary_inflected";

export interface Normalization {
  preferred_form: string | null;
  status: NormalizationStatus;
  label: string;
  surface_matches_preferred: boolean | null;
}

export interface Candidate {
  term_id: string;
  term: string;
  matched_form: string;
  match_type: MatchType;
  domain: string | null;
  definition: string | null;
  status: "approved" | "needs_review";
  source: string | null;
  normalization: Normalization;
}

export interface Match {
  surface: string;
  base_surface: string;
  suffix: string;
  /** Unicode belgilari bo'yicha (UTF-16 emas). */
  start: number;
  end: number;
  term: string | null;
  method: Method;
  confidence: number | null;
  ambiguous: boolean;
  review_required: boolean;
  candidates: Candidate[];
}

export interface AnalyzeResponse {
  method: "dictionary_baseline";
  positions: "unicode_codepoints";
  text_length: number;
  terms_in_dictionary: number;
  matches: Match[];
  notes: string[];
}

export interface Health {
  status: "ok";
  terms_in_dictionary: number;
  max_text_chars: number;
}

// --- annotatsiya ish joyi -----------------------------------------------------

export interface DocumentSummary {
  doc_id: string;
  title: string;
  paragraphs: number;
  annotated: number;
  reviewed: number;
}

export interface SavedSpan {
  start: number;
  end: number;
  term: string;
  label: "TERM";
  surface: string;
}

export interface ParagraphData {
  id: string;
  text: string;
  saved: { terms: SavedSpan[]; status: "draft" | "reviewed"; notes: string | null } | null;
  suggestions: { start: number; end: number; term: string | null; source: "dictionary" | "ai" | "model" }[];
}

export interface AnnotationDocument {
  doc_id: string;
  title: string;
  annotator: string;
  paragraphs: ParagraphData[];
}

export interface SavedRecord {
  id: string;
  doc_id: string;
  text: string;
  terms: SavedSpan[];
  annotator: string | null;
  status: "draft" | "reviewed";
  notes: string | null;
}

export interface JudgmentRow {
  candidate: string;
  judgment: "1" | "0" | "?" | "";
  notes: string;
  frequency: string;
  example: string;
}

// --- meʼyor tekshiruvi (POST /api/check-terms) ---------------------------------

export type Severity = "ok" | "info" | "warning" | "error";

export interface Finding {
  rule: string;
  basis: string;
  severity: Severity;
  message: string;
  suggestion: string | null;
}

export interface CheckResult {
  term: string;
  severity: Severity;
  suggestion: string | null;
  findings: Finding[];
}

export interface CheckTermsResponse {
  results: CheckResult[];
  note: string;
}

// --- tezaurus (GET /api/thesaurus) ------------------------------------------------

export interface ThesaurusConcept {
  label: string;
  broader: string[];
  narrower: string[];
  alt_labels: string[];
}

export interface ThesaurusRelation {
  narrower: string;
  broader: string;
  sources: Record<string, number>;
  evidence: string[];
}

export interface Thesaurus {
  concepts: ThesaurusConcept[];
  relations: ThesaurusRelation[];
  related: { a: string; b: string; pmi: number; count: number }[];
  summary: { concepts: number; broader_relations: number; roots: number; related_pairs: number };
}
