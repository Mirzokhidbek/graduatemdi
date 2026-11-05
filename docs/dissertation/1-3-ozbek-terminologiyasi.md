## 1.3. Oʻzbek tili terminologiyasining bugungi holati va avtomatik meʼyorlashtirish tizimlariga bo'lgan ehtiyoj

> **Qoralama.** Matnni Claude (AI) yozgan. Meʼyoriy hujjatlar nomi, sanasi va raqami
> rasmiy manbalar (lex.uz) bilan tekshirilishi kerak.

### 1.3.1. Til siyosati va meʼyoriy asos

Oʻzbek tili terminologiyasining hozirgi holatini bir necha meʼyoriy hujjat belgilaydi:

- **"Davlat tili haqida"gi Qonun** (1989-yil, 1995-yilda yangi tahrirda). Oʻzbek tili
  davlat tili sifatida ilm-fan, taʼlim va ish yuritishda qo'llanishi kerak. Bu
  terminologiyaga bo'lgan talabni keskin oshirdi.
- **Lotin yozuviga asoslangan oʻzbek alifbosi** (1993-yilgi Qonun, 1995-yilgi
  o'zgartirishlar bilan) va **"Oʻzbek tilining asosiy imlo qoidalari"** (Vazirlar
  Mahkamasining 1995-yil 24-avgustdagi 339-son qarori). Bu hujjatlar terminlarning
  lotin yozuvidagi imlosini belgilaydi.
- **Oʻzbekiston Respublikasi Prezidentining 2019-yil 21-oktyabrdagi PF-5850-son
  Farmoni.** U oʻzbek tilining davlat tili sifatidagi nufuzini oshirishga
  qaratilgan. Unda atamashunoslik va terminologik ishlarni muvofiqlashtirish vazifalari
  belgilangan.

### 1.3.2. Hozirgi holatning asosiy muammolari

**1. Yozuv va imlo variantdorligi.** Lotin yozuviga o'tish jarayoni davom etmoqda.
Ilmiy va taʼlimiy matnlarda bir vaqtning o'zida quyidagilar uchraydi:

- kirill yozuvidagi matnlar va ularning avtomatik transliteratsiyasi;
- *oʻ, gʻ* va tutuq belgisining kamida to'qqiz xil yozilishi: `' ` ´ ʹ ʻ ʼ ‘ ’ ′`;
- *ц* harfi bor o'zlashmalarning turlicha yozilishi: *sirk / tsirk*.

Natijada bitta termin elektron matnda bir necha "har xil" so'z bo'lib ko'rinadi.
Qidiruv, lug'at tuzish va statistik tahlil buzilib ketadi.

**2. Dubletlik va sinonimiya.** Ko'plab tushunchalar uchun ikki termin parallel
qo'llanadi: rus tili orqali kirgan xalqaro termin va oʻzbekcha muqobil.

| Xalqaro | Oʻzbekcha |
|---|---|
| lingvistika | tilshunoslik |
| intonatsiya | ohang |
| orfografiya | imlo |
| abbreviatsiya | qisqartma |
| affiks | qoʻshimcha |
| funksiya | vazifa |

Ulardan qaysi biri meʼyoriy ekani ko'p hollarda rasman belgilanmagan. Mualliflar
bir matnning o'zida ikkalasini ishlatadi. Ushbu ishda tuzilgan korpusda ham
ikkala shakl uchraydi va oʻzbekcha shakl ko'proq qo'llangan (3.3-bo'lim).

**3. Terminologik resurslarning holati.**

- Mavjud lug'atlar (masalan, A. Hojiyevning tilshunoslik terminlari izohli lug'ati, 1985)
  asosan bosma shaklda, kirill yozuvida va ko'p yillar avval tuzilgan.
- Mashinada o'qiladigan, tushunchalar tizimi va ko'p tilli ekvivalentlari bilan
  tavsiflangan ochiq terminologik baza yo'q.
- Terminlarni matndan avtomatik aniqlash uchun belgilangan korpus ham yo'q.

**4. Morfologik murakkablik.** Agglyutinativ tuzilish sababli termin matnda ko'plab
shakllarda keladi. Masalan, *fonema* uchun: *fonemalar, fonemaning, fonemasi,
fonemalardan*. Tovush o'zgarishlari ham bor: *kelishik → kelishigi*, *oʻrin → oʻrni*.
Shuning uchun matn bo'yicha terminologik tadqiqotning har bir bosqichi —
qidiruv, chastotani hisoblash, lug'at shakliga keltirish — morfologik tahlilni
talab qiladi.

### 1.3.3. Avtomatik tizimlarga bo'lgan ehtiyoj

Yuqoridagi muammolar avtomatik vositalar zarurligini ko'rsatadi.

| Ehtiyoj | Avtomatik yechim | Ushbu ishdagi bo'lim |
|---|---|---|
| Yangi matnlardan terminlarni topish va lug'atni to'ldirish | ATE: lingvistik, statistik, ML/DL modellari | 2.1, 2.2 |
| Terminlarni tushunchalar tizimiga joylashtirish | tezaurus va ontologiyani avtomatik shakllantirish | 2.3 |
| Imlo, yozuv va morfologik variantlarni birlashtirish; sinonim va dubletlarni aniqlash | variantdorlik modellari | 3.1 |
| Terminning ISO 704 va oʻzbek imlo qoidalariga muvofiqligini tekshirish | qoidaviy tekshiruvchi | 3.2 |
| Ruscha va inglizcha ekvivalentlarni topish, meʼyoriy oʻzbekcha muqobilni tanlash | tillararo moslashtirish | 3.3 |

Bu vositalar terminologning ishini almashtirmaydi, uni tezlashtiradi va
dalillar bilan taʼminlaydi:

- tizim minglab matnlardan nomzodlar va variantlarni topadi;
- ularning qo'llanish chastotasini o'lchaydi;
- meʼyorga zid holatlarni ko'rsatadi.

Yakuniy meʼyoriy qarorni mutaxassis yoki terminologik komissiya qabul qiladi.
