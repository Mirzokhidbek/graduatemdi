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

> **TODO.** Bu bo'lim hali yozilmagan. Reja: [../dissertation-plan.md](../dissertation-plan.md), C1 bosqich.
