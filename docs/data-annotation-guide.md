# Annotatsiya yo'riqnomasi (v1)

Bu hujjat matnlardagi terminlarni inson tomonidan belgilash qoidalarini
belgilaydi. Belgilangan maʼlumot modellarni baholash uchun "oltin standart"
bo'ladi. Shuning uchun qoidalar barcha annotatorlar uchun bir xil va
takrorlanadigan bo'lishi kerak.

## 1. Nima termin hisoblanadi

**Termin** — ona tili va tilshunoslik sohasidagi maxsus tushunchani ifodalovchi
so'z yoki so'z birikmasi. Muhim shart: matnda aynan shu **maxsus maʼnoda**
qo'llangan bo'lishi kerak.

Belgilanadi:

- soha bo'limlari: *fonetika, morfologiya, sintaksis, leksikologiya*;
- til birliklari va hodisalari: *fonema, morfema, oʻzak, affiks, undosh tovush*;
- grammatik tushunchalar: *soʻz turkumi, qoʻshma gap, kelishik*.

Belgilanmaydi:

- xuddi shu so'z umumiy maʼnoda kelganda: *"Ular uzoq **gap** qilishdi"*
  (suhbat maʼnosi), *"**qoʻshimcha** maʼlumot"* (affiks maʼnosida emas);
- umumilmiy so'zlar: *tahlil, usul, natija, misol, qoida*;
- shaxs, asar va tashkilot nomlari;
- terminning o'zi emas, unga tushuntirish beruvchi so'zlar.

Ikkilanayotgan bo'lsangiz, so'zni belgilang, yozuvga izoh (`notes`) qo'shing
va `status: "draft"` holatida qoldiring (7-bo'lim).

## 2. Chegara qoidalari

Pozitsiyalar Python uslubida, yarim ochiq interval ko'rinishida beriladi:
`[start, end)`. `start` — terminning birinchi belgisi indeksi, `end` — oxirgi
belgidan keyingi indeks. Shunda `text[start:end]` aynan terminni beradi.
Indekslar Unicode belgilari bo'yicha sanaladi (Python `str` indeksi).

1. **Span butun so'zlardan iborat.** So'z o'rtasidan boshlanmaydi va so'z
   o'rtasida tugamaydi. *polifonema* ichidan *fonema*ni ajratib bo'lmaydi.
   So'z ichidagi apostrof (*soʻz*, *maʼno*) so'zning bir qismi hisoblanadi.
2. **Qo'shimchalar span ichiga kiradi.** *"fonemalarning"* butunligicha
   belgilanadi, `term` maydoniga esa lug'at shakli yoziladi: `"fonema"`.
3. **Tinish belgilari kirmaydi.** Qo'shtirnoq, qavs, vergul, nuqta, chiziqcha
   va bo'shliq spanning boshida ham, oxirida ham bo'lmasligi kerak.
   Span harf yoki raqam bilan boshlanadi va tugaydi.
4. **Ko'p so'zli termin bitta span bo'ladi.** *"undosh tovush"* — bitta span.
   Ichidagi qisqa termin (*tovush*) alohida belgilanmaydi.
5. **Spanlar ustma-ust tushmaydi.** Annotatsiya tekis (flat) bo'ladi.
   Ikki termin kesishsa, to'liqroq yoki maʼno jihatidan aniqrog'ini belgilang
   va holatni `notes` ga yozing.
6. **Defisli so'z.** Agar *fonetik-fonologik* kabi defisli so'z bitta tushuncha
   bo'lsa, butunligicha belgilanadi. Agar defis ikki mustaqil terminni
   bog'lasa, ikkalasi alohida belgilanadi.
7. **Ellipsis (qisqartirilgan birikma).** *"unli va undosh tovushlar"*
   birikmasida matnda bor qismlar alohida belgilanadi:
   - `"unli"` → `term: "unli tovush"`;
   - `"undosh tovushlar"` → `term: "undosh tovush"`.
8. **Qavs ichidagi izoh.** *"Fonema (yunoncha phonema — tovush)"* birikmasida
   faqat *Fonema* belgilanadi. Chet tilidagi shakl termin sifatida
   belgilanmaydi.

## 3. `term` maydoni

`term` — terminning lug'at shakli: qo'shimchasiz, kichik harfda, rasmiy
lotin yozuvida (*oʻ, gʻ* uchun `ʻ`, tutuq belgisi uchun `ʼ`).
Agar termin `data/terms.json` da bo'lsa, undagi `term` yoziladi.
Bazada bo'lmagan terminlar ham belgilanadi: dataset lug'atdan mustaqil bo'lishi
kerak, aks holda lug'at baseline'i adolatsiz ustunlikka ega bo'ladi.

## 4. Teglar (`label`)

v1 da faqat bitta teg bor: `TERM`. Soha bo'yicha teglar (fonetika,
morfologiya va h.k.) kerak bo'lsa, yo'riqnomaning keyingi versiyasida
qo'shiladi.

