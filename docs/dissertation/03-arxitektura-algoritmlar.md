# 3-bob. Tizim arxitekturasi va algoritmlar

## 3.1. Umumiy arxitektura

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

## 3.2. Preprocessing

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

## 3.3. Lug'atga asoslangan aniqlagich

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

## 3.4. CRF modeli

**Model.** Chiziqli zanjirli shartli tasodifiy maydon (linear-chain CRF; Lafferty,
McCallum, Pereira, 2001). Tokenlar ketma-ketligi x = (x₁, …, xₙ) berilganda teglar
ketma-ketligi y = (y₁, …, yₙ), yᵢ ∈ {O, B-TERM, I-TERM} ning shartli ehtimoli:

```text
p(y | x) = (1 / Z(x)) · exp( Σᵢ Σₖ λₖ fₖ(yᵢ₋₁, yᵢ, x, i) ),
Z(x)     = Σ_{y'} exp( Σᵢ Σₖ λₖ fₖ(y'ᵢ₋₁, y'ᵢ, x, i) )
```

- fₖ — xususiyat funksiyalari: holat xususiyatlari "token xususiyati × teg" va
  o'tish xususiyatlari "teg × teg";
- λₖ — ularning og'irliklari.

**O'qitish.** Elastic net (L1 + L2) regulyarizatsiyali shartli log-ehtimollikni
maksimallashtirish, L-BFGS (OWL-QN) usuli bilan, CRFsuite kutubxonasida (Okazaki, 2007):

```text
L(λ) = Σ_(x,y) log p(y | x) − c₁ ‖λ‖₁ − c₂ ‖λ‖₂²
```

c₁ va c₂ validation to'plamida {0.01, 0.1, 0.5} × {0.01, 0.05, 0.2} to'r bo'yicha
tanlanadi. Tanlangan qiymatlar: c₁ = 0.1, c₂ = 0.01. Iteratsiyalar soni 200.

**Dekodlash.** Viterbi algoritmi. BIO dan span'ga o'tishda yetim `I-TERM`
(oldida `O` turgan) yangi span boshlaydi (yumshoq dekodlash).

**Xususiyatlar** (`token_features`):

| Guruh | Xususiyatlar | Asos |
|---|---|---|
| Leksik | so'z (kichik harf), korpus lemmatizatori bo'yicha o'zak | terminlarning o'zi takrorlanadi |
| Morfologik | oxirgi 2, 3, 4, 5 harf; boshidagi 3 harf | termin yasovchi qo'shimchalar (*-logiya, -ika, -shunoslik, -ema, -izm*), yunon-lotin o'zaklari (*fono-, morf-*) |
| Orfografik | registr shakli (UPPER / Title / lower), uzunlik (≤ 12), apostrof bor-yo'qligi | gap boshidagi taʼrif (*Fonema — …*) |
| Kontekst | ±1, ±2 qo'shni so'z va ularning o'zagi; ±1 qo'shnining oxirgi 3 harfi va registri; bigramlar `w₋₁|w₀`, `w₀|w₊₁` | ko'p so'zli terminlar (*qoʻshma gap*), taʼrif konstruksiyalari |
| Gazetteer (ixtiyoriy) | token train lug'ati moslashtirgichi topgan spanning `B/I/O` qismi; ±2 qo'shnilar uchun ham | lug'at bilimini kontekst bilan birlashtirish |

O'qitilgan modellar:

| Model | Holat xususiyatlari | Eng katta og'irliklar |
|---|---|---|
| `crf` | 6 065 | `lemma=boʻgʻin`, `lemma=oʻzak`, `lemma=fonema`, `pre3=feʼ`, `-1:suf3=hma → I-TERM` (*qoʻshma gap*) |
| `crf-gazetteer` | 3 130 | `gaz=I-TERM → I-TERM`, `gaz=B-TERM → B-TERM` |

Gazetteer belgisi qo'shilganda leksik xususiyatlar soni ikki baravar kamayadi:
model lug'at belgisiga tayanadi. Bu 4-bobdagi "yangi terminlar" natijasini
tushuntiradi.

## 3.5. Statistik termin nomzodlari

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

## 3.6. Meʼyorlashtirish algoritmi

Kirish: span matni s. Chiqish: lug'at shakli, asosiy termin, holat.

```text
1. Lug'at:  s butunligicha lug'at shakliga (qo'shimchalar va tovush o'zgarishlari bilan)
            mos kelsa → lug'at shakli = mos kelgan shakl (sinonim bo'lsa — o'zi),
            asosiy termin = yozuvning termini, holat = approved | needs_review.
2. Morfologiya: oxirgi so'z w uchun eng qisqa o'zak s₀ (≥ 3 harf) va qo'shimchalar zanjiri:
            w = s₀ · (lar)?(egalik)?(kelishik)?(ki)?(yuklama)?
            shartlar: (a) s₀ yoki uning tiklangan shakli (g→k, gʻ→q, CC→CiC/CuC)
                          korpus yoki lug'at so'zi;
                      (b) fonotaktika: -ka faqat k dan, -qa faqat q dan keyin
                          (egalikdan keyin hech qachon — "lingvistika" ≠ "lingvist"+"i"+"ka").
            (a) bajarilmasa (yangi so'z): faqat aniq ko'plik yoki kelishik
            qo'shimchasi ajratiladi (o'zak ≥ 5 harf).
3. Izofa:  ko'p so'zli terminda oxirgi so'zda III shaxs egaligi (-i/-si) bo'lsa va
            oldingi so'z sifat bo'lmasa, egalik saqlanadi:
            "soʻz birikmalari" → "soʻz birikmasi", "gap boʻlaklarini" → "gap boʻlagi"
            (ko'p bo'g'inli o'zakda k→g, q→gʻ). Sifat: -tik, -iy, -li, -siz, -gan, -vchi
            yoki ro'yxat (undosh, unli, sodda, qoʻshma, …): "undosh tovushlari" → "undosh tovush".
4. Faqat oxirgi so'z almashtiriladi; ichki so'zlar va defislar saqlanadi;
   apostroflar rasmiy shaklga keltiriladi.
   2–3-qadam natijasining holati: no_data ("lug'atda yo'q — tekshirish kerak").
```

Murakkablik: lug'at bosqichi O(|L| · n) (|L| — lug'at shakllari, n — matn uzunligi);
morfologiya bosqichi bitta so'z uchun O(|w|²).
