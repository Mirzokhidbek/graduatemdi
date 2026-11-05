import { useEffect, useState } from "react";
import App from "./App";
import { AnnotateView } from "./components/AnnotateView";
import { CheckView } from "./components/CheckView";
import { ThesaurusView } from "./components/ThesaurusView";
import { JudgeView } from "./components/JudgeView";

type View = "analyze" | "check" | "thesaurus" | "annotate" | "judge";

const VIEWS: { id: View; label: string }[] = [
  { id: "analyze", label: "Tahlil" },
  { id: "check", label: "Meʼyor tekshiruvi" },
  { id: "thesaurus", label: "Tezaurus" },
  { id: "annotate", label: "Belgilash (annotatsiya)" },
  { id: "judge", label: "Nomzodlarni baholash" },
];

const ANNOTATOR_KEY = "uzterm-annotator";
const ANNOTATOR_PATTERN = /^[A-Za-z][A-Za-z0-9_-]{0,15}$/;

function viewFromHash(): View {
  const id = window.location.hash.replace("#", "");
  return VIEWS.some((v) => v.id === id) ? (id as View) : "analyze";
}

function storedAnnotator(): string {
  try {
    return localStorage.getItem(ANNOTATOR_KEY) ?? "";
  } catch {
    return "";
  }
}

export default function Shell() {
  const [view, setView] = useState<View>(viewFromHash);
  const [annotator, setAnnotator] = useState(storedAnnotator);
  const [input, setInput] = useState(annotator);

  useEffect(() => {
    const onHash = () => setView(viewFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const valid = ANNOTATOR_PATTERN.test(input);

  function confirmAnnotator() {
    if (!valid) return;
    setAnnotator(input);
    try {
      localStorage.setItem(ANNOTATOR_KEY, input);
    } catch {
      /* xotira bloklangan: faqat shu sahifa uchun */
    }
  }

  return (
    <>
      <nav className="tabs" aria-label="Bo'limlar">
        {VIEWS.map((v) => (
          <a key={v.id} href={`#${v.id}`} className={v.id === view ? "tab tab-active" : "tab"} aria-current={v.id === view}>
            {v.label}
          </a>
        ))}
      </nav>
      {view === "analyze" ? (
        <App />
      ) : view === "check" ? (
        <CheckView />
      ) : view === "thesaurus" ? (
        <ThesaurusView />
      ) : (
        <div className="page">
          <div className="annotator">
            <label htmlFor="annotator">Annotator kodi</label>
            <input
              id="annotator"
              value={input}
              placeholder="A1"
              onChange={(e) => setInput(e.target.value.trim())}
              onKeyDown={(e) => e.key === "Enter" && confirmAnnotator()}
            />
            <button type="button" disabled={!valid || input === annotator} onClick={confirmAnnotator}>
              Tanlash
            </button>
            <span className="hint">
              Ism emas, kod (A1, A2). Har bir annotatorning ishi alohida saqlanadi va boshqasiga ko'rinmaydi.
            </span>
          </div>
          {!annotator ? (
            <p className="empty">Davom etish uchun annotator kodini kiriting.</p>
          ) : view === "annotate" ? (
            <AnnotateView key={annotator} annotator={annotator} />
          ) : (
            <JudgeView key={annotator} annotator={annotator} />
          )}
        </div>
      )}
    </>
  );
}
