import type { Match } from "./types";

export interface Segment {
  text: string;
  /** Mos keluvchi ``matches`` indeksi; oddiy matn uchun null. */
  match: number | null;
}

/** Matn uzunligi Unicode belgilari bo'yicha (backend bilan bir xil). */
export function codepointLength(text: string): number {
  return Array.from(text).length;
}

/**
 * Matnni belgilangan va oddiy bo'laklarga ajratadi.
 *
 * Backend pozitsiyalari Unicode belgilari bo'yicha, JavaScript satrlari esa
 * UTF-16 bo'yicha indekslanadi; shuning uchun matn avval belgilarga ajratiladi.
 * Spanlar ustma-ust tushmaydi deb hisoblanadi (backend kafolatlaydi);
 * noto'g'ri yoki kesishgan span e'tiborsiz qoldiriladi.
 */
export function toSegments(text: string, matches: Match[]): Segment[] {
  const chars = Array.from(text);
  const order = matches
    .map((match, index) => ({ match, index }))
    .sort((a, b) => a.match.start - b.match.start);

  const segments: Segment[] = [];
  let position = 0;
  for (const { match, index } of order) {
    if (match.start < position || match.end <= match.start || match.end > chars.length) continue;
    if (match.start > position) segments.push({ text: chars.slice(position, match.start).join(""), match: null });
    segments.push({ text: chars.slice(match.start, match.end).join(""), match: index });
    position = match.end;
  }
  if (position < chars.length) segments.push({ text: chars.slice(position).join(""), match: null });
  return segments;
}
