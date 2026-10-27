# Tajriba metodikasi

Bu hujjat UzTerm AI usullari qanday baholanishini belgilaydi. Maqsad —
natijalar takrorlanadigan bo'lishi va turli usullar adolatli solishtirilishi.

## 1. Vazifa

Kiruvchi maʼlumot — oʻzbek tilidagi matn (bir paragraf). Chiquvchi maʼlumot —
terminlar spanlari `[start, end)` va har biri uchun lug'at shakli. Spanlar
qo'shimchalar bilan birga olinadi; qoidalar
[data-annotation-guide.md](data-annotation-guide.md) da.

Termin nomzodlarini reyting qilish (3-bosqich) bundan **alohida** vazifa sifatida
baholanadi (masalan, Precision@K), chunki u matndagi pozitsiyani emas, terminlar
ro'yxatini qaytaradi.

## 2. Maʼlumotlar

- Oltin standart — inson belgilagan va `reviewed` holatidagi yozuvlar.
- Dataset manba (`doc_id`) darajasida train / validation / test ga ajratiladi.
  Takroriy matnli manbalar bitta to'plamga tushadi, taqsimot
  `data/splits/manifest.json` da muzlatiladi.
- Har bir hisobotda quyidagilar ko'rsatiladi: manbalar, yozuvlar va spanlar
  soni, manbalarning janri yoki nashri, annotatorlar soni.

**Test to'plami qoidasi.** Qoidalar, qo'shimchalar ro'yxati, lug'at, model
giperparametrlari va chegaralarni sozlash faqat `validation` asosida qilinadi.
`test` faqat yakuniy, oldindan qayd qilingan konfiguratsiyalarni bir marta
baholash uchun ishlatiladi. Test natijasi ko'rilgandan keyin tizim
o'zgartirilsa, bu hujjatlashtiriladi va natija "test bo'yicha sozlangan"
deb belgilanadi.

**Lug'at va test.** Lug'at baseline'i uchun `data/terms.json` ni test
to'plamidagi terminlar asosida to'ldirish taqiqlanadi, aks holda baseline
sun'iy ravishda yuqori natija beradi. Lug'atga qo'shilgan har bir termin
manbasi bilan qayd qilinadi.

## 3. Ko'rsatkichlar

Barcha ko'rsatkichlar micro-average usulida hisoblanadi: barcha yozuvlarning
spanlari birga sanaladi.

| Ko'rsatkich | Taʼrif |
|---|---|
| **exact P/R/F1** (asosiy) | bashorat `[start, end)` oltin span bilan aynan teng bo'lsa — to'g'ri |
| **partial P/R/F1** (yordamchi) | kamida bitta belgi kesishsa — to'g'ri. P: oltinga tekkan bashoratlar / barcha bashoratlar; R: bashorat tekkan oltinlar / barcha oltinlar |
| **lug'at shakli aniqligi** | aniq mos kelgan spanlar ichida bashorat qilingan lug'at shakli oltin `term` ga teng bo'lganlar ulushi (registr va apostrof farqisiz; noaniq bashorat — noto'g'ri) |

`Precision = to'g'ri bashoratlar / barcha bashoratlar`,
`Recall = topilgan oltin spanlar / barcha oltin spanlar`,
`F1 = 2PR / (P + R)`. Maxraj 0 bo'lsa, ko'rsatkich aniqlanmagan (`—`)
deb yoziladi, 0 yoki 1 deb emas.

## 4. Xato tahlili

`python -m app.evaluation.evaluate` har bir xatoni toifaga ajratadi va
kontekst bilan ko'rsatadi:

| Toifa | Maʼnosi |
|---|---|
| `missed` | oltin terminga hech qanday bashorat tegmagan. `in_dictionary` lug'atda bor-yo'qligini ko'rsatadi: lug'atda bo'lsa, sabab odatda morfologiya yoki yozilish |
| `false_positive` | bashorat hech qanday oltin spanga tegmagan (masalan, umumiy maʼnodagi so'z) |
| `boundary` | bashorat oltin span bilan kesishadi, lekin chegaralari boshqa |
| `term_mismatch` | span to'g'ri, lug'at shakli noto'g'ri |
| `ambiguous` | span to'g'ri, lekin bashorat bir nechta yozuvga mos kelgani uchun shakl tanlanmagan |

MDI hujjati uchun har bir toifadan misollar keltiriladi va asosiy sabablar
tahlil qilinadi.

## 5. Ishga tushirish

```bash
PYTHONPATH=backend python -m app.dataset.validate
PYTHONPATH=backend python -m app.dataset.split
PYTHONPATH=backend python -m app.evaluation.evaluate data/processed/validation.jsonl --output reports/dictionary-validation.json
```

JSON hisobotda usul nomi, lug'at fayli va undagi terminlar soni, baholangan
fayllar, ko'rsatkichlar va barcha xatolar ro'yxati saqlanadi. Natijani
takrorlash uchun hisobot bilan birga git commit identifikatori
(`git rev-parse HEAD`) ham qayd qilinadi.

## 6. Usullarni solishtirish

- Barcha usullar **bir xil** test to'plamida va bir xil skript bilan baholanadi.
- Har bir usul uchun konfiguratsiya (lug'at versiyasi, model nomi va
  litsenziyasi, giperparametrlar) qayd qilinadi.
- Murakkabroq usul natijasi baseline'dan yaxshi bo'lgandagina tanlanadi.
- Dataset kichik bo'lsa, natijalar orasidagi farq tasodifiy bo'lishi mumkin.
  Kerak bo'lsa, ishonch oralig'i (masalan, yozuvlar bo'yicha bootstrap)
  keyingi versiyada qo'shiladi.

## 7. Joriy holat

Baholash vositalari tayyor va testlangan. **Haqiqiy natija hali yo'q**, chunki
inson belgilagan dataset hali yig'ilmagan. `docs/examples/` dagi fayllar
faqat format namunasi; ular bo'yicha chiqqan raqamlar aniqlik ko'rsatkichi emas.
