import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addSpan,
  defaultTerm,
  openSuggestions,
  removeSpan,
  sliceChars,
  snapToWords,
  SOURCE_LABELS,
  toPieces,
  type MergedSuggestion,
  type Span,
} from "../annotation";
import { ApiError, getDocument, listDocuments, saveParagraph } from "../api";
import { codepointLength } from "../segments";
import type { AnnotationDocument, DocumentSummary } from "../types";

interface Props {
  annotator: string;
}

interface Draft {
  spans: Span[];
  reviewed: boolean;
  notes: string;
  dirty: boolean;
}

interface Pending {
  start: number;
  end: number;
  term: string;
}

/** Tanlangan nuqtaning paragrafdagi pozitsiyasi (Unicode belgilari bo'yicha). */
function pointOffset(node: Node | null, offset: number): number | null {
  if (!node) return null;
  const element = node.nodeType === Node.TEXT_NODE ? node.parentElement : (node as Element);
  const holder = element?.closest<HTMLElement>("[data-start]");
  if (!holder) return null;
  const base = Number(holder.dataset.start);
  if (node.nodeType !== Node.TEXT_NODE) return base;
  return base + codepointLength((node.textContent ?? "").slice(0, offset));
}

function draftFrom(paragraph: AnnotationDocument["paragraphs"][number]): Draft {
  return {
    spans: (paragraph.saved?.terms ?? []).map(({ start, end, term }) => ({ start, end, term })),
    reviewed: paragraph.saved?.status === "reviewed",
    notes: paragraph.saved?.notes ?? "",
    dirty: false,
  };
}

