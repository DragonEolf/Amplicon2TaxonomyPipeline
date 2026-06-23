from __future__ import annotations

import csv

from taxonomy_pipeline.models import ASVRecord
from taxonomy_pipeline.reference_matcher import assign_species, find_top_matches, sequence_identity, write_matches_csv


def test_sequence_identity_counts_mismatches_and_length_difference():
    identity, mismatches = sequence_identity("ACGT", "ACGA")

    assert identity == 75.0
    assert mismatches == 1

    identity, mismatches = sequence_identity("ACGT", "ACGTA")

    assert identity == 80.0
    assert mismatches == 1


def test_find_top_matches_ranks_reference_hits_and_assigns_species(tmp_path):
    reference = tmp_path / "refs.fasta"
    reference.write_text(
        ">ref1 Bacteria;Firmicutes;Bacilli;Order;Family;Genus;Species alpha\n"
        "ACGT\n"
        ">ref2 Bacteria;Firmicutes;Bacilli;Order;Family;Genus;Species beta\n"
        "ACGA\n"
    )
    asvs = [ASVRecord("ASV_1", "ACGT", 10)]

    matches = find_top_matches(asvs, [("TESTDB", reference)], top_n=2)

    assert [match.reference_id for match in matches["ASV_1"]] == ["ref1", "ref2"]
    assert matches["ASV_1"][0].identity == 100.0
    assert assign_species(matches, min_identity=99.0) == {"ASV_1": "Species alpha"}


def test_write_matches_csv_outputs_top_match_fields(tmp_path):
    reference = tmp_path / "refs.fasta"
    reference.write_text(">ref1 Bacteria;Firmicutes;Bacilli;Order;Family;Genus;Species alpha\nACGT\n")
    matches = find_top_matches([ASVRecord("ASV_1", "ACGT", 10)], [("TESTDB", reference)])
    output = tmp_path / "closest_matches.csv"

    write_matches_csv(output, "job1", matches)

    with output.open("rt", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["job_id"] == "job1"
    assert rows[0]["identity"] == "100.000"
    assert rows[0]["species"] == "Species alpha"
