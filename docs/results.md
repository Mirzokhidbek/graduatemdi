# Dastlabki natijalar (kumush maʼlumot bo'yicha)

> **Muhim.** Bu bo'limdagi barcha raqamlar **AI (Claude) annotatsiyasi** bo'yicha
> olingan ("kumush" maʼlumot, `data/silver/README.md`). Inson oltin standarti
> hali yo'q. Raqamlar usullar qaysi yo'nalishda farq qilishini ko'rsatadi, lekin
> ularni tizimning haqiqiy aniqligi deb ko'rsatib bo'lmaydi. Inson belgilagan
> `reviewed` maʼlumot tayyor bo'lgach, xuddi shu buyruqlar bilan qayta hisoblanadi.

Sana: 2026-10-31. Takrorlash:

```bash
PYTHONPATH=backend python -m app.annotation.silver          # AI annotatsiyasi -> data/annotations/claude/
PYTHONPATH=backend python -m app.dataset.split data/annotations/claude/*.jsonl --include-drafts --output-dir data/processed/silver
PYTHONPATH=backend python -m app.annotation.dictionary      # lug'atga faqat train terminlari
PYTHONPATH=backend python -m app.models.experiment          # -> reports/experiment-silver.json, models/*.crfsuite
```

## 1. Maʼlumot

| To'plam | Maqola | Paragraf | Termin (span) |
|---|---|---|---|
| train | 29 | 221 | 1786 |
| validation | 6 | 54 | 389 |
| test | 6 | 35 | 380 |
| **jami** | **41** | **310** | **2555** |

Taqsimot manba (maqola) darajasida, `data/splits/manifest.json` da muzlatilgan:

- **test:** Bogʻlovchi, Frazeologiya, Olmosh, Ravish, Soʻz turkumlari, Tilshunoslik;
- **validation:** Etimologiya, Leksika, Morfema, Morfonologiya, Omonimlar, Undosh tovushlar.

Inson annotatsiyasi ham shu taqsimotdan foydalanadi.

Test spanlarining 146 tasi (38 %) train'da umuman uchramagan lug'at shakllari.
Bu test to'plami yangi terminlarni topish qobiliyatini ham o'lchashini anglatadi.

## 2. Usullar

| Usul | Tavsif |
|---|---|
| `dictionary_seed` | dastlabki 15 terminli namuna lug'at (`data/terms-seed.json`) |
| `dictionary_train` | lug'at + train to'plamidagi barcha terminlar, ko'p maʼnoli so'zlarsiz (`data/terms.json`, 450 ta) |
| `crf` | CRF, BIO teglar; xususiyatlar: so'z, o'zak, qo'shimchalar (2–5 harf), registr, ±2 qo'shni (`app/models/crf.py`) |
| `crf_gazetteer` | o'sha CRF + train lug'ati topgan joy belgisi (gazetteer) xususiyati |

CRF giperparametrlari (c1 ∈ {0.01, 0.1, 0.5}, c2 ∈ {0.01, 0.05, 0.2}) faqat validation
bo'yicha tanlandi. Ikkala model uchun ham c1 = 0.1, c2 = 0.01 tanlandi. Test bir
marta baholandi.

## 3. Natijalar

### Test (exact span match; partial — kamida bitta belgi ustma-ust tushsa)

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi* |
|---|---|---|---|---|---|---|
| dictionary_seed | 0.708 | 0.166 | 0.269 | [0.171, 0.373] | 0.371 | 0.984 |
| dictionary_train | 0.770 | 0.432 | 0.553 | [0.471, 0.628] | 0.696 | 0.994 |
| crf | 0.714 | 0.526 | 0.606 | [0.523, 0.687] | 0.769 | 0.785 |
| **crf_gazetteer** | **0.792** | **0.550** | **0.649** | [0.566, 0.719] | **0.780** | 0.914 |

