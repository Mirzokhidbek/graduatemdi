# Tajribalarni taqqoslash jadvali

> Avtomatik yaratilgan: `PYTHONPATH=backend python -m app.evaluation.report`.
> Barcha natijalar **AI annotatsiyasi** (kumush maʼlumot) bo'yicha, inson oltin standarti emas.

Maʼlumot: train 221 / validation 54 / test 35 paragraf; termin spanlari: train 1786, validation 389, test 380.

## 1. Terminlarni aniqlash — test (ro'yxat usulidagi belgilar)

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |
|---|---|---|---|---|---|---|
| Lug'at (15 termin) | 0.708 | 0.166 | 0.269 | [0.171, 0.373] | 0.371 | 0.984 |
| Lug'at (train, 450 termin) | 0.770 | 0.432 | 0.553 | [0.471, 0.628] | 0.696 | 0.994 |
| CRF | 0.715 | 0.534 | 0.611 | [0.527, 0.690] | 0.773 | 0.798 |
| CRF + gazetteer | 0.792 | 0.550 | **0.649** | [0.566, 0.719] | 0.780 | 0.923 |

## 2. Terminlarni aniqlash — validation

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |
|---|---|---|---|---|---|---|
| Lug'at (15 termin) | 0.700 | 0.162 | 0.263 | — | 0.351 | 0.905 |
| Lug'at (train, 450 termin) | 0.671 | 0.393 | 0.496 | — | 0.665 | 0.961 |
| CRF | 0.651 | 0.450 | **0.532** | — | 0.689 | 0.800 |
| CRF + gazetteer | 0.672 | 0.437 | 0.530 | — | 0.696 | 0.947 |

## 3. Terminlarni aniqlash — test (uchrash-ma-uchrash qayta belgilangan, `claude2`)

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |
|---|---|---|---|---|---|---|
| Lug'at (15 termin) | 0.685 | 0.156 | 0.254 | [0.159, 0.354] | 0.358 | 0.934 |
| Lug'at (train, 450 termin) | 0.761 | 0.414 | 0.536 | [0.456, 0.611] | 0.680 | 0.975 |
| CRF | 0.715 | 0.519 | 0.601 | [0.516, 0.679] | 0.767 | 0.808 |
| CRF + gazetteer | 0.792 | 0.535 | **0.638** | [0.550, 0.713] | 0.776 | 0.914 |

## 4. Yangi terminlar (test, train'da uchramagan)

| Usul | Topildi | Recall |
|---|---|---|
| Lug'at (15 termin) | 0/146 | 0.000 |
| Lug'at (train, 450 termin) | 0/146 | 0.000 |
| CRF | 31/146 | 0.212 |
| CRF + gazetteer | 2/146 | 0.014 |

## 5. Meʼyorlashtirish (oltin spanlar uchun lug'at shakli aniqligi)

| Usul | test | test (claude2) |
|---|---|---|
| O'zgarishsiz (kichik harf) | 0.482 (183/380) | 0.473 (185/391) |
| Korpus lemmatizatori | 0.753 (286/380) | 0.744 (291/391) |
| Faqat lug'at | 0.711 (270/380) | 0.696 (272/391) |
| Lug'at + morfologik qoidalar | 0.921 (350/380) | 0.908 (355/391) |

Morfologik qoidalardagi `-ka` fonotaktika qoidasi va `-im`/`-ing` (I/II shaxs birlik egaligi) qoidasi test xatolari tahlilidan keyin qo'shilgan (test bo'yicha sozlangan). Undan oldin: test 0.861, test (claude2) 0.849; validation ikkala qoidada ham o'zgarmagan (0.936).

## 6. Transformer — test (`xlm-roberta-base`, eng yaxshi epoxa: 8)

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |
|---|---|---|---|---|---|---|
| Lug'at (train, 450 termin) | 0.770 | 0.432 | 0.553 | [0.471, 0.628] | 0.696 | 0.994 |
| CRF | 0.715 | 0.534 | 0.611 | [0.527, 0.690] | 0.773 | 0.798 |
| CRF + gazetteer | 0.792 | 0.550 | 0.649 | [0.566, 0.719] | 0.780 | 0.923 |
| Transformer | 0.698 | 0.784 | **0.739** | [0.654, 0.810] | 0.865 | 0.772 |

`crf_gazetteer` dan farqning 95 % oralig'i: Lug'at (train, 450 termin) [-0.138, -0.059]; CRF [-0.104, +0.035]; Transformer [-0.024, +0.198].

Train'da uchramagan terminlar: Lug'at (train, 450 termin) 0/146; CRF 31/146; CRF + gazetteer 2/146; Transformer 102/146.

## 6. Transformer — test, claude2 (`xlm-roberta-base`, eng yaxshi epoxa: 8)

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |
|---|---|---|---|---|---|---|
| Lug'at (train, 450 termin) | 0.761 | 0.414 | 0.536 | [0.456, 0.611] | 0.680 | 0.975 |
| CRF | 0.715 | 0.519 | 0.601 | [0.516, 0.679] | 0.767 | 0.808 |
| CRF + gazetteer | 0.792 | 0.535 | 0.638 | [0.550, 0.713] | 0.776 | 0.914 |
| Transformer | 0.700 | 0.765 | **0.731** | [0.651, 0.799] | 0.869 | 0.783 |

`crf_gazetteer` dan farqning 95 % oralig'i: Lug'at (train, 450 termin) [-0.145, -0.063]; CRF [-0.101, +0.039]; Transformer [-0.020, +0.199].

Train'da uchramagan terminlar: Lug'at (train, 450 termin) 3/156; CRF 30/156; CRF + gazetteer 5/156; Transformer 104/156.
