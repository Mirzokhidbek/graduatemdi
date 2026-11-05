# A ilova. Maʼlumotlar

## A.1. Korpus

Korpus Oʻzbekcha Vikipediyaning 41 ta tilshunoslik maqolasidan iborat
(`data/raw/`, manbalar reyestri `data/sources.json`). Har bir maqola uchun quyidagilar
qayd etilgan:

- aniq versiya (`revid`) va URL;
- mualliflar sahifasi;
- litsenziya: CC BY-SA 4.0.

Matnlar yuklangandan keyin faqat tozalangan: sarlavhalar va adabiyotlar ro'yxati
olib tashlangan. So'zlarning o'zi o'zgartirilmagan, OCR xatolari ham saqlangan
(`Fonemafonologiya`, `ran` — "gap", `fafika` — "grafika").

| Ko'rsatkich | Qiymat |
|---|---|
| Maqolalar | 41 |
| Paragraflar | 310 |
| Gaplar (`split_sentences`) | 1 000 |
| Tokenlar | 17 777 |
| Belgilangan termin uchrashlari | 2 555 |
| Turli lug'at shakllari (ro'yxat usuli) | 659 |

Maqolalar quyidagi bo'limlarni qamraydi:

- **fonetika va fonologiya:** Fonetika, Fonema, Urgʻu, Allofon va boshqalar;
- **morfologiya va so'z turkumlari:** Morfema, Ot, Feʼl, Koʻmakchi va boshqalar;
- **sintaksis:** Gap, Qoʻshma gap, Ega, Kesim;
- **leksikologiya va leksikografiya:** Leksika, Omonimlar, Etimologiya va boshqalar;
- **umumiy maqolalar:** Tilshunoslik, Grammatika, Imlo.

Janr bitta — ensiklopedik matn. Bu cheklov 5-bobda muhokama qilinadi.

### A.1.1. Kontrast korpus (sohaviy bo'lmagan matnlar)

Statistik termin nomzodlarini filtrlash va weirdness (g'ayrioddiylik) o'lchovini hisoblash
uchun Oʻzbekcha Vikipediyadan tilshunoslikka oid bo'lmagan 48 ta maqola yig'ildi
(`data/contrast/raw/`, manbalar: `data/contrast/sources.json`). Ular turli sohalarni
qamraydi: tabiiy fanlar (Fizika, Matematika), tibbiyot (Oʻzbekistonda tibbiyot tarixi),
din (Islom), sanoat va qishloq xoʻjaligi (Neft, Paxta, Bugʻdoy, Oltin), biologiya
(Burgut, Uzum, Olma) va sport (Olimpiya oʻyinlari). Barcha matnlar litsenziyasi CC BY-SA 4.0.

## A.2. Annotatsiya yo'riqnomasi

Annotatsiya qoidalari `docs/data-annotation-guide.md` da berilgan. Asosiy qoidalar:

1. **Span butun so'zlardan iborat.** Qo'shimchalar span ichiga kiradi
   (*fonemalarning*), lug'at shakli esa `term` maydoniga yoziladi (*fonema*).
2. **Tinish belgilari span chetida bo'lmaydi.** Ko'p so'zli termin bitta span
   bo'ladi (*undosh tovush*), ichidagi qisqa termin alohida belgilanmaydi.
3. **Ellipsis.** *unli va undosh tovushlar* birikmasida `unli` belgisining lug'at
   shakli `unli tovush` bo'ladi.
4. **Faqat termin maʼnosi.** Umumiy maʼnodagi qo'llanish (*qoʻshimcha maʼlumot*,
   *xususiyatga ega*), chet tilidagi izohlar va asar nomlari belgilanmaydi.

Har bir yozuv tekshiruvchi (`app.dataset.validate`) orqali avtomatik tekshiriladi:

- `[start, end)` chegaralari va `surface` mosligi;
- span so'z chegarasida ekani;
- spanlar ustma-ust tushmasligi;
- `id` noyobligi;
- manba reyestrda borligi.

## A.3. Annotatsiya jarayoni (kumush maʼlumot)

Inson annotatsiyasi hali yig'ilmagani uchun korpus **AI (Claude)** tomonidan
ikki usulda belgilandi:

1. **Ro'yxat usuli** (`data/silver/`, 41 ta maqola). Har bir maqola o'qilib,
   undagi terminlar ro'yxati va istisnolar tuzildi. Istisnolar umumiy maʼnodagi
   qo'llanish, izohlar va asar nomlarini qamraydi. Ro'yxat 2.1.3-bo'limdagi lug'at
   aniqlagichi bilan matnga qo'llandi.
2. **Uchrash-ma-uchrash usuli** (`data/silver/claude2/`, 6 ta test maqolasi).
   Har bir termin uchrashi alohida, kontekstga qarab hal qilindi. Ro'yxat va
   takliflar ishlatilmadi.

