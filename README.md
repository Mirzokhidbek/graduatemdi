# UzTerm AI

Oʻzbek tilidagi ona tili va tilshunoslikka oid matnlardan terminlarni avtomatik
aniqlash, tasniflash va meʼyorlashtirish prototipi (MDI loyihasi).

**Joriy holat:** 1-bosqich — lug'atga asoslangan baseline. Web-interfeys, API,
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
backend/tests/                        pytest testlari
data/terms.json                       terminlar bazasi (namuna)
data/raw, processed, annotated        2-bosqich datasetlari uchun
docs/project-plan.md                  bosqichlar rejasi va cheklovlar
```
