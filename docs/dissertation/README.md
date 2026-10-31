# UzTerm AI — dissertatsiya uchun ilmiy hujjat

**Mavzu:** Oʻzbek tilidagi ona tili va tilshunoslik matnlaridan terminlarni avtomatik
aniqlash va meʼyorlashtirish.

Bu papkada loyihaning arxitekturasi, algoritmlari, maʼlumotlari, tajribalari, natijalari
va cheklovlari ilmiy uslubda bayon qilingan. Matn magistrlik dissertatsiyasining
tegishli boblariga asos sifatida yozilgan. Barcha raqamlar repozitoriydagi skriptlar
bilan qayta hosil qilinadi (6-bo'lim).

| Bob | Fayl | Mazmuni |
|---|---|---|
| 1 | [01-kirish.md](01-kirish.md) | Dolzarblik, vazifaning qo'yilishi, ish hajmi, ilmiy yangilik |
| 2 | [02-malumotlar.md](02-malumotlar.md) | Korpus, annotatsiya yo'riqnomasi, BIO dataset, to'plamlarga ajratish |
| 3 | [03-arxitektura-algoritmlar.md](03-arxitektura-algoritmlar.md) | Tizim arxitekturasi, preprocessing, lug'at aniqlagichi, CRF, meʼyorlashtirish |
| 4 | [04-tajribalar-natijalar.md](04-tajribalar-natijalar.md) | Tajriba sxemasi, metrikalar, natijalar, xato tahlili |
| 5 | [05-cheklovlar-xulosa.md](05-cheklovlar-xulosa.md) | Cheklovlar, haqqoniylikka xavflar, xulosa, keyingi ishlar |
| 6 | [06-takrorlash.md](06-takrorlash.md) | Natijalarni takrorlash buyruqlari, dasturiy taʼminot |

> **Muhim eslatma.** Dissertatsiya matnida quyidagilar aniq ko'rsatilishi shart:
> - Barcha annotatsiyani AI (Claude) bajargan: korpus, 100 gaplik BIO dataset va
>   test to'plamining ikkinchi belgilanishi. Bu "kumush" maʼlumot.
> - Natijalar inson oltin standarti bo'yicha emas.
> - Ikki inson annotator kelishuvi o'lchanmagan.
>
> Inson annotatsiyasi yakunlangach, 4-bobdagi jadvallar 6-bobdagi buyruqlar bilan
> qayta hisoblanishi kerak.
