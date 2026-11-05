import type { MatchType, Method, NormalizationStatus } from "./types";

export const METHOD_LABELS: Record<Method, string> = {
  dictionary_exact: "Lug'at: aniq moslik",
  dictionary_inflected: "Lug'at: qo'shimchali shakl",
  crf: "CRF modeli",
  crf_gazetteer: "CRF + lug'at belgisi",
  transformer: "XLM-R modeli",
};

export const MATCH_TYPE_LABELS: Record<MatchType, string> = {
  term: "asosiy termin",
  variant: "yozilish varianti",
  synonym: "sinonim",
};

export const NORMALIZATION_BADGES: Record<NormalizationStatus, { text: string; tone: string }> = {
  approved: { text: "Tasdiqlangan", tone: "ok" },
  needs_review: { text: "Tavsiya — tekshirish kerak", tone: "warn" },
  no_data: { text: "Meʼyoriy shakl yo'q", tone: "muted" },
};
