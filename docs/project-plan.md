# UzTerm AI — loyiha rejasi

## MVP chegarasi

Kiruvchi maʼlumot: oʻzbek (lotin yozuvi) tilidagi ilmiy yoki taʼlimiy matn.
Natija: aniqlangan terminlar, ularning pozitsiyasi, bazadagi yozuvi va meʼyoriy
shakl bo'yicha tavsiya. Tizim manbasi bo'lmagan terminni hech qachon
"to'g'ri/meʼyoriy" deb eʼlon qilmaydi.

## Arxitektura (minimal)

```text
matn ──> normalize (1:1, uzunlik saqlanadi)
     ──> DictionaryMatcher (har bir shakl uchun regex, so'z chegarasi, qo'shimchalar)
     ──> uzun moslik ustunligi bilan ustma-ust tushishni hal qilish
     ──> analyzer (+ meʼyoriy shakl tavsiyasi) ──> JSON
```

Keyingi bosqichlarda shu `analyze_text` funksiyasi FastAPI endpointi va
statistik/ML aniqlagichlar uchun umumiy interfeys bo'ladi.

## Bosqichlar

| # | Bosqich | Holat |
|---|---|---|
| 0 | Rejalashtirish, tuzilma, README | bajarildi |
| 1 | Lug'atga asoslangan baseline + testlar | bajarildi |
| 2 | Dataset: manbali matnlar, inson annotatsiyasi (JSONL, `[start, end)`), annotation yo'riqnomasi, matn darajasida train/val/test | jarayonda: web annotatsiya interfeysi, annotatorlar kelishuvi va split tayyor; butun korpus **AI tomonidan** belgilangan (kumush, 2555 span); inson annotatsiyasi kutilmoqda |
| 3 | Statistik nomzodlar: n-gram, chastota, TF-IDF, C-value, Weirdness | bajarildi: usullar, POS filtri, kontrast korpus (48 ta maqola) va weirdness o'lchovi tayyor; inson baholari (A1, A2, kappa=0.474) va hakamlik konsensus bahosi (adjudicated) olingan, P@K hisoblangan |
| 4 | Token classification (`B-TERM`/`I-TERM`/`O`), baseline bilan bir xil testda solishtirish | bajarildi (kumush maʼlumotda): CRF, CRF + gazetteer; natija [results.md](results.md) |
| 5 | Meʼyorlashtirish: variant/sinonim bog'lash, manbalar, noaniq holatlarni tekshiruvga yuborish | qisman (baza formati va tavsiya mantig'i bor) |
| 6 | FastAPI + React/TypeScript/Vite interfeysi, eksport | bajarildi (MVP): API, web interfeys, JSON/CSV eksport |
| 7 | Precision/Recall/F1, exact span match, xato tahlili | qisman: skriptlar, bootstrap ishonch oraliqlari; o'lchov faqat kumush maʼlumotda |

## 1-bosqich: baseline qarorlari

- **Normalizatsiya faqat yozuvga tegishli.** Kichik harfga o'tkazish va
  `' ` ´ ʹ ʻ ʼ ‘ ’ ′` belgilarini bitta `'` ga keltirish. Har bir belgi bitta
  belgiga almashtiriladi, shuning uchun pozitsiyalar asl matnga to'g'ridan-to'g'ri
  mos keladi. `oʻ`/`gʻ` (ʻ) va tutuq belgisi (ʼ) ham bir xil ko'rinishga keladi,
  chunki amalda ular tez-tez almashtirib yoziladi.
- **Sinonimlar variantlardan alohida.** `variants` — yozilish farqi,
  `synonyms` — maʼno jihatidan teng termin. Natijada `match_type` orqali
  ko'rsatiladi.
