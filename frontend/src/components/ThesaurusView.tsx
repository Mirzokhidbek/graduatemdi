import { useEffect, useMemo, useState } from "react";
import { ApiError, thesaurus as loadThesaurus, thesaurusRoots } from "../api";
import type { Thesaurus, ThesaurusRelation } from "../types";

const SOURCE_LABELS: Record<string, string> = {
  head: "bosh so'z",
  definition: "taʼrif",
  pattern: "qolip",
};

interface NodeProps {
  label: string;
  children: Map<string, string[]>;
  relations: Map<string, ThesaurusRelation>;
  query: string;
  depth: number;
  path: Set<string>;
}

/** Tushuncha va uning tur (narrower) tushunchalari; qidiruvga mos shoxlar ochiq turadi. */
function Node({ label, children, relations, query, depth, path }: NodeProps) {
  const kids = (children.get(label) ?? []).filter((k) => !path.has(k));
  const hit = query !== "" && label.includes(query);
  const relation = [...path].length ? relations.get(`${label}|${[...path].at(-1)}`) : undefined;
  const sources = relation
    ? Object.keys(relation.sources)
        .map((s) => SOURCE_LABELS[s] ?? s)
        .join(", ")
    : "";
  const title = relation?.evidence[0] ? `${sources}: ${relation.evidence[0]}` : sources;
  const text = (
    <span className={hit ? "hit" : undefined} title={title || undefined}>
      {label}
    </span>
  );
  if (!kids.length) return <li className="leaf">{text}</li>;
  const next = new Set(path).add(label);
  return (
    <li>
      <details open={depth < 1 || (query !== "" && subtreeHas(label, children, query, new Set()))}>
        <summary>
          {text}
          <span className="count">({kids.length})</span>
        </summary>
        <ul>
          {kids.map((k) => (
            <Node key={k} label={k} children={children} relations={relations} query={query} depth={depth + 1} path={next} />
          ))}
        </ul>
      </details>
    </li>
  );
}

function subtreeHas(label: string, children: Map<string, string[]>, query: string, seen: Set<string>): boolean {
  if (seen.has(label)) return false;
  seen.add(label);
  return (children.get(label) ?? []).some((k) => k.includes(query) || subtreeHas(k, children, query, seen));
}

export function ThesaurusView() {
  const [data, setData] = useState<Thesaurus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    loadThesaurus()
      .then(setData)
      .catch((exc) => setError(exc instanceof ApiError ? exc.message : "Tezaurusni yuklab bo'lmadi."));
  }, []);

  const { children, relations, roots } = useMemo(() => {
    const children = new Map<string, string[]>();
    const relations = new Map<string, ThesaurusRelation>();
    for (const c of data?.concepts ?? []) children.set(c.label, c.narrower);
    for (const r of data?.relations ?? []) relations.set(`${r.narrower}|${r.broader}`, r);
    return { children, relations, roots: thesaurusRoots(data?.concepts ?? []) };
  }, [data]);

  const q = query.trim().toLowerCase();
  const visibleRoots = q ? roots.filter((r) => r.includes(q) || subtreeHas(r, children, q, new Set())) : roots;

  if (error) return <div className="page"><p className="error">{error}</p></div>;
  if (!data) return <div className="page"><p className="hint">Yuklanmoqda…</p></div>;

  return (
    <div className="page">
      <section className="results">
        <div className="results-header">
          <h2>Tezaurus: tur–jins ierarxiyasi</h2>
        </div>
        <p className="notes">
          {data.summary.concepts} ta tushuncha, {data.summary.broader_relations} ta tur–jins munosabati,{" "}
          {data.summary.related_pairs} ta assotsiativ juft. Munosabatlar avtomatik ajratilgan (bosh so'z, taʼrif,
          leksik-sintaktik qolip) va ekspert tekshiruvini talab qiladi. Manba va dalilni ko'rish uchun sichqonchani
          termin ustiga olib boring.
        </p>
        <div className="tree-toolbar">
          <input
            type="search"
            aria-label="Termin qidirish"
            placeholder="Termin qidirish…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <span className="hint">{visibleRoots.length} ta yuqori daraja tushuncha</span>
        </div>
        <ul className="tree">
          {visibleRoots.map((r) => (
            <Node key={r} label={r} children={children} relations={relations} query={q} depth={0} path={new Set()} />
          ))}
        </ul>
      </section>
    </div>
  );
}
