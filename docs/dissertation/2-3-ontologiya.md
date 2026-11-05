## 2.3. Sohaga oid terminologik ontologiyalar va tezauruslarni avtomatik shakllantirish modellari

### 2.3.1. Vazifa va format

Terminologik tezaurus terminlarni alohida emas, tushunchalar tizimi sifatida tavsiflaydi.
Unda uch xil munosabat bor:

- **tur–jins** (giponimiya: *undosh tovush* — *tovush* ning bir turi);
- **assotsiativ** munosabat (*sodda gap* — *qoʻshma gap*);
- **sinonimiya** (*affiks* — *qoʻshimcha*).

Natija W3C SKOS formatida saqlanadi: `skos:Concept`, `skos:broader`/`skos:narrower`,
`skos:related`, `skos:prefLabel`/`skos:altLabel`. Shu sababli uni boshqa terminologik
resurslar va ontologiya vositalari (Protégé, Skosmos) bilan birga ishlatish mumkin.

Model `backend/app/ontology/thesaurus.py` da. Kirish maʼlumotlari:

- soha korpusi;
- lug'at va annotatsiyadagi terminlar (659 ta tushuncha).

Model hech qanday belgilangan munosabatdan o'qitilmaydi.

### 2.3.2. Tur–jins munosabatlarini ajratish

Munosabatlar uch mustaqil manbadan olinadi.

**1. Bosh so'z ierarxiyasi.** Oʻzbek tilida aniqlovchi aniqlanmishdan oldin keladi.
Shuning uchun ko'p so'zli terminning o'ng qismi uning jinsini bildiradi. Terminning
lug'atda bor eng uzun o'ng qismi uning bevosita jinsi deb olinadi:

```text
broader(m₁ … mₖ h) = max_{i ≥ 2} { mᵢ … mₖ h ∈ T },   T — terminlar to'plami
```

Misol: *jarangli undosh tovush ⊂ undosh tovush ⊂ tovush*. Bu sintaktik dalil:
u tushuncha taʼrifiga emas, termin tuzilishiga tayanadi. Shu sababli faqat
shaffof (motivatsiyalangan) terminlar uchun ishlaydi.

**2. Taʼrif tahlili.** Ensiklopedik taʼrif klassik "jins + tur farqi"
(*genus proximum et differentia specifica*) tuzilishiga ega: "A — [tur farqi] X".
Jins X — taʼrifning birinchi bo'lagidagi (`;` gacha) oxirgi ot birikmasi.
U leksik-grammatik qolip (2.1.3) bilan topiladi. Oʻzbek tiliga xos ikki konstruksiya
oldindan olib tashlanadi:

- "X**lardan biri**": *Ot — mustaqil soʻz turkumlaridan biri* → *mustaqil soʻz turkumi*;
- "X**ning bir turi**": *Koʻmakchi — yordamchi soʻzlarning bir turi* → *yordamchi soʻz*.

Shartlar:

- taʼrif ot bilan tugashi kerak, undan keyin fe'l kelmasligi kerak;
  *Shevalar — lingvistik geografiya tomonidan oʻrganiladi* taʼrif emas;
- taʼriflanuvchi va jins (yoki jinsning bosh so'zi) lug'atda termin bo'lishi kerak.

**3. Leksik-sintaktik qoliplar.** Hearst (1992) taklif qilgan "X such as A, B" kabi
qoliplarning oʻzbek tilidagi moslamalari:

| Qolip | Misol |
|---|---|
| "A, B va C **kabi** X(lar)" | *paralingvistika, etnolingvistika, psixolingvistika kabi sohalar* |
| "X(lar) [N] **turga / xilga / guruhga boʻlinadi**: A, B va C" | *Gaplar 3 turga boʻlinadi: darak gap, soʻroq gap va undov gap* |
| "X**ning turlari**: A, B" | |

Imlo qoidalari matnida "*xona, noma kabi soʻzlar*" kabi misollar ko'p. Ularni
chiqarib tashlash uchun giponim termin bo'lishi talab qilinadi: lug'atda bo'lishi
yoki termin yasovchi qo'shimcha bilan tugashi kerak (*-shunoslik, -logiya, -ika,
-iya, -izm*). Juda umumiy jinslar (*tur, xil, masala, maʼno*) olinmaydi.

**Birlashtirish.** Har bir munosabat uchun manbalar va matndagi dalil saqlanadi.
Ikki manba bilan tasdiqlangan munosabat ishonchliroq: masalan, *undosh tovush ⊂ tovush*
ham bosh so'z, ham taʼrif bilan topilgan. Keyin graf tozalanadi:

