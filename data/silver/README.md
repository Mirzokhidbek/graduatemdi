# AI (Claude) annotatsiyasi — "kumush" maʼlumot

Bu papkadagi ro'yxatlar va ulardan yaratilgan `data/annotations/claude/*.jsonl`
**inson annotatsiyasi emas**. Ularni Claude (AI) 2026-10-31 da korpusdagi 41 ta
maqolaning har birini o'qib tuzgan. Barcha yozuvlar `annotator: "claude"`,
`status: "draft"`.

Nima uchun kerak:

- web interfeysda inson annotatorga **taklif** sifatida ko'rsatiladi (binafsha
  punktir), annotator har birini qabul qiladi yoki rad etadi;
- inson belgilagan maʼlumot tayyor bo'lguncha butun quvurni (split, lug'at,
  CRF, baholash) ishga tushirib ko'rish va dastlabki natija olish uchun.

Natijalar bu maʼlumot bo'yicha olinganda **"kumush maʼlumot bo'yicha (AI
annotatsiyasi)"** deb belgilanadi va inson oltin standarti o'rnida ko'rsatilmaydi
(`docs/results.md`).

## Qanday tuzilgan

`app/annotation/silver.py` ro'yxatlarni lug'at aniqlagichi bilan matnga qo'llaydi
(qo'shimchalar, tovush o'zgarishlari, uzun moslik ustunligi):

- `lexicon.txt` — barcha hujjatlarga umumiy, korpusda deyarli faqat termin
  maʼnosida keladigan so'zlar (fonetika, fonema, kelishik, qoʻshma gap, ...);
- `docs/<doc_id>.txt` — shu maqolaga xos terminlar, xato yozilgan shakllar
  (`jarangeiz undosh`, `ran` — "gap"ning OCR xatosi), qisqartmalar (`U.` —
  urgʻu, `St.` — soʻz turkumi) va istisnolar: chet tilidagi izohlar, asar nomlari,
  umumiy maʼnodagi qo'llanish (`!= sifatida`, `!~ ga ega`).

Qayta yaratish: `PYTHONPATH=backend python -m app.annotation.silver`.

## Qabul qilingan qarorlar (yo'riqnoma bilan farq qiladigan joylar shu yerda)

1. **Ko'p maʼnoli so'zlar** (`ot`, `sifat`, `son`, `ega`, `gap`, `hol`, `zamon`,
   `ravish`, `lugʻat`) faqat termin maʼnosida keladigan maqolalarda va
   istisnolar bilan belgilandi. `soʻz`, `til`, `maʼno` yolg'iz o'zi belgilanmadi
   (juda umumiy; `soʻz turkumi`, `qoʻshma gap` kabi birikmalar ichida belgilanadi).
2. **Ellipsis** (yo'riqnoma 2.7): `unlilar` → `unli tovush`, `atoqli` (`atoqli va
   turdosh otlar`) → `atoqli ot`.
3. **Fonetik belgilar** (`portlovchi`, `jarangli`, `til orqa`) belgi nomi sifatida
   kelganda termin deb olindi.
4. **Qisqartmalar** (`U.`, `M.`, `S.`, `L.`, `Q. g.`) termin sifatida, lug'at shakli
   to'liq termin bilan belgilandi.
5. **Bir maqola ichida bir xil qaror**: ro'yxat butun maqolaga qo'llangani uchun
   so'zning har bir uchrashi alohida baholanmagan — bu inson annotatsiyasidan
   asosiy farq. Shu sababli umumiy maʼnodagi ayrim uchrashlar termin bo'lib
   qolgan yoki aksincha bo'lishi mumkin.

## Cheklov: lug'at baseline'i uchun qulay

Kumush spanlar lug'at aniqlagichi bilan yaratilgani uchun ularning chegaralari
aniqlagich qoidalariga (qo'shimchalar ro'yxati) mos keladi. Shuning uchun lug'at
usulining bu maʼlumotdagi natijasi inson oltin standartidagidan yuqoriroq
chiqishi kutiladi. Usullarni yakuniy solishtirish faqat inson belgilagan
`reviewed` maʼlumotda qilinadi.

## Ikkinchi o'tish: test to'plami, uchrash-ma-uchrash (`claude2`)

`claude2/<doc_id>.txt` — 6 ta test maqolasi qaytadan belgilangan. Bu safar har
bir termin uchrashi matndagi tartibda alohida yozilgan, umumiy maʼnodagi
uchrashlar yozilmagan, ro'yxat va takliflar ishlatilmagan.
`PYTHONPATH=backend python -m app.annotation.sequential claude2` →
`data/annotations/claude2/`. Birinchi o'tish bilan kelishuv: exact F1 0.965
(`docs/results.md`).
