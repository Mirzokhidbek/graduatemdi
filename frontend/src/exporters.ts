import type { AnalyzeResponse, Match } from "./types";

export const CSV_COLUMNS = [
  "surface",
  "term",
  "lemma",
  "in_dictionary",
  "start",
  "end",
  "domain",
  "method",
  "match_type",
  "preferred_form",
  "normalization_status",
  "review_required",
  "ambiguous",
  "definition",
  "source",
] as const;

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function rowFor(match: Match): Record<(typeof CSV_COLUMNS)[number], unknown> {
  const first = match.candidates[0];
  const pick = <T>(get: (c: (typeof match.candidates)[number]) => T) =>
    match.ambiguous ? match.candidates.map(get).join(" | ") : first ? get(first) : null;
  return {
    surface: match.surface,
    term: match.ambiguous ? pick((c) => c.term) : match.term,
    lemma: match.lemma,
    in_dictionary: match.in_dictionary,
    start: match.start,
    end: match.end,
    domain: pick((c) => c.domain ?? ""),
    method: match.method,
    match_type: pick((c) => c.match_type),
    preferred_form: pick((c) => c.normalization.preferred_form ?? ""),
    normalization_status: pick((c) => c.normalization.status),
    review_required: match.review_required,
    ambiguous: match.ambiguous,
    definition: pick((c) => c.definition ?? ""),
    source: pick((c) => c.source ?? ""),
  };
}

/** CSV (Excel o'zbek harflarini to'g'ri ochishi uchun BOM bilan). */
export function toCsv(matches: Match[]): string {
  const lines = [CSV_COLUMNS.join(",")];
  for (const match of matches) {
    const row = rowFor(match);
    lines.push(CSV_COLUMNS.map((column) => csvCell(row[column])).join(","));
  }
  return "\uFEFF" + lines.join("\r\n") + "\r\n";
}

export function toJson(text: string, result: AnalyzeResponse): string {
  return JSON.stringify({ text, ...result }, null, 2) + "\n";
}

export function download(filename: string, content: string, type: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
