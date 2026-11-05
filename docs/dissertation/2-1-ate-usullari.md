# II BOB. TERMINLARNI AVTOMATIK ANIQLASH (ATE) VA ISHLAB CHIQISHNING MATEMATIK VA KOMPYUTER MODELLARI

## 2.1. Matnlardan terminologik birliklarni avtomatik ajratib olish (Automatic Term Extraction — ATE) usullari

### 2.1.1. Tizim arxitekturasi

```text
                ┌──────────────────────────── Preprocessing ───────────────────────────┐
 matn ──────────►  clean_text → canonical_apostrophes → split_sentences → tokenize      │
                └──────────────────────────────────┬────────────────────────────────────┘
                                                   │ normalize_text (1:1, qidiruv uchun)
                     ┌─────────────────────────────┼─────────────────────────────┐
                     ▼                             ▼                             ▼
          DictionaryMatcher               CRF (BIO teglash)            Statistik nomzodlar
     (lug'at + qo'shimchalar +       xususiyatlar: so'z, o'zak,      (frequency, TF-IDF,
      tovush o'zgarishlari)          qo'shimchalar, ±2 kontekst,      C-value, weirdness,
                     │               gazetteer ◄── lug'at            POS filtri)
                     └──────────────┬──────────────┘
                                    ▼ spanlar [start, end)
                         TermNormalizer: lug'at → morfologiya → izofa
                                    ▼
             JSON / CSV / BIO  ·  REST API (FastAPI)  ·  React va Streamlit interfeyslari
```

| Qatlam | Modul |
|---|---|
| Preprocessing | `app/nlp/clean.py`, `normalize.py`, `tokenize.py` |
| Aniqlash | `app/nlp/dictionary_matcher.py`, `app/models/crf.py`, `app/nlp/candidates.py` |
| Meʼyorlashtirish | `app/services/term_normalizer.py` |
| Maʼlumot | `app/dataset/` (annotatsiya, BIO, split), `app/annotation/` (web ish joyi, kelishuv) |
| Baholash | `app/evaluation/` (metrikalar, xato tahlili, meʼyorlashtirish, jadval), `app/models/experiment.py` |
| Interfeys | `app/main.py` (REST), `frontend/` (React), `streamlit_app.py` |

### 2.1.2. Matnni dastlabki qayta ishlash

**Apostroflar.** Oʻzbek lotin yozuvida *oʻ, gʻ* va tutuq belgisi uchun amalda
kamida to'qqiz xil belgi ishlatiladi: `' ` ´ ʹ ʻ ʼ ‘ ’ ′`. Tizimda ular ikki xil
qayta ishlanadi:

- `normalize_text` — qidiruv uchun. Barcha variantlar bitta `'` ga keltiriladi,
  registr kichik harfga o'tadi. Har bir belgi bitta belgiga almashadi, shuning uchun
  normallashgan matndagi pozitsiyalar asl matnga to'g'ridan-to'g'ri mos keladi.
  Uzunligi o'zgaradigan belgilar (masalan, `İ`) o'zgartirilmaydi.
- `canonical_apostrophes` — saqlash va ko'rsatish uchun. Rasmiy shaklga keltiradi:
  `o`/`g` dan keyin `ʻ` (U+02BB); so'z ichidagi boshqa holatlarda `ʼ` (U+02BC);
  so'z chetidagi qo'shtirnoq vazifasidagi belgi o'zgarmaydi.

**Tozalash** (`clean_text`, yangi matnni korpusga qo'shishda):

- Unicode NFC;
- ko'rinmas belgilar, `== sarlavha ==` qatorlari va `[1]` havolalari olib tashlanadi;
- ortiqcha bo'shliqlar qisqartiriladi;
- apostroflar rasmiy shaklga keltiriladi.

**Gaplarga ajratish** (`split_sentences`). Chegara: `. ! ? …` belgisidan keyin
bo'shliq va bosh harf (raqam, ochuvchi qo'shtirnoq). Nuqtadan oldingi so'z qisqartma
bo'lsa (*Mas., mil. av., yun., St.*, bir harfli bosh harflar *N. S.*), chegara
qo'yilmaydi.

**Tokenlash.** Token — harflar ketma-ketligi. So'z ichidagi apostrof tokenning
bir qismi (*soʻz*, *maʼno*).

### 2.1.3. Leksik-grammatik va sintaktik qoliplarga asoslangan (lingvistik) modellar

#### Lug'atga asoslangan aniqlagich

Lug'atdagi har bir shakl (termin, variant, sinonim) uchun muntazam ifoda tuziladi.
U quyidagi qismlardan iborat:

- **chegaralar:** oldida va keyin harf yoki so'z ichidagi apostrof bo'lmasligi;
- **ko'p so'zli shakl:** so'zlar orasida istalgan bo'shliq bo'lishi mumkin;
- **qo'shimchalar zanjiri** oxirgi so'zdan keyin, tartib bilan:

```text
(lar)? (imiz|ingiz|miz|ngiz|ing|im|ng|m|si|i)? (gacha|dagi|ning|dan|ni|ga|ka|qa|da)? (ki)? (dir|dek|mi)?
```

