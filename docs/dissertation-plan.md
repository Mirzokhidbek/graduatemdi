# Dissertatsiya rejasi bo'yicha ish rejasi

**Mavzu:** Terminlarni ishlab chiqish va meʼyorlashtirishning avtomatik modellari.

Bu hujjat tasdiqlangan 3 bobli reja (I–III bob) bilan hozirgi kodni bog'laydi.
Unda har bir bo'lim uchun nima qilinishi, natijasi (kod, tajriba, matn) va
tartibi ko'rsatilgan.

Belgilar: ✅ bor · 🟡 qisman · ❌ yo'q.

## 0. Hozirgi holat (2026-11-05, A–C va E bosqichlaridan keyin)

| Bo'lim | Holat | Bor narsa |
|---|---|---|
| 1.1 Lingvistik asoslar | 🟡 | qoralama (AI) — iqtiboslar tekshirilishi kerak |
| 1.2 NLP evolyutsiyasi | 🟡 | qoralama (AI) — iqtiboslar tekshirilishi kerak |
| 1.3 O'zbek terminologiyasi, ehtiyoj | 🟡 | qoralama (AI) — meʼyoriy hujjatlar tekshirilishi kerak |
| 2.1 Lingvistik qolip modellari | ✅ | `app/nlp/patterns.py`, gibrid tajriba (`reports/experiment-patterns.json`) |
| 2.1 Statistik modellar | ✅ | frequency, TF-IDF, C-value, NC-value, Weirdness |
| 2.2 ML / DL | 🟡 | CRF, CRF + gazetteer; XLM-R kodi bor, o'qitilmagan |
| 2.3 Ontologiya va tezaurus | ✅ | `app/ontology/thesaurus.py`, SKOS (`reports/thesaurus.ttl`), `#thesaurus` sahifasi; ekspert bahosi kutilmoqda |
| 3.1 Variantdorlik | ✅ | `app/variation/`: imlo, kirill, morfologiya, imlo xatosi, sinonim/dublet, omonimiya, meʼyoriy shakl tanlash |
| 3.2 Meʼyorga muvofiqlikni tekshirish | ✅ | `app/norms/`, `POST /api/check-terms`, `#check` sahifasi; ekspert bahosi kutilmoqda |
| 3.3 Ko'p tilli moslashtirish | ✅ | `app/multilingual/`: kognat modeli, etimonlar, meʼyoriy muqobil; LaBSE va Vikipediya — Colab |

---

**Qolgan ishlar (inson talab qiladi):**

1. D bosqich — inson oltin standarti va ekspert baholari: `docs/dissertation/umumiy-xulosa.md`
   dagi "Ekspert baholari kutilayotgan fayllar" jadvali.
2. Colab: XLM-R (`notebooks/xlmr_colab.ipynb`), LaBSE va Vikipediya ekvivalentlari
   (`notebooks/multilingual_colab.ipynb`).
3. I bob iqtiboslari va † belgili manbalarni asl nusxa bilan tekshirish.

## A bosqich. Dissertatsiya tuzilmasini rejaga moslash

`docs/dissertation/` hozir texnik hisobot shaklida (kirish → maʼlumot →
arxitektura → tajriba → xulosa). Uni rejadagi tuzilmaga o'tkazamiz:

```text
docs/dissertation/
  00-kirish.md            # dolzarblik, maqsad, vazifalar, yangilik, amaliy ahamiyat
  1-1-termin-asoslari.md
  1-2-nlp-evolyutsiya.md
  1-3-ozbek-terminologiyasi.md
  1-xulosa.md
  2-1-ate-usullari.md     # lingvistik + statistik (hozirgi 3.5, 4.6 shu yerga)
  2-2-ml-dl.md            # CRF, XLM-R (hozirgi 3.4, 4.3, 4.5, 4.7)
  2-3-ontologiya.md
  2-xulosa.md
  3-1-variantdorlik.md    # hozirgi 3.6, 4.4 shu yerga
  3-2-meyor-tekshiruvi.md
  3-3-kop-tilli.md
  3-xulosa.md
  umumiy-xulosa.md
  ilova-a-malumotlar.md   # korpus, annotatsiya, split (hozirgi 02)
  ilova-b-takrorlash.md   # hozirgi 06
  adabiyotlar.md
```

Mavjud matn yo'qolmaydi, faqat ko'chiriladi. Har bir yangi bo'lim avval
"bo'sh joy" (TODO) sifatida yaratiladi.

---

## B bosqich. II bob: yetishmayotgan modellar

### B1. Lingvistik qolip modeli (2.1)

