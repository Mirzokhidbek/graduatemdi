## 3.2. Terminlarni xalqaro mezonlar va lingvistik qoidalarga muvofiqligini tekshirishning avtomatik modellari

### 3.2.1. Mezonlar

Termin sifatiga qo'yiladigan talablar ikki manbadan olinadi.

**Xalqaro mezonlar.** ISO 704:2022 "Terminology work — Principles and methods"
standarti termin yaratish tamoyillarini belgilaydi. Tushunchalar ISO 1087:2019
taʼriflariga mos olinadi. Bu tamoyillar:

- shaffoflik (motivatsiya);
- izchillik (tizimlilik);
- muvofiqlik;
- lisoniy tejamkorlik (qisqalik);
- yasalish imkoniyati;
- lisoniy to'g'rilik;
- ona tilidagi shaklni afzal ko'rish.

Bundan tashqari, terminologik meʼyor talabi bor: bitta tushuncha — bitta termin
(sinonimsizlik), bitta termin — bitta tushuncha (bir maʼnolilik).

**Milliy qoidalar.** "Oʻzbek tilining asosiy imlo qoidalari" (1995):

- lotin alifbosi;
- *oʻ, gʻ* va tutuq belgisi;
- o'zlashma so'zlarda *ц* o'rnida *s/ts*;
- lug'atda terminning bosh shaklda (qo'shimchasiz) berilishi.

### 3.2.2. Model

Tekshiruvchi qoidaviy ekspert model (`backend/app/norms/checker.py`). Har bir qoida
natijasi to'rt darajadan biri:

- `ok` — muvofiq;
- `info` — izoh;
- `warning` — ogohlantirish;
- `error` — xato.

Natija izoh va qoida manbasi bilan beriladi. Imlo va shakl qoidalari uchun tuzatish
taklifi ham beriladi. Tuzatishlar ketma-ket qo'llanadi: *Fonemalar → fonemalar → fonema*.

**3.5-jadval.** Qoidalar:

