// Annotatsiya ish joyining sof (DOM'siz) mantig'i — vitest bilan tekshiriladi.
// Barcha pozitsiyalar Unicode belgilari bo'yicha (backend bilan bir xil), UTF-16 emas.

export interface Span {
  start: number;
  end: number;
  term: string;
}

export type SuggestionSource = "dictionary" | "ai" | "model";

export interface Suggestion {
  start: number;
  end: number;
  term: string | null;
  source: SuggestionSource;
}

/** Bir xil joydagi takliflar bitta bo'lib, manbalari birlashtiriladi. */
export interface MergedSuggestion {
  start: number;
  end: number;
  term: string | null;
  sources: SuggestionSource[];
}

const APOSTROPHES = new Set(["'", "ʻ", "ʼ", "‘", "’", "`", "´"]);

function isWordChar(ch: string | undefined): boolean {
  return ch !== undefined && /[\p{L}\p{N}]/u.test(ch);
}

/** So'z ichidagi apostrof (soʻz, maʼno): ikki tomonida harf bo'lsa. */
function isInnerApostrophe(chars: string[], index: number): boolean {
  return APOSTROPHES.has(chars[index]) && isWordChar(chars[index - 1]) && isWordChar(chars[index + 1]);
}

function partOfWord(chars: string[], index: number): boolean {
  return isWordChar(chars[index]) || isInnerApostrophe(chars, index);
}

/**
 * Sichqoncha bilan tanlangan oraliqni butun so'zlarga kengaytiradi va chetidagi
 * bo'shliq/tinish belgilarini olib tashlaydi (yo'riqnoma, 2-bo'lim). So'z yo'q bo'lsa null.
 */
export function snapToWords(text: string, start: number, end: number): { start: number; end: number } | null {
  const chars = Array.from(text);
  let s = Math.max(0, Math.min(start, end));
  let e = Math.min(chars.length, Math.max(start, end));
  while (s < e && !partOfWord(chars, s)) s++;
  while (e > s && !partOfWord(chars, e - 1)) e--;
  if (s >= e) return null;
  while (s > 0 && partOfWord(chars, s - 1)) s--;
  while (e < chars.length && partOfWord(chars, e)) e++;
  return { start: s, end: e };
}

export function sliceChars(text: string, start: number, end: number): string {
  return Array.from(text).slice(start, end).join("");
}

/**
 * Lug'at shakli taklifi: kichik harf, rasmiy apostroflar (oʻ, gʻ — ʻ; tutuq — ʼ).
 * Qo'shimchalarni annotator o'zi olib tashlaydi.
 */
export function defaultTerm(surface: string): string {
  return surface
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/([og])['‘’`´ʼ]/g, "$1ʻ")
    .replace(/(?<![og])['‘’`´ʻ](?=\p{L})/gu, "ʼ");
}

export function overlaps(a: { start: number; end: number }, b: { start: number; end: number }): boolean {
  return a.start < b.end && b.start < a.end;
}

/** Yangi spanni qo'shadi (tartiblangan holda); boshqa span bilan kesishsa xato matni qaytaradi. */
export function addSpan(spans: Span[], span: Span): Span[] | string {
  const clash = spans.find((other) => overlaps(other, span));
  if (clash) return "Bu joyda belgi bor: belgilar ustma-ust tushmasligi kerak. Avval eskisini olib tashlang.";
  if (!span.term.trim()) return "Lug'at shakli (termin) bo'sh bo'lmasligi kerak.";
  return [...spans, { ...span, term: span.term.trim() }].sort((a, b) => a.start - b.start || a.end - b.end);
}

export function removeSpan(spans: Span[], index: number): Span[] {
  return spans.filter((_, i) => i !== index);
}

/** Saqlangan belgilar bilan kesishmaydigan takliflar, bir joydagilari birlashtirilgan. */
export function openSuggestions(spans: Span[], suggestions: Suggestion[]): MergedSuggestion[] {
  const merged = new Map<string, MergedSuggestion>();
  for (const s of suggestions) {
    if (spans.some((span) => overlaps(span, s))) continue;
    const key = `${s.start}:${s.end}`;
    const existing = merged.get(key);
    if (existing) {
      if (!existing.sources.includes(s.source)) existing.sources.push(s.source);
      existing.term ??= s.term;
    } else {
      merged.set(key, { start: s.start, end: s.end, term: s.term, sources: [s.source] });
    }
  }
  // Kesishgan takliflardan (masalan lug'at "tovush" va AI "undosh tovush") faqat birinchisi ko'rinadi;
  // qolgani u qabul qilinsa yoki rad etilsa paydo bo'ladi.
  const ordered = [...merged.values()].sort((a, b) => a.start - b.start || b.end - a.end);
  const visible: MergedSuggestion[] = [];
  for (const s of ordered) if (!visible.some((v) => overlaps(v, s))) visible.push(s);
  return visible;
}

export type Piece =
  | { kind: "text"; start: number; text: string }
  | { kind: "span"; start: number; text: string; index: number }
  | { kind: "suggestion"; start: number; text: string; suggestion: MergedSuggestion };

/** Matnni oddiy matn, belgilar va takliflar bo'laklariga ajratadi (ikkalasi ustma-ust tushmaydi). */
export function toPieces(text: string, spans: Span[], suggestions: MergedSuggestion[]): Piece[] {
  const chars = Array.from(text);
  const marks = [
    ...spans.map((span, index) => ({ start: span.start, end: span.end, make: (t: string): Piece => ({ kind: "span", start: span.start, text: t, index }) })),
    ...suggestions.map((s) => ({ start: s.start, end: s.end, make: (t: string): Piece => ({ kind: "suggestion", start: s.start, text: t, suggestion: s }) })),
  ].sort((a, b) => a.start - b.start);
  const pieces: Piece[] = [];
  let position = 0;
  for (const mark of marks) {
    if (mark.start < position || mark.end > chars.length || mark.end <= mark.start) continue;
    if (mark.start > position) pieces.push({ kind: "text", start: position, text: chars.slice(position, mark.start).join("") });
    pieces.push(mark.make(chars.slice(mark.start, mark.end).join("")));
    position = mark.end;
  }
  if (position < chars.length) pieces.push({ kind: "text", start: position, text: chars.slice(position).join("") });
  return pieces;
}

export const SOURCE_LABELS: Record<SuggestionSource, string> = {
  dictionary: "lug'at",
  ai: "AI (tekshirilmagan)",
  model: "model",
};