Ikki usul orasidagi kelishuv (391 / 380 span): **exact F1 = 0.965**,
partial F1 = 0.973. Aynan mos spanlarning 98.7 % ida lug'at shakli ham bir xil.
Bu ko'rsatkich **bitta baholovchining o'z-o'ziga mosligini** o'lchaydi, ikki
mustaqil inson annotator kelishuvini emas.

Inson annotatsiyasi uchun web interfeys tayyorlangan (`#annotate`):

- har bir annotatorning ishi alohida saqlanadi;
- test maqolalarini **takliflarsiz** belgilash talab qilinadi (anchoring
  bias'ni oldini olish uchun);
- kelishuv `app.annotation.agreement compare` bilan o'lchanadi.

Span annotatsiyasida kelishuv o'lchovi sifatida Cohen's kappa (Cohen, 1960) emas,
annotatorlardan birini oltin deb olgan F1 ishlatiladi. Sababi: "termin emas"
toifasidagi birliklar soni aniqlanmagan, shuning uchun tasodifiy kelishuvni
hisoblab bo'lmaydi.

## A.4. 100 gaplik BIO dataset

Ketma-ketlikni belgilash modellari uchun alohida, qo'lda tekshirilgan BIO dataset
tayyorlandi (`data/bio/sentences-100.jsonl`, `app.dataset.bio`).

**Tanlash.** Barcha 41 maqoladan navbatma-navbat va maqola ichida bir tekis
tarqatib 100 ta gap olindi (deterministik algoritm). Faqat 6–40 tokenli gaplar
kiritildi, bibliografiya qatorlari chiqarildi.

**Belgilash.** Ramshaw va Marcus (1995) taklif qilgan BIO sxemasi ishlatildi:

- `B-TERM` — terminning birinchi tokeni;
- `I-TERM` — davomi;
- `O` — termin emas.

Tokenlash `app.nlp.tokenize` bo'yicha: harflar ketma-ketligi va so'z ichidagi apostrof.

**Tekshirish.** Har bir gap qo'lda ko'rib chiqildi. 14 ta gapda belgilar
tuzatildi, tuzatishlar `data/bio/review.txt` da hujjatlashtirilgan:

- 7 tasida belgilanmay qolgan termin qo'shildi (*soʻzlar turkumi*, *gapda*, *asos*);
- 3 tasida chegara kengaytirildi (*tovush* → *tovush qurilishi*, *S.* → *umumiy S.*);
- 3 tasida ellipsis belgilandi (*ayiruv va chegaralov yuklamalari*, *oʻz va oʻzlashgan
  qatlam*, *bogʻlangan va ergashgan qoʻshma gaplar*);
- 1 tasida umumiy maʼnodagi *qoʻshimcha maʼno* belgidan chiqarildi.

Qolgan 86 ta gap o'zgarishsiz tasdiqlandi.

**Avtomatik tekshiruv** (`validate_bio`):

- teglar faqat `O / B-TERM / I-TERM`;
- `I-TERM` faqat `B-TERM` yoki `I-TERM` dan keyin keladi;
- tokenlar matnni qayta tokenlash natijasiga teng;
- `tags` va `terms` bir-biriga mos;
- spanlar so'z chegarasida va ustma-ust tushmaydi.

Natija: 0 ta xato.

| Ko'rsatkich | Qiymat |
|---|---|
| Gaplar / maqolalar | 100 / 41 |
| Tokenlar | 1 720 (gapda o'rtacha 17.2; eng kami 6, eng ko'pi 39) |
| `B-TERM` / `I-TERM` / `O` | 293 / 113 / 1 314 |
| Terminlar: 1 / 2 / 3 so'zli | 183 / 101 / 9 |
| Termini yo'q gaplar | 6 |

Butun korpus ham BIO formatiga eksport qilinadi (`app.dataset.bio export`):
1 000 gap, xatolar 0.

## A.5. To'plamlarga ajratish

Korpus **manba (maqola) darajasida** ajratildi (`app.dataset.split`). Bitta maqola
gaplari turli to'plamlarga tushmaydi, aks holda bir maqoladagi takroriy terminlar
testga "sizib" o'tadi. Nisbat 0.7 / 0.15 / 0.15, muvozanat spanlar soni bo'yicha.
Taqsimot deterministik va `data/splits/manifest.json` da muzlatilgan.

| To'plam | Maqola | Paragraf | Span |
|---|---|---|---|
| train | 29 | 221 | 1 786 |
| validation | 6 | 54 | 389 |
| test | 6 | 35 | 380 |

Test to'plami: Bogʻlovchi, Frazeologiya, Olmosh, Ravish, Soʻz turkumlari, Tilshunoslik.
Test spanlarining 38 % i (146 ta) train'da uchramagan lug'at shakllari. Shu sababli
test yangi terminlarni topish qobiliyatini ham o'lchaydi.

**Lug'at** (`data/terms.json`, 450 ta yozuv) faqat **train** to'plamidagi terminlardan
to'ldirildi. Ko'p maʼnoli so'zlar (*ot, sifat, son, ega, gap, hol, zamon, ...*) ataylab
kiritilmadi. Test terminlarini lug'atga qo'shish metodika bo'yicha taqiqlanadi.
