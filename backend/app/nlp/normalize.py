"""Termin moslashtirish uchun matn normalizatsiyasi.

Normalizatsiya belgi-belgi (1:1) bajariladi: natija uzunligi har doim asl
matn uzunligiga teng. Shu sababli normallashtirilgan matnda topilgan
``[start, end)`` pozitsiyalari asl matnga ham bevosita mos keladi.

Bu modul faqat **yozuv** farqlarini tenglashtiradi (harf registri,
apostrof belgilari). Maʼno jihatidan tenglashtirish (sinonimlar) bu yerda
emas, terminlar bazasida qilinadi.
"""

from __future__ import annotations

APOSTROPHE = "'"

# Oʻzbek lotin yozuvida oʻ/gʻ va tutuq belgisi uchun amalda ishlatiladigan
# belgilar. Moslashtirishda ularning barchasi bitta ``'`` belgisiga keltiriladi.
APOSTROPHE_VARIANTS = frozenset(
    {
        "'",  # U+0027 oddiy apostrof
        "`",  # U+0060 grave accent
        "´",  # U+00B4 acute accent
        "ʹ",  # U+02B9 modifier letter prime
        "ʻ",  # U+02BB modifier letter turned comma (rasmiy oʻ, gʻ)
        "ʼ",  # U+02BC modifier letter apostrophe (rasmiy tutuq belgisi)
        "‘",  # U+2018 left single quotation mark
        "’",  # U+2019 right single quotation mark
        "′",  # U+2032 prime
    }
)


def normalize_char(ch: str) -> str:
    if ch in APOSTROPHE_VARIANTS:
        return APOSTROPHE
    lowered = ch.lower()
    # Ayrim belgilar (masalan, "İ") kichik harfga o'tganda 2 belgiga aylanadi;
    # 1:1 moslikni saqlash uchun bunday hollarda belgi o'zgartirilmaydi.
    return lowered if len(lowered) == 1 else ch


def normalize_text(text: str) -> str:
    """Matnni uzunligini o'zgartirmasdan normallashtiradi."""
    return "".join(normalize_char(ch) for ch in text)


def normalize_form(form: str) -> str:
    """Lug'at shaklini normallashtiradi va so'zlar orasidagi bo'shliqlarni birlashtiradi."""
    return " ".join(normalize_text(form).split())
