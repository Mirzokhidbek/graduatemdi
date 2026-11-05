"""Terminning meʼyoriy talablarga muvofiqligini avtomatik tekshirish (3.2-bo'lim).

Tekshiruv — qoidaviy (ekspert) model. Har bir qoida natijasi: ``ok``, ``info``,
``warning`` yoki ``error`` va izoh, kerak bo'lsa tuzatish taklifi bilan.
Qoidalar ikki manbaga asoslanadi.

**A. Termin yaratish tamoyillari** (ISO 704:2022, 7-bo'lim; ISO 1087:2019 taʼriflari):

| Qoida | Tamoyil | Tekshiruv |
|---|---|---|
| ``monosemy`` | bir maʼnolilik | shakl bazada bir nechta yozuvga tegishlimi; umumiy so'z bilan omonimmi |
| ``synonymy`` | sinonimsizlik (bitta tushuncha — bitta termin) | yozuvda sinonim/dublet bormi |
| ``conciseness`` | lisoniy tejamkorlik (qisqalik) | so'zlar soni (> 3 — ogohlantirish, > 5 — xato) |
| ``derivability`` | yasalish imkoniyati | ko'p so'zli termindan yangi so'z yasash qiyin (≥ 3 so'z — izoh) |
| ``systematicity`` | tizimlilik va shaffoflik | ko'p so'zli terminning bosh so'zi bazada termin sifatida bormi |
| ``native_form`` | ona tilidagi shaklni afzal ko'rish | xalqaro termin uchun bazada o'zbekcha muqobil bormi |

**B. Oʻzbek tilining asosiy imlo qoidalari** (Vazirlar Mahkamasining 1995-yil 24-avgustdagi
339-son qarori) va lug'at shakli talablari:

| Qoida | Tekshiruv |
|---|---|
| ``script`` | faqat lotin yozuvi; kirill yoki aralash yozuv — xato |
| ``alphabet`` | oʻzbek lotin alifbosida yo'q harflar (*c* (*ch* dan tashqari), *w*, *ş*, *ç*, *ı*, *ä* ...) |
| ``apostrophe`` | *oʻ, gʻ* — ``ʻ`` (U+02BB), tutuq belgisi — ``ʼ`` (U+02BC); boshqa belgilar — ogohlantirish |
| ``ts_rule`` | *ц* o'rnida: so'z boshida va undoshdan keyin *s*, unlidan keyin *ts* (*sirk*, *aksiya*, *militsiya*) |
| ``lowercase`` | termin kichik harf bilan yoziladi (atoqli ot bo'lmasa) |
| ``spacing`` | ortiqcha bo'shliq, defis atrofida bo'shliq |
| ``dictionary_form`` | lug'at shakli: ko'plik va kelishik qo'shimchasisiz (*fonemalar* → *fonema*) |

Natija tavsiya xarakterida: qoidalar meʼyoriy qarorni almashtirmaydi, faqat ekspert
eʼtiborini kerakli joyga qaratadi.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Iterable

from app.database.term_store import TermEntry
from app.nlp.clean import canonical_apostrophes
from app.nlp.normalize import APOSTROPHE_VARIANTS, normalize_form
from app.nlp.tokenize import tokenize
from app.services.term_normalizer import TermNormalizer
from app.variation.orthography import fix_mixed_script, has_cyrillic, has_mixed_script, to_latin
from app.variation.synonyms import is_international

OK, INFO, WARNING, ERROR = "ok", "info", "warning", "error"
SEVERITY_ORDER = {OK: 0, INFO: 1, WARNING: 2, ERROR: 3}

ISO = "ISO 704:2022"
IMLO = "Imlo qoidalari (1995)"
LEX = "Lug'at shakli"

# Train annotatsiyasida ham termin, ham umumiy maʼnoda uchragan so'zlar (3.1.3, omonimiya tajribasi)
# va bazaga ataylab kiritilmagan ko'p maʼnoli so'zlar (docs/project-plan.md, 1-bosqich cheklovlari).
POLYSEMOUS = frozenset(
    normalize_form(w)
    for w in (
        "birlik", "ega", "harf", "hol", "lugʻat", "obyekt", "qoʻshimcha", "ravish", "sifat", "son", "tovush",
        "leksika", "ot", "gap", "kesim", "asos", "belgi", "shakl", "maʼno", "soʻz", "til", "tur",
    )
)
UZBEK_LETTERS = set("abcdefghijklmnopqrstuvxyz") | {"ʻ", "ʼ"}  # "c" faqat "ch" ichida (alohida tekshiriladi)
_TS_BAD = re.compile(r"(?:^|(?<=[^aeiouʻ\W]))ts", re.IGNORECASE)  # so'z boshida yoki undoshdan keyin


@dataclass(frozen=True)
class Finding:
    rule: str
    basis: str
    severity: str
    message: str
    suggestion: str | None = None


@dataclass
class CheckResult:
    term: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def severity(self) -> str:
        return max((f.severity for f in self.findings), key=SEVERITY_ORDER.__getitem__, default=OK)

    @property
    def suggestion(self) -> str | None:
        """Imlo va lug'at shakli tuzatishlari ketma-ket qo'llangan shakl (o'zgarish bo'lsa)."""
        fixes = [f.suggestion for f in self.findings if f.suggestion and f.rule in _FORM_RULES]
        return fixes[-1] if fixes else None

    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "severity": self.severity,
            "suggestion": self.suggestion,
            "findings": [asdict(f) for f in self.findings],
        }


_FORM_RULES = ("script", "apostrophe", "ts_rule", "lowercase", "spacing", "dictionary_form")


class TermChecker:
    def __init__(
        self,
        entries: Iterable[TermEntry] = (),
        vocabulary: Iterable[str] = (),
        polysemous: Iterable[str] = POLYSEMOUS,
    ) -> None:
        self.entries = list(entries)
        self.polysemous = frozenset(polysemous)
        self.normalizer = TermNormalizer(self.entries, vocabulary)
        self.by_form: dict[str, list[TermEntry]] = defaultdict(list)
        for entry in self.entries:
            for form in {entry.term, *entry.variants, *entry.synonyms}:
                self.by_form[normalize_form(form)].append(entry)

    # --- B. imlo va lug'at shakli -------------------------------------------------

    def _orthography(self, term: str, out: list[Finding]) -> str:
        """Imlo qoidalarini tekshiradi va tuzatilgan shaklni qaytaradi."""
        fixed = term
        if has_cyrillic(term):
            kind = "aralash yozuv (kirill va lotin harflari bitta so'zda)" if any(
                has_mixed_script(w) for w in term.split()
            ) else "kirill yozuvi"
            fixed = to_latin(fix_mixed_script(term))
            out.append(Finding("script", IMLO, ERROR, f"{kind}: termin lotin yozuvida berilishi kerak", fixed))
        stray = sorted({ch for ch in fixed.lower() if ch.isalpha() and ch not in UZBEK_LETTERS})
        letters = re.sub(r"ch", "", fixed.lower())
        if "c" in letters and "c" not in stray:
            stray.append("c")
        if "w" in letters and "w" not in stray:
            stray.append("w")
        if stray:
            out.append(Finding("alphabet", IMLO, ERROR,
                               f"oʻzbek lotin alifbosida yo'q harf(lar): {', '.join(sorted(set(stray)))}"))
        if any(ch in APOSTROPHE_VARIANTS and ch not in "ʻʼ" for ch in fixed):
            canonical = canonical_apostrophes(fixed)
            out.append(Finding("apostrophe", IMLO, WARNING,
                               "rasmiy belgilar: oʻ, gʻ uchun ʻ (U+02BB), tutuq belgisi uchun ʼ (U+02BC)", canonical))
            fixed = canonical
        bad_ts = [w for w in fixed.split() if _TS_BAD.search(w)]
        if bad_ts:
            corrected = " ".join(_TS_BAD.sub("s", w) for w in fixed.split())
            out.append(Finding("ts_rule", IMLO, WARNING,
                               "ц o'rnida so'z boshida va undoshdan keyin «s» yoziladi (sirk, aksiya)", corrected))
            fixed = corrected
        if fixed[:1].isupper() and not fixed.isupper():
            lowered = fixed[:1].lower() + fixed[1:]
            out.append(Finding("lowercase", IMLO, INFO,
                               "termin kichik harf bilan yoziladi (atoqli ot bo'lmasa)", lowered))
            fixed = lowered
        if "  " in fixed or re.search(r"\s-|-\s", fixed) or fixed != fixed.strip():
            spaced = re.sub(r"\s*-\s*", "-", " ".join(fixed.split()))
            out.append(Finding("spacing", IMLO, WARNING, "ortiqcha bo'shliq yoki defis atrofida bo'shliq", spaced))
            fixed = spaced
        return unicodedata.normalize("NFC", fixed)

    def _dictionary_form(self, term: str, out: list[Finding]) -> None:
        result = self.normalizer.normalize(term)
        lemma = result.lemma
        if normalize_form(lemma) != normalize_form(term) and result.method != "unchanged":
            out.append(Finding("dictionary_form", LEX, WARNING,
                               "termin lug'at shaklida berilishi kerak (ko'plik va kelishik qo'shimchasisiz)", lemma))

    # --- A. ISO 704 tamoyillari ----------------------------------------------------

    def _principles(self, term: str, out: list[Finding]) -> None:
        norm = normalize_form(term)
        words = [t.norm for t in tokenize(term)]
        owners = {e.id: e for e in self.by_form.get(norm, [])}
        if len(owners) > 1:
            out.append(Finding("monosemy", ISO, WARNING,
                               f"shakl bazada {len(owners)} ta yozuvga tegishli (omonimiya): "
                               + ", ".join(sorted(e.term for e in owners.values()))))
        elif len(words) == 1 and norm in self.polysemous:
            out.append(Finding("monosemy", ISO, INFO,
                               "so'z umumiy maʼnoda ham ishlatiladi — matnda kontekst bo'yicha tekshirish kerak"))

        entry = next(iter(owners.values()), None) if len(owners) == 1 else None
        if entry is not None:
            others = sorted(
                f for f in {*entry.synonyms, entry.term} if normalize_form(f) != norm
            )
            if others:
                kinds = [
                    "dublet" if is_international(o.split()[-1]) != is_international(words[-1]) else "sinonim"
                    for o in others
                ]
                out.append(Finding("synonymy", ISO, WARNING,
                                   "bitta tushuncha uchun bir nechta termin: "
                                   + ", ".join(f"{o} ({k})" for o, k in zip(others, kinds))
                                   + " — bittasi meʼyoriy deb belgilanishi kerak"))
            if words and is_international(words[-1]):
                native = [s for s in entry.synonyms if not is_international(s.split()[-1])]
                if native:
                    out.append(Finding("native_form", ISO, INFO,
                                       "xalqaro termin; bazada oʻzbekcha muqobil bor: " + ", ".join(native)))

        if len(words) > 5:
            out.append(Finding("conciseness", ISO, ERROR, f"termin juda uzun ({len(words)} so'z)"))
        elif len(words) > 3:
            out.append(Finding("conciseness", ISO, WARNING, f"termin uzun ({len(words)} so'z), qisqaroq shakl izlash kerak"))
        if len(words) >= 3:
            out.append(Finding("derivability", ISO, INFO, "ko'p so'zli termindan yangi so'z yasash qiyin"))
        if len(words) >= 2:
            head = words[-1]
            head_lemma = normalize_form(self.normalizer.normalize(head).lemma)
            heads = {head, head_lemma}
            for n in range(1, len(words)):
                heads.add(" ".join(words[n:]))
            if not any(h in self.by_form for h in heads):
                out.append(Finding("systematicity", ISO, INFO,
                                   f"bosh so'z («{head_lemma}») bazada alohida termin sifatida yo'q — "
                                   "termin tizimdagi o'rnini tekshirish kerak"))

    def check(self, term: str) -> CheckResult:
        result = CheckResult(term)
        if not term or not any(ch.isalpha() for ch in term):
            result.findings.append(Finding("script", IMLO, ERROR, "termin kamida bitta harfdan iborat bo'lishi kerak"))
            return result
        fixed = self._orthography(term, result.findings)
        self._dictionary_form(fixed, result.findings)
        self._principles(fixed, result.findings)
        return result


def summarize(results: Iterable[CheckResult]) -> dict:
    results = list(results)
    by_rule: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        for f in r.findings:
            by_rule[f.rule][f.severity] += 1
    severity = defaultdict(int)
    for r in results:
        severity[r.severity] += 1
    return {
        "terms": len(results),
        "by_severity": dict(severity),
        "by_rule": {rule: dict(v) for rule, v in sorted(by_rule.items())},
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import csv
    import json
    import random
    from pathlib import Path

    from app.database.term_store import load_terms
    from app.dataset.validate import REPO_ROOT

    parser = argparse.ArgumentParser(description="Terminlarni meʼyoriy talablarga muvofiqlikka tekshirish")
    parser.add_argument("terms", nargs="*", help="tekshiriladigan terminlar (bo'lmasa — butun baza)")
    parser.add_argument("--base", type=Path, default=REPO_ROOT / "data" / "terms.json")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--output", type=Path, help="JSON hisobot")
    parser.add_argument("--review-sample", type=Path, help="ekspert bahosi uchun tasodifiy namuna (CSV)")
    parser.add_argument("--sample-size", type=int, default=100)
    args = parser.parse_args(argv)

    entries = load_terms(args.base)
    vocabulary = [t.norm for p in sorted(args.raw.glob("*.txt")) for t in tokenize(p.read_text(encoding="utf-8"))]
    checker = TermChecker(entries, vocabulary)
    terms = args.terms or [e.term for e in entries]
    results = [checker.check(t) for t in terms]

    if args.terms:
        for r in results:
            print(f"{r.term}: {r.severity}" + (f" -> {r.suggestion}" if r.suggestion else ""))
            for f in r.findings:
                print(f"   [{f.severity}] {f.rule} ({f.basis}): {f.message}" + (f" => {f.suggestion}" if f.suggestion else ""))
    summary = summarize(results)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": summary, "results": [r.to_dict() for r in results]}
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.review_sample:
        existing = {}
        if args.review_sample.is_file():
            with args.review_sample.open(encoding="utf-8-sig", newline="") as handle:
                existing = {row["term"]: row for row in csv.DictReader(handle)}
        sample = random.Random(13).sample(results, min(args.sample_size, len(results)))
        with args.review_sample.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["term", "system", "expert", "notes", "findings"])
            writer.writeheader()
            for r in sample:
                old = existing.get(r.term, {})
                writer.writerow({
                    "term": r.term,
                    "system": r.severity,
                    "expert": old.get("expert", ""),
                    "notes": old.get("notes", ""),
                    "findings": "; ".join(f"{f.rule}:{f.severity}" for f in r.findings if f.severity != OK),
                })
        print(f"Ekspert namunasi: {args.review_sample}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
