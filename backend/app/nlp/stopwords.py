"""Oʻzbek tilidagi yordamchi va umumiy so'zlar (termin nomzodlarini filtrlash uchun).

Diqqat: bu boshlang'ich ro'yxat Claude tomonidan tuzilgan va tilshunos
tomonidan tekshirilmagan. Termin bo'lishi mumkin bo'lgan so'zlar (masalan,
``ega`` — gap bo'lagi, ``kesim``, ``gap``) ataylab kiritilmagan.
So'zlar normallashtirilgan ko'rinishda: kichik harf, apostrof ``'``.
"""

from __future__ import annotations

STOPWORDS = frozenset(
    """
    va bilan uchun ham esa yoki lekin ammo biroq balki chunki agar hamda yoxud
    shuningdek na ya'ni masalan mas jumladan
    bu shu u ular ul o'sha bunday shunday ushbu
    uning ularning bunga shunga unga buning shuning undan bundan shundan
    bir har hamma barcha ba'zi ayrim boshqa turli xil
    kabi deb edi emas ekan bo'lib bo'ladi bo'lgan bo'lsa bo'lmaydi bo'lishi
    qilib qiladi qilingan qilinadi etadi etib etilgan etiladi
    hisoblanadi ataladi deyiladi aytiladi mavjud iborat tashkil
    keyin oldin so'ng orqali bo'yicha haqida tomonidan sifatida asosida
    yana faqat juda eng ko'p kam ba'zan ko'pincha asosan hozirgi hozir endi
    ichida o'z o'zi o'zining men biz siz sen ular
    nima kim qaysi qanday qancha necha
    mumkin kerak lozim zarur
    da de dir ki mi
    """.split()
)
