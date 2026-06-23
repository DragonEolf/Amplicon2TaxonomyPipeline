from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


DESKTOP = Path("/Users/krishnaiitm/Desktop")
VENDOR_ROOT = DESKTOP / "Metagenoics data"
OUR_ROOT = DESKTOP / "relaxed_runs_of_samples"
OUT_DIR = DESKTOP / "greengenes_taxon_count_comparison"

RANKS = ["family", "genus", "species"]

SAMPLES = [
    (
        VENDOR_ROOT / "borewell1" / "16sBowerwellB1_S6.summary.csv",
        OUR_ROOT / "16sBowerwellB1_S7_relaxed_taxonomy_long.csv",
    ),
    (
        VENDOR_ROOT / "Borewell2" / "16sBowerwellB2_S5.summary.csv",
        OUR_ROOT / "16sBowerwellB2_S8_relaxed_taxonomy_long.csv",
    ),
    (
        VENDOR_ROOT / "NTC 1" / "16sNtcBottle_S4.summary.csv",
        OUR_ROOT / "16sNtcBottle_S13_relaxed_taxonomy_long.csv",
    ),
    (
        VENDOR_ROOT / "River" / "16sRiverB5_S1.summary.csv",
        OUR_ROOT / "16sRiverB5_S11_relaxed_taxonomy_long.csv",
    ),
    (
        VENDOR_ROOT / "opentank" / "16sOpenTank1B3_S3.summary.csv",
        OUR_ROOT / "16sOpenTank1B3_S9_relaxed_taxonomy_long.csv",
    ),
    (
        VENDOR_ROOT / "opentank2" / "16sOpenTank2B4_S2.summary.csv",
        OUR_ROOT / "16sOpenTank2B4_S10_relaxed_taxonomy_long.csv",
    ),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rank in RANKS:
        their_counts: dict[str, int] = defaultdict(int)
        our_counts: dict[str, int] = defaultdict(int)
        for vendor_csv, our_csv in SAMPLES:
            add_vendor_counts(vendor_csv, rank, their_counts)
            add_our_counts(our_csv, rank, our_counts)
        write_comparison(rank, our_counts, their_counts)
    print(f"Wrote taxon count comparisons to {OUT_DIR}")


def add_vendor_counts(path: Path, rank: str, counts: dict[str, int]) -> None:
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            reads = int(float(row.get("num_hits") or 0))
            taxon = vendor_taxon(row, rank)
            counts[taxon] += reads


def add_our_counts(path: Path, rank: str, counts: dict[str, int]) -> None:
    seen_asvs = set()
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("database") != "Greengenes2":
                continue
            asv_id = row.get("asv_id", "")
            if asv_id in seen_asvs:
                continue
            seen_asvs.add(asv_id)
            reads = int(float(row.get("reads") or 0))
            taxon = our_taxon(row, rank)
            counts[taxon] += reads


def vendor_taxon(row: dict[str, str], rank: str) -> str:
    if rank == "species":
        genus = clean_taxon(row.get("Genus", ""))
        species = clean_species(row.get("Species", ""))
        if species and genus and not species.lower().startswith(genus.lower()):
            return f"{genus} {species}"
        return species or "Unclassified"
    return clean_taxon(row.get(rank.title(), "")) or "Unclassified"


def our_taxon(row: dict[str, str], rank: str) -> str:
    if rank == "species":
        genus = clean_taxon(row.get("genus", ""))
        species = clean_species(row.get("species", ""))
        if species and genus and not species.lower().startswith(genus.lower()):
            return f"{genus} {species}"
        return species or "Unclassified"
    return clean_taxon(row.get(rank, "")) or "Unclassified"


def clean_taxon(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+\(\d+(?:\.\d+)?\)$", "", value)
    value = re.sub(r"^[a-z]__", "", value)
    value = re.sub(r"_\d+$", "", value)
    if value.lower() in {"", "unclassified", "none", "na"}:
        return ""
    return value


def clean_species(value: str) -> str:
    value = clean_taxon(value)
    value = re.sub(r"\([^)]*\)", "", value).strip()
    value = value.replace("_", " ")
    return value


def write_comparison(rank: str, our_counts: dict[str, int], their_counts: dict[str, int]) -> None:
    taxa = sorted(set(our_counts) | set(their_counts), key=lambda t: (-(our_counts.get(t, 0) + their_counts.get(t, 0)), t))
    output = OUT_DIR / f"{rank}_greengenes_counts.csv"
    with output.open("wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["taxon", "our_count", "their_count"])
        writer.writeheader()
        for taxon in taxa:
            writer.writerow(
                {
                    "taxon": taxon,
                    "our_count": our_counts.get(taxon, 0),
                    "their_count": their_counts.get(taxon, 0),
                }
            )


if __name__ == "__main__":
    main()
