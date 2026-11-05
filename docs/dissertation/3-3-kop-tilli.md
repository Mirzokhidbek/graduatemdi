## 3.3. Ko'p tilli terminologik bazalarda meʼyoriy muqobillarni avtomatik tanlash va semantik moslashtirish (cross-lingual alignment)

### 3.3.1. Vazifa

Oʻzbek tilshunoslik terminlari asosan ikki yo'l bilan shakllangan:

- rus tili orqali kirgan xalqaro (yunon-lotin) terminlar: *fonema, morfologiya, sintaksis*;
- oʻzbekcha (turkiy yoki arab-fors) terminlar: *tilshunoslik, undosh tovush, soʻz turkumi*.

Ko'p tilli bazada har bir oʻzbekcha termin uchun ruscha va inglizcha ekvivalent
saqlanadi. Bu tarjima, darslik tayyorlash va xalqaro manbalar bilan ishlash uchun kerak.
Shu bilan birga teskari vazifa ham bor. Ruscha yoki inglizcha termin uchun bir nechta
oʻzbekcha muqobil bo'lishi mumkin (*интонация → ohang / intonatsiya*). Ulardan
meʼyoriysini tanlash kerak.

Vazifa ikki qismga bo'linadi:

1. **Moslashtirish (alignment).** Manba tildagi termin uchun oʻzbekcha terminlar
   bazasidan nomzodlar reytingini tuzish.
2. **Meʼyoriy muqobilni tanlash.** Bir nechta oʻzbekcha nomzod bo'lsa, meʼyoriy
   tamoyillar (3.1.4) asosida tavsiya berish.

Kod: `backend/app/multilingual/`.

### 3.3.2. Modellar

**Kognat modeli** (qoidaviy). Xalqaro terminlar uch tilda bitta yunon-lotin o'zakka
ega: *фонема — phoneme — fonema*. Har bir til shakli umumiy fonetik kalitga keltiriladi:

| Til | Qoidalar | Misol |
|---|---|---|
| rus | kirill → lotin (*ц → c, х → h, ия → iya*) | *интонация → intonaciya* |
| ingliz | yunon-lotin so'zlarining moslashuvi teskari: *ph → f, -tion → -ciya, -ology → -ologiya, -ics → -ika, -eme → -ema, -ism → -izm, -y → -iya, c → k/s* | *phonetics → fonetika*, *intonation → intonaciya* |
| oʻzbek | *oʻ, gʻ → o, g; x → h; q → k; ts → c* | *intonatsiya → intonaciya* |

O'xshashlik — kalitlar orasidagi normallashgan Levenshtein masofasi. Qo'sh harflar
birlashtiriladi:

```text
sim(a, b) = 1 − lev(key(a), key(b)) / max(|key(a)|, |key(b)|)
```

**Semantik model.** Ko'p tilli jumla embeddinglari — LaBSE (Feng va boshq., 2022),
109 tilda o'qitilgan, oʻzbek tili ham ular orasida. O'xshashlik — vektorlar
kosinusi. Bu model *языкознание ↔ tilshunoslik* kabi kognati yo'q juftlarni
moslashtira oladi.

**Gibrid model:** `score = w · cos + (1 − w) · sim`.

### 3.3.3. Maʼlumot

**Ekvivalentlar ro'yxati.** 121 ta uz–ru–en uchligi
(`data/multilingual/equivalents-silver.csv`):

- 71 tasi xalqaro termin;
- 50 tasi oʻzbekcha termin;
- ayrim ruscha va inglizcha terminlarning ikki oʻzbekcha muqobili bor
  (*интонация: ohang, intonatsiya*; *орфография: imlo, orfografiya*;
  *аббревиатура: qisqartma, abbreviatsiya*).

Ro'yxatni Claude (AI) tuzgan, shuning uchun bu **kumush** maʼlumot. U ekspert
tekshiruvidan o'tishi kerak.

**Nomzodlar** — 475 ta oʻzbekcha termin: lug'at va ro'yxat.

**Korpusdagi etimologik izohlar.** Ensiklopedik matnlarda terminning kelib chiqishi
ko'pincha qavsda beriladi: *Fonema (yun. phonema — tovush)*, *konsonantizm (lotincha:
consonans — undosh tovush)*. Ular avtomatik ajratiladi
(`data/multilingual/etymons.csv`, 19 ta izoh, tillar: lotin, yunon, arab).

**Vikipediya ekvivalentlari.** Oʻzbekcha Vikipediya maqolalarining ruscha va
inglizcha nomlari (`langlinks` API, `sources.fetch_langlinks`). Ishlab chiqish
muhitida internetga kirish cheklangan edi. Shuning uchun bu qadam va semantik
model Colab'da bajariladi (`notebooks/multilingual_colab.ipynb`). Natija
tekshirilmagan nomzodlar sifatida saqlanadi.

