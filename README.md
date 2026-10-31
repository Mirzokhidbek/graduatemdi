# UzTerm AI

Oʻzbek tilidagi ona tili va tilshunoslikka oid matnlardan terminlarni avtomatik
aniqlash, tasniflash va meʼyorlashtirish prototipi (MDI loyihasi).

**Joriy holat** (batafsil — [docs/project-plan.md](docs/project-plan.md)):

- ishlaydi: lug'atga asoslangan termin aniqlagich (450 termin, tekshirilmagan),
  web interfeys: tahlil, **annotatsiya** va nomzodlarni baholash, REST API;
- tayyor: dataset vositalari (tekshiruv, train/val/test, annotatorlar kelishuvi),
  statistik nomzodlar (frequency, TF-IDF, C-value, POS filtri), **CRF modeli**;
- korpus: Vikipediyadan 41 ta tilshunoslik maqolasi. Hammasi **AI tomonidan**
  belgilangan (kumush maʼlumot, 2555 termin), inson annotatsiyasi kutilmoqda.
  Dastlabki natijalar (faqat kumush maʼlumotda): CRF + lug'at F1 = 0.65,
  lug'at 0.55 — [docs/results.md](docs/results.md);
- yo'q: transformer modeli, inson oltin standarti.

## Talablar

- macOS yoki Linux
- Python 3.11+ (3.13.9 da tekshirilgan)

## O'rnatish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Testlarni ishga tushirish

```bash
python -m pytest
```

## Web interfeys va API

Backend (FastAPI):

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

API hujjati: http://127.0.0.1:8000/docs. Endpointlar:

- `POST /api/analyze` — `{"text": "..."}` → topilgan terminlar;
- `GET /api/terms` — terminlar bazasi;
- `GET /api/health` — holat va matn uzunligi cheklovi;
- `GET /api/annotate/documents`, `GET|PUT /api/annotate/documents/{doc_id}...` — annotatsiya;
- `GET|PUT /api/judgments/{annotator}` — nomzodlarni baholash.

Frontend (Node 20+; batafsil — [frontend/README.md](frontend/README.md)):

```bash
cd frontend && npm install && npm run dev
```