- `app/nlp/morph_tagger.py`: qo'shimchalarga asoslangan sodda so'z turkumi
  aniqlagichi (ot / sifat / fe'l / ravish / yordamchi). U lug'at va qo'shimcha
  qoidalariga tayanadi. O'zbek tili uchun ochiq POS-tegger yo'qligi sababli
  shunday yondashuv tanlandi.
- `app/nlp/patterns.py`: termin qoliplari.
  - `Ot`
  - `Sifat + Ot`
  - `Ot + Ot`
  - `Ot + Ot-(s)i` (izofa: *so'z turkumi*)
  - `Ot-ning + Ot-(s)i`
  - `Fe'l-sh/-ish + Ot` (*so'z yasash*)
- Tajriba: uchta usul solishtiriladi.
  1. Faqat qolip (lingvistik model).
  2. Faqat statistik model.
  3. Gibrid: qolip filtri + C-value / NC-value.
- Kutiladigan natija: "lingvistik / statistik / gibrid" taqqoslash jadvali.
  ATE bo'yicha klassik adabiyotdagi uchlik ham shu.

### B2. NC-value (2.1)

- `candidates.py --method ncvalue` (Frantzi va boshq., 2000):
  - kontekst so'zlari og'irligi `weight(w) = t(w)/n`;
  - `NC = 0.8·C-value + 0.2·Σ f(w)·weight(w)`.
- Mavjud inson baholari pulida P@K hisoblanadi. Pulda yo'q yangi nomzodlar
  alohida baholanadi.

### B3. ML/DL (2.2)

- XLM-R ni Colab'da o'qitish (`notebooks/xlmr_colab.ipynb`). Bu ishni **siz
  bajarasiz**, chunki GPU kerak va bu muhitdan HuggingFace'ga kirish yo'q.
- Ixtiyoriy: BiLSTM-CRF (CPU'da ishlaydi). U CRF va transformer orasida
  oraliq nuqta bo'ladi.
- Yakuniy jadval: Lug'at · CRF · CRF + gazetteer · BiLSTM-CRF · XLM-R ·
  XLM-R + gazetteer.

### B4. Ontologiya va tezaurusni avtomatik shakllantirish (2.3)

`app/ontology/` modulida uchta manba birlashtiriladi.

1. **Bosh so'z ierarxiyasi.** Ko'p so'zli terminning bosh so'zi uning
   giperonimi bo'ladi: *jarangli undosh → undosh → tovush*. Bu oddiy va
   ishonchli usul.
2. **Leksik-sintaktik qoliplar** (Hearst usulining o'zbekcha moslamasi):
   - "X ning turlari: A, B, C";
   - "A, B kabi X lar";
   - "A — X ning bir turi";
   - "X ikki xil bo'ladi: A va B".
3. **Taʼrif tahlili.** "A — ... X" ko'rinishidagi taʼriflarda oxirgi ot X
   giperonim bo'ladi.

Natija:
- SKOS / JSON-LD formatidagi tezaurus (`broader`, `narrower`, `related`, `altLabel`);
- web interfeysda daraxt ko'rinishi.

Baholash: tasodifiy 100 ta munosabatni inson tekshiradi (P), mavjud qo'lda
tuzilgan kichik ierarxiya bo'yicha esa R hisoblanadi.

---

## C bosqich. III bob: meʼyorlashtirish

### C1. Variantdorlikni aniqlash va bartaraf etish (3.1)

`app/normalization/variants.py`:

| Tur | Misol | Usul |
|---|---|---|
| Imlo varianti | *o'zak / oʻzak / ozak* | normalizatsiya + tahrir masofasi |
| Yozuv varianti | *ўзак ↔ o'zak* | kirill → lotin transliteratsiya |
| Morfologik variant | *so'z turkumi / so'z turkumlari* | lemma bo'yicha guruhlash |
| Sinonim / dublet | *tilshunoslik / lingvistika* | qavs va "yoki" qoliplari, taʼrif o'xshashligi, embedding |
| Omonim | *qo'shimcha* (termin / umumiy so'z) | kontekst klassifikatori (CRF belgilaridan foydalanadi) |

Har bir variant guruhi uchun bitta **meʼyoriy shakl** taklif qilinadi.
Mezonlar: manbadagi status, chastota, o'zbekcha / o'zlashma qoidasi,
qisqalik. Tavsiya sababi bilan qaytariladi va noaniq holatlar
`needs_review` ga yuboriladi.

Baholash: qo'lda tuzilgan variant juftlari bo'yicha P/R; omonimlar uchun
aniqlik (accuracy).

### C2. Meʼyorga muvofiqlikni avtomatik tekshirish (3.2)

`app/normalization/checker.py` qoidaviy model bo'lib, har bir qoida natijasi
`ok / ogohlantirish / xato` va izoh bilan qaytadi.

- **ISO 704 / ISO 1087 tamoyillari:**
  - bir maʼnolilik (bazada omonim yo'qligi);
  - qisqalik (so'zlar soni);
  - yasalish imkoniyati;
  - tizimlilik (ierarxiyadagi qo'shnilar bilan bir xil model);
  - sinonim ortiqchaligi.
- **O'zbek tili qoidalari:**
  - lotin alifbosi (1995) va imlo qoidalari: `oʻ`/`gʻ`/`ʼ` shakllari,
    kirill harflari aralashmasligi;
  - o'zlashma qo'shimcha va undosh birikmalari;
  - qo'shma so'zlarni qo'shib yoki ajratib yozish.
- Natija:
  - API: `POST /api/check-term`;
  - interfeysda "meʼyor hisoboti" ko'rinishi;
  - butun baza bo'yicha statistika.

Baholash: 100 ta terminni mutaxassis bilan solishtirib, Cohen kappa
hisoblanadi.

### C3. Ko'p tilli baza va cross-lingual alignment (3.3)

1. **Baza kengaytmasi.** `terms.json` ga `equivalents: {"ru": [...], "en": [...]}`
   maydoni qo'shiladi.
2. **Oltin juftlar.** Vikipediya tillararo havolalari / Wikidata orqali
   450 ta termindan mos keladiganlari olinadi, keyin qo'lda tekshiriladi.
   Taxminan 150–250 juft kutiladi.
3. **Avtomatik moslashtirish.** Ko'p tilli embedding (LaBSE yoki XLM-R)
   ishlatiladi:
   - inglizcha / ruscha termin berilganda o'zbekcha nomzodlar reytingi
     chiqariladi;
   - korpusdagi nomzodlar ham hisobga olinadi;
   - imlo o'xshashligi (transliteratsiya) bilan birlashtiriladi.
4. **Meʼyoriy muqobilni tanlash.** Bir nechta o'zbekcha nomzod bo'lsa, C1
   va C2 mezonlari bilan eng meʼyoriy shakl tanlanadi.

Baholash: Accuracy@1 / @5 va MRR. Taqqoslash nuqtalari: faqat
transliteratsiya, faqat embedding va gibrid.

Talab: embedding modeli uchun HuggingFace, Wikidata uchun internet kerak.
Bu muhitda bular bloklangan bo'lsa, Colab yoki sizning kompyuteringizda
ishlatiladi.

---

## D bosqich. Inson oltin standarti (hamma boblar uchun majburiy)

Hozir barcha natijalar AI belgilagan **kumush** maʼlumot bo'yicha olingan.
Himoyada bu eng zaif nuqta bo'ladi.

1. 2 annotator test to'plamini (6 maqola, 35 paragraf) web interfeysda
   (`#annotate`) belgilaydi. Keyin `agreement compare A1 A2` buyrug'i bilan
   kelishuv o'lchanadi.
2. B4, C1, C2 va C3 uchun kichik oltin to'plamlar tayyorlanadi: ierarxiya,
   variant juftlari, meʼyor bahosi, ekvivalentlar.
3. Barcha jadvallar `PYTHONPATH=backend python -m app.evaluation.report`
   bilan qayta hisoblanadi.

**Bu ishni inson bajarishi kerak.** Vositalar tayyor.

## E bosqich. I bob va xulosalar (matn)

- **1.1:**
  - termin taʼrifi (Lotte, Vüster, Reformatskiy, Superanskaya);
  - umumiy terminologiya nazariyasi va zamonaviy (kognitiv,
    sotsioterminologiya) yondashuvlar;
  - ISO 704 / 1087;
  - o'zbek terminologlari (A. Hojiyev, R. Doniyorov, N. Mahmudov va boshq.).
- **1.2:** ATE tarixi:
  - qoidaviy (Justeson & Katz 1995);
  - statistik (C/NC-value);
  - ML (CRF);
  - DL (BiLSTM, BERT, LLM);
  - benchmarklar (ACTER, GENIA).
- **1.3:**
  - O'zbekistondagi atamashunoslik qo'mitasi;
  - lotin alifbosiga o'tish muammolari;
  - mavjud resurslar va bo'shliqlar.
- Har bob oxirida xulosa, umumiy xulosa va adabiyotlar ro'yxati
  (DAK talabi bo'yicha).

Matn qoralamasini men yozaman. **Manbalarni siz tekshirasiz:** har bir iqtibos
haqiqiy manba bilan solishtiriladi.

---

## Tartib va taxminiy hajm

| # | Ish | Kim | Hajm |
|---|---|---|---|
| 1 | A: tuzilmani qayta tashkil qilish | Claude | 1 sessiya |
| 2 | B2: NC-value | Claude | kichik |
| 3 | B1: qolip modeli + gibrid tajriba | Claude | o'rta |
| 4 | C1: variantdorlik moduli | Claude | o'rta |
| 5 | C2: meʼyor tekshiruvchisi + API/UI | Claude | o'rta |
| 6 | B4: ontologiya / tezaurus + UI | Claude | o'rta–katta |
| 7 | C3: ko'p tilli baza va alignment | Claude + siz (Colab) | katta |
| 8 | B3: XLM-R o'qitish | siz (Colab) | kichik |
| 9 | D: inson annotatsiyasi va baholar | siz + 2 annotator | eng uzoq; **hoziroq boshlash kerak** |
| 10 | E: I bob, xulosalar, adabiyotlar | Claude (qoralama) + siz | o'rta |
| 11 | Barcha jadvallarni oltin maʼlumotda qayta hisoblash | Claude | kichik |

D bosqich parallel ravishda darhol boshlanishi kerak, chunki u boshqa
ishlarga bog'liq emas.

Har bir modul uchun bir xil talablar:
- kod;
- testlar (`pytest`);
- tajriba skripti va `reports/` dagi natija;
- dissertatsiyaning tegishli bo'limi;
- `06-takrorlash` / `ilova-b` ga buyruq.
