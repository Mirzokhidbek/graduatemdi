# Tajribalarni taqqoslash jadvali

> Avtomatik yaratilgan: `PYTHONPATH=backend python -m app.evaluation.report`.
> Barcha natijalar **AI annotatsiyasi** (kumush maʼlumot) bo'yicha, inson oltin standarti emas.

Maʼlumot: train 221 / validation 54 / test 35 paragraf; termin spanlari: train 1786, validation 389, test 380.

## 1. Terminlarni aniqlash — test (ro'yxat usulidagi belgilar)

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |
|---|---|---|---|---|---|---|
| Lug'at (15 termin) | 0.708 | 0.166 | 0.269 | [0.171, 0.373] | 0.371 | 0.984 |
| Lug'at (train, 450 termin) | 0.770 | 0.432 | 0.553 | [0.471, 0.628] | 0.696 | 0.994 |
| CRF | 0.714 | 0.526 | 0.606 | [0.523, 0.687] | 0.769 | 0.785 |
| CRF + gazetteer | 0.792 | 0.550 | **0.649** | [0.566, 0.719] | 0.780 | 0.914 |

## 2. Terminlarni aniqlash — validation

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |
|---|---|---|---|---|---|---|
| Lug'at (15 termin) | 0.700 | 0.162 | 0.263 | — | 0.351 | 0.905 |
| Lug'at (train, 450 termin) | 0.671 | 0.393 | 0.496 | — | 0.665 | 0.961 |
| CRF | 0.652 | 0.452 | **0.534** | — | 0.691 | 0.801 |
| CRF + gazetteer | 0.668 | 0.434 | 0.526 | — | 0.693 | 0.947 |

## 3. Terminlarni aniqlash — test (uchrash-ma-uchrash qayta belgilangan, `claude2`)

| Usul | P | R | F1 | F1, 95 % oraliq | Partial F1 | Lug'at shakli aniqligi |
|---|---|---|---|---|---|---|
| Lug'at (15 termin) | 0.685 | 0.156 | 0.254 | [0.159, 0.354] | 0.358 | 0.934 |
| Lug'at (train, 450 termin) | 0.761 | 0.414 | 0.536 | [0.456, 0.611] | 0.680 | 0.975 |
| CRF | 0.714 | 0.512 | 0.596 | [0.513, 0.673] | 0.763 | 0.795 |
| CRF + gazetteer | 0.792 | 0.535 | **0.638** | [0.550, 0.713] | 0.776 | 0.904 |

## 4. Yangi terminlar (test, train'da uchramagan)

| Usul | Topildi | Recall |
|---|---|---|
| Lug'at (15 termin) | 0/146 | 0.000 |
| Lug'at (train, 450 termin) | 0/146 | 0.000 |
| CRF | 29/146 | 0.199 |
| CRF + gazetteer | 2/146 | 0.014 |

## 5. Meʼyorlashtirish (oltin spanlar uchun lug'at shakli aniqligi)

| Usul | test | test (claude2) |
|---|---|---|
| O'zgarishsiz (kichik harf) | 0.482 (183/380) | 0.473 (185/391) |
| Korpus lemmatizatori | 0.747 (284/380) | 0.739 (289/391) |
| Faqat lug'at | 0.711 (270/380) | 0.696 (272/391) |
| Lug'at + morfologik qoidalar | 0.916 (348/380) | 0.903 (353/391) |

Morfologik qoidalardagi `-ka` fonotaktika qoidasi test xatolari tahlilidan keyin qo'shilgan (test bo'yicha sozlangan). Undan oldin: test 0.861, test (claude2) 0.849; validation o'zgarmagan (0.936).
