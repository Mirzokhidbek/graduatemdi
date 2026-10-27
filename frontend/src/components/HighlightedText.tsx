import { toSegments } from "../segments";
import type { Match } from "../types";

interface Props {
  text: string;
  matches: Match[];
  selected: number | null;
  onSelect: (index: number) => void;
}

export function HighlightedText({ text, matches, selected, onSelect }: Props) {
  return (
    <div className="highlighted" aria-label="Matnda topilgan terminlar">
      {toSegments(text, matches).map((segment, i) => {
        if (segment.match === null) return <span key={i}>{segment.text}</span>;
        const match = matches[segment.match];
        const classes = ["mark", match.ambiguous ? "mark-ambiguous" : "", segment.match === selected ? "mark-selected" : ""];
        return (
          <button
            key={i}
            type="button"
            className={classes.join(" ")}
            title={match.term ?? "bir nechta termin"}
            onClick={() => onSelect(segment.match as number)}
          >
            {segment.text}
          </button>
        );
      })}
    </div>
  );
}