export function AnnotateView({ annotator }: Props) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [docId, setDocId] = useState<string | null>(null);
  const [doc, setDoc] = useState<AnnotationDocument | null>(null);
  const [index, setIndex] = useState(0);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [rejected, setRejected] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<Pending | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  // test to'plami belgilanayotganda takliflarni o'chirish tavsiya etiladi (annotator AI/lug'atga "ergashib" qolmasin)
  const [showSuggestions, setShowSuggestions] = useState(() => {
    try {
      return localStorage.getItem("uzterm-suggestions") !== "off";
    } catch {
      return true;
    }
  });
  const textRef = useRef<HTMLDivElement>(null);

  const refreshList = useCallback(() => {
    listDocuments(annotator)
      .then(setDocuments)
      .catch((exc) => setError(exc instanceof ApiError ? exc.message : "Hujjatlar ro'yxatini yuklab bo'lmadi."));
  }, [annotator]);

  useEffect(refreshList, [refreshList]);

  useEffect(() => {
    if (!docId) return;
    setDoc(null);
    getDocument(docId, annotator)
      .then((loaded) => {
        setDoc(loaded);
        // birinchi saqlanmagan paragrafdan davom etamiz
        const next = loaded.paragraphs.findIndex((p) => !p.saved);
        setIndex(next === -1 ? 0 : next);
      })
      .catch((exc) => setError(exc instanceof ApiError ? exc.message : "Hujjatni yuklab bo'lmadi."));
  }, [docId, annotator]);

  const paragraph = doc?.paragraphs[index] ?? null;

  useEffect(() => {
    if (!paragraph) return;
    setDraft(draftFrom(paragraph));
    setRejected(new Set());
    setPending(null);
    setSelectedSpan(null);
    setError(null);
  }, [paragraph]);

  const suggestions = useMemo<MergedSuggestion[]>(() => {
    if (!paragraph || !draft || !showSuggestions) return [];
    const rest = paragraph.suggestions.filter((s) => !rejected.has(`${s.start}:${s.end}`));
    return openSuggestions(draft.spans, rest);
  }, [paragraph, draft, rejected, showSuggestions]);

  if (!documents.length && !error) return <p className="hint">Hujjatlar yuklanmoqda…</p>;

  function update(change: Partial<Draft>) {
    setDraft((current) => (current ? { ...current, ...change, dirty: true } : current));
  }

  function tryAdd(span: Span) {
    if (!draft) return;
    const result = addSpan(draft.spans, span);
    if (typeof result === "string") {
      setError(result);
      return;
    }
    setError(null);
    update({ spans: result });
  }

  function accept(s: MergedSuggestion) {
    if (!paragraph) return;
    tryAdd({ start: s.start, end: s.end, term: s.term ?? defaultTerm(sliceChars(paragraph.text, s.start, s.end)) });
  }

  function acceptAll() {
    if (!paragraph || !draft) return;
    let spans = draft.spans;
    for (const s of suggestions) {
      const next = addSpan(spans, {
        start: s.start,
        end: s.end,
        term: s.term ?? defaultTerm(sliceChars(paragraph.text, s.start, s.end)),
      });
      if (typeof next !== "string") spans = next;
    }
    update({ spans });
  }

  function reject(s: MergedSuggestion) {
    setRejected((current) => new Set(current).add(`${s.start}:${s.end}`));
  }

  function onMouseUp() {
    if (!paragraph) return;
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !textRef.current) return;
    if (!textRef.current.contains(selection.anchorNode) || !textRef.current.contains(selection.focusNode)) return;
    const a = pointOffset(selection.anchorNode, selection.anchorOffset);
    const b = pointOffset(selection.focusNode, selection.focusOffset);
    if (a === null || b === null) return;
    const snapped = snapToWords(paragraph.text, a, b);
    selection.removeAllRanges();
    if (!snapped) return;
    setPending({ ...snapped, term: defaultTerm(sliceChars(paragraph.text, snapped.start, snapped.end)) });
  }

  async function save(goNext: boolean) {
    if (!doc || !paragraph || !draft) return;
    setSaving(true);
    try {
      const saved = await saveParagraph(doc.doc_id, paragraph.id, annotator, {
        terms: draft.spans,
        status: draft.reviewed ? "reviewed" : "draft",
        notes: draft.notes.trim() || null,
      });
      const paragraphs = doc.paragraphs.map((p) =>
        p.id === saved.id ? { ...p, saved: { terms: saved.terms, status: saved.status, notes: saved.notes } } : p,
      );
      setDoc({ ...doc, paragraphs });
      setDraft((current) => (current ? { ...current, dirty: false } : current));
      setError(null);
      refreshList();
      if (goNext && index < doc.paragraphs.length - 1) setIndex(index + 1);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Saqlab bo'lmadi.");
    } finally {
      setSaving(false);
    }
  }

  function go(to: number) {
    if (draft?.dirty && !window.confirm("Saqlanmagan o'zgarishlar bor. Ular yo'qolsinmi?")) return;
    setIndex(to);
  }

  const totals = documents.reduce(
    (sum, d) => ({ paragraphs: sum.paragraphs + d.paragraphs, annotated: sum.annotated + d.annotated, reviewed: sum.reviewed + d.reviewed }),
    { paragraphs: 0, annotated: 0, reviewed: 0 },
  );

  return (
    <div className="annotate">
      <aside className="doc-list" aria-label="Hujjatlar">
        <p className="hint">
          {annotator}: {totals.annotated} / {totals.paragraphs} paragraf belgilangan, {totals.reviewed} tasi tekshirilgan
        </p>
        <ul>
          {documents.map((d) => (
            <li key={d.doc_id}>
              <button
                type="button"
                className={d.doc_id === docId ? "doc doc-active" : "doc"}
                onClick={() => {
                  if (draft?.dirty && !window.confirm("Saqlanmagan o'zgarishlar bor. Ular yo'qolsinmi?")) return;
                  setDocId(d.doc_id);
                }}
              >
                <span>{d.title.replace(/^Vikipediya: /, "")}</span>
                <span className={d.annotated === d.paragraphs ? "badge badge-ok" : "badge badge-muted"}>
                  {d.annotated}/{d.paragraphs}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="annotate-main">
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {!docId && <p className="empty">Chapdan hujjatni tanlang.</p>}
        {docId && !doc && !error && <p className="hint">Yuklanmoqda…</p>}
        {doc && paragraph && draft && (
          <>
            <div className="results-header">
              <h2>
                {doc.title} · {index + 1} / {doc.paragraphs.length}-paragraf
              </h2>
              <div className="toolbar">
                <button type="button" className="secondary" disabled={index === 0} onClick={() => go(index - 1)}>
                  ← Oldingi
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={index === doc.paragraphs.length - 1}
                  onClick={() => go(index + 1)}
                >
                  Keyingi →
                </button>
              </div>
            </div>
            <p className="hint">
              Terminni sichqoncha bilan belgilang (so'z chegarasiga avtomatik kengayadi). Punktir chiziqli joylar —
              takliflar: bosib qabul qiling yoki × bilan rad eting. Takliflar faqat yordam, ular avtomatik saqlanmaydi.
              Yo'riqnoma: <span className="mono">docs/data-annotation-guide.md</span>.
            </p>

            <div className="highlighted annotate-text" ref={textRef} onMouseUp={onMouseUp}>
              {toPieces(paragraph.text, draft.spans, suggestions).map((piece) => {
                if (piece.kind === "text")
                  return (
                    <span key={`t${piece.start}`} data-start={piece.start}>
                      {piece.text}
                    </span>
                  );
                if (piece.kind === "span")
                  return (
                    <span
                      key={`s${piece.start}`}
                      data-start={piece.start}
                      className={piece.index === selectedSpan ? "ann ann-selected" : "ann"}
                      title={draft.spans[piece.index].term}
                      onClick={() => setSelectedSpan(piece.index)}
                    >
                      {piece.text}
                    </span>
                  );
                const s = piece.suggestion;
                return (
                  <span key={`g${piece.start}`} className="sugg-wrap">
                    <span
                      data-start={piece.start}
                      className={`sugg ${s.sources.includes("ai") ? "sugg-ai" : ""}`}
                      title={`Taklif (${s.sources.map((x) => SOURCE_LABELS[x]).join(", ")}): ${s.term ?? "?"} — qabul qilish uchun bosing`}
                      onClick={() => accept(s)}
                    >
                      {piece.text}
                    </span>
                    <button type="button" className="sugg-x" aria-label="Taklifni rad etish" onClick={() => reject(s)}>
                      ×
                    </button>
                  </span>
                );
              })}
            </div>

            {pending && (
              <div className="pending">
                <span>
                  Belgi: <strong>{sliceChars(paragraph.text, pending.start, pending.end)}</strong> → lug'at shakli
                </span>
                <input
                  autoFocus
                  value={pending.term}
                  onChange={(e) => setPending({ ...pending, term: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      tryAdd(pending);
                      setPending(null);
                    }
                    if (e.key === "Escape") setPending(null);
                  }}
                />
                <button
                  type="button"
                  onClick={() => {
                    tryAdd(pending);
                    setPending(null);
                  }}
                >
                  Qo'shish
                </button>
                <button type="button" className="secondary" onClick={() => setPending(null)}>
                  Bekor
                </button>
              </div>
            )}

            <div className="toolbar toolbar-left">
              <label className="check check-inline">
                <input
                  type="checkbox"
                  checked={showSuggestions}
                  onChange={(e) => {
                    setShowSuggestions(e.target.checked);
                    try {
                      localStorage.setItem("uzterm-suggestions", e.target.checked ? "on" : "off");
                    } catch {
                      /* bloklangan */
                    }
                  }}
                />
                Takliflarni ko'rsatish
              </label>
              <span className="hint">
                {draft.spans.length} ta belgi · {suggestions.length} ta ochiq taklif
              </span>
              <button type="button" className="secondary" disabled={!suggestions.length} onClick={acceptAll}>
                Barcha takliflarni qabul qilish
              </button>
            </div>

            {draft.spans.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Matndagi shakl</th>
                      <th>Lug'at shakli (term)</th>
                      <th>Pozitsiya</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {draft.spans.map((span, i) => (
                      <tr key={`${span.start}:${span.end}`} className={i === selectedSpan ? "row-selected" : ""}>
                        <td>{sliceChars(paragraph.text, span.start, span.end)}</td>
                        <td>
                          <input
                            aria-label="Lug'at shakli"
                            value={span.term}
                            onChange={(e) =>
                              update({ spans: draft.spans.map((x, j) => (j === i ? { ...x, term: e.target.value } : x)) })
                            }
                          />
                        </td>
                        <td className="mono">
                          [{span.start}, {span.end})
                        </td>
                        <td>
                          <button type="button" className="secondary" onClick={() => update({ spans: removeSpan(draft.spans, i) })}>
                            O'chirish
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <label htmlFor="notes">Izoh (noaniq holatlar)</label>
            <textarea id="notes" rows={2} value={draft.notes} onChange={(e) => update({ notes: e.target.value })} />

            <div className="toolbar">
              <label className="check">
                <input type="checkbox" checked={draft.reviewed} onChange={(e) => update({ reviewed: e.target.checked })} />
                Tekshirildi (reviewed) — paragraf to'liq ko'rib chiqildi
              </label>
              {draft.dirty && <span className="badge badge-warn">saqlanmagan</span>}
              {!draft.dirty && paragraph.saved && <span className="badge badge-ok">saqlangan</span>}
              <button type="button" className="secondary" disabled={saving} onClick={() => save(false)}>
                Saqlash
              </button>
              <button type="button" disabled={saving} onClick={() => save(true)}>
                Saqlash va keyingisi
              </button>
            </div>
            {draft.spans.length === 0 && (
              <p className="hint">Termin bo'lmasa ham saqlang: bo'sh ro'yxat "bu paragrafda termin yo'q" degani.</p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
