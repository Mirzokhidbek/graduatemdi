"""Statistik termin nomzodlarini ajratish va reytinglash (3-bosqich).

Nomzod — 1..``max_words`` so'zli n-gram:
- tinish belgisini kesib o'tmaydi (``tokenize.phrases``);
- yordamchi so'z (``stopwords.STOPWORDS``) bilan boshlanmaydi va tugamaydi;
- oxirgi so'z korpusga tayangan lemmatizator bilan qo'shimchasiz holga
  keltiriladi (``fonemalarning`` -> ``fonema``), ichki so'zlar o'zgarmaydi;
- kamida 3 harfdan iborat.

Reyting usullari:
- ``frequency``: f(a) — korpusdagi uchrashlar soni;
- ``tfidf``: f(a) · idf(a), idf(a) = ln((1 + N) / (1 + df(a))) + 1
  (N — hujjatlar soni, df — nomzod uchragan hujjatlar soni; scikit-learn'dagi
  silliqlangan IDF);
- ``cvalue``: C-value (Frantzi, Ananiadou, Mima, 2000), bir so'zli
  nomzodlar uchun log2(|a|) o'rniga log2(|a| + 1) (Barrón-Cedeño va boshq., 2009):
      C(a) = log2(|a|+1) · f(a),                          agar a boshqa nomzod ichida bo'lmasa;
      C(a) = log2(|a|+1) · (f(a) − Σ_{b∈T_a} f(b) / |T_a|), aks holda,
  bu yerda T_a — a ni uzluksiz qism sifatida o'z ichiga olgan uzunroq nomzodlar.

- ``weirdness``: soha korpusidagi nisbiy chastotaning kontrast (sohaga oid
  bo'lmagan) korpusdagi nisbiy chastotaga nisbati (Ahmad va boshq., 1999),
  Laplace silliqlash bilan: W(a) = (f(a)/N_d) / ((f_c(a)+1)/(N_c+V)).
  Umumiy so'zlarni (``so'z``, ``til``, ``shakl``) pastga tushiradi; kontrast
  korpus (``--contrast``) talab qiladi.

Oʻzbek tili uchun ochiq va tekshirilgan POS-tegger ishlatilmadi. O'rniga
``--pos-filter`` morfologik qoida qo'llaydi (``looks_like_noun_head``): nomzodning
oxirgi so'zi fe'l (-adi, -gan, -moq, -ib, ...) yoki nisbiy sifat (-ik, -iy)
shaklida bo'lsa, u chiqariladi — "sifat + ot" iboralari (``grammatik kategoriya``)
qoladi, yolg'iz ``grammatik`` esa chiqadi. Bu qoida taxminiy.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Mapping

from app.nlp.lemmatize import CorpusLemmatizer
from app.nlp.stopwords import STOPWORDS
from app.nlp.tokenize import phrases, tokenize

METHODS = ("frequency", "tfidf", "cvalue", "weirdness")

# Fe'l, sifatdosh, ravishdosh va harakat nomi qo'shimchalari (oxirgi so'zda bo'lsa, nomzod ot birikmasi emas).
VERB_ENDINGS = (
    "adi", "aydi", "ydi", "moqda", "moq", "yapti", "gan", "kan", "qan", "ilgan", "ingan",
    "ib", "ganda", "gach", "guncha", "maydi", "mas", "sin", "aylik", "ylik",
)
# Nisbiy sifat: grammatik, fonetik, leksik, morfologik, nisbiy, tarixiy (lekin -lik otlari emas).
ADJECTIVE_ENDINGS = ("tik", "gik", "sik", "nik", "kik", "rik", "iy", "viy")
# -lik / -chilik otlari va ayrim -ik bilan tugaydigan otlar adjektiv emas.
NOUN_EXCEPTIONS = ("lik", "kelishik", "fonetik transkripsiya")
MIN_CANDIDATE_LETTERS = 3

Key = tuple[str, ...]


@dataclass
class Candidate:
    key: Key  # lemmatizatsiya qilingan so'zlar
    frequency: int = 0
    documents: set[str] = field(default_factory=set)
    surfaces: Counter = field(default_factory=Counter)  # matndagi ko'rinishlar

    @property
    def text(self) -> str:
        return " ".join(self.key)

    @property
    def length(self) -> int:
        return len(self.key)

    @property
    def doc_frequency(self) -> int:
        return len(self.documents)


def looks_like_noun_head(key: Key) -> bool:
    """Nomzodning oxirgi so'zi ot bo'la oladimi (morfologik qoida, taxminiy)."""
    if not key:
        return False
    last = key[-1]
    if last.endswith(NOUN_EXCEPTIONS[0]) or last in NOUN_EXCEPTIONS:
        return True
    if any(last.endswith(ending) for ending in VERB_ENDINGS) and len(last) > 4:
        return False
    if any(last.endswith(ending) for ending in ADJECTIVE_ENDINGS) and len(last) > 4:
        return False
    return True


def weirdness_scores(
    candidates: Mapping[Key, Candidate], domain_tokens: int, contrast: Counter, contrast_tokens: int
) -> dict[Key, float]:
    """Kontrast korpusga nisbatan "g'ayrioddiylik"; ``contrast`` — kalit -> kontrast korpusdagi chastota."""
    vocabulary = len(contrast) + 1
    return {
        key: (c.frequency / domain_tokens) / ((contrast.get(key, 0) + 1) / (contrast_tokens + vocabulary))
        for key, c in candidates.items()
    }


def contrast_frequencies(
    documents: Mapping[str, str], keys: set[Key], lemmatizer: CorpusLemmatizer, max_words: int = 4
) -> tuple[Counter, int]:
    """Kontrast korpusda berilgan nomzod kalitlari necha marta uchrashini sanaydi."""
    found = extract_candidates(documents, max_words=max_words, stopwords=frozenset(), lemmatizer=lemmatizer)
    counts = Counter({key: c.frequency for key, c in found.items() if key in keys})
    return counts, sum(len(tokenize(text)) for text in documents.values())


def build_lemmatizer(documents: Mapping[str, str]) -> CorpusLemmatizer:
    return CorpusLemmatizer(token.norm for text in documents.values() for token in tokenize(text))


def lemmatize_form(form: str, lemmatizer: CorpusLemmatizer) -> Key:
    """Lug'at shaklini nomzod kaliti ko'rinishiga keltiradi (oxirgi so'z lemmatizatsiya qilinadi)."""
    words = [token.norm for token in tokenize(form)]
    if not words:
        return ()
    return (*words[:-1], lemmatizer.lemma(words[-1]))


def extract_candidates(
    documents: Mapping[str, str],
    max_words: int = 4,
    stopwords: frozenset[str] = STOPWORDS,
    lemmatizer: CorpusLemmatizer | None = None,
) -> dict[Key, Candidate]:
    """``{doc_id: matn}`` dan barcha nomzodlarni chastotalari bilan yig'adi."""
    if max_words < 1:
        raise ValueError("max_words kamida 1 bo'lishi kerak")

    lemmatizer = lemmatizer or build_lemmatizer(documents)
    candidates: dict[Key, Candidate] = {}

    for doc_id, text in documents.items():
        for phrase in phrases(text):
            for start in range(len(phrase)):
                if phrase[start].norm in stopwords:
                    continue
                for end in range(start + 1, min(start + max_words, len(phrase)) + 1):
                    last = phrase[end - 1]
                    lemma = lemmatizer.lemma(last.norm)
                    # Qo'shimchali shakl ham (``o'ziga`` -> ``o'z``) tekshiriladi.
                    if last.norm in stopwords or lemma in stopwords:
                        continue
                    words = [token.norm for token in phrase[start : end - 1]]
                    key = (*words, lemma)
                    if sum(len(word) for word in key) < MIN_CANDIDATE_LETTERS:
                        continue
                    candidate = candidates.setdefault(key, Candidate(key))
                    candidate.frequency += 1
                    candidate.documents.add(doc_id)
                    candidate.surfaces[text[phrase[start].start : last.end]] += 1
    return candidates


def c_values(candidates: Mapping[Key, Candidate]) -> dict[Key, float]:
    containers: dict[Key, list[Key]] = {key: [] for key in candidates}
    for longer in candidates:
        for n in range(1, len(longer)):
            for i in range(len(longer) - n + 1):
                shorter = longer[i : i + n]
                if shorter in containers and longer not in containers[shorter]:
                    containers[shorter].append(longer)

    scores: dict[Key, float] = {}
    for key, candidate in candidates.items():
        weight = math.log2(candidate.length + 1)
        nested_in = containers[key]
        if nested_in:
            mean_container_freq = sum(candidates[b].frequency for b in nested_in) / len(nested_in)
            scores[key] = weight * (candidate.frequency - mean_container_freq)
        else:
            scores[key] = weight * candidate.frequency
    return scores


def tfidf_scores(candidates: Mapping[Key, Candidate], n_documents: int) -> dict[Key, float]:
    return {
        key: c.frequency * (math.log((1 + n_documents) / (1 + c.doc_frequency)) + 1)
        for key, c in candidates.items()
    }


def rank(
    candidates: Mapping[Key, Candidate],
    method: str,
    n_documents: int,
    min_frequency: int = 2,
    pos_filter: bool = False,
    weirdness: Mapping[Key, float] | None = None,
) -> list[tuple[Candidate, float]]:
    """Nomzodlarni kamayish tartibida reytinglaydi.

    ``min_frequency`` dan kam uchragan nomzodlar ballar hisoblanishidan oldin
    chiqarib tashlanadi (C-value'dagi T_a ham faqat qolganlar bo'yicha).
    """
    if method not in METHODS:
        raise ValueError(f"method quyidagilardan biri bo'lishi kerak: {', '.join(METHODS)}")
    kept = {
        k: c for k, c in candidates.items() if c.frequency >= min_frequency and (not pos_filter or looks_like_noun_head(k))
    }
    if method == "weirdness":
        if weirdness is None:
            raise ValueError("weirdness usuli kontrast korpusni talab qiladi (--contrast)")
        scores = {k: weirdness[k] for k in kept}
    elif method == "frequency":
        scores = {k: float(c.frequency) for k, c in kept.items()}
    elif method == "tfidf":
        scores = tfidf_scores(kept, n_documents)
    else:
        scores = c_values(kept)
    ordered = sorted(kept.values(), key=lambda c: (-scores[c.key], -c.frequency, c.text))
    return [(candidate, scores[candidate.key]) for candidate in ordered]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import csv
    import json
    import sys
    from pathlib import Path

    from app.dataset.annotation import STATUS_REVIEWED, validate_files
    from app.dataset.validate import REPO_ROOT
    from app.database.term_store import TermDatabaseError, load_terms
    from app.evaluation.ranking import coverage, precision_at_k
    from app.nlp.dictionary_matcher import DictionaryMatcher

    parser = argparse.ArgumentParser(description="Statistik termin nomzodlarini ajratish va reytinglash")
    parser.add_argument("files", nargs="*", type=Path, help="matn fayllari (standart: data/raw/*.txt)")
    parser.add_argument("--method", choices=METHODS, default="cvalue")
    parser.add_argument("--min-freq", type=int, default=2, help="eng kam chastota")
    parser.add_argument("--max-words", type=int, default=4, help="nomzoddagi eng ko'p so'zlar soni")
    parser.add_argument("--top", type=int, default=30, help="nechta nomzod ko'rsatish")
    parser.add_argument("--terms", type=Path, default=REPO_ROOT / "data" / "terms.json",
                        help="lug'at (nomzod lug'atda bormi — belgisi uchun)")
    parser.add_argument("--reference-terms", type=Path, help="Precision@K uchun lug'at (terms.json formati)")
    parser.add_argument("--reference-annotations", type=Path, nargs="+",
                        help="Precision@K uchun inson belgilagan JSONL (faqat reviewed)")
    parser.add_argument("--output", type=Path, help="barcha reytingni yozish (.json yoki .csv)")
    parser.add_argument("--pos-filter", action="store_true",
                        help="oxirgi so'zi fe'l yoki nisbiy sifat shaklidagi nomzodlarni chiqarish")
    parser.add_argument("--contrast", type=Path, nargs="+",
                        help="kontrast (sohaga oid bo'lmagan) korpus matnlari, weirdness usuli uchun")
    args = parser.parse_args(argv)

    files = args.files or sorted((REPO_ROOT / "data" / "raw").glob("*.txt"))
    if not files:
        print("Matn fayllari topilmadi.", file=sys.stderr)
        return 1
    documents = {path.stem: path.read_text(encoding="utf-8") for path in files}

    try:
        matcher = DictionaryMatcher(load_terms(args.terms))
        reference_entries = load_terms(args.reference_terms) if args.reference_terms else []
    except TermDatabaseError as exc:
        print(exc, file=sys.stderr)
        return 1

    lemmatizer = build_lemmatizer(documents)
    candidates = extract_candidates(documents, max_words=args.max_words, lemmatizer=lemmatizer)
    total_tokens = sum(len(tokenize(text)) for text in documents.values())
    weirdness = None
    if args.method == "weirdness":
        if not args.contrast:
            print("weirdness usuli uchun --contrast fayllari kerak.", file=sys.stderr)
            return 1
        contrast_docs = {path.stem: path.read_text(encoding="utf-8") for path in args.contrast}
        counts, contrast_tokens = contrast_frequencies(contrast_docs, set(candidates), lemmatizer, args.max_words)
        weirdness = weirdness_scores(candidates, total_tokens, counts, contrast_tokens)
    try:
        ranked = rank(candidates, args.method, len(documents), min_frequency=args.min_freq,
                      pos_filter=args.pos_filter, weirdness=weirdness)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Hujjatlar: {len(documents)}, tokenlar: {total_tokens}, nomzodlar: {len(candidates)} "
          f"(f >= {args.min_freq}: {len(ranked)}), usul: {args.method}"
          f"{', POS filtri' if args.pos_filter else ''}")
    print(f"\n{'#':>3}  {'ball':>8}  {'f':>4}  {'df':>3}  lug'at  nomzod (eng ko'p uchragan ko'rinish)")
    for position, (candidate, score) in enumerate(ranked[: args.top], start=1):
        surface = candidate.surfaces.most_common(1)[0][0]
        known = "  +   " if matcher.has_form(surface) or matcher.has_form(candidate.text) else "      "
        print(f"{position:>3}  {score:>8.2f}  {candidate.frequency:>4}  {candidate.doc_frequency:>3}  {known}  "
              f"{candidate.text}  ({surface})")

    reference: set[Key] = set()
    for entry in reference_entries:
        for form in (entry.term, *entry.variants, *entry.synonyms):
            reference.add(lemmatize_form(form, lemmatizer))
    if args.reference_annotations:
        report = validate_files(args.reference_annotations)
        if not report.ok:
            print(f"\nAnnotatsiyada xatolar ({len(report.errors)}); Precision@K hisoblanmadi.", file=sys.stderr)
            return 1
        for record in report.records:
            if record.status == STATUS_REVIEWED:
                reference.update(lemmatize_form(span.term, lemmatizer) for span in record.terms)
    reference.discard(())

    if reference:
        keys = [candidate.key for candidate, _ in ranked]
        print(f"\nMaʼlum terminlar ro'yxati: {len(reference)} ta (to'liq emas — Precision@K pastki chegara)")
        for k in (10, 20, 50, 100):
            result = precision_at_k(keys, reference, k)
            value = "—" if result.precision is None else f"{result.precision:.3f}"
            print(f"  Precision@{k:<3} = {value}  ({result.hits}/{result.considered})")
        found, total = coverage(keys, reference)
        print(f"  Qamrov: {found}/{total} maʼlum termin reytingda bor")

    if args.output is not None:
        rows = [
            {
                "rank": position,
                "candidate": candidate.text,
                "score": score,
                "frequency": candidate.frequency,
                "doc_frequency": candidate.doc_frequency,
                "words": candidate.length,
                "in_dictionary": matcher.has_form(candidate.text),
                "in_reference": candidate.key in reference if reference else None,
                "top_surface": candidate.surfaces.most_common(1)[0][0],
            }
            for position, (candidate, score) in enumerate(ranked, start=1)
        ]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.suffix == ".csv":
            with args.output.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["rank"])
                writer.writeheader()
                writer.writerows(rows)
        else:
            payload = {
                "method": args.method,
                "min_frequency": args.min_freq,
                "max_words": args.max_words,
                "documents": len(documents),
                "tokens": total_tokens,
                "candidates": rows,
            }
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nNatija: {args.output} ({len(rows)} nomzod)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
