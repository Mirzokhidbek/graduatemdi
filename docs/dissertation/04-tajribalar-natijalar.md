# 4-bob. Tajribalar va natijalar

> Barcha natijalar **AI annotatsiyasi** (kumush maʼlumot) bo'yicha. To'liq jadval
> `docs/experiments-table.md` da, xom natijalar `reports/*.json` da.

## 4.1. Tajriba sxemasi

1. Train / validation / test manba darajasida ajratilgan (2.5-bo'lim).
2. Lug'at va CRF faqat train'da quriladi (o'qitiladi).
3. Giperparametrlar va qoidalar validation'da sozlanadi.
4. Test har bir konfiguratsiya uchun bir marta baholanadi.
5. Test xatolari tahlilidan keyin tizimga kiritilgan o'zgarish alohida
   hujjatlashtiriladi va natija "test bo'yicha sozlangan" deb belgilanadi (4.4).

Taqqoslangan usullar:

| Belgi | Usul |
|---|---|
| D-15 | dastlabki 15 terminli namuna lug'at |
| D-train | train terminlari bilan to'ldirilgan lug'at (450) |
| CRF | 3.4-bo'limdagi model, gazetteersiz |
| CRF+G | CRF + train lug'ati gazetteer xususiyati |

## 4.2. Metrikalar

Spanlar exact mezon bo'yicha solishtiriladi: `[start, end)` aynan teng bo'lsa
to'g'ri. Partial mezonda kamida bitta belgi ustma-ust tushishi yetarli. Barcha
metrikalar micro-average (CoNLL-2003 an'anasi; Tjong Kim Sang, De Meulder, 2003):

```text
P  = |G ∩ S| / |S|,    R = |G ∩ S| / |G|,    F1 = 2PR / (P + R)
```

Bu yerda G — oltin spanlar, S — bashorat qilingan spanlar.

**Ishonch oralig'i.** Paragraflar bo'yicha bootstrap (Efron, Tibshirani, 1993):
B = 2000 ta qayta tanlanma, 2.5 va 97.5 persentil. Usullar farqi uchun juftlangan
bootstrap: har bir qayta tanlanmada ikkala usulning F1 farqi hisoblanadi.

**Meʼyorlashtirish aniqligi.** Oltin span matni uchun bashorat qilingan lug'at
shakli oltin `term` ga (registr va apostrof farqisiz) teng bo'lgan spanlar ulushi.

## 4.3. Terminlarni aniqlash natijalari

**4.1-jadval.** Test (ro'yxat usulidagi belgilar, 35 paragraf, 380 span):

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 |
|---|---|---|---|---|---|
| D-15 | 0.708 | 0.166 | 0.269 | [0.171, 0.373] | 0.371 |
| D-train | 0.770 | 0.432 | 0.553 | [0.471, 0.628] | 0.696 |
| CRF | 0.715 | 0.534 | 0.611 | [0.527, 0.690] | 0.773 |
| **CRF+G** | **0.792** | **0.550** | **0.649** | [0.566, 0.719] | **0.780** |

**4.2-jadval.** Test (uchrash-ma-uchrash qayta belgilangan, 391 span). Bu belgilar
lug'at aniqlagichiga bog'liq emas:

| Usul | P | R | F1 | F1, 95 % oraliq | D-train dan farq, 95 % |
|---|---|---|---|---|---|
| D-15 | 0.685 | 0.156 | 0.254 | [0.159, 0.354] | [−0.359, −0.207] |
| D-train | 0.761 | 0.414 | 0.536 | [0.456, 0.611] | — |
| CRF | 0.715 | 0.519 | 0.601 | [0.516, 0.679] | [−0.014, +0.151] |
| **CRF+G** | **0.792** | **0.535** | **0.638** | [0.550, 0.713] | **[+0.063, +0.145]** |

**4.3-jadval.** Train'da uchramagan terminlar (test, 146 span):

| Usul | Topildi | Recall |
|---|---|---|
| D-15, D-train | 0 | 0.000 |
| CRF | 31 | 0.212 |
| CRF+G | 2 | 0.014 |

**Tahlil.**

1. **Lug'at hajmi recall'ni deyarli 2.6 baravar oshiradi** (0.166 → 0.432).
   Precision esa o'zgarmaydi (≈ 0.7–0.8). Lug'at usulining asosiy cheklovi —
   to'liqlik (coverage).
2. **CRF+G eng yuqori F1 ga ega.** D-train dan farqining 95 % oralig'i ikkala
   belgilash variantida ham 0 ni o'z ichiga olmaydi, ya'ni farq statistik ishonchli.
   Gazetteersiz CRF ning ustunligi bu hajmdagi maʼlumotda ishonchli emas.
3. **Faqat CRF yangi terminlarni topadi** (21 %): *lingvostatistika, paralingvistika,
   etnolingvistika, sotsiolingvistika, transliteratsiya, antroponimika, semitologiya,
   hindevropashunoslik, sinxroniya, diaxroniya, oʻrin ravishlari, morfologik usul*.
   Buni oxirgi 2–5 harf xususiyatlari (*-ika, -iya, -shunoslik*) taʼminlaydi.
   Gazetteer qo'shilganda model lug'at belgisiga tayanadi va bu qobiliyat yo'qoladi
   (1.4 %). Demak, ikki model turli amaliy maqsadlarga mos:
   - CRF+G — aniqlik uchun;
   - CRF — lug'atni yangi terminlar bilan to'ldirish uchun.
4. **Validation bilan solishtirish.** Validation'da CRF (0.532) va CRF+G (0.530)
   deyarli teng, testda CRF+G yuqori. Kichik to'plamlarda tartib o'zgarishi
   bootstrap oraliqlarining kengligiga mos keladi.

## 4.4. Meʼyorlashtirish natijalari

**4.4-jadval.** Oltin spanlar uchun lug'at shakli aniqligi:

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
| 2 | *kesim → kes* ("*-im*" I shaxs egaligi) | I/II shaxs birlik egaligi so'zning o'zi korpusda bo'lsa ajratilmaydi (3.6, (c)) | 0.936 | 0.921 | 0.908 |

Ikkala tuzatish ham validation natijasini o'zgartirmadi: u yerda bunday so'zlar
yo'q. Tuzatishlar test xatolaridan kelib chiqqani uchun 0.921 va 0.908
**"test bo'yicha sozlangan"** natija. Sozlashdan oldingi qiymatlar: 0.861 va 0.849.
Ikkinchi tuzatishni tanlashda validation'dan foydalanildi: kengroq variant
(barcha I/II shaxs qo'shimchalari, shu jumladan *-imiz* va *-m*) lemmatizatorni
validation'da yomonlashtirdi (*tilimiz*, *slengmi* → noto'g'ri), shuning uchun
qoida *-im* va *-ing* bilan cheklandi. Toza baho uchun yangi, tizim hali ko'rmagan
maqolalarda bitta baholash kerak (5.3-bo'lim).

Qolgan xatolar ikki turga bo'linadi:

- **tiklab bo'lmaydiganlari:** ellipsis (*lugʻaviy → lugʻaviy maʼno*, 8–15 span),
  manbadagi imlo xatolari (*Nosatandart*, *stilistik buyoq*);
- **izofa qoidasining istisnolari:** *ozaytirma shakli* oltin belgida izofa bilan
  berilgan, qoida esa birinchi so'zni sifat deb oladi.

## 4.5. Xato tahlili (CRF, test)

**Chegara xatolari.** CRF ning 56 ta chegara xatosidan 27 tasida oxiri to'g'ri,
lekin boshidagi aniqlovchi tushib qolgan:

- *amaliy / nazariy / xususiy / strukturaviy tilshunoslik* → *tilshunoslik*;
- *mustaqil soʻz turkumi* → *soʻz turkumi*.

Sabab: o'qitish to'plamida *tilshunoslik* yolg'iz o'zi juda ko'p uchraydi. Bu
partial va exact F1 orasidagi 0.13–0.16 farqni tushuntiradi.

**Lemmatizator xatosi (tuzatilgan).** Birinchi versiyada korpus lemmatizatori
*kesim* so'zini *kes + im* deb bo'lardi, chunki *kes* korpusda mustaqil so'z va
eng qisqa o'zak tanlanadi. Natijada `lemma=kes` xususiyati modelda katta og'irlik
olgan, meʼyorlashtiruvchi ham *kesim → kes* xatosini qilgan. *-im* va *-ing*
(I/II shaxs birlik egaligi) ensiklopedik matnda deyarli uchramagani uchun bunday
bo'linish endi faqat boshqa imkon bo'lmasa olinadi (3.6, (c)). Tuzatishdan keyin
modellar qayta o'qitildi: CRF+G natijasi o'zgarmadi (0.649), gazetteersiz CRF
testda 0.606 → 0.611, validation'da 0.534 → 0.532, yaʼni farq bootstrap
oralig'idan ancha kichik. Train'da shu qoida bilan to'g'rilangan so'zlar:
*kesim, boʻlim, bilim, qadim, maʼlum, uning*.

## 4.6. Statistik nomzodlar

Nomzodlar 1–4 so'zli n-gramlar bo'yicha ajratildi. Reyting usullari: frequency, TF-IDF, C-value hamda 48 ta maqoladan iborat kontrast korpus asosidagi Weirdness (Ahmad va boshq., 1999). 119 ta nomzod mustaqil inson baholovchilar (A1, A2) tomonidan ko'r holda baholandi, shuningdek kelishmovchiliklar tilshunoslik tahlili orqali hakamlik (Adjudicated) konsensusiga keltirildi (`data/judgments/`).

Baholovchilararo kelishuv: A1 ↔ A2 Cohen's kappa = 0.474 (o'rtacha kelishuv — umumiy tilshunoslik leksikasida farqlar bo'lgan). Hakamlik bahosi bilan A1 va A2 ning kelishuvi esa mos ravishda kappa = 0.779 va 0.804 ni tashkil etdi.

**4.5-jadval.** Precision@K natijalari (hakamlik / konsensus bahosi bo'yicha, qatʼiy hisob):

| Usul | P@10 | P@20 | P@50 | P@100 |
|---|---|---|---|---|
| frequency | 0.40 | 0.35 | 0.34 | 0.34 |
| TF-IDF | 0.40 | 0.55 | 0.42 | 0.40 |
| C-value | 0.40 | 0.35 | 0.40 | 0.37 |
| frequency + POS filtri | 0.50 | 0.40 | 0.40 | ≥ 0.38 |
| TF-IDF + POS filtri | 0.50 | 0.65 | 0.46 | ≥ 0.43 |
| C-value + POS filtri | 0.40 | 0.40 | 0.42 | ≥ 0.39 |
| **Weirdness** | 0.80 | 0.80 | ≥ 0.58 | ≥ 0.32 |
| **Weirdness + POS filtri** | **0.90** | **0.90** | **≥ 0.60** | ≥ 0.32 |

POS filtri fe'l va nisbiy sifat shakllarini (*yoziladi*, *grammatik*) chiqarib,
reytingning yuqori qismini tozalaydi. Kontrast korpus yordamida hisoblangan
**Weirdness** o'lchovi esa barcha usullardan sezilarli darajada ustun kelib,
P@10 va P@20 da 0.90 aniqlikka erishdi (A1 bahosida hatto 1.00). Bu umumiy tilshunoslik
so'zlari o'rniga sof terminlarni tanlashda kontrast korpusning hal qiluvchi rolini isbotlaydi.

## 4.7. Transformer modeli

XLM-RoBERTa base (3.4.1) Google Colab'da (T4 GPU) o'qitiladi:
`notebooks/xlmr_colab.ipynb`. Notebook to'plamlarni manifestdan tiklaydi,
modelni o'qitadi va lug'at, CRF, CRF+G bilan bir xil testda solishtiradi.
Natija `docs/experiments-table.md` ning 6-bo'limiga avtomatik qo'shiladi.

**Holat: hali ishga tushirilmagan.** Ishlab chiqish muhitida HuggingFace'ga
kirish yo'q edi. Kod CPU'da kichik, tasodifiy boshlangan model bilan
tekshirilgan: o'qitish, epoxa tanlash, saqlash, qayta yuklash (natija aynan
takrorlanadi) va hisobot. Ushbu bo'lim Colab natijasi bilan to'ldiriladi:

| Usul | P | R | F1 | F1, 95 % oraliq | CRF+G dan farq, 95 % | Yangi terminlar |
|---|---|---|---|---|---|---|
| CRF+G | 0.792 | 0.550 | 0.649 | [0.566, 0.719] | — | 2 / 146 |
| XLM-R base | … | … | … | … | … | … |

Natijani talqin qilishda ikki narsa hisobga olinadi:

- train atigi 221 paragraf; transformer odatda ko'proq maʼlumot talab qiladi;
- XLM-R CRF+G dan farqli ravishda lug'atdan foydalanmaydi, shuning uchun
  uni gazetteersiz CRF bilan ham solishtirish kerak.