## 5. Fayl formati (JSONL)

`data/annotated/` papkasidagi `*.jsonl` fayllar. Har bir qatorda bitta JSON
obyekt bo'ladi va u bitta yozuvni ifodalaydi (bir paragraf yoki bir necha gap).

```json
{"id": "doc-0001-p001", "doc_id": "doc-0001", "text": "Fonemalar va unli tovush.", "terms": [{"start": 0, "end": 9, "term": "fonema", "label": "TERM", "surface": "Fonemalar"}, {"start": 13, "end": 24, "term": "unli tovush", "label": "TERM"}], "annotator": "A1", "status": "draft"}
```

| Maydon | Majburiy | Izoh |
|---|---|---|
| `id` | ha | barcha fayllar bo'yicha noyob yozuv identifikatori |
| `doc_id` | ha | `data/sources.json` dagi manba `id` si |
| `text` | ha | asl matn; o'zgartirilmaydi |
| `terms` | ha | spanlar ro'yxati (termin bo'lmasa — `[]`) |
| `terms[].start`, `terms[].end` | ha | `[start, end)` butun sonlar |
| `terms[].term` | ha | lug'at shakli |
| `terms[].label` | ha | `TERM` |
| `terms[].surface` | yo'q | `text[start:end]` nusxasi; berilsa, mosligi tekshiriladi |
| `annotator` | yo'q | annotator kodi (shaxsiy maʼlumot emas, masalan `A1`) |
| `status` | yo'q | `draft` (standart) yoki `reviewed` |
| `notes` | yo'q | noaniq holatlar bo'yicha izoh |

`surface` maydonini yozish tavsiya etiladi. U pozitsiyalardagi xatolarni
(masalan, matn tahrirlanib, indekslar siljib qolganda) darhol ko'rsatadi.

Matn Unicode NFC shaklida saqlanishi kerak. Boshqa shaklda bo'lsa,
tekshiruvchi skript ogohlantiradi.

### 5.1. Inline belgilash (tavsiya etiladigan usul)

Pozitsiyalarni qo'lda sanash xatoga moyil. Shuning uchun matnni oddiy `.txt`
faylda belgilab, JSONL'ni skript orqali yaratish tavsiya etiladi:

```text
[[Fonetika]] boʻlimida [[unli|unli tovush]] va [[undosh tovushlar|undosh tovush]]
oʻrganiladi.

[[Qoʻshma gaplarning|qoʻshma gap]] tuzilishi haqida qoʻshimcha maʼlumot.
```

- `[[ko'rinish|termin]]` — matndagi shakl va lug'at shakli (2–3-bo'limlar).
- `[[ko'rinish]]` — lug'at shakli ko'rinishning kichik harfli nusxasi bilan
  bir xil bo'lganda (*[[Fonetika]]* → `fonetika`).
- Bo'sh qator paragraflarni ajratadi. Har bir paragraf alohida yozuv bo'ladi:
  `<doc_id>-p001`, `<doc_id>-p002`, ...
