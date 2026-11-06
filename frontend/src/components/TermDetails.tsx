import { MATCH_TYPE_LABELS, METHOD_LABELS, NORMALIZATION_BADGES } from "../labels";
import type { Match, TermProfile } from "../types";
import { TermProfilePanel } from "./TermProfilePanel";

export function TermDetails({ match, profile }: { match: Match; profile?: TermProfile }) {
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
      {!match.in_dictionary && (
        <section className="candidate">
          <p className="badge badge-new block">
            Yangi termin nomzodi: model topdi, lekin lug'atda yo'q. Termin ekanini va lug'at shaklini mutaxassis
            tekshirishi kerak.
          </p>
          <dl>
            <dt>Taklif qilingan lug'at shakli</dt>
            <dd>{match.lemma ?? "—"}</dd>
            {match.related_terms.length > 0 && (
              <>
                <dt>Ichidagi lug'at terminlari</dt>
                <dd>{match.related_terms.join(", ")}</dd>
              </>
            )}
          </dl>
        </section>
      )}
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
      {profile && <TermProfilePanel profile={profile} />}
    </aside>
  );
}