\* Aynan topilgan spanlarda `term` (lug'at shakli) to'g'ri chiqqani.

Oraliqlar paragraflar bo'yicha bootstrap usulida olingan (2000 ta qayta tanlanma).
`dictionary_train` dan farqning 95 % oralig'i:

- **crf_gazetteer: [+0.059, +0.138]**. Farq ishonchli: oraliqda 0 yo'q.
- crf: [−0.025, +0.148]. Bu ma'lumot hajmida farq ishonchli emas.

### Validation

| Usul | P | R | F1 | Partial F1 |
|---|---|---|---|---|
| dictionary_seed | 0.700 | 0.162 | 0.263 | 0.351 |
| dictionary_train | 0.671 | 0.393 | 0.496 | 0.665 |
| crf | 0.652 | 0.452 | 0.534 | 0.691 |
| crf_gazetteer | 0.668 | 0.434 | 0.526 | 0.693 |

### Yangi terminlar (test, train'da uchramagan 146 ta span)

| Usul | Topildi | Recall |
|---|---|---|
| dictionary_seed, dictionary_train | 0 | 0.000 |
| crf | 29 | 0.199 |
| crf_gazetteer | 2 | 0.014 |

### Statistik nomzodlar: POS filtri (3-bosqich)

`--pos-filter` oxirgi so'zi fe'l yoki nisbiy sifat shaklidagi nomzodlarni chiqaradi.
Natija Claude baholari bo'yicha (`data/judgments/candidates-claude.csv`, AI bahosi):

| Usul | P@10 | P@20 | P@50 | P@100** |
|---|---|---|---|---|
| tfidf | 0.40 | 0.45 | 0.36 | 0.35 |
| tfidf + POS filtri | **0.50** | **0.55** | **0.40** | ≥0.37 |
| cvalue | 0.30 | 0.30 | 0.32 | 0.32 |
| cvalue + POS filtri | 0.30 | 0.30 | 0.34 | ≥0.34 |

\** Filtrdan keyin top-100 ga 3–6 ta yangi, baholanmagan nomzod kirdi. Ular termin emas deb sanaldi, shuning uchun ≥.

## 4. Xulosalar (kumush maʼlumot doirasida)

1. **Lug'at hajmi asosiy omil.** 15 terminli lug'at recall'i 0.17, train
   terminlari qo'shilgach 0.43. Lug'at yangi terminni hech qachon topmaydi
   (yangi terminlarda recall 0).
2. **CRF yangi terminlarni topadi.** Train'da yo'q terminlarning 20 % ini topdi
   (29 ta). Ular asosan qo'shimchasi termin yasovchi so'zlar: *lingvostatistika,
   paralingvistika, etnolingvistika, sotsiolingvistika, transliteratsiya,
   antroponimika, semitologiya, hindevropashunoslik, sinxroniya, diaxroniya*,
   shuningdek *oʻrin ravishlari, morfologik usul, sintaktik usul, olmosh-ot*.
   Model buni oxirgi 2–5 harf (`-ika`, `-iya`, `-shunoslik`) va qo'shni so'zlar
   xususiyatlaridan o'rgangan.
3. **Eng yaxshi natija — lug'at va CRF birga** (F1 0.65). Farq bootstrap
   bo'yicha ishonchli. Lekin gazetteer bilan model lug'atga "suyanib" qoladi
   (yangi terminlarda recall 0.01). Amalda ikki xil ishlatish mumkin:
   - **aniqlik kerak bo'lsa** — `crf_gazetteer`;
   - **yangi termin qidirilsa** (lug'atni to'ldirish) — `crf`.
4. **Chegara xatolari ko'p.** Partial F1 exact F1 dan 0.13–0.16 yuqori: model
   termin joyini topadi, lekin ko'p so'zli birikma chegarasini adashtiradi. Eng
   ko'p uchragani — aniqlovchi tushib qolishi: *amaliy / nazariy / xususiy /
   strukturaviy tilshunoslik* o'rniga faqat *tilshunoslik*, *mustaqil soʻz turkumi*
   o'rniga *soʻz turkumi*. CRF'ning testdagi 56 ta chegara xatosidan 27 tasi shu turdagi: oxiri to'g'ri, boshidagi aniqlovchi tushib qolgan. Kamroq
   uchraydigani — span qavs yoki keyingi so'zga cho'zilib ketishi
   (*frazeologiya tilning*).
5. **Lug'at baseline'i bu maʼlumotda imtiyozli.** Kumush spanlar lug'at
   aniqlagichi bilan yaratilgan, shuning uchun inson oltin standartida lug'at
   natijasi pastroq, CRF bilan farq esa kattaroq bo'lishi kutiladi.

## 5. Cheklovlar

- **Annotatsiya AI tomonidan qilingan.** Har bir maqola uchun bitta ro'yxat
  qo'llangan, har bir uchrash alohida baholanmagan. Inson tekshiruvi va ikki
  annotator kelishuvi hali yo'q.
- **Test to'plami kichik** (6 maqola, 35 paragraf). Oraliqlar keng, janr bitta
  (ensiklopedik).
- **Transformer modeli sinab ko'rilmadi.** Muhitda HuggingFace'ga kirish yo'q
  edi. CRF (Lafferty va boshq., 2001) shu ish uchun klassik va tushuntiriladigan
  baseline.

## 6. Keyingi qadamlar

1. Inson annotatsiyasi web interfeysda (`#annotate`). Test to'plamidagi
   maqolalarni **takliflarsiz** belgilash tavsiya etiladi ("Takliflarni
   ko'rsatish" belgisini o'chiring), aks holda annotator AI natijasiga ergashib
   qolishi mumkin.
2. Ikki annotator kelishuvi:
   `python -m app.annotation.agreement compare A1 A2`.
3. `reviewed` yozuvlarni oltin standartga o'tkazish (`... promote A1`) va
   `app.models.experiment --data data/processed` bilan qayta baholash.
4. Ko'proq maʼlumot bo'lsa (≈ 1000+ paragraf), transformer modeli (XLM-R)
   va ko'p so'zli terminlar uchun chegara xatolarini tahlil qilish.
