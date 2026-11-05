# III BOB. TERMINLARNI MEʼYORLASHTIRISH (STANDARTLASHTIRISH) VA UNIFIKATSIYA QILISHNING AVTOMATIK ALGORITMLARI

## 3.1. Terminologik variantdorlik (sinonimiya, omonimiya, dubletlik) muammosi va uni avtomatik bartaraf etish usullari

### 3.1.1. Lug'at shakliga keltirish (meʼyorlashtirish) algoritmi

Kirish: span matni s. Chiqish: lug'at shakli, asosiy termin, holat.

```text
1. Lug'at:  s butunligicha lug'at shakliga (qo'shimchalar va tovush o'zgarishlari bilan)
            mos kelsa → lug'at shakli = mos kelgan shakl (sinonim bo'lsa — o'zi),
            asosiy termin = yozuvning termini, holat = approved | needs_review.
2. Morfologiya: oxirgi so'z w uchun eng qisqa o'zak s₀ (≥ 3 harf) va qo'shimchalar zanjiri:
            w = s₀ · (lar)?(egalik)?(kelishik)?(ki)?(yuklama)?
            shartlar: (a) s₀ yoki uning tiklangan shakli (g→k, gʻ→q, CC→CiC/CuC)
                          korpus yoki lug'at so'zi;
                      (b) fonotaktika: -ka faqat k dan, -qa faqat q dan keyin
                          (egalikdan keyin hech qachon — "lingvistika" ≠ "lingvist"+"i"+"ka");
                      (c) I/II shaxs birlik egaligi (-im, -ing) bilan bo'linish faqat
                          boshqa bo'linish bo'lmasa va w o'zi korpusda uchramasa olinadi
                          (ensiklopedik matnda "mening/sening" deyarli yo'q:
                          "kesim" ≠ "kes"+"im", "boʻlim" ≠ "boʻl"+"im"). -imiz bundan
                          mustasno: ilmiy matnda bor (*tilimiz*).
            (a) bajarilmasa (yangi so'z): faqat aniq ko'plik yoki kelishik
            qo'shimchasi ajratiladi (o'zak ≥ 5 harf).
3. Izofa:  ko'p so'zli terminda oxirgi so'zda III shaxs egaligi (-i/-si) bo'lsa va
            oldingi so'z sifat bo'lmasa, egalik saqlanadi:
            "soʻz birikmalari" → "soʻz birikmasi", "gap boʻlaklarini" → "gap boʻlagi"
            (ko'p bo'g'inli o'zakda k→g, q→gʻ). Sifat: -tik, -iy, -li, -siz, -gan, -vchi
            yoki ro'yxat (undosh, unli, sodda, qoʻshma, …): "undosh tovushlari" → "undosh tovush".
4. Faqat oxirgi so'z almashtiriladi; ichki so'zlar va defislar saqlanadi;
   apostroflar rasmiy shaklga keltiriladi.
   2–3-qadam natijasining holati: no_data ("lug'atda yo'q — tekshirish kerak").
```

Murakkablik: lug'at bosqichi O(|L| · n) (|L| — lug'at shakllari, n — matn uzunligi);
morfologiya bosqichi bitta so'z uchun O(|w|²).

### 3.1.2. Lug'at shakliga keltirish natijalari

> Barcha natijalar **AI annotatsiyasi** (kumush maʼlumot) bo'yicha. To'liq jadval
> `docs/experiments-table.md` da, xom natijalar `reports/*.json` da.

**3.1-jadval.** Oltin spanlar uchun lug'at shakli aniqligi:

| Usul | Validation (389) | Test (380) | Test, claude2 (391) |
|---|---|---|---|
| O'zgarishsiz (kichik harf) | 0.375 | 0.482 | 0.473 |
| Korpus lemmatizatori | 0.805 | 0.753 | 0.744 |
| Faqat lug'at | 0.625 | 0.711 | 0.696 |
| **Lug'at + morfologiya + izofa** | **0.936** | **0.921** | **0.908** |

Lug'at + morfologiya usulining birinchi versiyasi testda 0.861 natija berdi.
Test xatolari tahlilidan keyin ikki tuzatish kiritildi:

| # | Xato | Tuzatish | Validation | Test | Test, claude2 |
|---|---|---|---|---|---|
| — | birinchi versiya | — | 0.936 | 0.861 | 0.849 |
| 1 | *lingvistika → lingvist* ("*-i* egalik + *-ka* kelishik") | fonotaktika: *-ka* egalikdan keyin kelmaydi | 0.936 | 0.916 | 0.903 |
| 2 | *kesim → kes* ("*-im*" I shaxs egaligi) | I/II shaxs birlik egaligi so'zning o'zi korpusda bo'lsa ajratilmaydi (3.1.1, (c)) | 0.936 | 0.921 | 0.908 |

