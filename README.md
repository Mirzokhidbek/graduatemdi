# UzTerm AI

Oʻzbek tilidagi ona tili va tilshunoslikka oid matnlardan terminlarni avtomatik
aniqlash, tasniflash va meʼyorlashtirish prototipi (MDI loyihasi).

**Joriy holat:** 1-bosqich (lug'atga asoslangan baseline) tayyor; 2-bosqich
(dataset) boshlandi — annotatsiya yo'riqnomasi, JSONL formati va tekshiruvchi
skript, inline belgidan JSONL yaratuvchi va to'plamlarga ajratuvchi vositalar hamda baholash skripti bor, lekin belgilangan maʼlumot hali yo'q, shuning uchun aniqlik hali o'lchanmagan. Web-interfeys, API,
statistik va ML modellari hali yo'q (rejani [docs/project-plan.md](docs/project-plan.md) da ko'ring).

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

> **Diqqat:** hozirgi 15 ta yozuv faqat namuna. Taʼriflarni Claude qoralama
> sifatida yozgan, ular ilmiy manba bilan tekshirilmagan. Shuning uchun barchasi
> `needs_review` holatida va `source: null`. Tizim ularni faqat
> "Tavsiya — tekshirish kerak" deb ko'rsatadi.

## Tuzilma

```text
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
backend/app/evaluation/metrics.py     exact va partial Precision/Recall/F1
backend/app/evaluation/errors.py      xato toifalari (missed, false_positive, boundary, ...)
backend/app/evaluation/evaluate.py    baholash CLI va JSON hisobot
backend/tests/                        pytest testlari
data/terms.json                       terminlar bazasi (namuna)
data/sources.json                     matn manbalari va foydalanish huquqlari
data/raw, processed, annotated        asl matnlar, ajratilgan to'plamlar, annotatsiya
data/splits/manifest.json             muzlatilgan taqsimot (split ishga tushgach paydo bo'ladi)
docs/project-plan.md                  bosqichlar rejasi va cheklovlar
docs/data-annotation-guide.md         annotatsiya yo'riqnomasi
docs/experiment-methodology.md        baholash metodikasi
docs/examples/                        format namunalari (dataset emas)
```