- **So'z chegarasi.** Termin oldida va keyin harf/raqam bo'lmasligi kerak.
  So'z ichidagi apostrof (`so'z`) so'zning bir qismi hisoblanadi; termin atrofidagi
  qo'shtirnoq esa chegara hisoblanadi.
- **Qo'shimchalar.** Agglyutinativ tuzilish sababli faqat aniq moslik juda kam
  narsani topadi. Shu sababli oxirgi so'zdan keyin cheklangan qo'shimchalar
  zanjiriga ruxsat beriladi: ko'plik (`-lar`), egalik (`-im, -ing, -i, -si, ...`),
  kelishik (`-ning, -ni, -ga/-ka/-qa, -da, -dan, -gacha, -dagi`), `-ki`,
  yuklama (`-dir, -dek, -mi`). Bunday topilmalar `dictionary_inflected` deb belgilanadi.
- **Ustma-ust tushish.** Avval eng uzun span tanlanadi; ichma-ich yoki kesishgan
  qisqa mosliklar tashlab yuboriladi ("undosh tovush" ichidagi "tovush" alohida
  chiqmaydi).
- **Omonimlar.** Bir xil shakl bir nechta yozuvda bo'lsa, natija `ambiguous: true`
  va `term: null` bo'ladi. Kontekst bo'yicha ajratish keyingi bosqichlarga qoldirildi.
- **Ishonchlilik ko'rsatkichi yo'q** (`confidence: null`), chunki lug'at usuli
  ehtimollik hisoblamaydi.

## 1-bosqich: maʼlum cheklovlar

1. **Lug'atda yo'q terminlarni topmaydi.** Bu baseline'ning asosiy cheklovi;
   3–4-bosqichlar shuni hal qilishi kerak.
2. **Morfologiya sodda.** Tovush o'zgarishlaridan faqat eng ko'p uchraydiganlari
   hisobga olinadi (2026-10-31): `k → g`, `q → gʻ` (`yurak → yuragi`) va tor
   unli tushishi (`o'rin → o'rni`), faqat unli bilan boshlanuvchi egalik
   qo'shimchasi oldida (`stem_alternations`). Qo'shimcha termin ichiga kirib keladigan
   holatlar (`so'z turkumi → so'z turkumlari`) ham topilmaydi. Hozircha bunday
   shakllarni `variants` ga qo'shish kerak.
3. **Qo'shimcha ro'yxati to'liq emas va ortiqcha qabul qilishi mumkin.**
   Masalan, egalik qo'shimchasining unli/undoshga mosligi tekshirilmaydi.
4. **Faqat lotin yozuvi.** Kirill yozuvidagi matnlar va Unicode birikma
   belgilari (NFD) qo'llab-quvvatlanmaydi.
5. **Umumiy so'zga o'xshash terminlar yolg'on ijobiy natija beradi.** Masalan,
   `qoʻshimcha` ("affiks" sinonimi) oddiy "qo'shimcha maʼlumot" birikmasida ham
   topiladi. Shuning uchun `ot`, `gap`, `ega`, `kesim` kabi ko'p maʼnoli so'zlar
   namuna bazaga ataylab kiritilmadi. Ularni kontekst asosida ajratish kerak.
6. **Ichma-ich terminlar.** Faqat eng uzun termin qaytariladi.
7. **Samaradorlik.** Har bir shakl uchun alohida regex qidiruvi ishlatiladi.
   Bu bir necha ming terminli baza uchun yetarli; katta baza uchun trie yoki
   Aho–Corasick kerak bo'ladi.

Aniqlik (Precision/Recall/F1) hali **o'lchanmagan**. Buning uchun 2-bosqichdagi
inson belgilagan test to'plami kerak.

## 2-bosqich: bajarilgan qism

- [data-annotation-guide.md](data-annotation-guide.md): nima termin hisoblanadi,
  chegara qoidalari (qo'shimcha span ichida, tinish belgilari tashqarida, tekis
  annotatsiya, ellipsis), JSONL formati, manbalar va ish jarayoni.
- `data/sources.json` — manbalar reyestri (hozircha bo'sh). `rights` maydoni majburiy.
- `python -m app.dataset.validate` quyidagilarni tekshiradi:
  - JSON sintaksisi;
  - majburiy maydonlar va ularning turlari;
  - `[start, end)` chegaralari va `surface` mosligi;
  - span so'z chegarasiga to'g'ri kelishi (lug'at aniqlagichi bilan bir xil qoida);
  - spanlar ustma-ust tushmasligi;
  - fayllar bo'yicha `id` noyobligi;
  - `doc_id` manbalar reyestrida borligi.
  
  Ogohlantirish beradigan holatlar: takroriy matnlar va NFC bo'lmagan Unicode.

**Muhim qaror:** span qo'shimchani ham o'z ichiga oladi (*fonemalarning*),
lug'at shakli esa alohida `term` maydonida yoziladi. Bu lug'at aniqlagichining
`surface` natijasi bilan bir xil. Shuning uchun exact span match baholashni
to'g'ridan-to'g'ri qilish mumkin, BIO teglari ham so'z darajasida qoladi.

## Keyingi qadam

1. ~~Manbalari va huquqi aniq matnlarni yig'ish~~ — boshlandi: Oʻzbekcha
   Vikipediyadan 41 ta tilshunoslik maqolasi (310 paragraf, ~18 ming so'z,
   CC BY-SA 4.0, har biri aniq revid bilan). Cheklovlar: barchasi bitta
   janrda (ensiklopedik), ko'pchiligi Oʻzbekiston milliy ensiklopediyasidan
   ko'chirilgan, ayrimlarida havolalardan qolgan probelsiz joylar bor
   (`Fonemafonologiya`) — matn o'zgartirilmadi. Darslik va maqolalar kabi boshqa
   janrlar foydalanish ruxsati bilan qo'shilishi kerak. Dastlab 42 ta maqola
   yuklangan edi; "Boʻgʻin" so'rovi biologiyadagi "Boʻgʻin (avlod)" maqolasini
   qaytargani uchun u korpusdan chiqarildi (2026-10-27). Qolgan 41 tasining
   boshlanishi qo'lda ko'rib chiqildi.
2. ~~Inline belgidan (`[[fonemalar|fonema]]`) JSONL yaratuvchi skript~~ —
   bajarildi: `python -m app.dataset.inline`.
3. ~~`doc_id` bo'yicha train/val/test ajratuvchi skript~~ — bajarildi:
   `python -m app.dataset.split` (takroriy matnli manbalar bitta guruhda,
   manifest muzlatiladi).
4. ~~Baholash skripti (exact/partial P/R/F1, xato tahlili)~~ — bajarildi:
   `python -m app.evaluation.evaluate`, metodika:
   [experiment-methodology.md](experiment-methodology.md). Real natija
   dataset tayyor bo'lgach olinadi.
5. Ikki annotator orasidagi kelishuvni o'lchash.

## 3-bosqich: statistik termin nomzodlari

`python -m app.nlp.candidates --method {frequency,tfidf,cvalue}`:

- **Nomzodlar** — 1–4 so'zli n-gramlar. Ular tinish belgisini kesib o'tmaydi va
  yordamchi so'z bilan boshlanmaydi yoki tugamaydi
  ([stopwords.py](../backend/app/nlp/stopwords.py), ro'yxatni Claude tuzgan,
  tekshirilmagan). Oxirgi so'z korpusga tayangan lemmatizator bilan qo'shimchasiz
  holga keltiriladi. Formulalar [candidates.py](../backend/app/nlp/candidates.py) da.
- **Precision@K** — maʼlum terminlar ro'yxatiga nisbatan:
  `--reference-terms` (lug'at) yoki `--reference-annotations` (inson belgilagan JSONL).

### Lug'atga nisbatan (2026-10-27, 41 ta Vikipediya maqolasi)

Korpus: 17 777 token, 18 592 nomzod, ulardan 2 474 tasi f ≥ 2.
Maʼlum terminlar — `data/terms.json` dagi 19 ta shakl.

| Usul | P@10 | P@20 | P@50 | P@100 |
|---|---|---|---|---|
| frequency | 0.100 | 0.150 | 0.140 | 0.110 |
| tfidf | 0.200 | 0.250 | 0.160 | 0.120 |
| cvalue | 0.100 | 0.150 | 0.180 | 0.110 |

**Bu raqamlar tizim aniqligi emas.** Maʼlum terminlar ro'yxati juda kichik
(19 ta) va namunaviy. Reyting tepasidagi ko'p nomzodlar (`gap`, `fe'l`, `ega`,
`grammatik`, `kategoriya`, `leksika`, `so'z birikma`) tilshunoslik terminiga
o'xshaydi, lekin lug'atda yo'qligi uchun xato deb sanalgan. Shuning uchun bu
qiymatlar faqat **pastki chegara**. Usullarni solishtirish uchun ham hali
asos emas: farqlar bir necha nomzodga teng.

