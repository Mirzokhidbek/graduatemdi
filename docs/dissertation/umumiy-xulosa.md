# Xulosa

## Asosiy natijalar

1. **Korpus va annotatsiya.** Oʻzbek tilshunoslik matnlari korpusi tuzildi:
   41 maqola, 17 777 token, manba va litsenziya bilan. Yo'riqnoma, JSONL va BIO
   formatlari, avtomatik tekshiruvchi va web annotatsiya interfeysi ishlab chiqildi.
   Korpus AI tomonidan belgilandi (2 555 span). 100 gaplik BIO dataset qo'lda
   tekshirildi (14 ta tuzatish, 0 ta format xatosi).
2. **Preprocessing.** Apostrof variantlari ikki xil qayta ishlanadi:
   - qidiruv uchun — uzunlikni saqlab bitta belgiga keltiriladi;
   - saqlash uchun — rasmiy *ʻ/ʼ* shaklga keltiriladi.

   Gaplarga ajratish qisqartmalarni hisobga oladi.
3. **Lug'at aniqlagichi.** Ot qo'shimchalari zanjiri va tovush o'zgarishlarini
   hisobga oladi, aniqligi yuqori (P ≈ 0.77). Lekin u faqat lug'atdagi terminlarni
   topadi (yangi terminlarda R = 0).
4. **CRF modeli.** Oʻzbek morfologiyasiga mos xususiyatlar bilan CRF lug'at
   usulidan yaxshiroq. Lug'at belgisi bilan birga (CRF+G) F1 = 0.638–0.649 ga
   yetadi. Lug'atdan ustunligi statistik ishonchli: farqning 95 % oralig'i
   [+0.06; +0.14]. Gazetteersiz CRF yangi terminlarning 21 % ini topadi.
5. **Meʼyorlashtirish.** Lug'at, morfologik qoidalar, tovush o'zgarishlarini
   tiklash, izofani saqlash va fonotaktik cheklov birgalikda lug'at shaklini
   91–94 % aniqlikda topadi (test natijasi test xatolari bo'yicha sozlangan,
   sozlashdan oldin 0.85–0.86). Faqat lug'at 63–71 %, korpus lemmatizatori 74–81 % beradi.
6. **Takrorlanuvchanlik.** Barcha natijalar repozitoriydagi buyruqlar bilan qayta
   hosil qilinadi. CRF deterministik: qayta o'qitilganda natija o'zgarmaydi.

## Cheklovlar va natijalarning haqqoniyligiga xavflar

1. **Annotatsiyani AI bajargan.**
   - Korpus, 100 gaplik BIO dataset va test to'plamining ikkinchi belgilanishini
     Claude bajargan.
   - Ikki belgilash orasidagi kelishuv (F1 0.965) — bitta baholovchining
     barqarorligi. U ikki mustaqil inson annotator kelishuvi o'rnini bosmaydi.
   - AI xatolari tizimli bo'lishi mumkin: bir xil qaror butun maqolaga qo'llangan.
     Bu holda model AI qarorlarini o'rganadi va baholash ham ularni "to'g'ri" deb
     hisoblaydi.
   - **Natijalar inson oltin standartida qayta tekshirilishi shart.**
2. **Lug'at baseline'i uchun qulay belgilash.** Ro'yxat usulidagi spanlar lug'at
   aniqlagichi bilan yaratilgan. Shuning uchun test qayta, uchrash-ma-uchrash
   belgilandi (2.3-jadval). Lug'at natijasi kutilganidek pasaydi (0.553 → 0.536),
   lekin xulosalar o'zgarmadi.
3. **Maʼlumot hajmi va janri.**
   - Korpus 41 ta ensiklopedik maqoladan iborat.
   - Test 6 ta maqola va 35 ta paragraf, bootstrap oraliqlari keng (± 0.08).
   - Darslik, ilmiy maqola va dissertatsiya janrlari uchun natija noma'lum.
4. **Transformer natijasi hali yo'q.** XLM-R kodi va Colab notebook tayyor
   (2.2.4, 2.2.7), lekin ishlab chiqish muhitida HuggingFace'ga kirish bo'lmagani
   uchun model hali o'qitilmagan. Ko'p tilli modellar odatda ko'proq belgilangan
   maʼlumot talab qiladi.
5. **Kontrast korpus hajmi cheklangan.** Weirdness usuli uchun 48 ta maqoladan
   iborat kontrast korpus (tarix, tibbiyot, matematika, islom, tabiat) yig'ilib
   sinaldi va u umumiy leksikani filtrlashda yuqori natija berdi (P@20=0.90).
   Biroq kattaroq va ko'p janrli umumiy korpus (masalan, to'liq o'zbekcha Vikipediya
   yoki matbuot korpusi) bilan solishtirish nomzodlar aniqligini yanada oshirishi mumkin.
6. **Morfologiya qoidaviy.** Qo'shimchalar ro'yxati faqat ot so'z turkumini
   qamraydi. Fe'l asosli terminlar (*soʻz yasash*) va izofa istisnolari to'liq
   hal qilinmagan. Ellipsis tiklanmaydi. Eng qisqa o'zakni tanlash qoidasi
   faqat I/II shaxs birlik egaligi uchun cheklangan (*kesim*); boshqa
   qo'shimchalarda korpusda mustaqil so'z bo'lgan qisqa o'zakda adashishi mumkin.
   *-ka* va *-im* tuzatishlari test xatolaridan kelib chiqqan (3.1.2).
7. **Lug'at tekshirilmagan.**
   - 450 ta yozuvning barchasi `needs_review` holatida.
   - 435 tasining ta'rifi yo'q.
   - Asosiy terminlar ilmiy manba (izohli va terminologik lug'atlar) bilan
     tasdiqlanishi kerak.

## Keyingi ishlar

1. **Inson annotatsiyasi.**
   - Ikki annotator belgilaydi; test to'plami takliflarsiz.
   - Kelishuv o'lchanadi (`agreement compare`).
   - Kelishmovchiliklar yo'riqnoma asosida hal qilinadi.
   - `reviewed` yozuvlar oltin standartga o'tkaziladi (`promote`) va 4-bob
     jadvallari qayta hisoblanadi.
2. **Korpusni kengaytirish.** Darsliklar, ilmiy maqolalar va dissertatsiya
   avtoreferatlari foydalanish huquqi bilan qo'shiladi. Maqsad 1 000+ paragraf.
3. **Transformer modeli.** `notebooks/xlmr_colab.ipynb` Colab'da ishga
   tushiriladi va 2.2.7-bo'lim to'ldiriladi. Inson oltin standarti tayyor bo'lgach,
   tajriba qayta takrorlanadi.
4. **Lug'atni tasdiqlash.** Terminlar izohli va terminologik lug'atlar bilan
   solishtiriladi va `approved` holati manba bilan beriladi. Variant va
   sinonimlar bog'lanadi (*lingvistika ↔ tilshunoslik*).
5. **Toza test.** Vikipediyadan tizim hali ko'rmagan 4–5 ta yangi tilshunoslik
   maqolasi olinadi va tizim hech narsa o'zgartirilmasdan bir marta baholanadi.
   3.1.2-bo'limdagi "test bo'yicha sozlangan" natijalar shu yo'l bilan tekshiriladi.
6. **Chegara xatolari.** Aniqlovchili birikmalar uchun maxsus xususiyatlar
   (*umumiy, amaliy, nazariy + termin*) yoki kontekstdan keyin qayta ishlovchi
   qoida qo'shiladi.