Ikkala tuzatish ham validation natijasini o'zgartirmadi: u yerda bunday so'zlar
yo'q. Tuzatishlar test xatolaridan kelib chiqqani uchun 0.921 va 0.908
**"test bo'yicha sozlangan"** natija. Sozlashdan oldingi qiymatlar: 0.861 va 0.849.
Ikkinchi tuzatishni tanlashda validation'dan foydalanildi: kengroq variant
(barcha I/II shaxs qo'shimchalari, shu jumladan *-imiz* va *-m*) lemmatizatorni
validation'da yomonlashtirdi (*tilimiz*, *slengmi* → noto'g'ri), shuning uchun
qoida *-im* va *-ing* bilan cheklandi. Toza baho uchun yangi, tizim hali ko'rmagan
maqolalarda bitta baholash kerak (Xulosa, «Keyingi ishlar»).

Qolgan xatolar ikki turga bo'linadi:

- **tiklab bo'lmaydiganlari:** ellipsis (*lugʻaviy → lugʻaviy maʼno*, 8–15 span),
  manbadagi imlo xatolari (*Nosatandart*, *stilistik buyoq*);
- **izofa qoidasining istisnolari:** *ozaytirma shakli* oltin belgida izofa bilan
  berilgan, qoida esa birinchi so'zni sifat deb oladi.

### 3.1.3. Variantlarni avtomatik aniqlash va guruhlash

Terminologik variantdorlik bir necha turga bo'linadi va har biri boshqa usul bilan
aniqlanadi (`backend/app/variation/`):

| Tur | Misol | Usul | Natija |
|---|---|---|---|
| Imlo varianti | *oʻzak / o'zak / o`zak / ozak* | imlo skeleti | avtomatik birlashtiriladi |
| Yozuv varianti | *ўзак ~ oʻzak* | kirill → lotin transliteratsiya (1995 qoidalari) | avtomatik birlashtiriladi |
| Morfologik shakl | *fonemalarning ~ fonema* | lug'at shakliga keltirish (3.1.1) | avtomatik birlashtiriladi |
| Imlo xatosi | *alloton ~ allofon*, *atnonim ~ antonim* | Damerau–Levenshtein masofasi | tekshiruvga |
| Sinonim | *supersegment ~ ustsegment* | matndagi qavs, *yoki*, *yaʼni* qoliplari | tekshiruvga |
| Dublet | *intonatsiya ~ ohang*, *lingvistika ~ tilshunoslik* | sinonim + o'zlashma/o'zbekcha belgisi | tekshiruvga |
| Omonim | *qoʻshimcha* (affiks / "yana") | kontekst klassifikatori (naiv Bayes) | har bir uchrash uchun |

**Imlo skeleti.** Shakl kichik harfga o'tkaziladi, kirill harflari lotinga o'giriladi,
apostrofning barcha turlari va defis olib tashlanadi: `skeleton("Oʻzak") =
skeleton("ўзак") = skeleton("ozak") = "ozak"`. Bir xil skeletli shakllar bitta imlo
guruhiga tushadi. Kirill → lotin o'girishda kontekstga bog'liq qoidalar hisobga olinadi:
*е* so'z boshida va unlidan keyin *ye* (*ер → yer*, *поезд → poyezd*); *ц* unlidan keyin
*ts* (*милиция → militsiya*), aks holda *s* (*цирк → sirk*).

**Imlo xatolari.** Ikki lug'at shakli quyidagi shartlarda xato varianti deb taklif qilinadi:

- oxirgi so'zlar orasidagi Damerau–Levenshtein masofasi kichik (10 harfgacha 1, uzunroqda 2);
- boshi va oxirgi 2 harfi bir xil, biri ikkinchisining boshlanmasi emas
  (*fonetik ~ fonetika* — yasalish, xato emas);
- zid maʼnoli yasalish emas (*mahsullilik ~ mahsulsizlik*, *makro- ~ mikro-*);
- kamroq uchragan shakl ko'pi bilan 2 marta va boshqasidan kamida 2 baravar kam
  uchraydi (xato kam takrorlanadi).

Butun korpusda shu qoidalar 6 ta juftni taklif qildi: *alloton ~ allofon*,
*atnonim ~ antonim*, *abbrivatsiya ~ abbreviatsiya*, *leksikofafiya ~ leksikografiya*,
*leksikalogiya ~ leksikologiya* (manbadagi imlo xatolari) va *morfofonologiya ~
morfonologiya* (haqiqiy variantlar). Oltitasi ham haqiqiy variant.

**Sinonim va dubletlar.** Ilmiy matnda muallif muqobil terminni ko'pincha o'zi beradi:
qavs ichida (*arabistika (arabshunoslik)*), *yoki* bilan (*Tilshunoslik yoki
Lingvistika*), *yaʼni* bilan. Ikkala tomon leksik-grammatik qolipga (2.1.3) mos
bo'lishi va kamida bittasi maʼlum termin (lug'at yoki train annotatsiyasi) bo'lishi
shart. Juftning bir tomoni xalqaro (yunon-lotin, yevropa) o'zlashma, ikkinchisi
o'zbekcha bo'lsa, u **dublet** deb belgilanadi. O'zlashma belgilari:

