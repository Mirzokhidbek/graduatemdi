## 1.2. Tabiiy tilni qayta ishlash (NLP) sohasida terminologik ishlarni kompyuterlashtirish evolyutsiyasi

> **Qoralama.** Matnni Claude (AI) yozgan; iqtiboslar asl manbalar bilan tekshirilishi kerak.

Terminologik ishlarni kompyuterlashtirish to'rt bosqichda rivojlangan. Har bir
bosqichda asosiy vazifa — matndan terminlarni avtomatik ajratib olish (Automatic
Term Extraction, ATE yoki Automatic Term Recognition, ATR) — boshqa usul bilan
hal qilingan.

### 1.2.1. Terminologik ma'lumotlar bazalari (1960–1980-yillar)

Birinchi kompyuterlashtirilgan terminologik resurslar ko'p tilli terminologik
bazalar edi. Ulardan Yevropa Ittifoqi tizimining avvalgisi EURODICAUTOM va
Kanadaning TERMIUM bazasi mashhur. Bu davrda kompyuter tayyor terminlarni
saqlash va qidirish vositasi bo'lgan. Terminlarni tanlash va tavsiflash esa
to'liq qo'lda bajarilgan.

### 1.2.2. Qoidaviy (lingvistik) usullar (1990-yillar boshi)

Matndan terminlarni avtomatik ajratish g'oyasi korpuslar paydo bo'lishi bilan
amalga oshdi.

- **Lingvistik usullar** terminning sintaktik tuzilishiga tayanadi. Termin ko'pincha
  ot birikmasi (noun phrase) bo'ladi. D. Burigo (D. Bourigault, 1992) yaratgan LEXTER
  tizimi fransuz tilidagi matnlardan ot birikmalarini sintaktik tahlil yordamida
  ajratdi. J. Juston va S. Kats (Justeson, Katz, 1995) ingliz tili uchun POS-teglar
  qolipini taklif qildi: `((A | N)+ | ((A | N)*(N P)?)(A | N)*) N`. Bu qolip hozirgacha
  ATE tizimlarining asosiy filtri bo'lib qolmoqda.
- Bu usullarning cheklovi: ular har qanday ot birikmasini nomzod deb oladi,
  shuning uchun aniqlik (precision) past.

### 1.2.3. Statistik va gibrid usullar (1990–2000-yillar)

Nomzodlarni saralash uchun statistik o'lchovlar qo'shildi. Bunda ikki xil
xususiyat o'lchanadi (Kageura, Umino, 1996):

- **termhood** — birlikning sohaviy tushunchaga ishora qilish darajasi;
- **unithood** — birikmaning barqaror birlik ekanligi.

Asosiy o'lchovlar:

| O'lchov | G'oya | Manba |
|---|---|---|
| TF-IDF | hujjatda tez-tez, korpusda kam uchraydigan birlik | Salton, Buckley (1988) |
| C-value | ko'p so'zli terminning chastotasi, ichma-ich nomzodlarni hisobga olib | Frantzi, Ananiadou, Mima (2000) |
| NC-value | C-value + termin kontekstidagi so'zlar og'irligi | Frantzi, Ananiadou, Mima (2000) |
| Weirdness | soha korpusidagi nisbiy chastotaning umumiy korpusdagiga nisbati | Ahmad va boshq. (1999) |
| Log-likelihood | soha va umumiy korpus chastotalari farqining statistik ahamiyati | Rayson, Garside (2000) |

B. Day (B. Daille, 1996) lingvistik filtrni statistik o'lchovlar bilan birlashtirish
samaradorligini ko'rsatdi. Gibrid "qolip + statistika" sxemasi bir necha o'n yil
davomida standart bo'lib qoldi. ATR4S kabi vositalar bunday o'lchovlarning
o'nlablarini bir xil sharoitda solishtirish imkonini berdi (Astrakhantsev, 2018).

### 1.2.4. Mashinali o'qitish (2000–2010-yillar)

ATE ketma-ketlikni belgilash (sequence labeling) vazifasi sifatida qo'yila boshlandi.
Bunda har bir token `B-TERM / I-TERM / O` tegi oladi. Bu nomlangan obyektlarni aniqlash
(NER) vazifasiga o'xshaydi. Asosiy modellar:

- shartli tasodifiy maydonlar (CRF; Lafferty, McCallum, Pereira, 2001);
- leksik, morfologik va kontekst xususiyatlariga asoslangan klassifikatorlar.

Belgilangan korpuslar paydo bo'ldi: biotibbiyot sohasida GENIA (Kim va boshq., 2003).
Ular nazoratli o'qitish va usullarni bir xil mezonda baholash imkonini berdi.

### 1.2.5. Chuqur o'qitish va transformatorlar (2015-yildan)

So'z vektorlari (word2vec; Mikolov va boshq., 2013) va neyron tarmoqlar qo'llanila
boshlandi.

- **BiLSTM-CRF** (Huang, Xu, Yu, 2015; Lample va boshq., 2016) xususiyatlarni qo'lda
  tanlash zaruratini kamaytirdi.
- **Transformer arxitekturasi** (Vaswani va boshq., 2017) va oldindan o'qitilgan til
  modellari (BERT — Devlin va boshq., 2019; ko'p tilli XLM-RoBERTa — Conneau va
  boshq., 2020) ATE natijalarini sezilarli oshirdi.
- **TermEval 2020** umumiy vazifasida (ACTER korpusi; Rigouts Terryn va boshq., 2020)
  eng yaxshi natijalarni transformerga asoslangan token klassifikatorlari ko'rsatdi.
  Ular ko'p tilli va sohalararo sharoitda ham yaxshi ishladi (Lang va boshq., 2021).
- **Ko'p tilli embedding modellari** (LaBSE — Feng va boshq., 2022) tillararo termin
  moslashtirish va bilingval terminologik lug'atlarni avtomatik tuzish imkonini berdi.

Hozirgi tendensiyalar:

1. katta til modellari (LLM) yordamida terminlarni ajratish va taʼriflash;
2. terminologiyani bilim graflari va ontologiyalar bilan bog'lash;
3. kam resursli tillar uchun ko'p tilli modellarni moslash.

### 1.2.6. Oʻzbek tili uchun holat

Oʻzbek tili NLP nuqtai nazaridan **kam resursli** til. Hozirda quyidagilar bor:

- ko'p tilli modellar (XLM-RoBERTa, LaBSE) oʻzbek tilini qamraydi;
- oʻzbek tili uchun alohida BERT modellari yaratilgan (UzBERT — Mansurov, Mansurov, 2021);
- morfologik tahlil, matn klassifikatsiyasi va mashina tarjimasi bo'yicha ishlar mavjud.

Lekin terminlarni avtomatik aniqlash bo'yicha quyidagilar yo'q:

- ochiq, belgilangan korpus;
- tekshirilgan ochiq POS-tegger;
- ATE usullarini oʻzbek tilida solishtirgan tadqiqot.

Agglyutinativ morfologiya (bitta termin o'nlab shaklda) va yozuvdagi variantdorlik
(kirill/lotin, apostrof shakllari) boshqa tillar uchun yaratilgan usullarni
bevosita qo'llashni qiyinlashtiradi. Ushbu ish shu bo'shliqni to'ldirishga qaratilgan.
Unda klassik va zamonaviy ATE usullari oʻzbek tiliga moslashtiriladi va bir xil
korpus hamda bir xil metrikalar bilan solishtiriladi (II bob).
