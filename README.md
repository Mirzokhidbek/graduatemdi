# UzTerm AI

A prototype for automatically extracting, classifying and normalizing terms from
Uzbek texts on the Uzbek language and linguistics (master's thesis project).

**Current status** (details in [docs/project-plan.md](docs/project-plan.md)):

- working: dictionary-based term extractor (450 terms, not yet verified),
  web interface for analysis, **annotation** and candidate judging, REST API;
- ready: dataset tooling (validation, train/val/test splits, inter-annotator agreement),
  statistical candidates (frequency, TF-IDF, C-value, POS filter), **CRF model**;
- corpus: 41 linguistics articles from Uzbek Wikipedia. All of them were annotated
  **by AI** (silver data, 2,555 terms); human annotation is pending.
  Preliminary results (silver data only): CRF + dictionary F1 = 0.65,
  dictionary 0.55 — see [docs/results.md](docs/results.md);
- ready but not yet run: transformer (XLM-R), trained in Colab:
  [notebooks/xlmr_colab.ipynb](notebooks/xlmr_colab.ipynb);
- missing: a human gold standard.

## Quick start

```bash
./run.sh                 # dev: backend :8000 + frontend :5173
./run.sh prod            # single port: http://localhost:8000
./run.sh --transformer   # + torch/transformers for XLM-R (the model must be in models/transformer/)
```

The first run creates `.venv` and installs the Python and Node dependencies.

## Requirements

- macOS or Linux
- Python 3.11+ (tested on 3.13.9)

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running tests

```bash
python -m pytest
```

## Web interface and API

Backend (FastAPI):

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs. Endpoints:

- `POST /api/analyze` — `{"text": "...", "method": "dictionary|crf|crf_gazetteer|transformer"}` → extracted
  terms; the models also find terms that are not in the dictionary (`in_dictionary: false`, `lemma` is a suggestion);
- `POST /api/check-terms` — check terms against ISO 704 and Uzbek spelling rules;
- `POST /api/term-profiles` — term profile: dictionary entry, norm check, thesaurus, equivalents;
- `GET /api/thesaurus` — automatically built thesaurus (`python -m app.ontology.thesaurus`);
- `GET /api/terms` — the term base;
- `GET /api/health` — status, text length limit and available extraction methods (with test F1);
- `GET /api/annotate/documents`, `GET|PUT /api/annotate/documents/{doc_id}...` — annotation;
- `GET|PUT /api/judgments/{annotator}` — candidate judging.

Frontend (Node 20+; details in [frontend/README.md](frontend/README.md)):

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 in your browser. Sections: **Analysis**, **Norm check** (`#check`),
**Thesaurus** (`#thesaurus`), **Annotation** (`#annotate`, guide section 7.1) and
**Candidate judging** (`#judge`). If port 8000 is busy, start the backend on another port and run
the frontend with `UZTERM_API_URL=http://127.0.0.1:<port> npm run dev`.

### Extraction methods ("Analysis" page)

| Method | Requirements | Test F1 (silver) |
|---|---|---|
| Dictionary | — | 0.55 |
| CRF, CRF + dictionary feature | `models/crf*.crfsuite` (included in the repo) | 0.61, 0.65 |
| XLM-R (transformer) | `pip install -r requirements-transformer.txt` and `models/transformer/` | 0.74 (reproduced on GPU and CPU) |

The XLM-R model (~1 GB) is not stored in git. Train it in `notebooks/xlmr_colab.ipynb` (GPU, ~10 minutes) or
locally (`PYTHONPATH=backend python -m app.models.transformer`, ~30 minutes on CPU). Cell 9 of the Colab notebook
saves the model to Google Drive as `uzterm-transformer.zip`; unzip it in the repository root:

```bash
unzip uzterm-transformer.zip      # -> models/transformer/
```

After restarting the server, the XLM-R method becomes available. The model is loaded on the first request
(a few seconds); a GPU (CUDA) or Apple Silicon (MPS) is used automatically when present.

## Analyzing text (CLI)

```bash
PYTHONPATH=backend python -m app.cli "Fonetika boʻlimida unli va undosh tovushlar oʻrganiladi."
```

You can also read from a file or stdin:

```bash
PYTHONPATH=backend python -m app.cli --file text.txt
```

To use a different term base: `--terms path/to/terms.json` or the `UZTERM_TERMS_PATH`
variable from `.env.example`.

The output is a JSON list. Each match contains:

| Field | Meaning |
|---|---|
| `surface` | the form found in the text (with its suffix) |
| `base_surface`, `suffix` | the form without the suffix, and the separated suffix |
| `start`, `end` | position, Python-style `[start, end)` |
| `term` | the main term (`null` for homonyms) |
| `method` | `dictionary_exact` or `dictionary_inflected` |
| `confidence` | `null` — the dictionary method does not compute probabilities |
| `ambiguous` | one form matched several entries |
| `review_required` | whether human review is needed |
| `candidates[]` | term entry: domain, definition, source, `match_type` (`term`/`variant`/`synonym`) and `normalization` (suggested normative form) |

## Data

`data/raw/` contains **41 linguistics articles** from Uzbek Wikipedia:
310 paragraphs, ~18 thousand words. The exact revision (revid) and license of each
are recorded in `data/sources.json`. The texts are **not yet annotated by humans**:
copies for annotation are in `data/inline/`.

Adding a new article:

```bash
PYTHONPATH=backend python -m app.dataset.fetch_wikipedia "Article title"
```

**License:** Wikipedia texts are licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). When distributing them
or annotations based on them, authors must be credited (via a link to the source) and
the result must also be released under CC BY-SA 4.0. Some linguistics articles in Uzbek
Wikipedia were copied from the National Encyclopedia of Uzbekistan; it is recommended
to mention this in the thesis as well.