### 3.3.4. Natijalar

**3.7-jadval.** Oʻzbekcha ekvivalentni topish, kognat modeli
(`reports/multilingual.json`):

| Yo'nalish | Termin turi | n | Acc@1 | Acc@5 | MRR |
|---|---|---|---|---|---|
| ru → uz | xalqaro | 71 | **0.986** | 0.986 | 0.986 |
| ru → uz | oʻzbekcha | 50 | 0.020 | 0.040 | 0.024 |
| ru → uz | hammasi | 118 | 0.602 | 0.610 | 0.603 |
| en → uz | xalqaro | 71 | **0.972** | 0.986 | 0.979 |
| en → uz | oʻzbekcha | 49 | 0.020 | 0.041 | 0.026 |
| en → uz | hammasi | 113 | 0.619 | 0.637 | 0.626 |
| ru/en → uz | semantik (LaBSE), gibrid | | Colab natijasi kutilmoqda | | |

Kognat modeli xalqaro terminlarni deyarli xatosiz moslashtiradi. Ingliz tilida bir
nechta xato bor:

- *syntax → sintaksis*: o'xshashlik 0.78, lekin baribir 1-o'rinda;
- *toponymy → toponimika*: -ika va -iya qo'shimchalari farq qiladi.

Oʻzbekcha terminlarda kognat modeli tasodifiy darajada ishlaydi (Acc@1 = 0.02).
Bu kutilgan natija: *согласный звук* va *undosh tovush* o'rtasida shakliy
o'xshashlik yo'q. Demak, bazaning taxminan 40 % i uchun semantik model kerak.

**Ishonch chegarasi.** Amalda kognat modeli faqat ishonchli bo'lganda javob berishi
kerak. Eng yaxshi nomzod bali θ dan past bo'lsa, model javob bermaydi.

**3.8-jadval.** Kognat modeli, barcha terminlar:

| θ | ru: qamrov | ru: aniqlik | en: qamrov | en: aniqlik |
|---|---|---|---|---|
| 0.5 | 0.653 | 0.909 | 0.735 | 0.819 |
| 0.6 | 0.593 | 0.971 | 0.646 | 0.918 |
| 0.7 | 0.576 | 0.985 | 0.593 | 0.985 |
| 0.8 | 0.551 | 1.000 | 0.575 | 1.000 |

θ = 0.7 da model terminlarning qariyb 58 % iga javob beradi va 98.5 % hollarda
to'g'ri. Qolganlari semantik modelga yoki ekspertga yuboriladi. Shu tarzda ikki
bosqichli sxema hosil bo'ladi:

1. ishonchli kognat;
2. embedding;
3. inson.

**Meʼyoriy muqobilni tanlash.** Bir nechta oʻzbekcha muqobili bor terminlar uchun
3.1.4-qoidalar qo'llandi. Lug'atda tasdiqlangan shakl yo'q, shuning uchun qaror
korpus chastotasi (uzus) bo'yicha qabul qilindi:

| Manba termin | Muqobillar (korpusdagi chastota) | Tavsiya |
|---|---|---|
| интонация | *ohang* (9), *intonatsiya* (5) | *ohang* |
| аббревиатура | *qisqartma* (11), *abbreviatsiya* (2) | *qisqartma* |
| орфография | *imlo* (10), *orfografiya* (3) | *imlo* |

Uchala holatda ham ensiklopedik korpusda oʻzbekcha shakl ko'proq qo'llanadi.
Tavsiya `needs_review` holatida beriladi. Dubletlardan qaysi biri meʼyoriy ekanini
terminologik qo'mita yoki lug'at belgilaydi, tizim faqat dalil (chastota, manba)
beradi.

### 3.3.5. Cheklovlar

1. **Ekvivalentlar ro'yxati AI tomonidan tuzilgan** va kichik (121 ta). Natijalarni
   ekspert tekshirgan ro'yxat va Vikipediya ekvivalentlari bilan qayta hisoblash kerak.
2. **Semantik model natijasi hali yo'q.** Kod va notebook tayyor, Colab'da ishga
   tushiriladi.
3. **Kognat modeli yolg'on do'stlarga moyil.** Masalan, *frazeologiya*: rus tilida
   soha nomi, ingliz tilida *phraseology* "ibora uslubi" maʼnosida ham ishlatiladi.
   Shakliy o'xshashlik maʼno tengligini kafolatlamaydi.
4. **Ko'p so'zli terminlar** uchun so'zma-so'z moslashtirish (*grammatik kategoriya ↔
   grammatical category*) bitta qator sifatida solishtiriladi. So'zlar bo'yicha
   kompozitsional moslashtirish qilinmagan.
