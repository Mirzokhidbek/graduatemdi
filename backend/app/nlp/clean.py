"""Matnni tozalash, apostroflarni rasmiy shaklga keltirish va gaplarga ajratish (preprocessing).

Uch xil vazifa, uch xil kafolat:

- ``normalize_text`` (``normalize.py``) — **qidiruv uchun**: kichik harf, barcha
  apostroflar ``'``; uzunlik saqlanadi, pozitsiyalar asl matnga mos.
- ``canonical_apostrophes`` — **ko'rsatish va saqlash uchun**: oʻ/gʻ dagi belgi
  ``ʻ`` (U+02BB), tutuq belgisi ``ʼ`` (U+02BC) — 1995-yilgi imlo qoidalariga
  mos rasmiy shakl. Uzunlik ham saqlanadi (har bir belgi bitta belgiga almashadi).
- ``clean_text`` — **yangi manba qo'shishda**: Vikipediya belgilari, havola
  raqamlari, ortiqcha bo'shliqlar olib tashlanadi. Uzunlik o'zgaradi, shuning
  uchun faqat annotatsiyadan **oldin** ishlatiladi (``data/raw/`` dagi matnlar
  shu bosqichdan o'tgan va endi o'zgartirilmaydi).

``split_sentences`` qisqartmalarni (``Mas.``, ``mil. av.``, ``N. S.``, ``U.si``)
gap oxiri deb hisoblamaydi.
"""

from __future__ import annotations

import re
import unicodedata

from app.nlp.normalize import APOSTROPHE_VARIANTS

TURNED_COMMA = "ʻ"  # ʻ — oʻ, gʻ
APOSTROPHE_MARK = "ʼ"  # ʼ — tutuq belgisi (maʼno, feʼl)
_LETTER = re.compile(r"[^\W\d_]")


def canonical_apostrophes(text: str) -> str:
    """Barcha apostrof variantlarini rasmiy ``ʻ`` / ``ʼ`` ga keltiradi (uzunlik saqlanadi).

    ``o``/``g`` dan keyin va keyingi belgi harf bo'lsa — ``ʻ`` (``oʻzak``, ``bogʻ``);
    so'z oxiridagi ``gʻ`` ham (``togʻ``). Boshqa so'z ichidagi apostrof — ``ʼ``.
    So'z chetidagi qo'shtirnoq vazifasidagi belgilar o'zgarmaydi.
    """
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch not in APOSTROPHE_VARIANTS:
            continue
        before = chars[i - 1] if i > 0 else ""
        after = chars[i + 1] if i + 1 < len(chars) else ""
        letter_before = bool(_LETTER.match(before))
        letter_after = bool(_LETTER.match(after))
        if before.lower() in ("o", "g") and (letter_after or before.lower() == "g" and letter_before):
            # "o'" so'z boshida ham uchraydi: "o'zak"; "g'" so'z oxirida ham: "tog'"
            chars[i] = TURNED_COMMA
        elif letter_before and letter_after:
            chars[i] = APOSTROPHE_MARK
    return "".join(chars)


_WIKI_HEADING = re.compile(r"^\s*=+\s*[^=\n]*=+\s*$", re.MULTILINE)
_REFERENCE = re.compile(r"\[(?:\d+|[a-z]|izoh \d+)\]")
_SPACES = re.compile(r"[ \t ]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_ZERO_WIDTH = re.compile("[​‌‍﻿]")


def clean_text(text: str) -> str:
    """Yangi matnni korpusga qo'shishdan oldin tozalaydi.

    - Unicode NFC, qator oxirlari ``\\n``;
    - ko'rinmas belgilar (zero-width, BOM) va ``== Sarlavha ==`` qatorlari olib tashlanadi;
    - ``[1]``, ``[a]`` kabi havola belgilari olib tashlanadi;
    - qator ichidagi ketma-ket bo'shliqlar bitta probelga, uch va undan ortiq bo'sh qator ikkitaga;
    - apostroflar rasmiy shaklga (``canonical_apostrophes``).

    So'zlarning o'zi (shu jumladan OCR xatolari) o'zgartirilmaydi: manba matni
    qanday bo'lsa, shunday qoladi.
    """
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = _ZERO_WIDTH.sub("", text)
    text = _WIKI_HEADING.sub("", text)
    text = _REFERENCE.sub("", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANK_LINES.sub("\n\n", text)
    return canonical_apostrophes(text.strip())


# Nuqtadan keyin gap tugamaydigan qisqartmalar (kichik harfda, nuqtasiz).
ABBREVIATIONS = frozenset(
    {
        "mas", "masalan", "mil", "av", "avv", "yun", "lot", "lotincha", "arab", "fors", "qad", "b", "va b",
        "y", "yy", "ad", "q", "k", "st", "t", "prof", "akad", "sh", "gʻ", "ye", "kv", "s", "l", "m", "u", "g",
        "f", "n", "v", "a", "i", "e", "o", "d", "r", "j", "x", "z", "p", "h", "nashr", "jild", "bet", "izd",
    }
)
_BOUNDARY = re.compile(r"[.!?…]+[»“”\")]*(?=\s+)")


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Matnni gaplarga ajratadi; ``[(start, end), ...]`` asl matn pozitsiyalarida.

    Gap chegarasi: ``. ! ? …`` (va undan keyingi yopuvchi qo'shtirnoq/qavs), keyin
    bo'shliq va keyingi so'z bosh harf, raqam yoki ochuvchi belgi bilan boshlanadi.
    Nuqtadan oldingi so'z qisqartma bo'lsa (``Mas.``, ``mil. av.``, bir harfli
    bosh harf ``N.``), chegara emas.
    """
    sentences: list[tuple[int, int]] = []
    start = 0
    for match in _BOUNDARY.finditer(text):
        end = match.end()
        rest = text[end:].lstrip()
        if not rest:
            continue
        first = rest[0]
        if not (first.isupper() or first.isdigit() or first in "„«\"(—–-["):
            continue
        if match.group().startswith("."):
            word = re.search(r"([^\W\d_][^\W\d_ʻʼ']*)$", text[start : match.start()])
            if word and (word.group(1).lower() in ABBREVIATIONS or len(word.group(1)) == 1):
                continue
        segment = text[start:end].strip()
        if segment:
            offset = start + (len(text[start:end]) - len(text[start:end].lstrip()))
            sentences.append((offset, offset + len(segment)))
        start = end
    tail = text[start:].strip()
    if tail:
        offset = start + (len(text[start:]) - len(text[start:].lstrip()))
        sentences.append((offset, offset + len(tail)))
    return sentences