Brauzerda http://localhost:5173 ni oching. Bo'limlar: **Tahlil**, **Belgilash**
(`#annotate`, yo'riqnoma 7.1) va **Nomzodlarni baholash** (`#judge`). Agar 8000-port band bo'lsa,
backendni boshqa portda ishga tushiring va frontendni
`UZTERM_API_URL=http://127.0.0.1:<port> npm run dev` bilan oching.

## Matnni tahlil qilish (CLI)

```bash
PYTHONPATH=backend python -m app.cli "Fonetika boʻlimida unli va undosh tovushlar oʻrganiladi."
```

Fayldan yoki stdin'dan o'qish ham mumkin:

```bash
PYTHONPATH=backend python -m app.cli --file matn.txt
```

Boshqa terminlar bazasini ishlatish: `--terms yo'l/terms.json` yoki `.env.example`
dagi `UZTERM_TERMS_PATH` o'zgaruvchisi.

Natija JSON ro'yxat ko'rinishida chiqadi. Har bir topilma uchun:

| Maydon | Maʼnosi |
|---|---|
| `surface` | matnda uchragan shakl (qo'shimchasi bilan) |
| `base_surface`, `suffix` | qo'shimchasiz shakl va ajratilgan qo'shimcha |
| `start`, `end` | pozitsiya, Python uslubidagi `[start, end)` |
| `term` | asosiy termin (omonim bo'lsa `null`) |
| `method` | `dictionary_exact` yoki `dictionary_inflected` |
| `confidence` | `null` — lug'at usuli ehtimollik hisoblamaydi |
| `ambiguous` | bitta shakl bir nechta yozuvga mos keldi |
| `review_required` | inson tekshiruvi kerakmi |
| `candidates[]` | termin yozuvi: soha, taʼrif, manba, `match_type` (`term`/`variant`/`synonym`) va `normalization` (meʼyoriy shakl tavsiyasi) |

## Maʼlumotlar

`data/raw/` da Oʻzbekcha Vikipediyadan olingan **41 ta tilshunoslik maqolasi**
bor: 310 paragraf, ~18 ming so'z. Har birining aniq versiyasi (revid) va
litsenziyasi `data/sources.json` da qayd qilingan. Matnlar **hali
belgilanmagan**: belgilash uchun nusxalar `data/inline/` da turibdi.

Yangi maqola qo'shish:

```bash
PYTHONPATH=backend python -m app.dataset.fetch_wikipedia "Maqola nomi"
```

**Litsenziya:** Vikipediya matnlari
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) ostida. Ularni va
ular asosidagi annotatsiyani tarqatishda mualliflar ko'rsatilishi (manba havolasi
orqali) va natija ham CC BY-SA 4.0 bilan tarqatilishi kerak. Oʻzbekcha
Vikipediyadagi tilshunoslik maqolalarining bir qismi Oʻzbekiston milliy
ensiklopediyasidan ko'chirilgan; MDI matnida buni ham ko'rsatish tavsiya etiladi.

## Statistik termin nomzodlari (3-bosqich)

Korpusdan lug'atga bog'liq bo'lmagan termin nomzodlari. Reyting usullari:
chastota, TF-IDF va C-value. Precision@K maʼlum terminlar ro'yxatiga nisbatan
hisoblanadi.

```bash
PYTHONPATH=backend python -m app.nlp.candidates --method cvalue --top 30 --reference-terms data/terms.json --output reports/candidates-cvalue.csv
```

Nomzodlarni inson baholashi (ko'r shablon, so'ng qatʼiy/yumshoq Precision@K va
Cohen's kappa; qoidalar — yo'riqnomaning 9-bo'limi):

```bash
PYTHONPATH=backend python -m app.evaluation.judgments template --rankings reports/candidates-*.csv --k 100 --output data/judgments/candidates-A1.csv
PYTHONPATH=backend python -m app.evaluation.judgments score --rankings reports/candidates-*.csv --judgments data/judgments/candidates-A1.csv
```

Birinchi natijalar va ularning cheklovlari: [docs/project-plan.md](docs/project-plan.md).

## Annotatsiya (dataset)

Qoidalar va format: [docs/data-annotation-guide.md](docs/data-annotation-guide.md).
Manbalar reyestri: [data/sources.json](data/sources.json), belgilangan matnlar:
`data/annotated/*.jsonl`. Tekshirish:

```bash
PYTHONPATH=backend python -m app.dataset.validate
```

Inline belgilangan matndan (`[[Fonemalar|fonema]]`) JSONL yaratish:

```bash
PYTHONPATH=backend python -m app.dataset.inline data/raw/doc-0001.txt --doc-id doc-0001 --annotator A1 -o data/annotated/doc-0001.jsonl
```

Manba darajasida train/validation/test ga ajratish (taqsimot
`data/splits/manifest.json` da muzlatiladi):

```bash
PYTHONPATH=backend python -m app.dataset.split
```

Baseline'ni baholash (exact/partial Precision, Recall, F1 va xato tahlili;
metodika: [docs/experiment-methodology.md](docs/experiment-methodology.md)):

```bash
PYTHONPATH=backend python -m app.evaluation.evaluate data/processed/validation.jsonl --output reports/dictionary-validation.json
```

Format namunasi (dataset emas):

```bash
PYTHONPATH=backend python -m app.dataset.validate docs/examples/annotation.example.jsonl --sources docs/examples/sources.example.json
```

## AI annotatsiyasi, lug'at va CRF

```bash
PYTHONPATH=backend python -m app.annotation.silver          # data/silver/ ro'yxatlaridan -> data/annotations/claude/
PYTHONPATH=backend python -m app.dataset.split data/annotations/claude/*.jsonl --include-drafts --output-dir data/processed/silver
PYTHONPATH=backend python -m app.annotation.dictionary      # lug'atga faqat train terminlari
PYTHONPATH=backend python -m app.models.experiment          # lug'at vs CRF, bootstrap; reports/, models/
PYTHONPATH=backend python -m app.annotation.agreement compare A1 A2
```

Kumush maʼlumot qanday tuzilgani: [data/silver/README.md](data/silver/README.md).
Natijalar va cheklovlar: [docs/results.md](docs/results.md).

## Terminlar bazasi

[data/terms.json](data/terms.json) — JSON massiv. Maydonlar:

| Maydon | Majburiy | Izoh |
|---|---|---|
| `id` | ha | noyob identifikator |
| `term` | ha | asosiy termin |
| `definition`, `domain` | yo'q | taʼrif va soha |
| `variants` | yo'q | yozuv variantlari |
| `synonyms` | yo'q | maʼnodosh terminlar (variantlardan alohida saqlanadi) |
| `preferred_form` | yo'q | meʼyoriy shakl |
| `status` | yo'q | `needs_review` (standart) yoki `approved` |
| `source` | `approved` uchun ha | manba |

Baza yuklanganda qatʼiy tekshiriladi: nomaʼlum maydon, takroriy `id`, noto'g'ri
tur yoki manbasiz `approved` bo'lsa, barcha xatolar ro'yxati bilan rad etiladi.

> **Diqqat:** dastlabki 15 ta yozuv (`data/terms-seed.json`) namuna, taʼriflarini
> Claude qoralama sifatida yozgan. Qolgan 435 tasi AI annotatsiyasining **train**
> to'plamidan olingan (taʼrifsiz). Ko'p maʼnoli so'zlar (`ot`, `sifat`, `gap`, ...)
> ataylab qo'shilmagan. Hech biri ilmiy manba bilan tekshirilmagan. Barchasi
> `needs_review` holatida, tizim ularni "Tavsiya — tekshirish kerak" deb ko'rsatadi.

## Tuzilma

```text
backend/app/main.py                   FastAPI ilovasi
backend/app/api/routes.py             /api/analyze, /api/terms, /api/health
backend/app/schemas.py                Pydantic so'rov/javob modellari
backend/app/core/config.py            sozlamalar (UZTERM_TERMS_PATH, UZTERM_MAX_TEXT_CHARS)
backend/app/database/term_store.py    bazani yuklash va tekshirish
backend/app/nlp/normalize.py          registr va apostrof normalizatsiyasi (uzunlik saqlanadi)
backend/app/nlp/dictionary_matcher.py lug'atga asoslangan aniqlagich
backend/app/services/normalization.py meʼyoriy shakl tavsiyasi
backend/app/services/analyzer.py      natijani JSON ko'rinishiga keltirish
backend/app/cli.py                    buyruq satri
backend/app/dataset/sources.py        manbalar reyestrini tekshirish
backend/app/dataset/annotation.py     JSONL annotatsiyani tekshirish
backend/app/dataset/validate.py       tekshiruvchi CLI
backend/app/dataset/inline.py         [[...]] belgili matndan JSONL yaratish
backend/app/dataset/split.py          doc_id bo'yicha train/validation/test ajratish
backend/app/dataset/fetch_wikipedia.py Vikipediya maqolalarini manbasi bilan yuklash
backend/app/evaluation/metrics.py     exact va partial Precision/Recall/F1
backend/app/evaluation/errors.py      xato toifalari (missed, false_positive, boundary, ...)
backend/app/evaluation/evaluate.py    baholash CLI va JSON hisobot
backend/app/evaluation/ranking.py     Precision@K va qamrov
backend/app/evaluation/judgments.py   nomzodlarni inson baholashi: shablon, P@K, kappa
backend/app/nlp/tokenize.py           tokenizator va iboralarga ajratish
backend/app/nlp/lemmatize.py          korpusga tayangan qo'shimcha ajratgich
backend/app/nlp/stopwords.py          yordamchi so'zlar ro'yxati (tekshirilmagan)
backend/app/nlp/candidates.py         n-gram nomzodlar, frequency/TF-IDF/C-value
backend/app/annotation/workspace.py   web annotatsiya va baholash ish joyi (fayllarga yozish)
backend/app/annotation/agreement.py   annotatorlar kelishuvi (span F1), oltin standartga o'tkazish
backend/app/annotation/silver.py      AI annotatsiyasini ro'yxatlardan yaratish
backend/app/annotation/dictionary.py  lug'atni train terminlari bilan to'ldirish
backend/app/models/crf.py             CRF termin aniqlagich (BIO)
backend/app/models/experiment.py      usullarni solishtirish, bootstrap ishonch oraliqlari
backend/tests/                        pytest testlari
frontend/                             React + TypeScript + Vite web interfeys
data/terms.json                       terminlar bazasi (450, needs_review); data/terms-seed.json — dastlabki 15 ta
data/silver/                          AI annotatsiyasi ro'yxatlari va README
data/annotations/<annotator>/         web interfeysda belgilangan ishlar (claude — AI)
models/                               o'qitilgan CRF modellari (models/*.json — sozlamalar)
data/sources.json                     matn manbalari va foydalanish huquqlari
data/raw/                             asl matnlar (o'zgartirilmaydi)
data/inline/                          belgilash uchun nusxalar ([[...]] shu yerda qo'shiladi)
data/judgments/                       nomzodlarga inson baholari (har bir baholovchi alohida CSV)
data/annotated/, data/processed/      JSONL annotatsiya va ajratilgan to'plamlar
data/splits/manifest.json             muzlatilgan taqsimot (split ishga tushgach paydo bo'ladi)
docs/project-plan.md                  bosqichlar rejasi va cheklovlar
docs/data-annotation-guide.md         annotatsiya yo'riqnomasi
docs/experiment-methodology.md        baholash metodikasi
docs/results.md                       dastlabki natijalar (kumush maʼlumot)
docs/examples/                        format namunalari (dataset emas)
reports/                              ishga tushirish natijalari (nomzodlar reytingi)
```
