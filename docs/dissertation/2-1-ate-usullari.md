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

Lingvistik ATE modellari terminning sintaktik tuzilishiga tayanadi: termin, odatda,
ot yoki ot birikmasi bo'ladi. Klassik qolip — Justeson va Katz (1995) taklif qilgan
`((A | N)+ | ((A | N)* (N P)?)(A | N)*) N`. Oʻzbek tili uchun ikki muammo bor:

1. Ochiq va tekshirilgan POS-tegger yo'q.
2. Agglyutinativ tuzilish: so'z birikmasidagi bog'lanish so'z tartibi bilan emas,
   qo'shimcha bilan ifodalanadi. Aniqlovchi ot qo'shimcha olmaydi (*soʻz turkumi*),
   qaratqich kelishigidagi so'z esa erkin birikma hosil qiladi (*gapning boʻlagi* —
   termin emas, *gap boʻlagi* — termin).

Shu sababli so'z turkumi **morfologik qoidalar** bilan taxminiy aniqlanadi
(`app/nlp/patterns.py`, `MorphTagger`):

| Teg | Qoida | Misol |
|---|---|---|
| `FUNC` | yordamchi so'z, ko'makchi, son, olmosh ro'yxati | *va, koʻra, xos, bir* |
| `NOUN` | ot yasovchi qo'shimchalar (*-lik, -shunoslik, -ish, -uv, -iya, -ika, -ema, -izm*) | *tilshunoslik, yasash, fonema* |
| `VERB` | fe'l, sifatdosh, ravishdosh shakllari (*-adi, -gan, -moq, -ib, -gach*) | *yoziladi, oʻrganadigan* |
| `ADJ` | nisbiy sifat (*-tik, -iy, -li, -siz, -vchi*) yoki aniqlovchi so'zlar ro'yxati | *grammatik, undosh, qoʻshma* |
| `NOUN` | qolgan so'zlar | *tovush, gap* |

Termin qolipi:

```text
T = (ADJ | NOUN₀)* NOUN,     1 ≤ |T| ≤ 4,
```

