import { useEffect, useMemo, useState } from "react";
import { ApiError, listJudgments, saveJudgment } from "../api";
import type { JudgmentRow } from "../types";

interface Props {
  annotator: string;
}

const CHOICES: { value: JudgmentRow["judgment"]; label: string; title: string }[] = [
  { value: "1", label: "Termin", title: "1 — tilshunoslik termini" },
  { value: "0", label: "Termin emas", title: "0 — termin emas" },
  { value: "?", label: "Noaniq", title: "? — ikkilanaman (izoh yozing)" },
];

/** Context ichida ⟦…⟧ bilan belgilangan joyni ajratib ko'rsatadi. */
function Example({ text }: { text: string }) {
  const match = /⟦(.*?)⟧/.exec(text);
  if (!match) return <>{text}</>;
  return (
    <>
      {text.slice(0, match.index)}
      <mark>{match[1]}</mark>
      {text.slice(match.index + match[0].length)}
    </>
  );
}

export function JudgeView({ annotator }: Props) {
  const [rows, setRows] = useState<JudgmentRow[] | null>(null);
  const [onlyOpen, setOnlyOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRows(null);
    listJudgments(annotator)
      .then(setRows)
      .catch((exc) => setError(exc instanceof ApiError ? exc.message : "Baholarni yuklab bo'lmadi."));
  }, [annotator]);

  const visible = useMemo(() => (rows ?? []).filter((row) => !onlyOpen || !row.judgment), [rows, onlyOpen]);

  async function judge(row: JudgmentRow, judgment: JudgmentRow["judgment"], notes = row.notes) {
    try {
      const saved = await saveJudgment(annotator, { candidate: row.candidate, judgment, notes: notes || null });
      setRows((current) => (current ?? []).map((r) => (r.candidate === saved.candidate ? saved : r)));
      setError(null);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : "Saqlab bo'lmadi.");
    }
  }

  if (error && !rows) return <p className="error">{error}</p>;
  if (!rows) return <p className="hint">Yuklanmoqda…</p>;
  const done = rows.filter((r) => r.judgment).length;

  return (
    <section className="results">
      <div className="results-header">
        <h2>
          Nomzodlarni baholash · {annotator}: {done} / {rows.length}
        </h2>
        <label className="check">
          <input type="checkbox" checked={onlyOpen} onChange={(e) => setOnlyOpen(e.target.checked)} />
          Faqat baholanmaganlar
        </label>
      </div>
      <p className="hint">
        Ro'yxat ko'r: qaysi usul topgani va o'rni ko'rsatilmaydi. Har bir nomzod tilshunoslik termini bo'la oladimi —
        yo'riqnomaning 9.2-bo'limi bo'yicha. Baho darhol <span className="mono">data/judgments/candidates-{annotator}.csv</span>{" "}
        fayliga yoziladi. Boshqa baholovchining baholari ko'rsatilmaydi.
      </p>
      {error && <p className="error">{error}</p>}
      {visible.length === 0 ? (
        <p className="empty">Hammasi baholandi. Natija: <span className="mono">python -m app.evaluation.judgments score …</span></p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nomzod</th>
                <th>Misol</th>
                <th>Baho</th>
                <th>Izoh</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.candidate}>
                  <td>
                    <strong>{row.candidate}</strong>
                    <div className="hint">f = {row.frequency}</div>
                  </td>
                  <td className="example">
                    <Example text={row.example} />
                  </td>
                  <td>
                    <div className="choices">
                      {CHOICES.map((choice) => (
                        <button
                          key={choice.value}
                          type="button"
                          title={choice.title}
                          className={row.judgment === choice.value ? "" : "secondary"}
                          onClick={() => judge(row, row.judgment === choice.value ? "" : choice.value)}
                        >
                          {choice.label}
                        </button>
                      ))}
                    </div>
                  </td>
                  <td>
                    <input
                      aria-label={`${row.candidate} uchun izoh`}
                      defaultValue={row.notes}
                      onBlur={(e) => e.target.value !== row.notes && judge(row, row.judgment, e.target.value)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