| Qoida | Manba | Daraja | Tekshiruv | Misol |
|---|---|---|---|---|
| `script` | Imlo (1995) | xato | kirill yoki aralash yozuv | *фонема → fonema*; *fonemа* (kirill «а») *→ fonema* |
| `alphabet` | Imlo (1995) | xato | alifboda yo'q harflar (*c* (*ch* dan tashqari), *w*, *ş*, *ı*) | *abstraction* |
| `apostrophe` | Imlo (1995) | ogohl. | *oʻ, gʻ* uchun ʻ (U+02BB), tutuq belgisi uchun ʼ (U+02BC) | *o'zak → oʻzak* |
| `ts_rule` | Imlo (1995) | ogohl. | *ц*: so'z boshida va undoshdan keyin *s*, unlidan keyin *ts* | *tsirk → sirk* |
| `lowercase` | Imlo (1995) | izoh | termin kichik harf bilan | *Fonema → fonema* |
| `spacing` | Imlo (1995) | ogohl. | ortiqcha bo'shliq, defis atrofida bo'shliq | *soʻz  turkumi* |
| `dictionary_form` | Lug'at shakli | ogohl. | ko'plik va kelishik qo'shimchasisiz (3.1.1-algoritm) | *fonemalarning → fonema* |
| `monosemy` | ISO 704 | ogohl. / izoh | shakl bazada bir nechta yozuvga tegishli; umumiy so'z bilan omonim (3.1.3) | *qoʻshimcha* |
| `synonymy` | ISO 704 | ogohl. | yozuvda sinonim yoki dublet bor | *lingvistika ~ tilshunoslik* |
| `native_form` | ISO 704 | izoh | xalqaro termin uchun bazada oʻzbekcha muqobil bor | *affiks → qoʻshimcha* |
| `conciseness` | ISO 704 | ogohl. (> 3 so'z), xato (> 5) | lisoniy tejamkorlik | *ikkinchi shaxs koʻplik qoʻshimchasi turi* |
| `derivability` | ISO 704 | izoh | ≥ 3 so'zli termindan yasash qiyin | |
| `systematicity` | ISO 704 | izoh | ko'p so'zli terminning bosh so'zi bazada termin sifatida yo'q | *soʻz turkumi* (*turkum* yo'q) |

Kirill → lotin o'girish rasmiy moslik jadvali va kontekst qoidalari asosida
bajariladi (3.1.3):

- *е* so'z boshida, unlidan va *ъ* dan keyin *ye* bo'ladi;
- undosh va iotali unli orasidagi *ъ* yozilmaydi: *объект → obyekt*, lekin *меъёр → meʼyor*;
- *ц* yuqoridagi qoida bo'yicha o'giriladi.

Aralash yozuvli so'zda (lotin so'z ichida kirill harfi) esa transliteratsiya emas,
**vizual o'xshashlik** bo'yicha almashtirish qo'llanadi. Masalan, *уordamchi* ichidagi
kirill «у» — bu *y*, *u* emas. Bunday xato klaviatura almashganda yoki matn
nusxalanganda paydo bo'ladi va ko'z bilan ko'rinmaydi.

**Qo'llanish.**

- Interfeys: "Meʼyor tekshiruvi" sahifasi (`#check`). Har qatorda bitta termin
  kiritiladi, natija jadval ko'rinishida chiqadi.
- API: `POST /api/check-terms`.
- Butun bazani tekshirish: `python -m app.norms.checker --output reports/term-check.json`.

### 3.2.3. Baholash

**Imlo va shakl qoidalari: sintetik baholash.** Inson belgilagan "meʼyorga zid
terminlar" to'plami hali yo'q. Shuning uchun bazadagi 450 ta termin to'g'ri shakl deb
olindi va har biri bitta turdagi xato bilan buzildi (`app/norms/experiment.py`).
Ikki narsa o'lchandi:

- tekshiruvchi kutilgan qoidani ishga tushirdimi (aniqlash);
- taklif qilingan shakl asl terminga tengmi (tuzatish).

**3.6-jadval.** Sintetik xatolar (`reports/term-check-synthetic.json`):

| Xato turi | Qoida | Soni | Aniqlandi | To'g'ri tuzatildi |
|---|---|---|---|---|
| Kirill yozuvi | `script` | 450 | 1.000 | 0.996 |
| Aralash yozuv (bitta kirill harfi) | `script` | 441 | 1.000 | 1.000 |
| Norasmiy apostrof (`'`) | `apostrophe` | 148 | 1.000 | 1.000 |
| Ko'plik + qaratqich (*-larning*) | `dictionary_form` | 119 | 1.000 | 1.000 |
| O'rin-payt kelishigi (*-da*) | `dictionary_form` | 119 | 1.000 | 1.000 |
| Bosh harf | `lowercase` | 450 | 1.000 | 1.000 |
| Ortiqcha bo'shliq | `spacing` | 335 | 1.000 | 1.000 |

Buzilmagan 450 ta terminda imlo va shakl qoidalari birorta ham yolg'on
ogohlantirish bermadi (0.000).

Kirill yozuvidagi 2 ta tuzatilmagan holat (*obyekt*, *subyekt*) sintetik
generatorning soddaligidan kelib chiqqan. Generator *обект* yozadi, to'g'ri
kirill shakli esa *объект*. To'g'ri yozilgan *объект* to'g'ri o'giriladi.

Bu natijalar faqat qoidalarning **ichki izchilligini** ko'rsatadi, chunki sintetik
xatolar qoidalar qamragan turlardan yasalgan. Real matndagi xatolar xilma-xilroq:

- manbadagi imlo xatolari (*Nosatandart*, *alloton*). Ularni 3.1.3-dagi imlo xatosi
  detektori topadi;
- ellipsis;
- qo'shma so'zlarni qo'shib yoki ajratib yozish. Bu qoidalar hozircha tekshirilmaydi.

**ISO 704 tamoyillari: ekspert bahosi.** Butun baza (450 termin) bo'yicha natija
(`reports/term-check.json`):

- 193 ta termin `ok`;
- 252 tasida faqat izoh: asosan `systematicity` (224) va `derivability` (39);
- 5 tasida ogohlantirish: 4 ta sinonim/dublet, 1 ta uzun termin.

Baza oldindan rasmiy imloga keltirilgani uchun imlo xatolari yo'q.

Tamoyillar bo'yicha qarorlar (sinonimlik, bir maʼnolilik, tizimlilik) subyektiv.
Shuning uchun ular mutaxassis bahosi bilan solishtiriladi: tasodifiy 100 ta termin
(`data/judgments/term-check-review.csv`, `expert` ustuni). Baho to'ldirilgach,
tizim va ekspert darajalari orasidagi Cohen's kappa hisoblanadi. **Holat: ekspert
bahosi kutilmoqda.**

### 3.2.4. Cheklovlar

1. **Qo'shma so'zlar imlosi** (qo'shib, ajratib yoki defis bilan yozish) tekshirilmaydi.
   Imlo qoidalarining bu bo'limi ko'p istisnoli va lug'atga tayanadi.
2. **O'zlashma va o'zbekcha so'zni ajratish** taxminiy. U qo'shimcha va harf
   birikmalariga asoslanadi: *tavsifiy* (arabcha) o'zbekcha deb olinadi, chunki
   o'zlashib bo'lgan.
3. **`systematicity` qoidasi** bazaning to'liqligiga bog'liq. 450 terminli bazada
   bosh so'zlarning ko'pchiligi yo'q, shuning uchun bu izoh ko'p chiqadi. Baza
   kengaygani sari u aniqlashadi.
4. **Qoidalar meʼyoriy qarorni almashtirmaydi.** *lingvistika* yoki *tilshunoslik*
   shakllaridan qaysi biri meʼyoriy ekanini terminologik siyosat va manba belgilaydi.
   Tizim faqat ziddiyatni ko'rsatadi.
