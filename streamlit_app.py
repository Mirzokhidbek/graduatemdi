"""UzTerm AI — Streamlit interfeysi (7-bosqich).

Ishga tushirish (repo ildizidan):
    pip install -r requirements.txt
    streamlit run streamlit_app.py

Matn kiritiladi, tanlangan usul (lug'at, CRF, CRF + gazetteer) terminlarni topadi,
har bir termin lug'at shakliga keltiriladi (``TermNormalizer``). Natija: belgilangan
matn, jadval, BIO teglar, JSON/CSV/JSONL eksport. Ikkinchi bo'limda 100 gaplik
tekshirilgan BIO dataset, uchinchisida tajribalar jadvali ko'rsatiladi.
"""

from __future__ import annotations

import csv
import html
import io
import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from app.database.term_store import load_terms  # noqa: E402
from app.dataset.bio import to_bio  # noqa: E402
from app.evaluation.evaluate import predict as dictionary_predict  # noqa: E402
from app.models.crf import TermCrf, build_lemmatizer  # noqa: E402
from app.nlp.clean import clean_text  # noqa: E402
from app.nlp.dictionary_matcher import DictionaryMatcher  # noqa: E402
from app.services.term_normalizer import build_normalizer  # noqa: E402

MAX_CHARS = 20_000
SAMPLE = (
    "Fonetika boʻlimida unli va undosh tovushlar oʻrganiladi. Qoʻshma gaplarning tuzilishi sintaksisda koʻriladi, "
    "morfologiyada esa affikslar va oʻzak tahlil qilinadi. Sotsiolingvistika va etnolingvistika tilning jamiyatdagi "
    "vazifasini, dialektografiya esa shevalarning tavsifini oʻrganadi."
)
METHODS = {
    "CRF + lug'at (gazetteer)": "crf-gazetteer",
    "CRF (yangi terminlarni ham topadi)": "crf",
    "Faqat lug'at": "dictionary",
}
STATUS_LABELS = {
    "approved": "tasdiqlangan",
    "needs_review": "lug'atda, tekshirilmagan",
    "no_data": "lug'atda yo'q — tekshirish kerak",
}


@st.cache_resource
def resources():
    texts = [p.read_text(encoding="utf-8") for p in sorted((ROOT / "data" / "raw").glob("*.txt"))]
    entries = load_terms(ROOT / "data" / "terms.json")
    matcher = DictionaryMatcher(entries)
    lemmatizer = build_lemmatizer(texts)
    models = {}
    for name, gazetteer in (("crf", None), ("crf-gazetteer", matcher)):
        path = ROOT / "models" / f"{name}.crfsuite"
        if path.exists():
            models[name] = TermCrf(lemmatizer, gazetteer).load(path)
    return {"entries": entries, "matcher": matcher, "normalizer": build_normalizer(entries, texts), "models": models}


def find_terms(text: str, method: str, res) -> list[tuple[int, int]]:
    if method == "dictionary":
        return [(s.start, s.end) for s in dictionary_predict(res["matcher"], text)]
    return list(res["models"][method].predict_spans(text))


def highlighted(text: str, rows: list[dict]) -> str:
    out, position = [], 0
    for row in rows:
        out.append(html.escape(text[position : row["start"]]))
        color = {"approved": "#d1f0d8", "needs_review": "#fff1b8"}.get(row["status"], "#f6f0ff")
        title = html.escape(f"{row['lemma']} · {STATUS_LABELS[row['status']]}")
        out.append(
            f'<mark title="{title}" style="background:{color};border-radius:3px;padding:0 2px">'
            f"{html.escape(text[row['start']:row['end']])}</mark>"
        )
        position = row["end"]
    out.append(html.escape(text[position:]))
    return '<div style="line-height:1.9;white-space:pre-wrap">' + "".join(out) + "</div>"


def to_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["surface", "start", "end", "lemma", "term", "status", "method"])
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row[k] for k in writer.fieldnames})
    return "﻿" + buffer.getvalue()


