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

1. Matn manbasi va huquqi `data/sources.json` ga yoziladi.
2. Asl matn `data/raw/` ga saqlanadi.
3. Annotator matnni belgilaydi (5.1-bo'lim) va JSONL yaratadi: `status: "draft"`.
4. Ikkinchi odam tekshiradi. Kelishmovchilik bo'lsa, shu yo'riqnoma asosida
   hal qilinadi; yo'riqnomada javob bo'lmasa, yo'riqnoma to'ldiriladi.
5. Tekshirilgan yozuv `status: "reviewed"` holatiga o'tadi. Baholashda faqat
   `reviewed` yozuvlar ishlatiladi.
6. Har bir o'zgarishdan keyin tekshiruvchi skript ishga tushiriladi:

```bash
PYTHONPATH=backend python -m app.dataset.validate
```

Annotatorlar orasidagi kelishuvni o'lchash (inter-annotator agreement)
keyingi versiyada qo'shiladi.

## 8. Train/validation/test haqida

Dataset **manba darajasida** (`doc_id` bo'yicha) ajratiladi: bitta manbadan
olingan yozuvlar turli to'plamlarga tushmasligi kerak. Tekshiruvchi skript bir
xil matnli takroriy yozuvlar haqida ogohlantiradi, chunki ular to'plamlar
orasida maʼlumot sizib kirishiga sabab bo'ladi.
