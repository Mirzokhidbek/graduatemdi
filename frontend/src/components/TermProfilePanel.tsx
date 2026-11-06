import type { Severity, TermProfile } from "../types";

const SEVERITY: Record<Severity, { label: string; className: string }> = {
  ok: { label: "muvofiq", className: "badge badge-ok" },
  info: { label: "izoh", className: "badge badge-muted" },
  warning: { label: "ogohlantirish", className: "badge badge-warn" },
  error: { label: "xato", className: "badge badge-error" },
};

const LANGS: Record<string, string> = {
  ru: "ruscha", en: "inglizcha", la: "lotincha", grc: "yunoncha", ar: "arabcha", fa: "forscha", fr: "fransuzcha",
};

function List({ items }: { items: string[] }) {
  return items.length ? <>{items.join(", ")}</> : <span className="hint">—</span>;
}

/** Terminning boshqa modullardagi maʼlumoti: meʼyor, tezaurus, ekvivalentlar. */
export function TermProfilePanel({ profile }: { profile: TermProfile }) {
  const { check, thesaurus, equivalents, dictionary } = profile;
  const findings = check.findings.filter((f) => f.severity !== "ok");
  return (
    <>
      <section className="candidate">
        <h4>
          Meʼyor tekshiruvi <span className={SEVERITY[check.severity].className}>{SEVERITY[check.severity].label}</span>
        </h4>
        {check.suggestion && (
          <p>
            Tavsiya etilgan shakl: <strong>{check.suggestion}</strong>
          </p>
        )}
        {findings.length ? (
          <ul className="findings">
            {findings.map((f, i) => (
              <li key={i}>
                <span className={SEVERITY[f.severity].className}>{SEVERITY[f.severity].label}</span> {f.message}{" "}
                <span className="hint">({f.basis})</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="hint">ISO 704 va imlo qoidalari bo'yicha muammo topilmadi.</p>
        )}
      </section>

      {dictionary && (dictionary.synonyms.length > 0 || dictionary.variants.length > 0) && (
        <section className="candidate">
          <h4>Variantlar va sinonimlar</h4>
          <dl>
            {dictionary.synonyms.length > 0 && (
              <>
                <dt>Sinonim / dublet</dt>
                <dd>{dictionary.synonyms.join(", ")}</dd>
              </>
            )}
            {dictionary.variants.length > 0 && (
              <>
                <dt>Yozilish variantlari</dt>
                <dd>{dictionary.variants.join(", ")}</dd>
              </>
            )}
          </dl>
        </section>
      )}

      <section className="candidate">
        <h4>Tezaurusda</h4>
        <dl>
          <dt>Jinsi (keng tushuncha)</dt>
          <dd>
            <List items={thesaurus.broader} />
          </dd>
          <dt>Turlari</dt>
          <dd>
            <List items={thesaurus.narrower} />
          </dd>
          <dt>Bog'liq terminlar</dt>
          <dd>
            <List items={thesaurus.related} />
          </dd>
        </dl>
      </section>

      <section className="candidate">
        <h4>Ekvivalentlar</h4>
        {equivalents.length ? (
          <ul className="findings">
            {equivalents.map((e, i) => (
              <li key={i} title={e.source}>
                <span className="hint">{LANGS[e.lang] ?? e.lang}:</span> <strong>{e.value}</strong>
                {e.gloss && <span className="hint"> — {e.gloss}</span>}{" "}
                <span className={e.verified ? "badge badge-ok" : "badge badge-muted"}>
                  {e.verified ? "tasdiqlangan" : "tekshirilmagan"}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="hint">Bazada ekvivalent yo'q.</p>
        )}
      </section>
    </>
  );
}