def analyze_page(res) -> None:
    st.sidebar.header("Sozlamalar")
    available = {label: key for label, key in METHODS.items() if key == "dictionary" or key in res["models"]}
    method = available[st.sidebar.radio("Usul", list(available))]
    clean = st.sidebar.checkbox("Matnni tozalash (apostroflar, ortiqcha bo'shliq, [1] havolalar)", value=True)
    st.sidebar.caption(f"Lug'atda {len(res['entries'])} ta termin (tekshirilmagan). Modellar: {', '.join(res['models']) or 'yo‘q'}.")

    if "text" not in st.session_state:
        st.session_state.text = ""
    if st.button("Namuna matn"):
        st.session_state.text = SAMPLE
    text = st.text_area("Matn (oʻzbek lotin yozuvi)", key="text", height=170, max_chars=MAX_CHARS)
    if not st.button("Tahlil qilish", type="primary", disabled=not text.strip()):
        return

    source = clean_text(text) if clean else text
    spans = find_terms(source, method, res)
    rows = []
    for start, end in spans:
        result = res["normalizer"].normalize(source[start:end])
        rows.append({"surface": source[start:end], "start": start, "end": end, "lemma": result.lemma,
                     "term": result.term or "", "status": result.status, "method": result.method})

    col1, col2, col3 = st.columns(3)
    col1.metric("Topilgan terminlar", len(rows))
    col2.metric("Lug'atda bor", sum(r["status"] != "no_data" for r in rows))
    col3.metric("Yangi (lug'atda yo'q)", sum(r["status"] == "no_data" for r in rows))

    st.markdown(highlighted(source, rows), unsafe_allow_html=True)
    st.caption("Sariq — lug'atda bor (tekshirilmagan), binafsha — lug'atda yo'q, model topgan. "
               "Lug'at shakli avtomatik taklif, meʼyoriy deb eʼlon qilinmaydi.")
    if rows:
        st.dataframe(
            [{"Matndagi shakl": r["surface"], "Pozitsiya": f"[{r['start']}, {r['end']})", "Lug'at shakli": r["lemma"],
              "Asosiy termin": r["term"], "Holat": STATUS_LABELS[r["status"]], "Meʼyorlashtirish": r["method"]}
             for r in rows],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Termin topilmadi.")

    bio = to_bio(source, [(r["start"], r["end"], r["lemma"]) for r in rows])
    with st.expander("BIO teglar"):
        st.dataframe([{"token": t, "teg": g} for t, g in zip(bio["tokens"], bio["tags"])], hide_index=True)

    payload = {"text": source, "method": method, "positions": "unicode_codepoints", "terms": rows}
    c1, c2, c3 = st.columns(3)
    c1.download_button("JSON", json.dumps(payload, ensure_ascii=False, indent=2), "uzterm.json", "application/json")
    c2.download_button("CSV", to_csv(rows), "uzterm.csv", "text/csv")
    c3.download_button("BIO JSONL", json.dumps(bio, ensure_ascii=False) + "\n", "uzterm-bio.jsonl", "application/jsonl")


def dataset_page() -> None:
    path = ROOT / "data" / "bio" / "sentences-100.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    st.write(f"{len(rows)} ta gap, {sum(len(r['terms']) for r in rows)} ta termin, "
             f"{len({r['doc_id'] for r in rows})} ta maqoladan. Har bir gap qo'lda tekshirilgan "
             f"({sum(r['review'] == 'tuzatildi' for r in rows)} tasi tuzatilgan: `data/bio/review.txt`). "
             "Annotatsiya AI tomonidan qilingan, inson tekshirmagan.")
    choice = st.selectbox("Gap", [f"{r['id']} · {r['text'][:80]}" for r in rows])
    row = rows[[f"{r['id']} · {r['text'][:80]}" for r in rows].index(choice)]
    st.markdown(highlighted(row["text"], [{"start": t["start"], "end": t["end"], "lemma": t["term"], "status": "needs_review"}
                                          for t in row["terms"]]), unsafe_allow_html=True)
    st.dataframe([{"token": t, "teg": g} for t, g in zip(row["tokens"], row["tags"])], hide_index=True)


def results_page() -> None:
    table = ROOT / "docs" / "experiments-table.md"
    st.markdown(table.read_text(encoding="utf-8") if table.exists() else "Jadval hali yaratilmagan.")


def main() -> None:
    st.set_page_config(page_title="UzTerm AI", page_icon="🔤", layout="wide")
    st.title("UzTerm AI")
    st.caption("Oʻzbek tilshunoslik matnlaridan terminlarni aniqlash va meʼyorlashtirish prototipi")
    res = resources()
    tab1, tab2, tab3 = st.tabs(["Tahlil", "BIO dataset (100 gap)", "Tajribalar"])
    with tab1:
        analyze_page(res)
    with tab2:
        dataset_page()
    with tab3:
        results_page()


main()