- qo'shimchalar: *-iya, -ika, -izm, -tsiya, -logiya, -tiv*;
- old qo'shimchalar: *ekstra-, kvazi-, trans-, sotsio-*;
- harf birikmalari: *ts, ks* va undoshlar orasidagi *f*.

Korpusdan 46 ta juft ajratildi: 15 tasi dublet, 31 tasi sinonim nomzodi
(`data/judgments/synonyms-review.csv`). Ular orasida to'g'ri juftlar ham, shovqin ham bor:

- to'g'ri juftlar: *affiks ~ qoʻshimcha*, *intonatsiya ~ ohang*, *maʼno ~ semantika*,
  *boʻlishsizlik ~ inkor*, *supersegment ~ ustsegment*, *antonim ~ zid maʼnoli soʻz*,
  *semantika ~ semasiologiya*, *lingvistika ~ tilshunoslik*;
- shovqin: qavs ichidagi misollar (*feʼl ~ olma*), giperonimlar (*grammatika ~
  morfologiya*) va zid tushunchalar (*obyekt ~ subyekt*).

Shuning uchun juftlar lug'atga avtomatik kiritilmaydi, ekspert tekshiruviga beriladi.
Bu ro'yxatning aniqligi ekspert baholagandan keyin hisoblanadi.

**Omonimiya.** Train annotatsiyasida ham termin, ham umumiy maʼnoda uchragan bir
so'zli lemmalar avtomatik topildi (kamida 5 uchrash, termin ulushi 10–90 %):
*birlik, ega, fonetika, harf, hol, leksika, lugʻat, obyekt, qoʻshimcha, ravish,
sifat, sintaksis, son, tovush* (14 ta). Har bir uchrash ikki sinfga ajratiladi:
termin yoki umumiy maʼno. Buning uchun naiv Bayes klassifikatori ishlatiladi
(`homonymy.py`):

```text
log P(termin | x) − log P(umumiy | x) = log (n_t(lemma)+1)/(n_u(lemma)+1) + Σ_f log P(f | termin)/P(f | umumiy)
```

Xususiyatlar:

- lemma va ±1, ±2 qo'shni so'zlar (lemma);
- qo'shni so'z yordamchi so'zmi;
- o'ng qo'shni va so'zning o'zi qo'shimcha olganmi;
- bosh harf.

**3.2-jadval.** Omonim lemmalarning uchrashlari, aniqlik (accuracy) va termin sinfi bo'yicha F1:

