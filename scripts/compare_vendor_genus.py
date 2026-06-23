from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path


DESKTOP = Path("/Users/krishnaiitm/Desktop")
VENDOR_ROOT = DESKTOP / "Metagenoics data"
OUR_ROOT = DESKTOP / "relaxed_runs_of_samples"
OUT_DIR = DESKTOP / "genus_comparison_analysis"

SAMPLES = [
    {
        "sample": "Borewell1",
        "vendor": VENDOR_ROOT / "borewell1" / "16sBowerwellB1_S6.summary.csv",
        "ours": OUR_ROOT / "16sBowerwellB1_S7_relaxed_taxonomy_long.csv",
    },
    {
        "sample": "Borewell2",
        "vendor": VENDOR_ROOT / "Borewell2" / "16sBowerwellB2_S5.summary.csv",
        "ours": OUR_ROOT / "16sBowerwellB2_S8_relaxed_taxonomy_long.csv",
    },
    {
        "sample": "NTC Bottle",
        "vendor": VENDOR_ROOT / "NTC 1" / "16sNtcBottle_S4.summary.csv",
        "ours": OUR_ROOT / "16sNtcBottle_S13_relaxed_taxonomy_long.csv",
    },
    {
        "sample": "River",
        "vendor": VENDOR_ROOT / "River" / "16sRiverB5_S1.summary.csv",
        "ours": OUR_ROOT / "16sRiverB5_S11_relaxed_taxonomy_long.csv",
    },
    {
        "sample": "OpenTank1",
        "vendor": VENDOR_ROOT / "opentank" / "16sOpenTank1B3_S3.summary.csv",
        "ours": OUR_ROOT / "16sOpenTank1B3_S9_relaxed_taxonomy_long.csv",
    },
    {
        "sample": "OpenTank2",
        "vendor": VENDOR_ROOT / "opentank2" / "16sOpenTank2B4_S2.summary.csv",
        "ours": OUR_ROOT / "16sOpenTank2B4_S10_relaxed_taxonomy_long.csv",
    },
]

UNCLASSIFIED = "Unclassified at genus"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overview_rows = []
    all_rows = []
    top_rows = []

    for item in SAMPLES:
        sample = item["sample"]
        vendor_counts = read_vendor_genus_counts(item["vendor"])
        our_counts = read_our_genus_counts(item["ours"], database="Greengenes2")
        comparison = compare_counts(sample, vendor_counts, our_counts)
        overview_rows.append(comparison["overview"])
        all_rows.extend(comparison["all_rows"])
        top_rows.extend(comparison["top_rows"])

    write_csv(OUT_DIR / "genus_comparison_overview.csv", overview_rows)
    write_csv(OUT_DIR / "genus_comparison_all_genera.csv", all_rows)
    write_csv(OUT_DIR / "genus_comparison_top20_by_sample.csv", top_rows)
    write_markdown_summary(OUT_DIR / "genus_comparison_summary.md", overview_rows, top_rows)
    print(f"Wrote comparison outputs to {OUT_DIR}")


def read_vendor_genus_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            reads = int(float(row.get("num_hits") or 0))
            genus = normalize_genus(row.get("Genus", ""))
            if not genus:
                genus = UNCLASSIFIED
            counts[genus] += reads
    return dict(counts)


