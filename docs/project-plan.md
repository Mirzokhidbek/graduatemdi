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
| 2 | Dataset: manbali matnlar, inson annotatsiyasi (JSONL, `[start, end)`), annotation yo'riqnomasi, matn darajasida train/val/test | jarayonda: yo'riqnoma, format, tekshiruvchi, inline konvertor va split tayyor; belgilangan maʼlumot yo'q |
| 3 | Statistik nomzodlar: n-gram, chastota, TF-IDF, C-value | reja |
| 4 | Token classification (`B-TERM`/`I-TERM`/`O`), baseline bilan bir xil testda solishtirish | reja |
| 5 | Meʼyorlashtirish: variant/sinonim bog'lash, manbalar, noaniq holatlarni tekshiruvga yuborish | qisman (baza formati va tavsiya mantig'i bor) |
| 6 | FastAPI + React/TypeScript/Vite interfeysi, eksport | reja |
| 7 | Precision/Recall/F1, exact span match, xato tahlili | reja |

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
2. **Morfologiya sodda.** Tovush o'zgarishlari (`o'rin → o'rni`,
   `yurak → yuragi`) hisobga olinmaydi. Qo'shimcha termin ichiga kirib keladigan
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

1. Manbalari va foydalanish huquqi aniq bo'lgan matnlarni yig'ish
   (foydalanuvchi taqdim etadi), `data/sources.json` ni to'ldirish.
2. ~~Inline belgidan (`[[fonemalar|fonema]]`) JSONL yaratuvchi skript~~ —
   bajarildi: `python -m app.dataset.inline`.
3. ~~`doc_id` bo'yicha train/val/test ajratuvchi skript~~ — bajarildi:
   `python -m app.dataset.split` (takroriy matnli manbalar bitta guruhda,
   manifest muzlatiladi).
4. Baseline'ni test to'plamida baholash (exact span P/R/F1).
5. Ikki annotator orasidagi kelishuvni o'lchash.
