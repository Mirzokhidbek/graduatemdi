import type { AnalyzeResponse, Health } from "./types";

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

export function analyze(text: string, signal?: AbortSignal): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
}

export function health(): Promise<Health> {
  return request<Health>("/api/health");
}
