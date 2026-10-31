# 5-bob. Cheklovlar, muhokama va xulosa

## 5.1. Cheklovlar va natijalarning haqqoniyligiga xavflar

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
   belgilandi (4.2-jadval). Lug'at natijasi kutilganidek pasaydi (0.553 → 0.536),
   lekin xulosalar o'zgarmadi.
3. **Maʼlumot hajmi va janri.**
   - Korpus 41 ta ensiklopedik maqoladan iborat.
   - Test 6 ta maqola va 35 ta paragraf, bootstrap oraliqlari keng (± 0.08).
   - Darslik, ilmiy maqola va dissertatsiya janrlari uchun natija noma'lum.
4. **Transformer modellari sinab ko'rilmadi.** Ishlab chiqish muhitida
   HuggingFace'ga kirish yo'q edi. XLM-R kabi ko'p tilli modellar katta ehtimol
   bilan yuqoriroq natija beradi, lekin ular ko'proq belgilangan maʼlumot talab qiladi.
5. **Weirdness usuli sinalmadi.** Usul amalga oshirilgan, lekin unga kerakli
   kontrast korpus (sohaga oid bo'lmagan oʻzbek matnlari) yig'ilmagan.
6. **Morfologiya qoidaviy.** Qo'shimchalar ro'yxati faqat ot so'z turkumini
   qamraydi. Fe'l asosli terminlar (*soʻz yasash*) va izofa istisnolari to'liq
   hal qilinmagan. Ellipsis tiklanmaydi. Eng qisqa o'zakni tanlash qoidasi
   korpusda mustaqil so'z bo'lgan qisqa o'zakda adashadi (*kesim → kes*).
7. **Lug'at tekshirilmagan.**
   - 450 ta yozuvning barchasi `needs_review` holatida.
   - 435 tasining ta'rifi yo'q.
   - Asosiy terminlar ilmiy manba (izohli va terminologik lug'atlar) bilan
     tasdiqlanishi kerak.

## 5.2. Xulosa

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
   [+0.06; +0.14]. Gazetteersiz CRF yangi terminlarning 20 % ini topadi.
5. **Meʼyorlashtirish.** Lug'at, morfologik qoidalar, tovush o'zgarishlarini
   tiklash, izofani saqlash va fonotaktik cheklov birgalikda lug'at shaklini
   90–94 % aniqlikda topadi. Faqat lug'at 63–71 %, korpus lemmatizatori 74–81 % beradi.
6. **Takrorlanuvchanlik.** Barcha natijalar repozitoriydagi buyruqlar bilan qayta
   hosil qilinadi. CRF deterministik: qayta o'qitilganda natija o'zgarmaydi.

## 5.3. Keyingi ishlar

1. **Inson annotatsiyasi.**
   - Ikki annotator belgilaydi; test to'plami takliflarsiz.
   - Kelishuv o'lchanadi (`agreement compare`).
   - Kelishmovchiliklar yo'riqnoma asosida hal qilinadi.
   - `reviewed` yozuvlar oltin standartga o'tkaziladi (`promote`) va 4-bob
     jadvallari qayta hisoblanadi.
2. **Korpusni kengaytirish.** Darsliklar, ilmiy maqolalar va dissertatsiya
   avtoreferatlari foydalanish huquqi bilan qo'shiladi. Maqsad 1 000+ paragraf.
3. **Transformer modeli.** XLM-R yoki mBERT asosida token classification.
   CRF bilan bir xil test to'plamida va bir xil metrika bilan solishtiriladi.
4. **Lug'atni tasdiqlash.** Terminlar izohli va terminologik lug'atlar bilan
   solishtiriladi va `approved` holati manba bilan beriladi. Variant va
   sinonimlar bog'lanadi (*lingvistika ↔ tilshunoslik*).
5. **Chegara xatolari.** Aniqlovchili birikmalar uchun maxsus xususiyatlar
   (*umumiy, amaliy, nazariy + termin*) yoki kontekstdan keyin qayta ishlovchi
   qoida qo'shiladi.

## Adabiyotlar

1. Ahmad K., Gillam L., Tostevin L. University of Surrey participation in TREC8:
   weirdness indexing for logical document extrapolation and retrieval (WILDER) //
   TREC-8, 1999.
2. Cohen J. A coefficient of agreement for nominal scales // Educational and
   Psychological Measurement, 1960, 20(1), 37–46.
3. Efron B., Tibshirani R. J. An Introduction to the Bootstrap. Chapman & Hall, 1993.
4. Frantzi K., Ananiadou S., Mima H. Automatic recognition of multi-word terms:
   the C-value/NC-value method // International Journal on Digital Libraries,
   2000, 3(2), 115–130.
5. Lafferty J., McCallum A., Pereira F. Conditional random fields: probabilistic
   models for segmenting and labeling sequence data // ICML, 2001.
6. Okazaki N. CRFsuite: a fast implementation of Conditional Random Fields (CRFs),
   2007. http://www.chokkan.org/software/crfsuite/
7. Ramshaw L., Marcus M. Text chunking using transformation-based learning //
   Third Workshop on Very Large Corpora, 1995.
8. Tjong Kim Sang E. F., De Meulder F. Introduction to the CoNLL-2003 shared task:
   language-independent named entity recognition // CoNLL, 2003.
9. Oʻzbek tilining asosiy imlo qoidalari. Vazirlar Mahkamasining 1995-yil
   24-avgustdagi 339-son qarori bilan tasdiqlangan.