- Ko'p so'zli termin qator tashlash orqali davom etishi mumkin.
- Belgilanmagan paragraf `terms: []` bo'ladi, yaʼni "termin yo'q" deb
  hisoblanadi. Shuning uchun faylning to'liq ko'rib chiqilganiga ishonch hosil
  qiling.

```bash
PYTHONPATH=backend python -m app.dataset.inline data/raw/doc-0001.txt --doc-id doc-0001 --annotator A1 -o data/annotated/doc-0001.jsonl
```

Skript quyidagicha ishlaydi:

- avval `doc_id` manbalar reyestrida borligini tekshiradi;
- matnni Unicode NFC shakliga va qator oxirlarini `\n` ga keltiradi;
- natijani 2-bo'lim qoidalari bo'yicha tekshiradi va xatolarni asl fayldagi
  `qator:ustun` bilan ko'rsatadi (masalan, `[[fonem]]alar` — so'z o'rtasida tugaydi);
- birorta xato bo'lsa, hech narsa yozmaydi;
- mavjud JSONL faylni `--force` siz qayta yozmaydi.

**Muhim:** paragraf qo'shilsa yoki o'chirilsa, keyingi yozuvlarning `id` lari
siljiydi. Hujjat qayta yaratilgandan keyin `id` lar o'zgarishini hisobga oling.

## 6. Manbalar (`data/sources.json`)

Har bir `doc_id` manbalar reyestrida bo'lishi shart. **Foydalanish huquqi
aniq bo'lmagan matn datasetga kiritilmaydi.**

```json
[
  {
    "id": "doc-0001",
    "title": "Asar yoki maqola nomi",
    "author": "Muallif",
    "publication": "Nashriyot yoki jurnal",
    "year": 2020,
    "url": null,
    "rights": "Foydalanish huquqi: masalan, CC BY 4.0 yoki muallifning yozma ruxsati",
    "notes": null
  }
]
```

Majburiy maydonlar: `id`, `title`, `rights`. Qolganlari matn yoki `null`
(`year` — butun son yoki `null`).

## 7. Ish jarayoni

1. Matn manbasi va huquqi `data/sources.json` ga yoziladi
   (Vikipediya uchun `fetch_wikipedia` buni avtomatik qiladi).
