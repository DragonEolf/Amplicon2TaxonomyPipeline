from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from taxonomy_pipeline.models import ASVRecord
from taxonomy_pipeline.utils import normalize_sequence, parse_fasta


MATCH_FIELDS = [
    "job_id",
    "asv_id",
    "database",
    "rank",
    "identity",
    "mismatches",
    "reference_id",
    "reference_taxonomy",
    "species",
    "reference_sequence",
]


@dataclass(frozen=True)
class ReferenceMatch:
    asv_id: str
    database: str
    rank: int
    identity: float
    mismatches: int
    reference_id: str
    reference_taxonomy: str
    species: str
    reference_sequence: str


def find_top_matches(
    asvs: list[ASVRecord],
    references: list[tuple[str, Path]],
    top_n: int = 5,
) -> dict[str, list[ReferenceMatch]]:
    matches = {asv.asv_id: [] for asv in asvs}
    if not asvs or top_n <= 0:
        return matches

    for database, fasta_path in references:
        for header, reference_sequence in parse_fasta(fasta_path):
            reference_sequence = normalize_sequence(reference_sequence)
            reference_id, taxonomy = split_reference_header(header)
            species = species_from_taxonomy(taxonomy)
            for asv in asvs:
                identity, mismatches = sequence_identity(asv.sequence, reference_sequence)
                add_ranked_match(
                    matches[asv.asv_id],
                    ReferenceMatch(
                        asv_id=asv.asv_id,
                        database=database,
                        rank=0,
                        identity=identity,
                        mismatches=mismatches,
                        reference_id=reference_id,
                        reference_taxonomy=taxonomy,
                        species=species,
                        reference_sequence=reference_sequence,
                    ),
                    top_n,
                )

    ranked: dict[str, list[ReferenceMatch]] = {}
    for asv_id, asv_matches in matches.items():
        ordered = sorted(
            asv_matches,
            key=lambda match: (-match.identity, match.mismatches, match.database.casefold(), match.reference_id.casefold()),
        )
        ranked[asv_id] = [
            ReferenceMatch(
                asv_id=match.asv_id,
                database=match.database,
                rank=index,
                identity=match.identity,
                mismatches=match.mismatches,
                reference_id=match.reference_id,
                reference_taxonomy=match.reference_taxonomy,
                species=match.species,
                reference_sequence=match.reference_sequence,
            )
            for index, match in enumerate(ordered[:top_n], start=1)
        ]
    return ranked


def add_ranked_match(matches: list[ReferenceMatch], candidate: ReferenceMatch, top_n: int) -> None:
    matches.append(candidate)
    matches.sort(key=lambda match: (-match.identity, match.mismatches, match.database.casefold(), match.reference_id.casefold()))
    del matches[top_n:]


def sequence_identity(query: str, reference: str) -> tuple[float, int]:
    query = normalize_sequence(query)
    reference = normalize_sequence(reference)
    if not query and not reference:
        return 100.0, 0
    if not query or not reference:
        return 0.0, max(len(query), len(reference))

    overlap = min(len(query), len(reference))
    mismatches = sum(1 for index in range(overlap) if query[index] != reference[index])
    mismatches += abs(len(query) - len(reference))
    denominator = max(len(query), len(reference))
    identity = ((denominator - mismatches) / denominator) * 100.0
    return max(identity, 0.0), mismatches


def split_reference_header(header: str) -> tuple[str, str]:
    header = (header or "").strip()
    if not header:
        return "", ""
    parts = header.split(None, 1)
    reference_id = parts[0]
    taxonomy = parts[1] if len(parts) > 1 else ""
    return reference_id, taxonomy.strip()


def species_from_taxonomy(taxonomy: str) -> str:
    parts = [part.strip() for part in taxonomy.replace("|", ";").split(";") if part.strip()]
    if not parts:
        return ""
    species = parts[-1]
    for prefix in ("s__", "species:"):
        if species.lower().startswith(prefix):
            species = species[len(prefix) :]
    return species.strip()


def assign_species(matches: dict[str, list[ReferenceMatch]], min_identity: float = 99.0) -> dict[str, str]:
    assignments = {}
    for asv_id, asv_matches in matches.items():
        best = next((match for match in asv_matches if match.species and match.identity >= min_identity), None)
        assignments[asv_id] = best.species if best else ""
    return assignments


def write_matches_csv(path: str | Path, job_id: str, matches: dict[str, list[ReferenceMatch]]) -> None:
    with Path(path).open("wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATCH_FIELDS)
        writer.writeheader()
        for asv_id in sorted(matches):
            for match in matches[asv_id]:
                writer.writerow(
                    {
                        "job_id": job_id,
                        "asv_id": match.asv_id,
                        "database": match.database,
                        "rank": match.rank,
                        "identity": f"{match.identity:.3f}",
                        "mismatches": match.mismatches,
                        "reference_id": match.reference_id,
                        "reference_taxonomy": match.reference_taxonomy,
                        "species": match.species,
                        "reference_sequence": match.reference_sequence,
                    }
                )
