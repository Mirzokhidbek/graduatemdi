"""Datasetni train/validation/test to'plamlariga manba (``doc_id``) darajasida ajratish.

Qoidalar:
- bitta manbaning barcha yozuvlari bitta to'plamga tushadi;
- bir xil matn (``duplicate_key``) uchragan manbalar bitta guruhga
  birlashtiriladi, shunda takroriy matn turli to'plamlarga tushmaydi;
- taqsimot ``manifest`` faylida saqlanadi va **muzlatiladi**: qayta
  ishga tushirilganda avval ajratilgan manbalar o'z to'plamida qoladi,
  faqat yangi manbalar taqsimlanadi. Shu sababli test to'plami dataset
  o'sganda ham o'zgarmaydi;
- yangi guruhlar maqsadli nisbatga eng ko'p yetishmayotgan to'plamga
  beriladi. Og'irlik — spanlar soni. Tasodifiylik yo'q, natija
  kiruvchi fayllar tartibiga bog'liq emas.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from app.dataset.annotation import AnnotatedRecord, duplicate_key

TRAIN, VALIDATION, TEST = "train", "validation", "test"
SPLITS = (TRAIN, VALIDATION, TEST)
DEFAULT_RATIOS = (0.7, 0.15, 0.15)
MANIFEST_VERSION = 1


class SplitError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        details = "\n".join(f"- {p}" for p in problems)
        super().__init__(f"Ajratishda xatolar:\n{details}")


@dataclass(frozen=True)
class DocGroup:
    doc_ids: tuple[str, ...]  # tartiblangan
    records: tuple[AnnotatedRecord, ...]

    @property
    def key(self) -> str:
        return self.doc_ids[0]

    @property
    def weight(self) -> int:
        return max(1, sum(len(record.terms) for record in self.records))


def validate_ratios(ratios: Sequence[float]) -> tuple[float, float, float]:
    if len(ratios) != len(SPLITS):
        raise SplitError([f"{len(SPLITS)} ta nisbat kerak: train validation test"])
    if any(not math.isfinite(r) or r < 0 for r in ratios):
        raise SplitError(["nisbatlar manfiy bo'lmagan son bo'lishi kerak"])
    if not math.isclose(sum(ratios), 1.0, abs_tol=1e-6):
        raise SplitError([f"nisbatlar yig'indisi 1 bo'lishi kerak (hozir {sum(ratios):g})"])
    if ratios[0] == 0 or ratios[2] == 0:
        raise SplitError(["train va test nisbati 0 dan katta bo'lishi kerak"])
    return tuple(float(r) for r in ratios)  # type: ignore[return-value]


def group_documents(records: Iterable[AnnotatedRecord]) -> list[DocGroup]:
    """Manbalarni guruhlaydi: umumiy (takroriy) matnga ega manbalar birlashtiriladi."""
    parent: dict[str, str] = {}

    def find(doc_id: str) -> str:
        while parent[doc_id] != doc_id:
            parent[doc_id] = parent[parent[doc_id]]
            doc_id = parent[doc_id]
        return doc_id

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[max(root_a, root_b)] = min(root_a, root_b)

    records = list(records)
    owner_of_text: dict[str, str] = {}
    for record in records:
        parent.setdefault(record.doc_id, record.doc_id)
        key = duplicate_key(record.text)
        if key in owner_of_text:
            union(owner_of_text[key], record.doc_id)
        else:
            owner_of_text[key] = record.doc_id

    members: dict[str, list[AnnotatedRecord]] = {}
    for record in records:
        members.setdefault(find(record.doc_id), []).append(record)

    groups = []
    for group_records in members.values():
        doc_ids = tuple(sorted({record.doc_id for record in group_records}))
        ordered = tuple(sorted(group_records, key=lambda r: (r.doc_id, r.id)))
        groups.append(DocGroup(doc_ids, ordered))
    return sorted(groups, key=lambda group: group.key)


def assign_splits(
    groups: Sequence[DocGroup],
    frozen: dict[str, str],
    ratios: Sequence[float] = DEFAULT_RATIOS,
) -> dict[str, str]:
    """Har bir ``doc_id`` uchun to'plamni qaytaradi (muzlatilganlari o'zgarmaydi)."""
    ratios = validate_ratios(ratios)
    assignments = dict(frozen)
    current = dict.fromkeys(SPLITS, 0)
    problems: list[str] = []
    new_groups: list[DocGroup] = []

    for group in groups:
        known = {frozen[doc_id] for doc_id in group.doc_ids if doc_id in frozen}
        if len(known) > 1:
            details = ", ".join(f"{d}={frozen[d]}" for d in group.doc_ids if d in frozen)
            problems.append(
                f"takroriy matnli manbalar turli to'plamlarda muzlatilgan ({details}); "
                "takroriy matnni olib tashlang yoki manifestni qo'lda tuzating"
            )
        elif known:
            split = known.pop()
            for doc_id in group.doc_ids:
                assignments[doc_id] = split
            current[split] += group.weight
        else:
            new_groups.append(group)

    if problems:
        raise SplitError(problems)

    for group in sorted(new_groups, key=lambda g: (-g.weight, g.key)):
        total = sum(current.values()) + group.weight
        deficits = [ratio * total - current[split] for split, ratio in zip(SPLITS, ratios)]
        split = SPLITS[deficits.index(max(deficits))]
        for doc_id in group.doc_ids:
            assignments[doc_id] = split
        current[split] += group.weight

    return assignments


def build_splits(
    records: Iterable[AnnotatedRecord], assignments: dict[str, str]
) -> dict[str, list[AnnotatedRecord]]:
    result: dict[str, list[AnnotatedRecord]] = {split: [] for split in SPLITS}
    for record in sorted(records, key=lambda r: (r.doc_id, r.id)):
        result[assignments[record.doc_id]].append(record)
    return result


def load_manifest(path: str | Path) -> tuple[dict[str, str], tuple[float, float, float] | None]:
    """Manifestdan ``doc_id -> to'plam`` taqsimoti va nisbatlarni o'qiydi.

    Fayl bo'lmasa — bo'sh taqsimot va ``None``.
    """
    path = Path(path)
    if not path.exists():
        return {}, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SplitError([f"{path}: JSON xatosi: {exc}"]) from None

    if not isinstance(raw, dict) or not isinstance(raw.get("assignments"), dict):
        raise SplitError([f"{path}: 'assignments' obyekti bo'lishi kerak"])
    if raw.get("version") != MANIFEST_VERSION:
        raise SplitError([f"{path}: noma'lum manifest versiyasi: {raw.get('version')!r}"])

    problems = [
        f"{path}: '{doc_id}' uchun noto'g'ri to'plam: {split!r}"
        for doc_id, split in raw["assignments"].items()
        if split not in SPLITS
    ]
    ratios = raw.get("ratios")
    if isinstance(ratios, dict) and set(ratios) == set(SPLITS):
        try:
            parsed_ratios = validate_ratios([ratios[split] for split in SPLITS])
        except (SplitError, TypeError):
            parsed_ratios = None
    else:
        parsed_ratios = None
    if parsed_ratios is None:
        problems.append(f"{path}: 'ratios' noto'g'ri: {ratios!r}")

    if problems:
        raise SplitError(problems)
    return dict(raw["assignments"]), parsed_ratios


def manifest_to_dict(assignments: dict[str, str], ratios: Sequence[float]) -> dict[str, Any]:
    return {
        "version": MANIFEST_VERSION,
        "ratios": dict(zip(SPLITS, ratios)),
        "assignments": dict(sorted(assignments.items())),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from app.dataset.annotation import STATUS_REVIEWED, record_to_dict, validate_files
    from app.dataset.sources import SourceRegistryError, load_sources
    from app.dataset.validate import DEFAULT_ANNOTATED_DIR, DEFAULT_SOURCES, REPO_ROOT

    parser = argparse.ArgumentParser(
        description="Datasetni manba darajasida train/validation/test ga ajratish"
    )
    parser.add_argument("files", nargs="*", type=Path, help="JSONL fayllar (standart: data/annotated/*.jsonl)")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "data" / "splits" / "manifest.json")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "data" / "processed")
    parser.add_argument(
        "--ratios", type=float, nargs=3, metavar=("TRAIN", "VAL", "TEST"),
        help=f"yangi manbalar uchun nisbatlar (standart: manifestdagi yoki {' '.join(map(str, DEFAULT_RATIOS))})",
    )
    parser.add_argument("--include-drafts", action="store_true", help="'draft' yozuvlarni ham qo'shish")
    parser.add_argument("--dry-run", action="store_true", help="faqat ko'rsatish, hech narsa yozmaslik")
    args = parser.parse_args(argv)

    try:
        source_ids = {source.id for source in load_sources(args.sources)}
        frozen, manifest_ratios = load_manifest(args.manifest)
        ratios = validate_ratios(args.ratios) if args.ratios else manifest_ratios or DEFAULT_RATIOS
    except (SourceRegistryError, SplitError) as exc:
        print(exc, file=sys.stderr)
        return 1

    files = args.files or sorted(DEFAULT_ANNOTATED_DIR.glob("*.jsonl"))
    report = validate_files(files, source_ids)
    if not report.ok:
        print(f"Annotatsiyada xatolar ({len(report.errors)}); avval tuzating:", file=sys.stderr)
        for issue in report.errors:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    records = [r for r in report.records if args.include_drafts or r.status == STATUS_REVIEWED]
    skipped = len(report.records) - len(records)
    if skipped:
        print(f"'draft' holatidagi {skipped} ta yozuv kiritilmadi (--include-drafts bilan qo'shish mumkin).")
    if not records:
        print("Ajratish uchun yozuv yo'q.")
        return 0

    try:
        assignments = assign_splits(group_documents(records), frozen, ratios)
    except SplitError as exc:
        print(exc, file=sys.stderr)
        return 1
    splits = build_splits(records, assignments)

    present = {record.doc_id for record in records}
    new_docs = sorted(present - set(frozen))
    total_spans = sum(len(r.terms) for r in records)
    print("Nisbatlar: " + ", ".join(f"{s}={r:g}" for s, r in zip(SPLITS, ratios)))
    print(f"Yangi taqsimlangan manbalar: {len(new_docs)}, muzlatilgan: {len(present) - len(new_docs)}")
    print(f"{"to'plam":<11} {'manba':>6} {'yozuv':>6} {'span':>6} {'span ulushi':>12}")
    for split in SPLITS:
        split_records = splits[split]
        spans = sum(len(r.terms) for r in split_records)
        share = spans / total_spans if total_spans else 0.0
        docs = len({r.doc_id for r in split_records})
        print(f"{split:<11} {docs:>6} {len(split_records):>6} {spans:>6} {share:>12.1%}")
        if not split_records:
            print(f"  ogohlantirish: '{split}' to'plami bo'sh — manbalar soni yetarli emas")
    missing = sorted(set(frozen) - present)
    if missing:
        print(f"Ogohlantirish: manifestdagi {len(missing)} ta manba datasetda yo'q, taqsimoti saqlanadi.")

    if args.dry_run:
        print("\n--dry-run: hech narsa yozilmadi.")
        return 0

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest_to_dict(assignments, ratios), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        lines = "".join(json.dumps(record_to_dict(r), ensure_ascii=False) + "\n" for r in splits[split])
        (args.output_dir / f"{split}.jsonl").write_text(lines, encoding="utf-8")
    print(f"\nManifest: {args.manifest}\nTo'plamlar: {args.output_dir}/{{{','.join(SPLITS)}}}.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