Kuzatilgan muammolar (to'liq reyting: `reports/candidates-*.csv`):

1. **Umumiy so'zlar ustunlik qiladi** (`so'z`, `til`, `ma'no`, `shakl`). Korpus
   bitta sohadan bo'lgani uchun umumiy tilshunoslik leksikasi ham "termin"
   kabi ko'rinadi. Kontrast korpus (sohaga oid bo'lmagan matnlar) bilan
   solishtirish kerak (masalan, weirdness yoki log-likelihood).
2. **Tasniflanmagan yordamchi so'zlar.** `ko'ra` (ko'makchi) stop-ro'yxatda yo'q.
   Ro'yxat test natijasiga qarab emas, tilshunos tekshiruvi asosida
   to'ldirilishi kerak.
3. **Bitta katta hujjatning taʼsiri.** `yoziladi` (f = 68, df = 1) faqat `Imlo`
   maqolasidan keladi, u korpusning ~14 % ini tashkil qiladi. TF-IDF uni
   yuqoriga ko'taradi.
4. **So'z turkumi filtri yo'q.** Fe'llar (`yoziladi`) va sifatlar (`grammatik`)
   ham nomzod bo'ladi. POS-tegger yoki morfologik qoidalar bilan
   (masalan, "ot yoki sifat + ot" andozasi) cheklash keyingi qadam.

### Claude bahosi bo'yicha (AI bahosi, inson emas)

Uchala usulning top-100 nomzodlari birlashtirildi (119 ta nomzod). Ularni
**Claude (AI)** yo'riqnomaning 9.2-bo'limi asosida baholadi: 38 ta `1`, 61 ta `0`,
20 ta `?`. Baholar va har bir `?` uchun sabab
`data/judgments/candidates-claude.csv` da.

| Usul | P@10 qatʼiy / yumshoq | P@20 | P@50 | P@100 |
|---|---|---|---|---|
| frequency | 0.30 / 0.80 | 0.25 / 0.65 | 0.26 / 0.52 | 0.30 / 0.47 |
| tfidf | 0.40 / 0.90 | 0.45 / 0.80 | 0.36 / 0.60 | 0.35 / 0.54 |
| cvalue | 0.30 / 0.80 | 0.30 / 0.65 | 0.32 / 0.58 | 0.32 / 0.49 |

Qatʼiy hisobda faqat `1` termin, yumshoq hisobda `1` va `?` termin hisoblanadi.

**Bu natijalarni MDI'da qanday ko'rsatish mumkin.** Faqat "AI bahosi" sifatida,
inson bahosi o'rnida emas. Cheklovlar:

1. **Baholovchi bitta va u AI.** Inson baholovchilar bilan kelishuv (kappa)
   hali o'lchanmagan.
2. **Baholash to'liq ko'r emas.** Claude baholashdan oldin reytinglarning top-20
   ro'yxatini va qaysi nomzod lug'atda borligini ko'rgan.
3. **Farqlar kichik.** K = 10 da bir nomzod 0.10 ga teng, shuning uchun usullar
   orasidagi farqni statistik ahamiyatli deb bo'lmaydi.
4. **Natija yumshoq hisobga juda bog'liq.** Qatʼiy va yumshoq hisob orasidagi
   katta farq `so'z`, `til`, `ma'no`, `shakl`, `ega` kabi `?` nomzodlardan
   kelib chiqadi. Ular umumiy maʼnoda ham, termin maʼnosida ham ishlatiladi.

Shu cheklovlar bilan kuzatish: uchala usulda ham top-100 ning taxminan
uchdan bir qismi aniq termin. TF-IDF har bir K da qolgan ikki usuldan yuqori
yoki ularga teng, lekin farq kichik.

### Keyingi qadamlar

1. Har bir usulning top-100 nomzodini inson baholashi ("termin / termin emas")
   va shu asosda haqiqiy Precision@K. **Vosita tayyor:**
   `python -m app.evaluation.judgments`. Shablon
   `data/judgments/candidates-A1.csv` va `candidates-A2.csv` inson baholovchilarni
   kutmoqda. Ular to'ldirilgach, `score` buyrug'iga `candidates-claude.csv` ni ham
   berib, AI va inson baholari orasidagi kappa o'lchanadi.
2. Kontrast korpus va so'z turkumi andozalarini qo'shib, natijani **validation**
   bo'yicha solishtirish.
3. Lug'atda yo'q, yuqori reytingli nomzodlarni `needs_review` holatida
   `terms.json` ga taklif qilish — faqat inson tasdig'idan keyin. Test
   to'plamidagi terminlar lug'atga qo'shilmaydi (metodika, 2-bo'lim).

## 6-bosqich: API va web interfeys

- **Backend** (`backend/app/main.py`). Endpointlar: `POST /api/analyze`,
  `GET /api/terms`, `GET /api/health`.
  - Terminlar bazasi ishga tushishda tekshiriladi: buzuq baza bo'lsa, server
    ishga tushmaydi.
  - Matn uzunligi cheklangan (`UZTERM_MAX_TEXT_CHARS`, standart 20 000
    belgi); oshsa, 413 qaytadi.
  - Kutilmagan xatoda ichki tafsilotlar qaytarilmaydi.
  - Javobda pozitsiyalar Unicode belgilari bo'yicha ekani ko'rsatiladi.
- **Frontend** (`frontend/`).
  - Matn maydoni, matnda terminlarni ajratib ko'rsatish, natijalar jadvali va
    termin tafsilotlari (taʼrif, manba, meʼyoriy shakl belgisi).
  - Holatlar: yuklanish, xato, bo'sh natija va "matn tahlildan keyin o'zgardi".
  - JSON va CSV eksport. Ishonchlilik ustunida "hisoblanmagan" yoziladi,
    chunki lug'at usuli ehtimollik bermaydi.
- **Tekshiruv.**
  - Testlar: backend `test_api.py` (pytest) va frontend 14 ta `vitest` testi.
  - Brauzerda qo'lda tekshirildi: namuna matn, termin tanlash, emoji'li matnda
    pozitsiyalar, eski natija ogohlantirishi, backend o'chiq holati.
- **Cheklovlar.** Autentifikatsiya yo'q (lokal prototip). Lug'atni tahrirlash
  interfeysi yo'q. Frontend komponentlari uchun brauzer testlari (React Testing
  Library) qo'shilmagan; ular qo'lda tekshirildi.

## 2026-10-31: annotatsiya interfeysi, kumush maʼlumot, CRF

- **Web annotatsiya** (`#annotate`): paragraf bo'yicha belgilash, lug'at / AI /
  model takliflari, so'z chegarasiga avtomatik kengaytirish, server tomonida
  yo'riqnoma qoidalari bilan tekshirish. Har bir annotatorning ishi alohida:
  `data/annotations/<kod>/`. Nomzodlarni baholash ham web'da (`#judge`).
- **Kelishuv va oltin standart**: `python -m app.annotation.agreement compare A1 A2`
  (exact/partial span F1), `... promote A1` (`reviewed` yozuvlar `data/annotated/` ga).
- **Kumush maʼlumot**: korpusning hammasi AI tomonidan belgilandi
  (`data/silver/README.md`). Manifest shu maʼlumot bo'yicha muzlatildi:
  29 / 6 / 6 maqola.
- **Lug'at**: 15 → 450 termin, faqat train to'plamidan va ko'p maʼnoli so'zlarsiz
  (`app/annotation/dictionary.py`). Barchasi `needs_review`, taʼrifsiz.
  Dastlabki 15 ta `data/terms-seed.json` da.
- **CRF** (`app/models/crf.py`) va solishtirish (`app/models/experiment.py`).
  Natija: [results.md](results.md).
