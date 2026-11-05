import { useRef, useState } from "react";
import { ApiError, checkTerms, parseTermLines } from "../api";
import type { CheckTermsResponse, Severity } from "../types";

const SEVERITY: Record<Severity, { label: string; className: string }> = {
  ok: { label: "muvofiq", className: "badge badge-ok" },
  info: { label: "izoh", className: "badge badge-muted" },
  warning: { label: "ogohlantirish", className: "badge badge-warn" },
  error: { label: "xato", className: "badge badge-error" },
};

const EXAMPLE = ["Fonemalar", "o'zak", "фонема", "lingvistika", "tsirk", "ikkinchi shaxs koʻplik qoʻshimchasi turi"].join(
  "\n",
);

/** Terminlarni ISO 704 tamoyillari va oʻzbek imlo qoidalari bo'yicha tekshirish sahifasi. */
export function CheckView() {
  const [text, setText] = useState("");
  const [response, setResponse] = useState<CheckTermsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const terms = parseTermLines(text);

  async function run() {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setLoading(true);
    setError(null);
    try {
      setResponse(await checkTerms(terms, current.signal));
    } catch (exc) {
      if (exc instanceof DOMException && exc.name === "AbortError") return;
      setError(exc instanceof ApiError ? exc.message : "Tekshirib bo'lmadi.");
    } finally {
      if (controller.current === current) setLoading(false);
    }
  }

  return (
    <div className="page">
      <section className="input">
        <label htmlFor="check-terms">Terminlar (har qatorda bittadan, 200 tagacha)</label>
        <textarea
          id="check-terms"
          rows={6}
          value={text}
          placeholder={EXAMPLE}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="toolbar">
          <span className="counter">{terms.length} ta termin</span>
          <button type="button" className="secondary" onClick={() => setText(EXAMPLE)}>
            Namuna
          </button>
          <button type="button" disabled={!terms.length || loading} onClick={run}>
            {loading ? "Tekshirilmoqda…" : "Tekshirish"}
          </button>
        </div>
      </section>
      {error && <p className="error">{error}</p>}
      {response && (
        <section className="results">
          <div className="results-header">
            <h2>Natija: {response.results.length} ta termin</h2>
          </div>
          <p className="notes">{response.note}</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Termin</th>
                  <th>Holat</th>
                  <th>Tavsiya etilgan shakl</th>
                  <th>Izohlar</th>
                </tr>
              </thead>
              <tbody>
                {response.results.map((result) => (
                  <tr key={result.term}>
                    <td>{result.term}</td>
                    <td>
                      <span className={SEVERITY[result.severity].className}>{SEVERITY[result.severity].label}</span>
                    </td>
                    <td>{result.suggestion ?? "—"}</td>
                    <td>
                      {result.findings.length ? (
                        <ul className="findings">
                          {result.findings.map((f, i) => (
                            <li key={i}>
                              <span className={SEVERITY[f.severity].className}>{SEVERITY[f.severity].label}</span>{" "}
                              {f.message} <span className="hint">({f.basis})</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="hint">qoidalar bo'yicha muammo topilmadi</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
