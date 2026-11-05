## 2.2. Mashinali o'qitish va chuqur o'qitish algoritmlari asosida terminlarni aniqlash

> Barcha natijalar **AI annotatsiyasi** (kumush maʼlumot) bo'yicha. To'liq jadval
> `docs/experiments-table.md` da, xom natijalar `reports/*.json` da.

### 2.2.1. Tajriba sxemasi

1. Train / validation / test manba darajasida ajratilgan (A.5-ilova).
2. Lug'at va CRF faqat train'da quriladi (o'qitiladi).
3. Giperparametrlar va qoidalar validation'da sozlanadi.
4. Test har bir konfiguratsiya uchun bir marta baholanadi.
5. Test xatolari tahlilidan keyin tizimga kiritilgan o'zgarish alohida
   hujjatlashtiriladi va natija "test bo'yicha sozlangan" deb belgilanadi (3.1.2).

Taqqoslangan usullar:

| Belgi | Usul |
|---|---|
| D-15 | dastlabki 15 terminli namuna lug'at |
| D-train | train terminlari bilan to'ldirilgan lug'at (450) |
| CRF | 2.2.3-bo'limdagi model, gazetteersiz |
| CRF+G | CRF + train lug'ati gazetteer xususiyati |

### 2.2.2. Metrikalar

Spanlar exact mezon bo'yicha solishtiriladi: `[start, end)` aynan teng bo'lsa
to'g'ri. Partial mezonda kamida bitta belgi ustma-ust tushishi yetarli. Barcha
metrikalar micro-average (CoNLL-2003 an'anasi; Tjong Kim Sang, De Meulder, 2003):

```text
P  = |G ∩ S| / |S|,    R = |G ∩ S| / |G|,    F1 = 2PR / (P + R)
```

Bu yerda G — oltin spanlar, S — bashorat qilingan spanlar.

**Ishonch oralig'i.** Paragraflar bo'yicha bootstrap (Efron, Tibshirani, 1993):
B = 2000 ta qayta tanlanma, 2.5 va 97.5 persentil. Usullar farqi uchun juftlangan
bootstrap: har bir qayta tanlanmada ikkala usulning F1 farqi hisoblanadi.

**Meʼyorlashtirish aniqligi.** Oltin span matni uchun bashorat qilingan lug'at
shakli oltin `term` ga (registr va apostrof farqisiz) teng bo'lgan spanlar ulushi.

### 2.2.3. CRF modeli

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

### 2.2.4. Transformer modeli (token classification)

CRF bilan solishtirish uchun ko'p tilli transformer (XLM-RoBERTa base;
`app/models/transformer.py`) ham tayyorlangan. Sharoit CRF bilan bir xil:

- so'zlar `app.nlp.tokenize` bo'yicha, teglar `bio_labels` bo'yicha;
- so'z subword'larga bo'linganda teg faqat **birinchi** subword'ga beriladi,
  qolganlari yo'qotishdan chiqariladi;
- 512 subword chegarasi uchun paragraf 150 so'zlik bo'laklarga ajratiladi;
- o'qitish: AdamW, lr 3·10⁻⁵, batch 8, 10 epoxa, warmup 10 %, weight decay 0.01,
  seed 13; epoxa validation exact F1 bo'yicha tanlanadi;
- bashorat: CRF dagi kabi `spans_from_labels`, lug'at shakli lemmatizatordan.

XLM-R (Conneau va boshq., 2020) BERT arxitekturasiga (Devlin va boshq., 2019)
asoslangan. Model GPU talab qiladi va Google Colab'da ishga tushiriladi
(`notebooks/xlmr_colab.ipynb`). Natijalari 2.2.7-bo'limda.

### 2.2.5. Terminlarni aniqlash natijalari

**2.2-jadval.** Test (ro'yxat usulidagi belgilar, 35 paragraf, 380 span):

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 |
|---|---|---|---|---|---|
| D-15 | 0.708 | 0.166 | 0.269 | [0.171, 0.373] | 0.371 |
| D-train | 0.770 | 0.432 | 0.553 | [0.471, 0.628] | 0.696 |
| CRF | 0.715 | 0.534 | 0.611 | [0.527, 0.690] | 0.773 |
| **CRF+G** | **0.792** | **0.550** | **0.649** | [0.566, 0.719] | **0.780** |

**2.3-jadval.** Test (uchrash-ma-uchrash qayta belgilangan, 391 span). Bu belgilar
lug'at aniqlagichiga bog'liq emas:

| Usul | P | R | F1 | F1, 95 % oraliq | D-train dan farq, 95 % |
|---|---|---|---|---|---|
| D-15 | 0.685 | 0.156 | 0.254 | [0.159, 0.354] | [−0.359, −0.207] |
| D-train | 0.761 | 0.414 | 0.536 | [0.456, 0.611] | — |
| CRF | 0.715 | 0.519 | 0.601 | [0.516, 0.679] | [−0.014, +0.151] |
| **CRF+G** | **0.792** | **0.535** | **0.638** | [0.550, 0.713] | **[+0.063, +0.145]** |

**2.4-jadval.** Train'da uchramagan terminlar (test, 146 span):

| Usul | Topildi | Recall |
|---|---|---|
| D-15, D-train | 0 | 0.000 |
| CRF | 31 | 0.212 |
| CRF+G | 2 | 0.014 |

**Tahlil.**

1. **Lug'at hajmi recall'ni deyarli 2.6 baravar oshiradi** (0.166 → 0.432).
   Precision esa o'zgarmaydi (≈ 0.7–0.8). Lug'at usulining asosiy cheklovi —
   to'liqlik (coverage).
2. **CRF+G eng yuqori F1 ga ega.** D-train dan farqining 95 % oralig'i ikkala
   belgilash variantida ham 0 ni o'z ichiga olmaydi, ya'ni farq statistik ishonchli.
   Gazetteersiz CRF ning ustunligi bu hajmdagi maʼlumotda ishonchli emas.
3. **Faqat CRF yangi terminlarni topadi** (21 %): *lingvostatistika, paralingvistika,
   etnolingvistika, sotsiolingvistika, transliteratsiya, antroponimika, semitologiya,
   hindevropashunoslik, sinxroniya, diaxroniya, oʻrin ravishlari, morfologik usul*.
   Buni oxirgi 2–5 harf xususiyatlari (*-ika, -iya, -shunoslik*) taʼminlaydi.
   Gazetteer qo'shilganda model lug'at belgisiga tayanadi va bu qobiliyat yo'qoladi
   (1.4 %). Demak, ikki model turli amaliy maqsadlarga mos:
   - CRF+G — aniqlik uchun;
   - CRF — lug'atni yangi terminlar bilan to'ldirish uchun.
4. **Validation bilan solishtirish.** Validation'da CRF (0.532) va CRF+G (0.530)
   deyarli teng, testda CRF+G yuqori. Kichik to'plamlarda tartib o'zgarishi
   bootstrap oraliqlarining kengligiga mos keladi.

### 2.2.6. Xato tahlili (CRF, test)

**Chegara xatolari.** CRF ning 56 ta chegara xatosidan 27 tasida oxiri to'g'ri,
lekin boshidagi aniqlovchi tushib qolgan:

- *amaliy / nazariy / xususiy / strukturaviy tilshunoslik* → *tilshunoslik*;
- *mustaqil soʻz turkumi* → *soʻz turkumi*.

Sabab: o'qitish to'plamida *tilshunoslik* yolg'iz o'zi juda ko'p uchraydi. Bu
partial va exact F1 orasidagi 0.13–0.16 farqni tushuntiradi.

**Lemmatizator xatosi (tuzatilgan).** Birinchi versiyada korpus lemmatizatori
*kesim* so'zini *kes + im* deb bo'lardi, chunki *kes* korpusda mustaqil so'z va
eng qisqa o'zak tanlanadi. Natijada `lemma=kes` xususiyati modelda katta og'irlik
olgan, meʼyorlashtiruvchi ham *kesim → kes* xatosini qilgan. *-im* va *-ing*
(I/II shaxs birlik egaligi) ensiklopedik matnda deyarli uchramagani uchun bunday
bo'linish endi faqat boshqa imkon bo'lmasa olinadi (3.1.1, (c)). Tuzatishdan keyin
modellar qayta o'qitildi: CRF+G natijasi o'zgarmadi (0.649), gazetteersiz CRF
testda 0.606 → 0.611, validation'da 0.534 → 0.532, yaʼni farq bootstrap
oralig'idan ancha kichik. Train'da shu qoida bilan to'g'rilangan so'zlar:
*kesim, boʻlim, bilim, qadim, maʼlum, uning*.

### 2.2.7. Transformer modeli natijalari

XLM-RoBERTa base (2.2.4) Google Colab'da (T4 GPU) o'qitiladi:
`notebooks/xlmr_colab.ipynb`. Notebook to'plamlarni manifestdan tiklaydi,
modelni o'qitadi va lug'at, CRF, CRF+G bilan bir xil testda solishtiradi.
Natija `docs/experiments-table.md` ning 6-bo'limiga avtomatik qo'shiladi.

**Holat: hali ishga tushirilmagan.** Ishlab chiqish muhitida HuggingFace'ga
kirish yo'q edi. Kod CPU'da kichik, tasodifiy boshlangan model bilan
tekshirilgan: o'qitish, epoxa tanlash, saqlash, qayta yuklash (natija aynan
takrorlanadi) va hisobot. Ushbu bo'lim Colab natijasi bilan to'ldiriladi:

| Usul | P | R | F1 | F1, 95 % oraliq | CRF+G dan farq, 95 % | Yangi terminlar |
|---|---|---|---|---|---|---|
| CRF+G | 0.792 | 0.550 | 0.649 | [0.566, 0.719] | — | 2 / 146 |
| XLM-R base | … | … | … | … | … | … |

Natijani talqin qilishda ikki narsa hisobga olinadi:

- train atigi 221 paragraf; transformer odatda ko'proq maʼlumot talab qiladi;
- XLM-R CRF+G dan farqli ravishda lug'atdan foydalanmaydi, shuning uchun
  uni gazetteersiz CRF bilan ham solishtirish kerak.
