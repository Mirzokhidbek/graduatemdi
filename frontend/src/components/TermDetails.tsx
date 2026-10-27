import { MATCH_TYPE_LABELS, METHOD_LABELS, NORMALIZATION_BADGES } from "../labels";
import type { Match } from "../types";

export function TermDetails({ match }: { match: Match }) {
  return (
    <aside className="details" aria-label="Termin tafsilotlari">
      <h3>
        «{match.surface}»
        {match.suffix && (
          <span className="hint">
            {" "}
            = {match.base_surface} + -{match.suffix}
          </span>
        )}
      </h3>
      <p className="hint">
        {METHOD_LABELS[match.method]} · pozitsiya [{match.start}, {match.end})
      </p>
      {match.ambiguous && (
        <p className="badge badge-warn block">
          Bu shakl bir nechta terminga mos keladi. Qaysi biri nazarda tutilganini kontekst bo'yicha tekshiring.
        </p>
      )}
      {match.candidates.map((candidate) => {
        const badge = NORMALIZATION_BADGES[candidate.normalization.status];
        return (
          <section key={candidate.term_id} className="candidate">
            <h4>
              {candidate.term} <span className="hint">({candidate.term_id})</span>
            </h4>
            <dl>
              <dt>Mos kelgan shakl</dt>
              <dd>
                {candidate.matched_form} — {MATCH_TYPE_LABELS[candidate.match_type]}
              </dd>
              <dt>Soha</dt>
              <dd>{candidate.domain ?? "—"}</dd>
              <dt>Taʼrif</dt>
              <dd>{candidate.definition ?? "Bazada taʼrif yo'q"}</dd>
              <dt>Meʼyoriy shakl</dt>
              <dd>
                {candidate.normalization.preferred_form ?? "—"}{" "}
                <span className={`badge badge-${badge.tone}`}>{badge.text}</span>
                {candidate.normalization.label !== badge.text && (
                  <div className="hint">{candidate.normalization.label}</div>
                )}
              </dd>
              <dt>Manba</dt>
              <dd>{candidate.source ?? "Manba ko'rsatilmagan"}</dd>
            </dl>
          </section>
        );
      })}
    </aside>
  );
}