## Statistical term candidates (stage 3)

Dictionary-independent term candidates from the corpus. Ranking methods:
frequency, TF-IDF and C-value. Precision@K is computed against a list of known terms.

```bash
PYTHONPATH=backend python -m app.nlp.candidates --method cvalue --top 30 --reference-terms data/terms.json --output reports/candidates-cvalue.csv
```

Human judging of candidates (blind template, then strict/lenient Precision@K and
Cohen's kappa; rules are in section 9 of the annotation guide):

```bash
PYTHONPATH=backend python -m app.evaluation.judgments template --rankings reports/candidates-*.csv --k 100 --output data/judgments/candidates-A1.csv
PYTHONPATH=backend python -m app.evaluation.judgments score --rankings reports/candidates-*.csv --judgments data/judgments/candidates-A1.csv
```

First results and their limitations: [docs/project-plan.md](docs/project-plan.md).

## Annotation (dataset)

Rules and format: [docs/data-annotation-guide.md](docs/data-annotation-guide.md).
Source registry: [data/sources.json](data/sources.json); annotated texts:
`data/annotated/*.jsonl`. Validation:

```bash
PYTHONPATH=backend python -m app.dataset.validate
```

Building JSONL from inline-annotated text (`[[Fonemalar|fonema]]`):

```bash
PYTHONPATH=backend python -m app.dataset.inline data/raw/doc-0001.txt --doc-id doc-0001 --annotator A1 -o data/annotated/doc-0001.jsonl
```

Splitting into train/validation/test at the source level (the split is frozen in
`data/splits/manifest.json`):

```bash
PYTHONPATH=backend python -m app.dataset.split
```

Evaluating the baseline (exact/partial Precision, Recall, F1 and error analysis;
methodology: [docs/experiment-methodology.md](docs/experiment-methodology.md)):

```bash
PYTHONPATH=backend python -m app.evaluation.evaluate data/processed/validation.jsonl --output reports/dictionary-validation.json
```

Format example (not part of the dataset):

```bash
PYTHONPATH=backend python -m app.dataset.validate docs/examples/annotation.example.jsonl --sources docs/examples/sources.example.json
```

## By stage (thesis plan)

| Stage | Where |
|---|---|
| 1. Dataset (BIO, JSONL) | `data/bio/sentences-100.jsonl` — 100 sentences, manually reviewed (`data/bio/review.txt`); `python -m app.dataset.bio sample / validate / export` |
| 2. Preprocessing | `app/nlp/clean.py` (cleaning, official apostrophes, sentence splitting), `normalize.py`, `tokenize.py` |
| 3. Features | `app/models/crf.py` → `token_features` |
| 4. Training, saving, loading | `python -m app.models.crf train / evaluate / predict` |
| 5. Normalization | `app/services/term_normalizer.py`; accuracy: `python -m app.evaluation.normalization` |
| 6. Evaluation | `python -m app.models.experiment`, `python -m app.evaluation.report` → [docs/experiments-table.md](docs/experiments-table.md) |
| 7. Web interface | `streamlit run streamlit_app.py` (plus React: analysis, annotation, judging) |
| 8. Thesis document | [docs/dissertation/](docs/dissertation/README.md) |
| Transformer (XLM-R) | `app/models/transformer.py`; Colab: [notebooks/xlmr_colab.ipynb](notebooks/xlmr_colab.ipynb) |

## AI annotation, dictionary and CRF

```bash
PYTHONPATH=backend python -m app.annotation.silver          # from data/silver/ lists -> data/annotations/claude/
PYTHONPATH=backend python -m app.dataset.split data/annotations/claude/*.jsonl --include-drafts --output-dir data/processed/silver
PYTHONPATH=backend python -m app.annotation.dictionary      # adds only train-set terms to the dictionary
PYTHONPATH=backend python -m app.models.experiment          # dictionary vs CRF, bootstrap; reports/, models/
PYTHONPATH=backend python -m app.annotation.agreement compare A1 A2
```

How the silver data was built: [data/silver/README.md](data/silver/README.md).
Results and limitations: [docs/results.md](docs/results.md).

## Term base

[data/terms.json](data/terms.json) is a JSON array. Fields:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | unique identifier |
| `term` | yes | the main term |
| `definition`, `domain` | no | definition and domain |
| `variants` | no | spelling variants |
| `synonyms` | no | synonymous terms (stored separately from variants) |
| `preferred_form` | no | normative form |
| `status` | no | `needs_review` (default) or `approved` |
| `source` | yes for `approved` | source |

The base is strictly validated on load: an unknown field, a duplicate `id`, a wrong
type or an `approved` entry without a source causes it to be rejected with a full list of errors.

> **Note:** the first 15 entries (`data/terms-seed.json`) are samples whose definitions
> were drafted by AI. The remaining 435 come from the **train** split of the AI
> annotation (without definitions). Polysemous words (`ot`, `sifat`, `gap`, ...)
> were deliberately left out. None of them have been verified against a scholarly source.
> All are in `needs_review` status, and the system shows them as "Suggestion — needs review".

## Project structure

```text
backend/app/main.py                     FastAPI app
backend/app/api/routes.py               /api/analyze, /api/terms, /api/health
backend/app/schemas.py                  Pydantic request/response models
backend/app/core/config.py              settings (UZTERM_TERMS_PATH, UZTERM_MAX_TEXT_CHARS)
backend/app/database/term_store.py      loading and validating the term base
backend/app/nlp/normalize.py            case and apostrophe normalization (length-preserving)
backend/app/nlp/dictionary_matcher.py   dictionary-based extractor
backend/app/services/normalization.py   normative form suggestions
backend/app/services/analyzer.py        shaping results as JSON
backend/app/cli.py                      command line interface
backend/app/dataset/sources.py          source registry validation
backend/app/dataset/annotation.py       JSONL annotation validation
backend/app/dataset/validate.py         validation CLI
backend/app/dataset/inline.py           JSONL from [[...]]-annotated text
backend/app/dataset/split.py            train/validation/test split by doc_id
backend/app/dataset/fetch_wikipedia.py  downloading Wikipedia articles with their sources
backend/app/evaluation/metrics.py       exact and partial Precision/Recall/F1
backend/app/evaluation/errors.py        error categories (missed, false_positive, boundary, ...)
backend/app/evaluation/evaluate.py      evaluation CLI and JSON report
backend/app/evaluation/ranking.py       Precision@K and coverage
backend/app/evaluation/judgments.py     human candidate judging: template, P@K, kappa
backend/app/nlp/tokenize.py             tokenizer and phrase chunking
backend/app/nlp/lemmatize.py            corpus-based suffix splitter
backend/app/nlp/stopwords.py            function word list (not verified)
backend/app/nlp/candidates.py           n-gram candidates, frequency/TF-IDF/C-value
backend/app/annotation/workspace.py     web annotation and judging workspace (file-based)
backend/app/annotation/agreement.py     inter-annotator agreement (span F1), promotion to gold standard
backend/app/annotation/silver.py        building AI annotation from lists
backend/app/annotation/dictionary.py    filling the dictionary with train-set terms
backend/app/models/crf.py               CRF term extractor (BIO): features, training, saving, CLI
backend/app/nlp/clean.py                text cleaning, official apostrophes, sentence splitting
backend/app/dataset/bio.py              BIO dataset: export, validation, 100-sentence set
backend/app/services/term_normalizer.py normalization: dictionary + morphology + izofa
backend/app/evaluation/normalization.py normalization accuracy
backend/app/evaluation/report.py        experiments table (docs/experiments-table.md)
backend/app/models/experiment.py        method comparison, bootstrap confidence intervals
streamlit_app.py                        Streamlit interface
backend/tests/                          pytest tests
frontend/                               React + TypeScript + Vite web interface
data/terms.json                         term base (450, needs_review); data/terms-seed.json — the first 15
data/silver/                            AI annotation lists and README
data/annotations/<annotator>/           work annotated in the web interface (claude — AI)
models/                                 trained CRF models (models/*.json — settings)
data/sources.json                       text sources and usage rights
data/raw/                               original texts (never modified)
data/inline/                            copies for annotation ([[...]] markup goes here)
data/judgments/                         human candidate judgments (one CSV per judge)
data/annotated/, data/processed/        JSONL annotations and split sets
data/splits/manifest.json               frozen split (created after running split)
docs/project-plan.md                    stage plan and limitations
docs/data-annotation-guide.md           annotation guide
docs/experiment-methodology.md          evaluation methodology
docs/results.md                         preliminary results (silver data)
docs/dissertation/                      thesis document (6 chapters)
data/bio/                               100-sentence BIO dataset and review notes
docs/examples/                          format examples (not part of the dataset)
reports/                                run outputs (candidate rankings)
```
