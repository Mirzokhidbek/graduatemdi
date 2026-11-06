import type { Span } from "./annotation";
import type {
  AnalyzeResponse,
  AnnotationDocument,
  CheckTermsResponse,
  DetectionMethod,
  DocumentSummary,
  Health,
  TermProfile,
  Thesaurus,
  JudgmentRow,
  SavedRecord,
} from "./types";

export class ApiError extends Error {}

export const UNREACHABLE_MESSAGE = "Backend serveriga ulanib bo'lmadi. U ishga tushirilganini tekshiring.";

/**
 * Xato javobidan foydalanuvchiga ko'rsatiladigan xabar.
 *
 * Bizning backend xatolarni doim ``{"detail": ...}`` JSON ko'rinishida qaytaradi.
 * JSON bo'lmagan 5xx javob odatda dev-proksidan keladi — backend o'chiq.
 */
export async function readError(response: Response): Promise<string> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    if (response.status >= 500) return UNREACHABLE_MESSAGE;
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (response.status === 422) return "So'rov noto'g'ri formatda.";
  if (response.status >= 500) return "Serverda xato yuz berdi. Keyinroq urinib ko'ring.";
  return `Server xatosi (${response.status}).`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch (exc) {
    if (exc instanceof DOMException && exc.name === "AbortError") throw exc;
    throw new ApiError(UNREACHABLE_MESSAGE);
  }
  if (!response.ok) throw new ApiError(await readError(response));
  return (await response.json()) as T;
}

export function analyze(
  text: string,
  signal?: AbortSignal,
  method: DetectionMethod = "dictionary",
): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, method }),
    signal,
  });
}

/** Terminlarni ISO 704 tamoyillari va imlo qoidalariga muvofiqlikka tekshirish. */
export function checkTerms(terms: string[], signal?: AbortSignal): Promise<CheckTermsResponse> {
  return request<CheckTermsResponse>("/api/check-terms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ terms }),
    signal,
  });
}

/** Matn maydonidagi qatorlardan terminlar ro'yxati: bo'sh qatorlar va takrorlar tashlanadi. */
export function parseTermLines(text: string, limit = 200): string[] {
  const seen = new Set<string>();
  const terms: string[] = [];
  for (const line of text.split(/\r?\n/)) {
    const term = line.trim();
    if (!term || seen.has(term)) continue;
    seen.add(term);
    terms.push(term);
    if (terms.length >= limit) break;
  }
  return terms;
}

/** Terminlar profili: lug'at, meʼyor tekshiruvi, tezaurus, ekvivalentlar. */
export async function termProfiles(terms: string[], signal?: AbortSignal): Promise<Map<string, TermProfile>> {
  const unique = [...new Set(terms.filter(Boolean))].slice(0, 200);
  if (!unique.length) return new Map();
  const body = await request<{ profiles: TermProfile[] }>("/api/term-profiles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ terms: unique }),
    signal,
  });
  return new Map(body.profiles.map((p) => [p.term, p]));
}

/** Moslik uchun profil kaliti: lug'atdagi termin, bo'lmasa taklif qilingan lug'at shakli. */
export function profileKey(match: { term: string | null; lemma: string | null; surface: string }): string {
  return match.term ?? match.lemma ?? match.surface;
}

export function thesaurus(): Promise<Thesaurus> {
  return request<Thesaurus>("/api/thesaurus");
}

/** Tezaurus daraxtining ildizlari: kichik terminlari bor, o'zi hech kimga tegishli bo'lmagan tushunchalar. */
export function thesaurusRoots(concepts: { label: string; broader: string[]; narrower: string[] }[]): string[] {
  return concepts
    .filter((c) => c.broader.length === 0 && c.narrower.length > 0)
    .map((c) => c.label)
    .sort((a, b) => a.localeCompare(b, "uz"));
}

export function health(): Promise<Health> {
  return request<Health>("/api/health");
}

// --- annotatsiya ish joyi -----------------------------------------------------


const q = (annotator: string) => `annotator=${encodeURIComponent(annotator)}`;

export function listDocuments(annotator: string): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>(`/api/annotate/documents?${q(annotator)}`);
}

export function getDocument(docId: string, annotator: string): Promise<AnnotationDocument> {
  return request<AnnotationDocument>(`/api/annotate/documents/${encodeURIComponent(docId)}?${q(annotator)}`);
}

export function saveParagraph(
  docId: string,
  recordId: string,
  annotator: string,
  body: { terms: Span[]; status: "draft" | "reviewed"; notes: string | null },
): Promise<SavedRecord> {
  return request<SavedRecord>(
    `/api/annotate/documents/${encodeURIComponent(docId)}/paragraphs/${encodeURIComponent(recordId)}?${q(annotator)}`,
    { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
  );
}

export function listJudgments(annotator: string): Promise<JudgmentRow[]> {
  return request<JudgmentRow[]>(`/api/judgments/${encodeURIComponent(annotator)}`);
}

export function saveJudgment(
  annotator: string,
  body: { candidate: string; judgment: JudgmentRow["judgment"]; notes: string | null },
): Promise<JudgmentRow> {
  return request<JudgmentRow>(`/api/judgments/${encodeURIComponent(annotator)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
