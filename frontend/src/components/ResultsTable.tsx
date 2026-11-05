import { MATCH_TYPE_LABELS, METHOD_LABELS, NORMALIZATION_BADGES } from "../labels";
import type { Match } from "../types";

interface Props {
  matches: Match[];
  selected: number | null;
  onSelect: (index: number) => void;
}

export function ResultsTable({ matches, selected, onSelect }: Props) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Matndagi shakl</th>
            <th>Asosiy termin</th>
            <th>Pozitsiya</th>
            <th>Soha</th>
            <th>Aniqlash usuli</th>
            <th>Meʼyoriy shakl</th>
            <th>Ishonchlilik</th>
          </tr>
        </thead>
        <tbody>
          {matches.map((match, index) => {
            const first = match.candidates[0];
            const badge = first ? NORMALIZATION_BADGES[first.normalization.status] : null;
            return (
              <tr
                key={`${match.start}-${match.end}`}
                className={index === selected ? "row-selected" : undefined}
                onClick={() => onSelect(index)}
              >
                <td>{index + 1}</td>
                <td>{match.surface}</td>
                <td>
                  {!match.in_dictionary ? (
                    <>
                      {match.lemma ?? match.surface} <span className="badge badge-new">yangi</span>
                    </>
                  ) : match.ambiguous ? (
                    <span className="badge badge-warn">noaniq: {match.candidates.map((c) => c.term).join(" / ")}</span>
                  ) : (
                    <>
                      {match.term}
                      {first.match_type !== "term" && (
                        <span className="hint"> ({MATCH_TYPE_LABELS[first.match_type]})</span>
                      )}
                    </>
                  )}
                </td>
                <td className="mono">
                  [{match.start}, {match.end})
                </td>
                <td>{match.ambiguous || !first ? "—" : first.domain ?? "—"}</td>
                <td>{METHOD_LABELS[match.method]}</td>
                <td>
                  {first && badge ? (
                    <>
                      {first.normalization.preferred_form ?? "—"}{" "}
                      <span className={`badge badge-${badge.tone}`}>{badge.text}</span>
                    </>
                  ) : (
                    <span className="badge badge-warn" title="Lug'atda yo'q — tekshirish kerak">lug'atda yo'q</span>
                  )}
                </td>
                <td title="Ishonchlilik ko'rsatkichi hisoblanmaydi">
                  {match.confidence === null ? "hisoblanmagan" : match.confidence.toFixed(2)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
