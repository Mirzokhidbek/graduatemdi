import { describe, expect, it } from "vitest";
import { codepointLength, toSegments } from "./segments";
import type { Match } from "./types";

function match(start: number, end: number): Match {
  return {
    surface: "", base_surface: "", suffix: "", start, end, term: "t", method: "dictionary_exact",
    confidence: null, ambiguous: false, review_required: true, candidates: [],
  };
}

describe("toSegments", () => {
  it("matnni belgilangan va oddiy bo'laklarga ajratadi", () => {
    expect(toSegments("Fonema va morfema.", [match(0, 6), match(10, 17)])).toEqual([
      { text: "Fonema", match: 0 },
      { text: " va ", match: null },
      { text: "morfema", match: 1 },
      { text: ".", match: null },
    ]);
  });

  it("pozitsiyalarni Unicode belgilari bo'yicha hisoblaydi (UTF-16 emas)", () => {
    const text = "😀 fonema";
    expect(text.slice(2, 8)).not.toBe("fonema"); // oddiy slice noto'g'ri bo'lardi
    expect(toSegments(text, [match(2, 8)])).toEqual([
      { text: "😀 ", match: null },
      { text: "fonema", match: 0 },
    ]);
  });

  it("tartibsiz kelgan mosliklarni saralaydi va asl indeksni saqlaydi", () => {
    const segments = toSegments("ab cd", [match(3, 5), match(0, 2)]);
    expect(segments.map((s) => s.match)).toEqual([1, null, 0]);
  });

  it("noto'g'ri va kesishgan spanlarni o'tkazib yuboradi", () => {
    const segments = toSegments("abcdef", [match(0, 3), match(2, 4), match(5, 99), match(4, 4)]);
    expect(segments).toEqual([
      { text: "abc", match: 0 },
      { text: "def", match: null },
    ]);
  });

  it("bo'sh matn va mosliksiz holat", () => {
    expect(toSegments("", [])).toEqual([]);
    expect(toSegments("matn", [])).toEqual([{ text: "matn", match: null }]);
  });

  it("codepointLength backend bilan bir xil sanaydi", () => {
    expect(codepointLength("oʻzak")).toBe(5);
    expect(codepointLength("😀a")).toBe(2);
  });
});
