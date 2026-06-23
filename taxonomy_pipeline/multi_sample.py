from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from taxonomy_pipeline.models import RANKS


def discover_taxonomy_csvs(job_root: str | Path) -> list[Path]:
    return sorted(Path(job_root).glob("*/outputs/taxonomy_long.csv"))


def build_multi_sample_tables(
    taxonomy_csvs: list[str | Path],
    database: str = "consensus",
    rank: str = "genus",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if rank not in RANKS:
        raise ValueError(f"rank must be one of: {', '.join(RANKS)}")

    asv_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    asv_sequences: dict[str, str] = {}
    taxon_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    sample_totals: dict[str, int] = defaultdict(int)
    samples: list[str] = []

    for csv_path in taxonomy_csvs:
        rows = read_rows(Path(csv_path))
        sample_id = infer_sample_id(rows, Path(csv_path))
        if sample_id not in samples:
            samples.append(sample_id)
        for row in choose_rows(rows, database):
            asv_id = row.get("asv_id", "")
            reads = int(float(row.get("reads") or 0))
            sequence = row.get("sequence", "")
            sample_totals[sample_id] += reads
            asv_sequences[asv_id] = sequence
            asv_counts[asv_id][sample_id] = reads

            taxon = taxon_for_row(row, database, rank) or f"Unclassified {rank.title()}"
            taxon_counts[taxon][sample_id] += reads

    asv_rows = []
    for asv_id in sorted(asv_counts, key=lambda item: (-sum(asv_counts[item].values()), item.casefold())):
        asv_rows.append(matrix_row(asv_id, asv_sequences.get(asv_id, ""), samples, asv_counts[asv_id], sample_totals))

    taxon_rows = []
    for taxon in sorted(taxon_counts, key=lambda item: (-sum(taxon_counts[item].values()), item.casefold())):
        taxon_rows.append(matrix_row(taxon, "", samples, taxon_counts[taxon], sample_totals, id_field="taxon"))

    return asv_rows, taxon_rows


def write_multi_sample_tables(
    taxonomy_csvs: list[str | Path],
    asv_output: str | Path,
    taxon_output: str | Path,
    database: str = "consensus",
    rank: str = "genus",
) -> None:
    asv_rows, taxon_rows = build_multi_sample_tables(taxonomy_csvs, database=database, rank=rank)
    write_matrix(asv_output, asv_rows)
    write_matrix(taxon_output, taxon_rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("rt", newline="") as handle:
        return list(csv.DictReader(handle))


def infer_sample_id(rows: list[dict[str, str]], csv_path: Path) -> str:
    for row in rows:
        if row.get("job_id"):
            return row["job_id"]
    return csv_path.parent.parent.name if csv_path.parent.name == "outputs" else csv_path.stem


def choose_rows(rows: list[dict[str, str]], database: str) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("asv_id", "")].append(row)

    chosen = []
    for asv_rows in grouped.values():
        if database.lower() == "consensus":
            chosen.append(asv_rows[0])
            continue
        for row in asv_rows:
            if row.get("database", "").lower() == database.lower():
                chosen.append(row)
                break
        else:
            chosen.append(asv_rows[0])
    return chosen


def taxon_for_row(row: dict[str, str], database: str, rank: str) -> str:
    if database.lower() == "consensus" and row.get("consensus_taxonomy"):
        parts = [part.strip() for part in row["consensus_taxonomy"].split(";")]
        rank_index = list(RANKS).index(rank)
        return parts[rank_index] if rank_index < len(parts) else ""
    return row.get(rank, "")


def matrix_row(
    row_id: str,
    sequence: str,
    samples: list[str],
    counts: dict[str, int],
    sample_totals: dict[str, int],
    id_field: str = "asv_id",
) -> dict[str, str]:
    row = {id_field: row_id}
    if sequence:
        row["sequence"] = sequence
    total = sum(counts.values())
    row["total_reads"] = str(total)
    for sample in samples:
        reads = counts.get(sample, 0)
        row[sample] = str(reads)
        denominator = sample_totals.get(sample, 0)
        row[f"{sample}_percent"] = f"{(reads / denominator * 100) if denominator else 0.0:.6f}"
    return row


def write_matrix(path: str | Path, rows: list[dict[str, str]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for field in row:
            if field not in fieldnames:
                fieldnames.append(field)
    with path.open("wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