- qarama-qarshi juftdan (A ⊂ B va B ⊂ A) kamroq dalillisi olib tashlanadi;
- **tranzitiv reduksiya** qilinadi: A ⊂ C ⊂ B bo'lsa, to'g'ridan-to'g'ri A ⊂ B
  ortiqcha, uning dalili A ⊂ C ga o'tadi. Masalan, *mayl kategoriyasi ⊂ kategoriya*
  o'rniga *mayl kategoriyasi ⊂ grammatik kategoriya ⊂ kategoriya* qoladi.

### 2.3.3. Assotsiativ munosabatlar

Bir paragrafda birga kelgan terminlar uchun PMI hisoblanadi (Church, Hanks, 1990):

```text
PMI(a, b) = log₂ ( c(a, b) · N / (c(a) · c(b)) ),
```

bu yerda c — terminni o'z ichiga olgan paragraflar soni, N — paragraflar soni.
Kamida 3 marta birga kelgan, PMI > 0 bo'lgan va tur–jins bilan bog'lanmagan
juftlar `skos:related` deb olinadi. Eng yuqori juftlar:

- *bosh gap ~ ergash gap*;
- *harakat nomi ~ ravishdosh*;
- *portlovchi ~ sirgʻaluvchi*;
- *argo ~ jargon*;
- *mustaqil feʼl ~ yordamchi feʼl*;
- *sodda gap ~ qoʻshma gap*.

Ular ko'pincha bir tasnifdagi qarama-qarshi turlar (ko-giponimlar).

### 2.3.4. Natija

**2.5-jadval.** Avtomatik qurilgan tezaurus (`reports/thesaurus.json`, `reports/thesaurus.ttl`):

| Ko'rsatkich | Qiymat |
|---|---|
| Tushunchalar | 662 |
| Tur–jins munosabatlari (reduksiyadan keyin) | 268 |
| — bosh so'z ierarxiyasidan | 234 |
| — taʼriflardan | 17 |
| — leksik-sintaktik qoliplardan | 23 |
| — ikki manba tasdiqlagan | 6 |
| Jinsi aniqlangan terminlar | 264 (40 %) |
| Ierarxiya chuqurligi (eng ko'p) | 3 |
| Bir nechta jinsli tushunchalar (poliierarxiya) | 3 |
| Sikllar | 0 |
| Assotsiativ juftlar | 226 |

Ierarxiya namunasi:

```text
tovush ─┬─ undosh tovush        gap ─┬─ sodda gap         kategoriya ─┬─ grammatik kategoriya ─┬─ mayl kategoriyasi
        ├─ unli tovush               ├─ qoʻshma gap                   │                        ├─ nisbat kategoriyasi
        ├─ portlovchi tovush         ├─ ergash gap                    │                        └─ zamon kategoriyasi
        └─ titroq tovush             └─ soʻroq gap                    └─ egalik kategoriyasi
```

Interfeysdagi "Tezaurus" sahifasi (`#thesaurus`) ierarxiyani daraxt ko'rinishida
ko'rsatadi. Unda qidiruv bor, har bir munosabatning manbasi va dalili ham ko'rinadi.
API: `GET /api/thesaurus`.

**Sifat bahosi.** Munosabatlarning to'g'riligini mutaxassis baholaydi. Har bir
manbadan tasodifiy 40 tadan, jami 79 ta munosabat tanlandi
(`data/judgments/thesaurus-review.csv`). Har bir munosabat uchun precision manba
bo'yicha alohida hisoblanadi. **Holat: ekspert bahosi kutilmoqda.**

Dastlabki ko'rib chiqishda (muallif, AI yordamida) xatolar asosan qolip manbasida
uchradi:

- ro'yxat chegarasi noto'g'ri aniqlanadi: *Shu tariqa semitologiya* → *tariqa semitologiya*;
- yuqori darajadagi umumiy jinslar ishlatiladi: *masala*, *xususiyat*.

Bosh so'z va taʼrif manbalari esa deyarli xatosiz ishladi.

### 2.3.5. Cheklovlar

1. **Bosh so'z qoidasi** faqat shaffof terminlarda ishlaydi. *ega ⊂ bosh boʻlak* kabi
   munosabatni faqat taʼrif beradi. Ba'zan esa u xato beradi: *soʻz birikmasi* —
   *birikma* ning turi, lekin *bosh soʻz* (lug'atchilikda) *soʻz* ning turi emas.
2. **Taʼriflar kam.** Korpusda faqat 41 ta maqola bor, ularning har birida bitta
   asosiy taʼrif. Darslik va lug'at taʼriflari qo'shilsa, bu manba kengayadi.
3. **Faqat tur–jins munosabati.** Butun–qism munosabati (*boʻgʻin — soʻz*) ajratilmaydi.
4. **Jinsi aniqlanmagan terminlar.** Terminlarning 60 % i ierarxiyaga ulanmagan.
   Bularning ko'pi bir so'zli terminlar (*fonema, morfema*), ular uchun yagona dalil
   taʼrifdir.
