## Uchinchi bob bo'yicha xulosalar

1. **Variantdorlik turlari va ularni aniqlash usullari:**
   - imlo va yozuv variantlari — imlo skeleti va kontekstga bog'liq kirill → lotin
     transliteratsiyasi;
   - morfologik shakllar — lug'at shakliga keltirish;
   - imlo xatolari — tahrir masofasi va chastota sharti;
   - sinonim va dubletlar — matndagi qavs, *yoki*, *yaʼni* qoliplari;
   - omonimiya — kontekst klassifikatori.

   Morfologik va imlo shakllarini birlashtirish guruhlash recall'ini 0.64 dan 0.93 ga
   oshiradi, precision 1.000 da qoladi. Sintetik imlo shovqini (apostrof,
   kirill yozuvi, bosh harf) to'liq bartaraf etiladi.
2. **Omonimiya.** Lug'at usuli ko'p maʼnoli terminlarning (*sifat, ega, ravish,
   qoʻshimcha*) qariyb yarmida xato qiladi. Kontekst modeli aniqlikni 0.47–0.58 dan
   0.83–0.84 gacha oshiradi.
3. **Meʼyorga muvofiqlikni tekshirish** qoidaviy ekspert model sifatida qurildi.
   Uning qoidalari ISO 704 tamoyillari va "Oʻzbek tilining asosiy imlo qoidalari"
   (1995) dan olingan. Imlo va lug'at shakli qoidalari sintetik xatolarning 100 % ini
   aniqlaydi, 99.6–100 % ini to'g'ri tuzatadi, toza terminlarda yolg'on signal bermaydi.
   ISO 704 tamoyillari bo'yicha qarorlar ekspert bahosi bilan tekshirilishi kerak.
4. **Ko'p tilli moslashtirish** ikki sinf terminlar uchun turlicha hal bo'ladi.
   - Xalqaro terminlarni qoidaviy kognat modeli deyarli xatosiz moslashtiradi
     (Acc@1 0.97–0.99).
   - Oʻzbekcha terminlar (taxminan 40 %) uchun semantik (embedding) model zarur.

   Ishonch chegarasi bilan ikki bosqichli sxema taklif qilindi: θ = 0.7 da qamrov
   58 %, aniqlik 98.5 %.
5. **Meʼyoriy shaklni tanlash** qoidalar zanjiri bilan bajariladi:
   - tasdiqlangan manba;
   - rasmiy imlo;
   - lug'atdagi meʼyoriy shakl;
   - korpus chastotasi (uzus);
   - qisqalik.

   Har bir tavsiya sababi bilan beriladi. Dubletlar orasida (*intonatsiya / ohang*,
   *orfografiya / imlo*, *abbreviatsiya / qisqartma*) korpusda oʻzbekcha shakllar
   ko'proq qo'llangan. Lekin tizim bu shakllarni meʼyoriy deb eʼlon qilmaydi: qaror
   terminologik komissiya yoki manba bilan qabul qilinadi.
