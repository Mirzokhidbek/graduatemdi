"""Variantlarni bitta tushuncha atrofida guruhlash va meʼyoriy shaklni tanlash (3.1-bo'lim).

Bog'lanish turlari (graf qirralari):

| Tur | Aniqlash | Avtomatik birlashtiriladimi |
|---|---|---|
| ``orthographic`` | bir xil imlo skeleti (``orthography.skeleton``): apostrof, registr, kirill | ha |
| ``morphological`` | bir xil lug'at shakli (``TermNormalizer``): *fonemalar ~ fonema* | ha |
| ``misspelling`` | kichik tahrir masofasi (``orthography.likely_misspelling``) | yo'q, tekshiruvga |
| ``synonym`` / ``doublet`` | lug'atdagi ``synonyms`` yoki matndan ajratilgan juftlar | yo'q, tekshiruvga |

**Meʼyoriy shaklni tanlash qoidalari** (tartib bilan; birinchi hal qilgani natija beradi).
Ular ISO 704 dagi termin tanlash tamoyillariga — uzusga (amaldagi qo'llanish),
qisqalikka va lisoniy to'g'rilikka — asoslanadi:

1. Lug'atda ``approved`` holatdagi yozuvning ``preferred_form`` i (manba bilan tasdiqlangan).
2. Rasmiy imlo: lotin yozuvi va rasmiy apostroflar (*oʻ, gʻ, ʼ*) bilan yozilgan shakl.
   Imlo variantlari orasida tanlov faqat shu qoida bilan hal qilinadi.
3. Lug'atdagi ``preferred_form`` (tekshirilmagan bo'lsa ham).
4. Korpusdagi chastota (uzus).
5. Qisqalik (so'zlar, keyin harflar soni).

Loyiha qoidasi: tizim manbasiz shaklni **meʼyoriy deb eʼlon qilmaydi**. 1-qoidadan
boshqa holatlarda natija holati ``needs_review`` — "tavsiya, tekshirish kerak".
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from app.database.term_store import STATUS_APPROVED, TermEntry
from app.nlp.normalize import normalize_form
from app.variation.orthography import canonical_form, has_cyrillic, likely_misspelling, skeleton

AUTO_LINKS = ("orthographic", "morphological")
REVIEW_LINKS = ("misspelling", "synonym", "doublet")


@dataclass
class VariantGroup:
    members: Counter  # shakl (asl ko'rinish) -> chastota
    links: list[tuple[str, str, str]] = field(default_factory=list)  # (a, b, tur)
    preferred: str | None = None
    status: str = "needs_review"
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "preferred": self.preferred,
            "status": self.status,
            "reasons": self.reasons,
            "members": dict(self.members.most_common()),
            "links": [{"a": a, "b": b, "type": t} for a, b, t in self.links],
        }


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        self.parent[self.find(a)] = self.find(b)


def is_official_spelling(form: str) -> bool:
    return not has_cyrillic(form) and canonical_form(form) == " ".join(form.split())


def choose_preferred(
    forms: Counter, entries: Iterable[TermEntry] = ()
) -> tuple[str, str, list[str]]:
    """(tanlangan shakl, holat, sabablar). ``forms`` — shakl -> chastota."""
    entries = list(entries)
    by_norm = {}
    for entry in entries:
        for form in (entry.term, *entry.variants, *entry.synonyms):
            by_norm.setdefault(normalize_form(form), entry)
    for entry in entries:
        if entry.status == STATUS_APPROVED and entry.preferred_form:
            return entry.preferred_form, STATUS_APPROVED, [f"lug'atda tasdiqlangan (manba: {entry.source})"]

    reasons: list[str] = []
    # Imlo variantlarini bitta rasmiy shaklga keltirish (chastotalar qo'shiladi).
    merged: Counter = Counter()
    for form, count in forms.items():
        merged[canonical_form(form).lower()] += count
    if len(merged) < len(forms):
        reasons.append("imlo variantlari rasmiy lotin yozuviga keltirildi")

    candidates = list(merged)
    preferred_in_base = {
        canonical_form(e.preferred_form).lower() for e in entries if e.preferred_form
    } & set(candidates)
    if len(preferred_in_base) == 1:
        choice = preferred_in_base.pop()
        reasons.append("lug'atdagi meʼyoriy shakl (tekshirilmagan)")
        return choice, "needs_review", reasons

    top = max(merged.values())
    frequent = [c for c in candidates if merged[c] == top]
    if len(frequent) == 1 and len(candidates) > 1:
        reasons.append(f"korpusda eng ko'p qo'llangan ({top} marta)")
        return frequent[0], "needs_review", reasons
    choice = min(frequent, key=lambda c: (len(c.split()), len(c), c))
    if len(candidates) > 1:
        reasons.append("chastota teng — qisqaroq shakl")
    elif sum(forms.values()) > 1 and len(forms) > 1:
        reasons.append("barcha shakllar bitta lug'at shakliga keltirildi")
    return choice, "needs_review", reasons


def build_groups(
    forms: Mapping[str, int],
    lemma_of: Mapping[str, str],
    entries: Iterable[TermEntry] = (),
    pairs: Iterable[tuple[str, str, str]] = (),
    detect_misspellings: bool = True,
) -> list[VariantGroup]:
    """``forms`` — shakl -> chastota; ``lemma_of`` — shakl -> lug'at shakli; ``pairs`` — (a, b, tur).

    Avtomatik bog'lanishlar (imlo, morfologiya) guruh hosil qiladi; sinonim, dublet va imlo
    xatosi nomzodlari guruhlar orasida faqat ``links`` sifatida yoziladi.
    """
    entries = list(entries)
    uf = _UnionFind()
    links: list[tuple[str, str, str]] = []
    by_skeleton: dict[str, list[str]] = defaultdict(list)
    by_lemma: dict[str, list[str]] = defaultdict(list)
    for form in forms:
        uf.find(form)
        by_skeleton[skeleton(form)].append(form)
        by_lemma[skeleton(lemma_of.get(form, form))].append(form)
    for kind, buckets in (("orthographic", by_skeleton), ("morphological", by_lemma)):
        for bucket in buckets.values():
            for other in bucket[1:]:
                if uf.find(other) != uf.find(bucket[0]):
                    links.append((bucket[0], other, kind))
                uf.union(other, bucket[0])

    groups: dict[str, VariantGroup] = {}
    for form, count in forms.items():
        groups.setdefault(uf.find(form), VariantGroup(Counter())).members[form] += count
    for a, b, kind in links:
        groups[uf.find(a)].links.append((a, b, kind))

    review: list[tuple[str, str, str]] = list(pairs)
    for entry in entries:
        for synonym in entry.synonyms:
            review.append((entry.term, synonym, "synonym"))
    if detect_misspellings:
        lemma_freq: Counter = Counter()
        for form, count in forms.items():
            lemma_freq[lemma_of.get(form, form)] += count
        lemmas = sorted(lemma_freq)
        for i, a in enumerate(lemmas):
            for b in lemmas[i + 1 :]:
                if likely_misspelling(a, b) and _rare_vs_common(lemma_freq[a], lemma_freq[b]):
                    review.append((a, b, "misspelling"))
    lemma_owner = {skeleton(lemma_of.get(f, f)): uf.find(f) for f in forms}
    seen: set[tuple[str, str]] = set()
    for a, b, kind in review:
        ga, gb = lemma_owner.get(skeleton(a)), lemma_owner.get(skeleton(b))
        pair = tuple(sorted((skeleton(a), skeleton(b))))
        if ga is not None and gb is not None and ga != gb and pair not in seen:
            seen.add(pair)
            groups[ga].links.append((a, b, kind))

    for group in groups.values():
        lemmas: Counter = Counter()
        for form, count in group.members.items():
            lemmas[lemma_of.get(form, form)] += count
        group.preferred, group.status, group.reasons = choose_preferred(lemmas, entries)
    return sorted(groups.values(), key=lambda g: -sum(g.members.values()))


def _rare_vs_common(a: int, b: int) -> bool:
    """Imlo xatosi kam uchraydi: kamroq shakl ≤ 2 marta va boshqasidan kamida 2 baravar kam."""
    low, high = sorted((a, b))
    return low <= 2 and high >= 2 * low


def bcubed(predicted: Mapping[str, str], gold: Mapping[str, str], weights: Mapping[str, int] | None = None) -> dict:
    """B-cubed P/R/F1 (Bagga, Baldwin, 1998): har bir element uchun o'z klasteridagi to'g'ri qo'shnilar ulushi."""
    items = [x for x in gold if x in predicted]
    weights = weights or {x: 1 for x in items}
    pred_clusters: dict[str, set] = defaultdict(set)
    gold_clusters: dict[str, set] = defaultdict(set)
    for x in items:
        pred_clusters[predicted[x]].add(x)
        gold_clusters[gold[x]].add(x)
    total = sum(weights[x] for x in items) or 1
    precision = recall = 0.0
    for x in items:
        p, g = pred_clusters[predicted[x]], gold_clusters[gold[x]]
        both = p & g
        precision += weights[x] * sum(weights[y] for y in both) / sum(weights[y] for y in p)
        recall += weights[x] * sum(weights[y] for y in both) / sum(weights[y] for y in g)
    precision, recall = precision / total, recall / total
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "items": len(items)}