bu yerda NOUN₀ — **qo'shimchasiz** ot (korpus lemmatizatori bo'yicha so'zning o'zi
uning lemmasi), oxirgi NOUN (bosh so'z) esa istalgan qo'shimcha bilan keladi. Qolip
tinish belgisini kesib o'tmaydi.

Model ikki xil ishlatiladi:

1. **Matndan to'g'ridan-to'g'ri ajratish** (`PatternExtractor`). Har bir iborada
   chapdan o'ngga eng uzun mos zanjir olinadi, bosh so'zdan keyin yangi zanjir
   boshlanadi. Bu sof lingvistik model: unda statistika ham, lug'at ham yo'q.
2. **Statistik nomzodlar uchun filtr** (`--pattern-filter`). Qolipga mos kelmagan
   n-gramlar reytingdan chiqariladi. Bu gibrid model (2.1.5-bo'lim).

Gibrid span modeli (`pattern + ball`) qolip zanjirini faqat uning statistik bali
(C-value, NC-value yoki Weirdness) θ chegaradan yuqori bo'lsa qabul qiladi. Aks holda
zanjirning bosh so'z bilan tugaydigan qisqaroq qismlari tekshiriladi:
*jarangli undosh tovushlar* rad etilsa, *undosh tovushlar* sinaladi. Ballar butun
soha korpusi bo'yicha belgisiz hisoblanadi, θ esa faqat validation to'plamida
tanlanadi (`app/models/pattern_experiment.py`).

### 2.1.4. Statistik modellar (TF-IDF, C-value, NC-value, Weirdness)

Nomzodlar 1–4 so'zli n-gramlar. Ular tinish belgisini kesib o'tmaydi va yordamchi
so'z bilan boshlanmaydi yoki tugamaydi. Oxirgi so'z lemmatizatsiya qilinadi.

- **TF-IDF:** f(a) · (ln((1 + N) / (1 + df(a))) + 1).
- **C-value** (Frantzi, Ananiadou, Mima, 2000):
  - C(a) = log₂(|a| + 1) · f(a), agar a boshqa nomzod ichida bo'lmasa;
  - aks holda C(a) = log₂(|a| + 1) · (f(a) − Σ_{b∈Tₐ} f(b) / |Tₐ|).
- **NC-value** (Frantzi, Ananiadou, Mima, 2000). C-value'ga terminning kontekstini
  qo'shadi. Terminlar yonida keladigan so'zlar (*tovush*, *qoʻshimcha* oldidagi
  *jarangli*, *kelishik*) boshqa terminlar yonida ham kelishi kutiladi:
  - weight(w) = t(w) / n, bu yerda n — C-value bo'yicha eng yuqori 100 ta nomzod
    ("termin namunasi"), t(w) — w ulardan nechtasining kontekstida uchragani;
  - NC(a) = 0.8 · C(a) + 0.2 · Σ_{w∈Cₐ} f_a(w) · weight(w), bu yerda Cₐ — a ning
    kontekst so'zlari, f_a(w) — w ning a yonida uchrashlar soni.

  Kontekst — nomzoddan bevosita oldin va keyin kelgan bittadan so'z (lemma),
  yordamchi so'zlarsiz va tinish belgisini kesib o'tmasdan. Asl usulda kontekst
  so'zlari ot, sifat va fe'l bilan cheklanadi; bu yerda faqat yordamchi so'zlar
  chiqariladi.
- **Weirdness** (Ahmad va boshq., 1999): W(a) = (f(a)/N_d) / ((f_c(a)+1)/(N_c+V)).
  Kontrast korpus talab qiladi.
- **POS filtri.** Morfologik qoida: oxirgi so'zi fe'l, sifatdosh, ravishdosh
  (*-adi, -gan, -moq, -ib, …*) yoki nisbiy sifat (*-tik, -gik, -iy, …*) shaklida
  bo'lgan nomzod chiqariladi. *-lik* otlari bundan mustasno. Natijada "sifat + ot"
  andozasi (*grammatik kategoriya*) qoladi.

### 2.1.5. Statistik modellar bo'yicha tajriba

#### Nomzodlar reytingi (Precision@K)

Nomzodlar 1–4 so'zli n-gramlar bo'yicha ajratildi. Reyting usullari: frequency, TF-IDF,
C-value, NC-value hamda 48 ta maqoladan iborat kontrast korpus asosidagi Weirdness
(Ahmad va boshq., 1999). Dastlabki uchta usulning top-100 nomzodlari birlashtirilib
(119 ta), ikki inson baholovchi (A1, A2) tomonidan ko'r holda baholandi.
Kelishmovchiliklar hakam tomonidan hal qilindi (`data/judgments/candidates-adjudicated.csv`;
hakam — Claude, AI). Keyingi usullarning top-K ro'yxatlarida bu 119 ta nomzoddan
tashqaridagilari ham bor. Ular termin emas deb sanaladi, shuning uchun bunday
qiymatlar "≥" bilan, pastki chegara sifatida berilgan. Yangi 100 ta nomzod
A1 va A2 fayllariga baholash uchun qo'shildi.

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
| NC-value | 0.30 | 0.35 | 0.40 | 0.37 |
| NC-value + POS filtri | 0.40 | 0.40 | 0.40 | ≥ 0.39 |
| frequency + qolip (lingvistik model) | 0.50 | 0.40 | 0.42 | ≥ 0.37 |
| C-value + qolip | 0.40 | 0.50 | 0.46 | ≥ 0.38 |
| NC-value + qolip | 0.40 | 0.45 | 0.44 | ≥ 0.38 |
| **Weirdness + qolip** | **0.90** | **0.90** | ≥ 0.58 | ≥ 0.30 |

POS filtri fe'l va nisbiy sifat shakllarini (*yoziladi*, *grammatik*) chiqarib,
reytingning yuqori qismini tozalaydi. Kontrast korpus yordamida hisoblangan
**Weirdness** o'lchovi esa barcha usullardan sezilarli darajada ustun kelib,
P@10 va P@20 da 0.90 aniqlikka erishdi (A1 bahosida hatto 1.00). Bu umumiy tilshunoslik
so'zlari o'rniga sof terminlarni tanlashda kontrast korpusning hal qiluvchi rolini isbotlaydi.

**NC-value** bu korpusda C-value'ni yaxshilamadi (P@10 0.40 → 0.30, qolganlari
teng). Sabab: eng og'ir kontekst so'zlari terminologik emas, umumiy so'zlar —
*soʻz* (weight = 0.55), *til* (0.48), *maʼno* (0.33), *xos* (0.27). Korpus bitta
sohadan bo'lgani uchun "termin namunasi"ning o'zi ham umumiy tilshunoslik
leksikasidan iborat va kontekst og'irligi shu so'zlarni yana yuqoriga ko'taradi.
NC-value g'oyasi kontrast korpus bilan birga ishlatilganda (masalan, namunani
Weirdness bo'yicha olish) foydali bo'lishi mumkin.

**Leksik-grammatik qolip** filtri sifatida C-value'ni P@20 da 0.35 dan 0.50 ga,
P@50 da 0.40 dan 0.46 ga oshirdi. U *koʻra*, *xos*, *yoziladi*, *grammatik* kabi
nomzodlarni olib tashlaydi, ammo *soʻz*, *til* kabi umumiy otlarni ajrata olmaydi:
ular qolipga mos keladi. Bu vazifani Weirdness bajaradi.

#### Lingvistik, statistik va gibrid modellar: span darajasida

Qolip modeli matndagi terminlarni ham ajratadi, shuning uchun uni CRF bilan bir xil
sharoitda (kumush test, exact span) baholash mumkin.

**2.1a-jadval.** Test (35 paragraf, 380 span), exact span bo'yicha.
Hisobot: `reports/experiment-patterns.json`.

| Usul | P | R | F1 | F1, 95 % oraliq | Qolipdan farq, 95 % | Yangi terminlar (146) |
|---|---|---|---|---|---|---|
| Qolip (lingvistik) | 0.184 | **0.655** | 0.288 | [0.225, 0.355] | — | **100 (0.685)** |
| Qolip + C-value | 0.212 | 0.492 | 0.296 | [0.247, 0.348] | [−0.046, +0.060] | 24 (0.164) |
| Qolip + NC-value | 0.214 | 0.495 | 0.299 | [0.249, 0.351] | [−0.044, +0.062] | 24 (0.164) |
| **Qolip + Weirdness** | 0.513 | 0.416 | **0.459** | [0.388, 0.518] | **[+0.081, +0.259]** | 22 (0.151) |
| Lug'at (train) | 0.770 | 0.432 | 0.553 | [0.471, 0.628] | [+0.140, +0.391] | 0 |
| CRF | 0.715 | 0.534 | 0.611 | [0.527, 0.690] | [+0.210, +0.436] | 31 (0.212) |
| CRF + gazetteer | 0.792 | 0.550 | 0.649 | [0.566, 0.719] | [+0.244, +0.478] | 2 (0.014) |

Chegaralar validation'da tanlandi: C-value ≥ 2.32, NC-value ≥ 1.87, Weirdness ≥ 17.5.

1. **Sof lingvistik model** eng yuqori recall'ga ega (0.655) va train'da uchramagan
   terminlarning 68.5 % ini topadi — CRF dan (21 %) uch baravar ko'p. Lekin har
   beshta spandan faqat bittasi termin (P = 0.18): qolip *soni*, *harf*, *bayon* kabi
   har qanday otni oladi.
2. **Qolip + Weirdness** gibrid modeli F1 ni 0.288 dan 0.459 ga oshiradi va bu farq
   statistik ishonchli. C-value va NC-value esa sof qolipdan ishonchli farq qilmaydi:
   ular ham umumiy otlarni yuqori baholaydi.
3. **Nazoratli modellar** (lug'at, CRF) ancha yuqori natija beradi, chunki ular
   annotatsiyadan o'rganadi. Lingvistik va gibrid modellar esa belgilangan maʼlumot
   talab qilmaydi. Shu sababli ularning amaliy o'rni — **yangi terminlarni topish**
   va lug'atni to'ldirish uchun nomzodlar berish (yuqori recall), CRF ning esa —
   aniq belgilash.

