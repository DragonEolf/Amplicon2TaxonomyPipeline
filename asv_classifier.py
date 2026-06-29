from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from pipeline_errors import PipelineError, ensure_asv_outputs
from taxonomy_pipeline.config import DatabaseConfig, load_config
from taxonomy_pipeline.models import ASVRecord, Assignment, RANKS, Taxonomy
from taxonomy_pipeline.utils import normalize_sequence, parse_fasta


APP_ROOT = Path(__file__).resolve().parent
ASSIGN_TAXONOMY_SCRIPT = APP_ROOT / "scripts" / "assign_taxonomy.R"

OUTPUT_FIELDS = [
    "job_id",
    "asv_id",
    "sequence",
    "reads",
    "percent_abundance",
    "marker",
    "database",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
    "match_type",
    "identity",
    "consensus_taxonomy",
]


def read_count_table(path: str | Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    with Path(path).open("rt", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return counts
        id_field = first_present(reader.fieldnames, ["asv_id", "ASV", "asv", "sequence", "Sequence"])
        read_field = first_present(reader.fieldnames, ["reads", "Reads", "count", "Count", "total", "Total"])
        if id_field is None or read_field is None:
            raise ValueError("Count table must contain ASV/asv_id and reads/count columns")
        for row in reader:
            counts[str(row[id_field])] = int(float(row[read_field] or 0))
    return counts


def first_present(values: list[str], candidates: list[str]) -> str | None:
    lookup = set(values)
    for candidate in candidates:
        if candidate in lookup:
            return candidate
    return None


def read_asvs(fasta_path: str | Path, count_table_path: str | Path) -> list[ASVRecord]:
    counts = read_count_table(count_table_path)
    records: list[ASVRecord] = []
    for index, (header, sequence) in enumerate(parse_fasta(fasta_path), start=1):
        asv_id = header.split()[0] if header else f"ASV_{index}"
        reads = counts.get(asv_id)
        if reads is None:
            reads = counts.get(sequence, 0)
        records.append(ASVRecord(asv_id=asv_id, sequence=normalize_sequence(sequence), reads=reads))
    if not records:
        raise PipelineError("Failed because no ASVs were produced.")
    return records


def run_assign_taxonomy(
    asv_fasta: str | Path,
    databases: list[DatabaseConfig],
    rscript_path: str,
    work_dir: str | Path,
    min_boot: int = 50,
) -> dict[str, dict[str, Assignment]]:
    assignments: dict[str, dict[str, Assignment]] = defaultdict(dict)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    for db in databases:
        if db.assign_taxonomy_fasta is None:
            raise FileNotFoundError(f"No DADA2 assignTaxonomy trainset configured for {db.name}")
        if not db.assign_taxonomy_fasta.exists():
            raise FileNotFoundError(f"DADA2 assignTaxonomy trainset does not exist for {db.name}: {db.assign_taxonomy_fasta}")
        manifest_path = work_dir / f"assign_taxonomy_{db.name}.json"
        output_csv = work_dir / f"assign_taxonomy_{db.name}.csv"
        manifest = {
            "asv_fasta": str(asv_fasta),
            "training_fasta": str(db.assign_taxonomy_fasta),
            "database": db.name,
            "output_csv": str(output_csv),
            "min_boot": min_boot,
            "try_rc": False,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))
        subprocess.run(
            [rscript_path, str(ASSIGN_TAXONOMY_SCRIPT), str(manifest_path)],
            check=True,
            text=True,
            capture_output=True,
        )
        for assignment in read_assign_taxonomy_csv(output_csv, db.name):
            assignments[assignment[0]][db.name] = assignment[1]
    return assignments


def read_assign_taxonomy_csv(path: str | Path, database: str) -> list[tuple[str, Assignment]]:
    results: list[tuple[str, Assignment]] = []
    with Path(path).open("rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            taxonomy = Taxonomy.from_parts([row.get(rank, "") for rank in RANKS])
            results.append(
                (
                    row["asv_id"],
                    Assignment(
                        database=database,
                        taxonomy=taxonomy,
                        match_type="assign_taxonomy",
                    ),
                )
            )
    return results


def compute_consensus(marker: str, db_assignments: dict[str, Assignment]) -> str:
    if marker == "its":
        assignment = next(iter(db_assignments.values()), None)
        return taxonomy_lineage_without_bootstrap(assignment.taxonomy) if assignment else ""

    consensus_parts = []
    for rank in RANKS:
        values = [
            strip_bootstrap(assignment.taxonomy.as_dict()[rank])
            for assignment in db_assignments.values()
            if assignment.taxonomy.as_dict()[rank]
        ]
        winner = majority_value(values)
        if not winner:
            break
        consensus_parts.append(winner)
    return ";".join(consensus_parts)


def taxonomy_lineage_without_bootstrap(taxonomy: Taxonomy) -> str:
    values = [strip_bootstrap(taxonomy.as_dict()[rank]) for rank in RANKS]
    while values and not values[-1]:
        values.pop()
    return ";".join(values)


def strip_bootstrap(value: str) -> str:
    return re.sub(r"\s+\(\d+\)$", "", value).strip()


def majority_value(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    for value, count in counts.items():
        if count >= 2:
            return value
    return values[0] if len(values) == 1 else ""


def write_long_csv(
    path: str | Path,
    job_id: str,
    marker: str,
    asvs: list[ASVRecord],
    databases: list[DatabaseConfig],
    assignments: dict[str, dict[str, Assignment]],
) -> None:
    total_reads = sum(asv.reads for asv in asvs)
    with Path(path).open("wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for asv in asvs:
            asv_assignments = assignments.get(asv.asv_id, {})
            consensus = compute_consensus(marker, asv_assignments)
            percent = (asv.reads / total_reads * 100) if total_reads else 0.0
            for db in databases:
                assignment = asv_assignments.get(
                    db.name,
                    Assignment(database=db.name, taxonomy=Taxonomy.empty(), match_type="unclassified"),
                )
                writer.writerow(output_row(job_id, asv, percent, marker, db.name, assignment, consensus))


def output_row(
    job_id: str,
    asv: ASVRecord,
    percent: float,
    marker: str,
    database: str,
    assignment: Assignment,
    consensus: str,
) -> dict[str, str]:
    row = {
        "job_id": job_id,
        "asv_id": asv.asv_id,
        "sequence": asv.sequence,
        "reads": asv.reads,
        "percent_abundance": f"{percent:.6f}",
        "marker": marker,
        "database": database,
        "match_type": assignment.match_type,
        "identity": "" if assignment.identity is None else f"{assignment.identity:.3f}",
        "consensus_taxonomy": consensus,
    }
    row.update(assignment.taxonomy.as_dict())
    return row


def classify_from_files(
    config_path: str | Path,
    marker: str,
    asv_fasta: str | Path,
    count_table: str | Path,
    output_csv: str | Path,
    job_id: str = "cli",
    work_dir: str | Path = "jobs/cli",
    min_boot: int = 50,
) -> None:
    config = load_config(config_path)
    marker_config = config.markers[marker]
    ensure_asv_outputs(asv_fasta, count_table)
    asvs = read_asvs(asv_fasta, count_table)
    assignments = run_assign_taxonomy(
        asv_fasta=asv_fasta,
        databases=marker_config.databases,
        rscript_path=config.rscript_path,
        work_dir=Path(work_dir) / "assign_taxonomy",
        min_boot=min_boot,
    )
    write_long_csv(
        output_csv,
        job_id,
        marker,
        asvs,
        marker_config.databases,
        assignments,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify DADA2 ASVs with DADA2 assignTaxonomy trainsets.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--marker", choices=["16s_v3v4", "its"], required=True)
    parser.add_argument("--asv-fasta", required=True)
    parser.add_argument("--count-table", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--job-id", default="cli")
    parser.add_argument("--work-dir", default="jobs/cli")
    args = parser.parse_args()
    classify_from_files(
        config_path=args.config,
        marker=args.marker,
        asv_fasta=args.asv_fasta,
        count_table=args.count_table,
        output_csv=args.output_csv,
        job_id=args.job_id,
        work_dir=args.work_dir,
    )


if __name__ == "__main__":
    main()
