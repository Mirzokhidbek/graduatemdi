"""Imlo va yozuv variantlari: kirill -> lotin transliteratsiya, imlo "skeleti", tahrir masofasi (3.1-bo'lim).

- ``to_latin`` — oʻzbek kirill yozuvini rasmiy lotin yozuviga (1995) o'giradi.
  Qoidalar "Oʻzbek tilining asosiy imlo qoidalari" (1995) va kirill–lotin
  moslik jadvaliga asoslanadi: ``ш -> sh``, ``ч -> ch``, ``ў -> oʻ``, ``ғ -> gʻ``,
  ``ё -> yo``, ``ю -> yu``, ``я -> ya``, ``ъ -> ʼ``, ``ь`` tushiriladi;
  ``е`` so'z boshida, unlidan va ``ъ`` dan keyin ``ye``, aks holda ``e``
  (``ъ`` undosh va iotali unli orasida yozilmaydi: *объект -> obyekt*, lekin *меъёр -> meʼyor*);
  ``ц`` so'z boshida va undoshdan keyin ``s``, unlidan keyin ``ts``.
- ``skeleton`` — imlo farqlari olib tashlangan kalit: kichik harf, transliteratsiya,
  barcha apostrof turlari va defislar o'chiriladi. Bir xil skeletli shakllar —
  **imlo variantlari** (*oʻzak / o'zak / o`zak / ozak / ўзак*).
- ``edit_distance`` — Damerau–Levenshtein masofasi (qo'shni harflar o'rin almashishi
  bilan); uzun so'zlarda kichik masofa — ehtimoliy **imlo xatosi**
  (*nosatandart ~ nostandart*). Bu faqat tekshiruvga taklif, avtomatik birlashtirilmaydi.
"""

from __future__ import annotations

import re
import unicodedata

from app.nlp.clean import canonical_apostrophes
from app.nlp.normalize import APOSTROPHE_VARIANTS

_SIMPLE = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "x", "ҳ": "h", "қ": "q", "ш": "sh", "ч": "ch", "ў": "oʻ", "ғ": "gʻ", "ё": "yo", "ю": "yu",
    "я": "ya", "ъ": "ʼ", "ь": "", "э": "e", "ы": "i", "щ": "sh",
}
_VOWELS = set("аеёиоуўэюяaeiou")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def has_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC.search(text))


def has_mixed_script(word: str) -> bool:
    """So'z ichida kirill va lotin harflari aralash (masalan, kirill "о" lotin so'z ichida)."""
    latin = any("a" <= ch.lower() <= "z" for ch in word)
    return latin and has_cyrillic(word)


# Ko'rinishi lotin harfiga o'xshash kirill harflari (aralash yozuvdagi "yashirin" xato).
HOMOGLYPHS = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "к": "k", "м": "m", "т": "t",
    "в": "b", "н": "h", "і": "i", "ј": "j",
    "А": "A", "Е": "E", "О": "O", "Р": "P", "С": "C", "У": "Y", "Х": "X", "К": "K", "М": "M", "Т": "T",
    "В": "B", "Н": "H",
}


def fix_mixed_script(text: str) -> str:
    """Aralash yozuvli so'zlarda kirill "o'xshash" harflarini lotin harfi bilan almashtiradi
    (transliteratsiya emas: lotin so'z ichidagi kirill "у" — bu "y", "u" emas)."""
    words = []
    for word in text.split(" "):
        if has_mixed_script(word):
            word = "".join(HOMOGLYPHS.get(ch, ch) for ch in word)
        words.append(word)
    return " ".join(words)


def to_latin(text: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(text):
        low = ch.lower()
        prev = text[i - 1].lower() if i > 0 else ""
        word_start = not prev.isalpha()
        nxt = text[i + 1].lower() if i + 1 < len(text) else ""
        if low == "е":
            latin = "ye" if word_start or prev in _VOWELS or prev == "ъ" else "e"
        elif low == "ъ" and nxt in "еёюя" and prev.isalpha() and prev not in _VOWELS:
            latin = ""  # undoshdan keyin: объект -> obyekt, съезд -> syezd (unlidan keyin: меъёр -> meʼyor)
        elif low == "ц":
            latin = "ts" if prev in _VOWELS and not word_start else "s"
        elif low in _SIMPLE:
            latin = _SIMPLE[low]
        else:
            out.append(ch)
            continue
        if ch != low and latin:  # bosh harf: faqat birinchi harf katta (Ш -> Sh)
            latin = latin[0].upper() + latin[1:]
        out.append(latin)
    return "".join(out)


def canonical_form(form: str) -> str:
    """Saqlash uchun rasmiy yozuv: lotin, NFC, rasmiy apostroflar, bitta bo'shliq."""
    text = unicodedata.normalize("NFC", to_latin(form))
    return canonical_apostrophes(" ".join(text.split()))


def skeleton(form: str) -> str:
    text = unicodedata.normalize("NFC", to_latin(form)).lower()
    text = "".join(ch for ch in text if ch not in APOSTROPHE_VARIANTS and ch != "-")
    return " ".join(text.split())


def edit_distance(a: str, b: str) -> int:
    """Damerau–Levenshtein (cheklangan: optimal string alignment)."""
    if a == b:
        return 0
    rows = [list(range(len(b) + 1))]
    for i in range(1, len(a) + 1):
        row = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            row[j] = min(rows[-1][j] + 1, row[j - 1] + 1, rows[-1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                row[j] = min(row[j], rows[-2][j - 2] + 1)
        rows.append(row)
    return rows[-1][-1]


def likely_misspelling(a: str, b: str, min_length: int = 6) -> bool:
    """Ikki shakl bitta so'zning imlo xatoli varianti bo'lishi mumkinmi (taxminiy)."""
    fa, fb = skeleton(a), skeleton(b)
    if fa == fb or fa.split()[:-1] != fb.split()[:-1]:  # ko'p so'zlilarda faqat oxirgi so'z farqlansin
        return False
    sa, sb = fa.split()[-1], fb.split()[-1]
    if min(len(sa), len(sb)) < min_length:
        return False
    # So'z yasalishi va qo'shimcha farqi imlo xatosi emas: fonetik ~ fonetika, fonologik ~ fonologiya.
    # Shu sababli boshi va oxiri bir xil, biri ikkinchisining boshlanmasi bo'lmagan juftlar olinadi.
    if sa[0] != sb[0] or sa[-2:] != sb[-2:] or sa.startswith(sb) or sb.startswith(sa):
        return False
    # Maʼnosi qarama-qarshi yasalishlar: mahsullilik ~ mahsulsizlik, makro- ~ mikro-.
    for x, y in (("lilik", "sizlik"), ("makro", "mikro"), ("li", "siz")):
        if sa.replace(x, y) == sb or sb.replace(x, y) == sa:
            return False
    limit = 1 if max(len(sa), len(sb)) < 10 else 2
    return edit_distance(sa, sb) <= limit