**Tovush o'zgarishlari** (`stem_alternations`). Unli bilan boshlanuvchi egalik
qo'shimchasi (`-i, -im, -ing, -imiz, -ingiz`) oldida o'zakning muqobil shakli ham
qidiriladi:

- jarangsizlanish: `k → g` (*kelishik → kelishigi*), `q → gʻ` (*qishloq → qishlogʻi*);
- tor unli tushishi: `…C(i|u)C → …CC` (*oʻrin → oʻrni*, *burun → burni*).

Qoida faqat egalik qo'shimchasi bilan birga qo'llanadi va butun o'zak mos kelishi
shart. Shu sababli noto'g'ri moslik ehtimoli kichik.

**Ustma-ust tushish.** Barcha mosliklardan ochko'z (greedy) algoritm bilan
kesishmaydigan to'plam tanlanadi. Tartib: avval uzunroq span, keyin qo'shimchasi
qisqarog'i, keyin matnda oldinroq kelgani. *undosh tovush* ichidagi *tovush*
alohida chiqmaydi.

#### Leksik-grammatik qoliplar

> **TODO.** Bu bo'lim hali yozilmagan. Reja: [../dissertation-plan.md](../dissertation-plan.md), B1 bosqich.

### 2.1.4. Statistik modellar (TF-IDF, C-value, NC-value, Weirdness)

Nomzodlar 1–4 so'zli n-gramlar. Ular tinish belgisini kesib o'tmaydi va yordamchi
so'z bilan boshlanmaydi yoki tugamaydi. Oxirgi so'z lemmatizatsiya qilinadi.

- **TF-IDF:** f(a) · (ln((1 + N) / (1 + df(a))) + 1).
- **C-value** (Frantzi, Ananiadou, Mima, 2000):
  - C(a) = log₂(|a| + 1) · f(a), agar a boshqa nomzod ichida bo'lmasa;
  - aks holda C(a) = log₂(|a| + 1) · (f(a) − Σ_{b∈Tₐ} f(b) / |Tₐ|).
- **Weirdness** (Ahmad va boshq., 1999): W(a) = (f(a)/N_d) / ((f_c(a)+1)/(N_c+V)).
  Kontrast korpus talab qiladi.
- **POS filtri.** Morfologik qoida: oxirgi so'zi fe'l, sifatdosh, ravishdosh
  (*-adi, -gan, -moq, -ib, …*) yoki nisbiy sifat (*-tik, -gik, -iy, …*) shaklida
  bo'lgan nomzod chiqariladi. *-lik* otlari bundan mustasno. Natijada "sifat + ot"
  andozasi (*grammatik kategoriya*) qoladi.

### 2.1.5. Statistik modellar bo'yicha tajriba

Nomzodlar 1–4 so'zli n-gramlar bo'yicha ajratildi. Reyting usullari: frequency, TF-IDF, C-value hamda 48 ta maqoladan iborat kontrast korpus asosidagi Weirdness (Ahmad va boshq., 1999). 119 ta nomzod mustaqil inson baholovchilar (A1, A2) tomonidan ko'r holda baholandi, shuningdek kelishmovchiliklar tilshunoslik tahlili orqali hakamlik (Adjudicated) konsensusiga keltirildi (`data/judgments/`).

Baholovchilararo kelishuv: A1 ↔ A2 Cohen's kappa = 0.474 (o'rtacha kelishuv — umumiy tilshunoslik leksikasida farqlar bo'lgan). Hakamlik bahosi bilan A1 va A2 ning kelishuvi esa mos ravishda kappa = 0.779 va 0.804 ni tashkil etdi.

**2.1-jadval.** Precision@K natijalari (hakamlik / konsensus bahosi bo'yicha, qatʼiy hisob):

| Usul | P@10 | P@20 | P@50 | P@100 |
|---|---|---|---|---|
| frequency | 0.40 | 0.35 | 0.34 | 0.34 |
| TF-IDF | 0.40 | 0.55 | 0.42 | 0.40 |
| C-value | 0.40 | 0.35 | 0.40 | 0.37 |
| frequency + POS filtri | 0.50 | 0.40 | 0.40 | ≥ 0.38 |
| TF-IDF + POS filtri | 0.50 | 0.65 | 0.46 | ≥ 0.43 |
| C-value + POS filtri | 0.40 | 0.40 | 0.42 | ≥ 0.39 |
| **Weirdness** | 0.80 | 0.80 | ≥ 0.58 | ≥ 0.32 |
| **Weirdness + POS filtri** | **0.90** | **0.90** | **≥ 0.60** | ≥ 0.32 |

POS filtri fe'l va nisbiy sifat shakllarini (*yoziladi*, *grammatik*) chiqarib,
reytingning yuqori qismini tozalaydi. Kontrast korpus yordamida hisoblangan
**Weirdness** o'lchovi esa barcha usullardan sezilarli darajada ustun kelib,
P@10 va P@20 da 0.90 aniqlikka erishdi (A1 bahosida hatto 1.00). Bu umumiy tilshunoslik
so'zlari o'rniga sof terminlarni tanlashda kontrast korpusning hal qiluvchi rolini isbotlaydi.
