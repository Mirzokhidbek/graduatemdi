# Kirish

## Mavzuning dolzarbligi

Terminologiya fan tilining tayanchi hisoblanadi. Oʻzbek tilida tilshunoslik
terminlari bir necha yozuv islohotlari va turli manbalar taʼsirida shakllangan.
Natijada bir tushuncha uchun bir nechta shakl uchraydi: *lingvistika* va
*tilshunoslik*, *affiks* va *qoʻshimcha*, *oʻzak* va *asos*. Apostrof belgilari ham
turlicha yoziladi: *oʻ*, *o'*, *o‘*, *o`*. Terminlar matndan qo'lda ajratilsa, bu
ko'p mehnat talab qiladi va natija subyektiv bo'ladi. Terminlarni avtomatik
aniqlash quyidagilar uchun asos bo'ladi:

- terminologik lug'atlarni tuzish va yangilash;
- darslik va ilmiy matnlarda atamalar izchilligini tekshirish;
- qidiruv va mashina tarjimasi tizimlari.

Oʻzbek tili agglyutinativ tildir. Bitta termin matnda o'nlab shaklda keladi:
*fonema, fonemalar, fonemaning, fonemalardan, fonemasi*. Bunga tovush o'zgarishlari
ham qo'shiladi: *kelishik → kelishigi*, *oʻrin → oʻrni*. Shu sababli boshqa tillar
uchun ishlab chiqilgan, so'zni o'zgarmas birlik deb oluvchi usullar oʻzbek tiliga
bevosita mos kelmaydi. Oʻzbek tili uchun ochiq, belgilangan termin korpusi va
tekshirilgan POS-tegger ham mavjud emas.

## Vazifaning qo'yilishi

**Kiruvchi maʼlumot:** oʻzbek (lotin yozuvi) tilidagi ilmiy yoki taʼlimiy matn.

**Chiquvchi maʼlumot:**

1. matndagi har bir terminning pozitsiyasi `[start, end)` (Unicode belgilari bo'yicha);
2. terminning lug'at shakli (qo'shimchasiz): *fonemalarning → fonema*;
3. lug'atda bo'lsa, asosiy termin va meʼyoriy shakl, hamda uning holati
   (tasdiqlangan / tekshirilmagan).

Vazifa ikki bosqichga bo'linadi:

- **termin chegaralarini aniqlash** — ketma-ketlikni belgilash (sequence
  labeling), BIO sxemasida;
- **meʼyorlashtirish** — topilgan shaklni lug'at shakliga keltirish.

**Termin** deganda ona tili va tilshunoslik sohasidagi maxsus tushunchani
ifodalovchi so'z yoki so'z birikmasi tushuniladi. U matnda aynan shu maxsus maʼnoda
qo'llangan bo'lishi kerak (annotatsiya yo'riqnomasi, 1-bo'lim). Masalan,
*qoʻshimcha* "affiks" maʼnosida termin, "qoʻshimcha maʼlumot" birikmasida termin emas.

## Ish hajmi

- **Soha:** ona tili va tilshunoslik (fonetika, morfologiya, sintaksis,
  leksikologiya va boshqalar).
- **Yozuv:** lotin. Kirill yozuvi ishga kirmaydi.
- **Annotatsiya:** bitta teg — `TERM`. Ichma-ich terminlar belgilanmaydi (tekis annotatsiya).
- **Meʼyoriylik:** tizim manbasi bo'lmagan shaklni hech qachon "meʼyoriy" deb eʼlon
  qilmaydi. Lug'atda yo'q termin uchun natija faqat taklif bo'ladi.

## Ishning amaliy va ilmiy natijalari

1. **Korpus.** Oʻzbek tilshunoslik matnlari korpusi tuzildi: 41 ta maqola,
   17 777 token. Har bir matnning manbasi va litsenziyasi qayd etilgan.
2. **Annotatsiya vositalari.** Annotatsiya yo'riqnomasi, JSONL va BIO formatlari,
   tekshiruvchi va web annotatsiya interfeysi ishlab chiqildi.
3. **Lug'at aniqlagichi.** Oʻzbek ot qo'shimchalari zanjiri va tovush
   o'zgarishlarini hisobga oladi.
4. **CRF modeli.** Xususiyatlar oʻzbek morfologiyasiga moslab tanlandi.
   Lug'atga asoslangan usul bilan statistik ishonch oralig'i bilan taqqoslandi.
5. **Meʼyorlashtirish algoritmi.** Lug'at va morfologik qoidalarga (izofa va
   tovush o'zgarishlarini tiklash bilan) asoslanadi.
6. **Takrorlanuvchi tajriba metodikasi:**
   - manba darajasida to'plamlarga ajratish;
   - test to'plamini bir marta ishlatish qoidasi;
   - bootstrap ishonch oraliqlari.

**Ilmiy yangilik** (kumush maʼlumot doirasida tasdiqlangan):

- Oʻzbek tilshunoslik terminlarini aniqlashda ikki usul birlashtirildi: CRF ketma-ketlik
  modeli va lug'at belgisi (gazetteer) xususiyati. Bu birlashma lug'at usulidan statistik
  ishonchli yaxshiroq: F1 farqining 95 % oralig'i [+0.06; +0.14].
- Meʼyorlashtirishda ko'p so'zli terminlardagi izofa qo'shimchasini saqlash qoidasi
  (*soʻz birikmalari → soʻz birikmasi*) va jo'nalish kelishigi uchun fonotaktik cheklov
  taklif qilindi. Ular aniqlikni 0.71 dan (faqat lug'at) 0.92 gacha oshiradi.
