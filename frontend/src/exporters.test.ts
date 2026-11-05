import { describe, expect, it } from "vitest";
import { CSV_COLUMNS, toCsv, toJson } from "./exporters";
import type { AnalyzeResponse, Candidate, Match } from "./types";

function candidate(overrides: Partial<Candidate> = {}): Candidate {
  return {
    term_id: "t1", term: "fonema", matched_form: "fonema", match_type: "term", domain: "fonetika",
    definition: "Ta'rif, vergul bilan", status: "needs_review", source: null,
    normalization: { preferred_form: "fonema", status: "needs_review", label: "Tavsiya", surface_matches_preferred: true },
    ...overrides,
  };
}

function match(overrides: Partial<Match> = {}): Match {
  return {
    surface: "Fonemalar", base_surface: "Fonema", suffix: "lar", start: 0, end: 9, term: "fonema",
    method: "dictionary_inflected", confidence: null, ambiguous: false, review_required: true,
    candidates: [candidate()], lemma: null, in_dictionary: true, related_terms: [], ...overrides,
  };
}

describe("toCsv", () => {
  it("sarlavha, BOM va CRLF bilan yozadi", () => {
    const csv = toCsv([match()]);
    expect(csv.startsWith("\uFEFF")).toBe(true);
    const [header, row] = csv.slice(1).split("\r\n");
    expect(header).toBe(CSV_COLUMNS.join(","));
    expect(row).toBe(
      'Fonemalar,fonema,,true,0,9,fonetika,dictionary_inflected,term,fonema,needs_review,true,false,"Ta\'rif, vergul bilan",',
    );
  });

  it("yangi (lug'atda yo'q) terminni lug'at shakli bilan yozadi", () => {
    const csv = toCsv([match({ surface: "paralingvistikada", term: null, candidates: [], lemma: "paralingvistika", in_dictionary: false })]);
    const row = csv.slice(1).split("\r\n")[1];
    expect(row.startsWith("paralingvistikada,,paralingvistika,false,")).toBe(true);
  });

  it("qo'shtirnoq va qator tashlashni ekranlaydi", () => {
    const csv = toCsv([match({ surface: 'a "b"\nc' })]);
    expect(csv).toContain('"a ""b""\nc"');
  });

  it("noaniq moslikda barcha nomzodlarni ko'rsatadi", () => {
    const csv = toCsv([
      match({
        term: null, ambiguous: true,
        candidates: [candidate({ term: "ot", domain: "morfologiya" }), candidate({ term: "ot", domain: "boshqa" })],
      }),
    ]);
    const row = csv.split("\r\n")[1];
    expect(row).toContain("ot | ot");
    expect(row).toContain("morfologiya | boshqa");
  });

  it("bo'sh natija faqat sarlavha", () => {
    expect(toCsv([])).toBe("\uFEFF" + CSV_COLUMNS.join(",") + "\r\n");
  });
});

describe("toJson", () => {
  it("matn va to'liq javobni saqlaydi", () => {
    const result: AnalyzeResponse = {
      method: "dictionary_baseline", positions: "unicode_codepoints", text_length: 9,
      terms_in_dictionary: 15, matches: [match()], notes: ["izoh"],
    };
    const parsed = JSON.parse(toJson("Fonemalar", result));
    expect(parsed.text).toBe("Fonemalar");
    expect(parsed.matches[0].start).toBe(0);
    expect(parsed.positions).toBe("unicode_codepoints");
  });
});