2. Asl matn `data/raw/` ga saqlanadi va **o'zgartirilmaydi**.
3. Annotator `data/inline/<doc_id>.txt` nusxasida terminlarni belgilaydi
   (5.1-bo'lim), butun faylni oxirigacha ko'rib chiqadi va JSONL yaratadi:
   `status: "draft"`. Bitta ham belgi bo'lmagan fayl `--allow-empty` siz
   qabul qilinmaydi.
4. Ikkinchi odam tekshiradi. Kelishmovchilik bo'lsa, shu yo'riqnoma asosida
   hal qilinadi; yo'riqnomada javob bo'lmasa, yo'riqnoma to'ldiriladi.
5. Tekshirilgan yozuv `status: "reviewed"` holatiga o'tadi. Baholashda faqat
   `reviewed` yozuvlar ishlatiladi.
6. Har bir o'zgarishdan keyin tekshiruvchi skript ishga tushiriladi:

```bash
PYTHONPATH=backend python -m app.dataset.validate
```

### 7.1. Web interfeysda belgilash (tavsiya etiladi)

```bash
PYTHONPATH=backend uvicorn app.main:app --port 8000   # backend
cd frontend && npm run dev                              # http://localhost:5173/#annotate
```

1. Annotator kodini kiriting (`A1`, `A2` — ism emas).
2. Chapdan maqolani tanlang. Terminni sichqoncha bilan belgilang: tanlov butun
   so'zgacha kengayadi, chetidagi tinish belgilari olib tashlanadi. Lug'at
   shakli (`term`) avtomatik taklif qilinadi, uni qo'shimchasiz holga keltiring.
3. Punktir chiziqli joylar — takliflar. Sariq: lug'at, binafsha: AI annotatsiyasi
   (tekshirilmagan), model takliflari ham shu yerda. Bosish — qabul qilish,
   `×` — rad etish. Takliflar avtomatik saqlanmaydi.
   **Test to'plamidagi maqolalarni takliflarsiz belgilang** ("Takliflarni
   ko'rsatish" belgisini o'chiring; metodika, 7-bo'lim).
4. Paragraf to'liq ko'rib chiqilgach "Tekshirildi" belgisini qo'ying va
   saqlang. Termin bo'lmasa ham saqlang: bo'sh ro'yxat "termin yo'q" degani.
   Saqlashda 2-bo'lim qoidalari server tomonida tekshiriladi.

Natija: `data/annotations/<annotator>/<doc_id>.jsonl`. Annotatorlar bir-birining
belgilarini ko'rmaydi.

### 7.2. Kelishuv va oltin standart

```bash
PYTHONPATH=backend python -m app.annotation.agreement compare A1 A2
PYTHONPATH=backend python -m app.annotation.agreement promote A1
```

- `compare` faqat ikkalasi belgilagan paragraflar bo'yicha ishlaydi. U exact va
  partial F1 (bir annotator "oltin", ikkinchisi "bashorat"), bir xil spanlarda
  lug'at shakli mosligini va kelishmovchilik misollarini chiqaradi. Span
  annotatsiyasida kappa o'rniga F1 ishlatiladi: "termin emas" spanlarini sanab
  bo'lmaydi.
- `promote` annotatorning `reviewed` yozuvlarini `data/annotated/` ga
  (oltin standart) o'tkazadi. Mavjud faylni `--force` siz qayta yozmaydi.

## 8. Train/validation/test ajratish

Dataset **manba darajasida** (`doc_id` bo'yicha) ajratiladi: bitta manbadan
olingan yozuvlar turli to'plamlarga tushmaydi.

```bash
PYTHONPATH=backend python -m app.dataset.split
```

- Standart holatda faqat `reviewed` yozuvlar olinadi (`--include-drafts`
  bilan qoralamalarni ham qo'shish mumkin).
- Bir xil matn (registr, apostrof va bo'shliq farqisiz) uchragan manbalar
  bitta guruhga birlashtiriladi va bitta to'plamga tushadi.
- Standart nisbat — 0.7 / 0.15 / 0.15. Muvozanat spanlar soni bo'yicha
  saqlanadi. Natija deterministik: tasodifiylik yo'q va kiruvchi fayllar
  tartibiga bog'liq emas.
- Taqsimot `data/splits/manifest.json` da saqlanadi va **muzlatiladi**: dataset
  o'sganda eski manbalar o'z to'plamida qoladi, faqat yangilari taqsimlanadi.
  Manifest git'ga commit qilinadi.
- `data/processed/{train,validation,test}.jsonl` manifest asosida qayta
  yaratiladi, shuning uchun git'ga qo'shilmaydi.
- `--dry-run` taqsimotni ko'rsatadi, lekin hech narsa yozmaydi.

**Test to'plami qoidasi:** test to'plami faqat yakuniy baholashda ishlatiladi.
Model yoki qoidalarni sozlash, qo'shimchalar ro'yxatini kengaytirish va xato
tahlili `validation` to'plamida qilinadi. Test natijasiga qarab tizim
o'zgartirilsa, bu albatta hujjatlashtiriladi.

Manbalar kam bo'lsa, `validation` va `test` bo'sh qolishi mumkin; skript bu
haqda ogohlantiradi. Og'irligi teng manbalarda standart nisbat bilan
`validation` 3-manbadan, `test` esa 5-manbadan boshlab to'ladi. Lekin bitta
manbadan iborat test to'plami ishonchli baholash uchun yetarli emas.

## 9. Termin nomzodlarini baholash (3-bosqich)

Statistik usullar topgan nomzodlar ro'yxatini inson baholaydi. Bu matnni
belgilashdan alohida va ancha tezroq ish: har bir nomzodga bitta baho.

### 9.1. Shablon

```bash
PYTHONPATH=backend python -m app.evaluation.judgments template --rankings reports/candidates-frequency.csv reports/candidates-tfidf.csv reports/candidates-cvalue.csv --k 100 --output data/judgments/candidates-A1.csv
```

Har bir baholovchi uchun alohida fayl bo'ladi (`candidates-A1.csv`,
`candidates-A2.csv`). Fayl UTF-8 formatida va Excel yoki Numbers'da ochiladi.
Ustunlar:

| Ustun | Kim to'ldiradi | Maʼnosi |
|---|---|---|
| `candidate` | skript | nomzodning lug'at shakli (oxirgi so'z qo'shimchasiz, kichik harf, `'` apostrof) |
| `judgment` | **baholovchi** | `1`, `0`, `?` yoki bo'sh |
| `notes` | baholovchi | ixtiyoriy izoh |
| `frequency` | skript | korpusda necha marta uchragani |
| `example` | skript | korpusdan bitta misol, nomzod `⟦ ⟧` ichida |

Ro'yxat **ko'r**: qaysi usul topgani, nechanchi o'rinda turgani va lug'atda
bor-yo'qligi ko'rsatilmaydi, nomzodlar alifbo tartibida. Baholash tugaguncha
`reports/` dagi reytinglarni ko'rmang. Shablon qayta yaratilsa, qo'yilgan
baholar saqlanadi va faqat yangi nomzodlar qo'shiladi.

### 9.2. Baho qoidalari

Nomzod **butunligicha** baholanadi:

- **`1` — termin.** Nomzod tilshunoslikdagi tushunchaning to'liq nomi (1-bo'lim).
  Lug'at shakli bo'lgani uchun qo'shimchasiz ko'rinishi baholanadi:
  `undosh tovush` (matnda *undosh tovushlar*) — `1`.
- **`0` — termin emas:**
  - umumiy yoki yordamchi so'z (`bu`, `ko'ra`, `bilan`);
  - fe'l shakli (*yoziladi*);
  - terminning bo'lagi: `qo'shma` yolg'iz o'zi termin emas, `qo'shma gap` esa termin;
  - tinish belgisi yo'qligi sababli ikki tushuncha qo'shilib qolgan n-gram;
  - lemmatizatsiya natijasida tanib bo'lmaydigan darajada qisqargan shakl.
- **`?` — noaniq.** Maʼnosi kontekstga bog'liq (umumiy maʼnoda ham, termin
  maʼnosida ham keng ishlatiladi) yoki tilshunoslikka yaqin, lekin termin
  ekaniga ishonch yo'q. Sababini `notes` ga yozing.

Misol jumla nomzod qaysi maʼnoda ishlatilganini ko'rsatadi. Lekin baho shu
bitta misolga emas, nomzodning tilshunoslik matnlaridagi odatiy maʼnosiga
qarab qo'yiladi.

### 9.3. Ikki baholovchi

Ikkala baholovchi bir-biridan **mustaqil** baholaydi va ish tugaguncha baholar
muhokama qilinmaydi. Keyin:

```bash
PYTHONPATH=backend python -m app.evaluation.judgments score --rankings reports/candidates-frequency.csv reports/candidates-tfidf.csv reports/candidates-cvalue.csv --judgments data/judgments/candidates-A1.csv data/judgments/candidates-A2.csv
```

Natijada quyidagilar chiqadi:

- har bir usul va baholovchi uchun **qatʼiy** P@K (faqat `1`) va **yumshoq**
  P@K (`1` va `?`);
- baholovchilar orasidagi kelishuv: **Cohen's kappa**, faqat ikkalasi `0`/`1`
  qo'ygan nomzodlar bo'yicha.

Top-K ichida baholanmagan nomzod bo'lsa, qiymat `≥` bilan chiqadi, yaʼni bu
pastki chegara. Kelishmovchiliklar keyin muhokama qilinib, kelishilgan baho
uchinchi fayl sifatida saqlanishi mumkin (masalan, `candidates-consensus.csv`).