| Usul | Validation (78) acc. | F1 | Test (64) acc. | F1 |
|---|---|---|---|---|
| Har doim termin (lug'at usuli) | 0.474 | 0.643 | 0.578 | 0.733 |
| Lemma bo'yicha ko'pchilik sinf | **0.872** | **0.878** | 0.766 | 0.769 |
| Naiv Bayes (kontekst) | 0.833 | 0.843 | **0.844** | **0.868** |

Lug'at usuli (har doim termin) bu so'zlarning qariyb yarmida xato qiladi. Kontekst
klassifikatori testda eng yaxshi natija beradi. Validation'da esa lemma bo'yicha
ko'pchilik sinfdan biroz past. Ikki to'plamda tartib har xil va ikkalasi ham kichik
(64–78 uchrash). Shu sababli kontekst modelining ko'pchilik sinfdan ustunligi
isbotlanmagan. Lekin lug'at usulidan ustunligi ikkala to'plamda ham katta
(+0.27…+0.36).

**Guruhlash natijasi.** Oltin spanlarning matndagi shakllari oltin lug'at shakli
bo'yicha klasterlanadi. Usullar shu klasterlarni qanchalik tiklashi B-cubed
mezoni (Bagga, Baldwin, 1998) bilan o'lchanadi, shakllar chastotasi bilan tortiladi.

**3.3-jadval.** Variantlarni guruhlash, B-cubed:

| Usul | Validation P | R | F1 | Test P | R | F1 |
|---|---|---|---|---|---|---|
| Aynan moslik | 1.000 | 0.501 | 0.668 | 1.000 | 0.601 | 0.751 |
| Kichik harf | 1.000 | 0.552 | 0.711 | 1.000 | 0.636 | 0.778 |
| Imlo skeleti | 1.000 | 0.552 | 0.711 | 1.000 | 0.640 | 0.781 |
| Skelet + korpus lemmatizatori | 1.000 | 0.911 | 0.953 | 1.000 | 0.869 | 0.930 |
| **Skelet + lug'at shakliga keltirish (3.1.1)** | 1.000 | **0.961** | **0.980** | 1.000 | **0.934** | **0.966** |

Precision barcha usullarda 1.000: hech bir usul turli terminlarni bitta guruhga
qo'shmadi. Asosiy farq recall'da. Morfologik shakllarni birlashtirish uni
0.64 dan 0.93 ga oshiradi. Imlo skeleti bu korpusda deyarli taʼsir qilmaydi, chunki
maqolalar bir manbadan va bir xil imloda.

Shuning uchun imlo variantlariga chidamlilik **sintetik** sinov bilan tekshirildi.
Test to'plamidagi har bir oltin terminga sun'iy variant yasaldi: apostrof almashtirildi
(`'`, `` ` ``, `‘’`), apostrof tushirib qoldirildi, bosh harf va kirill yozuvi berildi.

**3.4-jadval.** Sintetik variant asl shakl bilan bitta guruhga tushgan ulush (test):

| Usul | Bosh harf | Apostrof `'` | `` ` `` | `‘’` | Apostrofsiz | Kirill |
|---|---|---|---|---|---|---|
| Aynan moslik | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Kichik harf | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Imlo skeleti | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

Sintetik kirill shakllari soddalashtirilgan lotin → kirill jadvali bilan yasalgan
(*e → э* so'z boshida, *ye → е*). *объект* kabi *ъ* li shakllar unda yo'q,
ularning o'girilishi alohida birlik testlari bilan tekshirilgan.

### 3.1.4. Meʼyoriy shaklni tanlash

Variantlar guruhi uchun tavsiya etiladigan shakl qoidalar bilan tanlanadi
(`groups.py`, `choose_preferred`). Qoidalar ISO 704 dagi termin tanlash
tamoyillariga asoslanadi: amaldagi qo'llanish (uzus), qisqalik, lisoniy to'g'rilik.
Ular tartib bilan qo'llanadi, birinchi hal qilgan qoida natija beradi:

1. Lug'atda **tasdiqlangan** (`approved`, manbasi bilan) yozuvning meʼyoriy shakli.
2. **Rasmiy imlo:** lotin yozuvi va rasmiy apostroflar (*oʻ, gʻ, ʼ*). Imlo variantlari
   orasidagi tanlov shu bilan hal bo'ladi.
3. Lug'atdagi meʼyoriy shakl (tekshirilmagan bo'lsa ham).
4. Korpusdagi **chastota** (uzus).
5. **Qisqalik:** avval so'zlar, keyin harflar soni.

Har bir tavsiya sababi bilan qaytariladi. Masalan:

- "imlo variantlari rasmiy lotin yozuviga keltirildi";
- "korpusda eng ko'p qo'llangan (34 marta)".

Loyiha qoidasiga ko'ra, 1-qoidadan boshqa barcha holatlarda holat `needs_review`
bo'ladi. Tizim manbasiz shaklni meʼyoriy deb eʼlon qilmaydi. Sinonim va dublet
guruhlari avtomatik birlashtirilmaydi, ular faqat tekshiruv uchun bog'lanadi.
Sababi: *lingvistika* yoki *tilshunoslik* shakllaridan qaysi biri meʼyoriy ekanini
terminologik siyosat va manba belgilaydi, chastota emas.

Butun annotatsiya (1 418 ta turli shakl) bo'yicha 703 ta guruh hosil bo'ldi, 250
tasida bir nechta shakl bor. Guruhlar orasida tekshiruv uchun 23 ta bog'lanish
taklif qilindi: 10 ta sinonim, 7 ta dublet, 6 ta imlo xatosi
(`reports/variation-groups.json`).
