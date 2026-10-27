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
