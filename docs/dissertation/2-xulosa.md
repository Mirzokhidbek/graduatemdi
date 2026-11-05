## Ikkinchi bob bo'yicha xulosalar

> Barcha raqamlar AI tomonidan belgilangan (kumush) maʼlumot bo'yicha. Inson oltin
> standarti tayyor bo'lgach, ular qayta hisoblanadi (B ilova).

1. **Lingvistik model** oʻzbek tilining qo'shimchaga asoslangan sintaksisini hisobga
   oladi. Qolip `(Sifat | qo'shimchasiz Ot)* Ot`: aniqlovchi ot qo'shimcha olmaydi,
   qaratqich birikmani bo'ladi. Model eng yuqori recall'ga ega (0.655) va train'da
   uchramagan terminlarning 68.5 % ini topadi. Lekin aniqligi past (0.184).
2. **Statistik modellar** ichida kontrast korpusga asoslangan **Weirdness** eng
   yaxshi natija berdi: qolip filtri bilan P@10 = P@20 = 0.90. C-value va NC-value
   bitta sohali korpusda umumiy so'zlarni (*soʻz, til, maʼno*) yuqoriga ko'taradi.
   NC-value C-value'ni yaxshilamadi, chunki kontekst so'zlarining o'zi umumiy leksika.
3. **Gibrid model** (qolip + Weirdness) sof lingvistik modeldan statistik ishonchli
   yaxshiroq: F1 0.288 → 0.459, farqning 95 % oralig'i [+0.08; +0.26].
   Belgilangan maʼlumot talab qilmaydi.
4. **Nazoratli CRF modeli** oʻzbek morfologiyasiga moslashtirilgan xususiyatlar
   (o'zak, qo'shimcha, ±2 kontekst) va lug'at belgisi (gazetteer) bilan eng yuqori
   F1 ga erishdi: 0.649. Lug'atdan ustunligi statistik ishonchli. Gazetteersiz CRF
   yangi terminlarning 21 % ini topadi. Transformer (XLM-R) modeli tayyorlangan,
   natijasi Colab'da olinadi.
5. **Tezaurus** uch mustaqil manbadan avtomatik shakllantirildi:
   - bosh so'z ierarxiyasi;
   - taʼrif tahlili ("A — … X ning bir turi");
   - Hearst qoliplarining oʻzbekcha moslamalari.

   Natija: 662 tushuncha, 268 tur–jins munosabati, 226 assotsiativ juft, sikllar yo'q.
   Format — SKOS.
6. **Amaliy xulosa: usullar bir-birini to'ldiradi.**
   - Lingvistik va gibrid modellar yangi terminlarni topish va lug'atni to'ldirish
     uchun mos.
   - CRF + gazetteer — matnni aniq belgilash uchun.
   - Tezaurus — topilgan terminlarni tushunchalar tizimiga joylashtirish uchun.
