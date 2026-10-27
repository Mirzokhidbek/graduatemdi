import { useEffect, useRef, useState } from "react";
import { analyze, ApiError, health } from "./api";
import { HighlightedText } from "./components/HighlightedText";
import { ResultsTable } from "./components/ResultsTable";
import { TermDetails } from "./components/TermDetails";
import { download, toCsv, toJson } from "./exporters";
import { codepointLength } from "./segments";
import type { AnalyzeResponse, Health } from "./types";

const SAMPLE_TEXT =
  "Fonetika boʻlimida unli va undosh tovushlar oʻrganiladi. Qoʻshma gaplarning tuzilishi " +
  "sintaksisda koʻriladi, morfologiyada esa affikslar va oʻzak tahlil qilinadi.";

type Status = "idle" | "loading" | "done" | "error";

export default function App() {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [analyzedText, setAnalyzedText] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [server, setServer] = useState<Health | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    health()
      .then(setServer)
      .catch(() => setServer(null));
  }, []);

  const length = codepointLength(text);
  const limit = server?.max_text_chars ?? null;
  const tooLong = limit !== null && length > limit;
  const stale = result !== null && text !== analyzedText;

  async function submit() {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setStatus("loading");
    setError(null);
    try {
      const response = await analyze(text, current.signal);
      setResult(response);
      setAnalyzedText(text);
      setSelected(response.matches.length ? 0 : null);
      setStatus("done");
    } catch (exc) {
      if (current.signal.aborted) return;
      setError(exc instanceof ApiError ? exc.message : "Kutilmagan xato yuz berdi.");
      setStatus("error");
    }
  }

  const matches = result?.matches ?? [];

  return (
    <div className="page">
      <header>
        <h1>UzTerm AI</h1>
        <p className="hint">
          Oʻzbek tilshunoslik matnlaridan terminlarni aniqlash prototipi ·{" "}
          {server ? `lug'atda ${server.terms_in_dictionary} ta termin` : "server holati nomaʼlum"}
        </p>
      </header>

      <section className="input">
        <label htmlFor="text">Matn</label>
        <textarea
          id="text"
          value={text}
          rows={7}
          placeholder="Oʻzbek tilidagi matnni shu yerga kiriting…"
          onChange={(event) => setText(event.target.value)}
        />
        <div className="toolbar">
          <span className={tooLong ? "counter counter-over" : "counter"}>
            {length}
            {limit !== null && ` / ${limit}`} belgi
          </span>
          <button type="button" className="secondary" onClick={() => setText(SAMPLE_TEXT)}>
            Namuna matn
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={status === "loading" || !text.trim() || tooLong}
          >
            {status === "loading" ? "Tahlil qilinmoqda…" : "Tahlil qilish"}
          </button>
        </div>
        {tooLong && <p className="error">Matn juda uzun: eng ko'pi {limit} belgi.</p>}
      </section>

      {status === "error" && error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {result && (
        <section className="results" aria-live="polite">
          <div className="results-header">
            <h2>
              Natija: {matches.length} ta termin
            </h2>
            <div className="toolbar">
              <button
                type="button"
                className="secondary"
                onClick={() => download("uzterm-natija.json", toJson(analyzedText, result), "application/json")}
              >
                JSON
              </button>
              <button
                type="button"
                className="secondary"
                disabled={!matches.length}
                onClick={() => download("uzterm-natija.csv", toCsv(matches), "text/csv;charset=utf-8")}
              >
                CSV
              </button>
            </div>
          </div>

          {stale && (
            <p className="badge badge-warn block">Matn tahlildan keyin o'zgartirildi — natija eski matnga tegishli. Qayta tahlil qiling.</p>
          )}
          <ul className="notes">
            {result.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>

          {matches.length === 0 ? (
            <p className="empty">
              Matnda lug'atdagi terminlar topilmadi. Lug'at usuli bazada yo'q terminlarni aniqlay olmaydi (bazada{" "}
              {result.terms_in_dictionary} ta termin).
            </p>
          ) : (
            <>
              <HighlightedText text={analyzedText} matches={matches} selected={selected} onSelect={setSelected} />
              <div className="split">
                <ResultsTable matches={matches} selected={selected} onSelect={setSelected} />
                {selected !== null && matches[selected] && <TermDetails match={matches[selected]} />}
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