def read_our_genus_counts(path: Path, database: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    seen_asvs = set()
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("database") != database:
                continue
            asv_id = row.get("asv_id", "")
            if asv_id in seen_asvs:
                continue
            seen_asvs.add(asv_id)
            reads = int(float(row.get("reads") or 0))
            genus = normalize_genus(row.get("genus", ""))
            if not genus:
                genus = UNCLASSIFIED
            counts[genus] += reads
    return dict(counts)


def normalize_genus(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+\(\d+(?:\.\d+)?\)$", "", value)
    value = value.strip("; ")
    value = re.sub(r"^[a-z]__", "", value)
    value = re.sub(r"_\d+$", "", value)
    if value.lower() in {"", "unclassified", "na", "none"}:
        return ""
    return value


def compare_counts(sample: str, vendor: dict[str, int], ours: dict[str, int]) -> dict[str, object]:
    vendor_total = sum(vendor.values())
    our_total = sum(ours.values())
    genera = sorted(set(vendor) | set(ours))
    rows = []
    for genus in genera:
        vendor_reads = vendor.get(genus, 0)
        our_reads = ours.get(genus, 0)
        vendor_pct = pct(vendor_reads, vendor_total)
        our_pct = pct(our_reads, our_total)
        rows.append(
            {
                "sample": sample,
                "genus": genus,
                "vendor_reads": vendor_reads,
                "vendor_pct": round(vendor_pct, 6),
                "our_reads": our_reads,
                "our_pct": round(our_pct, 6),
                "pct_difference_our_minus_vendor": round(our_pct - vendor_pct, 6),
                "present_in_vendor": "yes" if vendor_reads else "no",
                "present_in_ours": "yes" if our_reads else "no",
            }
        )

    top_rows = [
        dict(row)
        for row in sorted(rows, key=lambda r: max(float(r["vendor_pct"]), float(r["our_pct"])), reverse=True)[:20]
    ]
    for rank, row in enumerate(top_rows, start=1):
        row["rank_by_max_pct"] = rank

    overview = {
        "sample": sample,
        "vendor_total_reads": vendor_total,
        "our_total_reads": our_total,
        "vendor_genera_including_unclassified": len(vendor),
        "our_genera_including_unclassified": len(ours),
        "shared_genera_including_unclassified": len(set(vendor) & set(ours)),
        "bray_curtis_similarity_including_unclassified": round(bray_similarity(vendor, ours), 6),
        "bray_curtis_similarity_classified_only": round(
            bray_similarity(without_unclassified(vendor), without_unclassified(ours)), 6
        ),
        "vendor_unclassified_genus_pct": round(pct(vendor.get(UNCLASSIFIED, 0), vendor_total), 6),
        "our_unclassified_genus_pct": round(pct(ours.get(UNCLASSIFIED, 0), our_total), 6),
        "top_vendor_genus": top_genus(vendor),
        "top_our_genus": top_genus(ours),
    }
    return {"overview": overview, "all_rows": rows, "top_rows": top_rows}


def pct(reads: int, total: int) -> float:
    return (reads / total * 100.0) if total else 0.0


def bray_similarity(a: dict[str, int], b: dict[str, int]) -> float:
    total_a = sum(a.values())
    total_b = sum(b.values())
    if not total_a and not total_b:
        return 1.0
    if not total_a or not total_b:
        return 0.0
    genera = set(a) | set(b)
    l1 = sum(abs(a.get(g, 0) / total_a - b.get(g, 0) / total_b) for g in genera)
    return max(0.0, 1.0 - 0.5 * l1)


def without_unclassified(counts: dict[str, int]) -> dict[str, int]:
    return {key: value for key, value in counts.items() if key != UNCLASSIFIED}


def top_genus(counts: dict[str, int]) -> str:
    classified = without_unclassified(counts)
    if not classified:
        return ""
    genus, reads = max(classified.items(), key=lambda item: item[1])
    return f"{genus} ({pct(reads, sum(counts.values())):.2f}%)"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields = list(rows[0].keys())
    with path.open("wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_summary(path: Path, overview_rows: list[dict[str, object]], top_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Genus-Level Comparison Analysis",
        "",
        "Comparison source:",
        "- Vendor result: Desktop/Metagenoics data/*/*.summary.csv",
        "- Our result: Desktop/relaxed_runs_of_samples/*_relaxed_taxonomy_long.csv",
        "- Our taxonomy source used for the comparison: Greengenes2",
        "- Scope: genus level, with blank genus values grouped as 'Unclassified at genus'",
        "",
        "## Overview",
        "",
        "| Sample | Vendor reads | Our reads | Vendor genus unclassified % | Our genus unclassified % | Shared genera | Bray-Curtis similarity | Classified-only similarity | Top vendor genus | Top our genus |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in overview_rows:
        lines.append(
            "| {sample} | {vendor_total_reads} | {our_total_reads} | {vendor_unclassified_genus_pct:.2f} | "
            "{our_unclassified_genus_pct:.2f} | {shared_genera_including_unclassified} | "
            "{bray_curtis_similarity_including_unclassified:.3f} | {bray_curtis_similarity_classified_only:.3f} | "
            "{top_vendor_genus} | {top_our_genus} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- The vendor reports use an older Greengenes-style taxonomy summary, while our closest comparable source is Greengenes2.",
            "- Genus names are normalized lightly by removing bootstrap values and Greengenes2 numeric suffixes.",
            "- High unclassified percentages can dominate similarity metrics, so the classified-only similarity is included separately.",
            "- Exact genus agreement should be interpreted cautiously because database versions and naming conventions differ.",
            "",
            "## Top Genus Differences",
            "",
        ]
    )
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in top_rows:
        grouped[str(row["sample"])].append(row)
    for sample, rows in grouped.items():
        lines.extend([f"### {sample}", "", "| Genus | Vendor % | Our % | Difference |", "|---|---:|---:|---:|"])
        for row in rows[:10]:
            lines.append(
                "| {genus} | {vendor_pct:.2f} | {our_pct:.2f} | {pct_difference_our_minus_vendor:.2f} |".format(**row)
            )
        lines.append("")

    path.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
