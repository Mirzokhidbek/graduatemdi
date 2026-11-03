import { describe, expect, it } from "vitest";
import { addSpan, defaultTerm, openSuggestions, snapToWords, toPieces } from "./annotation";

describe("snapToWords", () => {
  const text = "Fonemalar (tovushlar) soʻz ichida.";

  it("expands a partial selection to whole words", () => {
    expect(snapToWords(text, 2, 5)).toEqual({ start: 0, end: 9 });
  });

  it("drops brackets and spaces at the edges", () => {
    expect(snapToWords(text, 10, 21)).toEqual({ start: 11, end: 20 });
  });

  it("keeps the apostrophe inside a word", () => {
    expect(snapToWords(text, 22, 24)).toEqual({ start: 22, end: 26 });
  });

  it("counts code points, not UTF-16 units", () => {
    expect(snapToWords("😀 fonema", 2, 4)).toEqual({ start: 2, end: 8 });
  });

  it("returns null for punctuation only", () => {
    expect(snapToWords(text, 9, 11)).toBeNull();
  });
});

describe("defaultTerm", () => {
  it("lowercases and uses the official apostrophes", () => {
    expect(defaultTerm("Qo'shma  Gap")).toBe("qoʻshma gap");
    expect(defaultTerm("MA'NO")).toBe("maʼno");
  });
});

describe("spans and suggestions", () => {
  it("refuses overlapping spans", () => {
    const spans = [{ start: 0, end: 6, term: "fonema" }];
    expect(typeof addSpan(spans, { start: 3, end: 9, term: "x" })).toBe("string");
    expect(addSpan(spans, { start: 7, end: 9, term: "ot" })).toHaveLength(2);
  });

  it("merges suggestions from several sources and hides those under a span", () => {
    const merged = openSuggestions(
      [{ start: 0, end: 6, term: "fonema" }],
      [
        { start: 0, end: 6, term: "fonema", source: "dictionary" },
        { start: 10, end: 16, term: "tovush", source: "dictionary" },
        { start: 10, end: 16, term: "tovush", source: "ai" },
        { start: 4, end: 16, term: "undosh tovush", source: "ai" },
      ],
    );
    expect(merged).toEqual([{ start: 10, end: 16, term: "tovush", sources: ["dictionary", "ai"] }]);
  });

  it("splits text into pieces", () => {
    const pieces = toPieces("ab cd ef", [{ start: 0, end: 2, term: "ab" }], [{ start: 6, end: 8, term: null, sources: ["ai"] }]);
    expect(pieces.map((p) => [p.kind, p.text])).toEqual([
      ["span", "ab"],
      ["text", " cd "],
      ["suggestion", "ef"],
    ]);
  });
});
