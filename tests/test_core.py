from __future__ import annotations

import csv
from pathlib import Path

import pytest

from asv_classifier import compute_consensus, read_asvs, write_long_csv
from pipeline_errors import PipelineError, dada2_failure_message, ensure_asv_outputs
from taxonomy_pipeline.config import DatabaseConfig, load_config
from taxonomy_pipeline.models import ASVRecord, Assignment, Taxonomy
from taxonomy_pipeline.utils import normalize_sequence, parse_fasta


def test_sequence_normalization_is_stable():
    assert normalize_sequence(" acg\nta ") == "ACGTA"


def test_parse_fasta_normalizes_sequences(tmp_path):
    fasta = tmp_path / "asvs.fasta"
    fasta.write_text(">ASV_1\nacg\nTA\n")

    assert list(parse_fasta(fasta)) == [("ASV_1", "ACGTA")]


def test_read_asvs_accepts_asv_id_count_table(tmp_path):
    fasta = tmp_path / "asvs.fasta"
    counts = tmp_path / "counts.csv"
    fasta.write_text(">ASV_1\nACGT\n>ASV_2\nTTTT\n")
    counts.write_text("asv_id,reads\nASV_1,12\nASV_2,3\n")

    asvs = read_asvs(fasta, counts)

    assert asvs == [ASVRecord("ASV_1", "ACGT", 12), ASVRecord("ASV_2", "TTTT", 3)]


def test_empty_asv_fasta_fails_with_friendly_message(tmp_path):
    fasta = tmp_path / "asvs.fasta"
    counts = tmp_path / "counts.csv"
    fasta.write_text("")
    counts.write_text("asv_id,reads,sequence\n")

    with pytest.raises(PipelineError, match="no ASVs were produced"):
        ensure_asv_outputs(fasta, counts)


def test_dada2_filter_failure_message_mentions_quality_and_n_bases(tmp_path):
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    log = output_dir / "dada2.log"
    log.write_text("Error in filterAndTrim(...): No reads passed the filter")

    message = dada2_failure_message(log, output_dir)

    assert "no reads passed DADA2 filtering" in message
    assert "N bases" in message


def test_consensus_requires_two_database_agreement_for_16s():
    assignments = {
        "SILVA": Assignment("SILVA", Taxonomy.from_parts(["Bacteria", "Firmicutes", "Bacilli"]), "assign_taxonomy"),
        "RDP": Assignment("RDP", Taxonomy.from_parts(["Bacteria", "Firmicutes", "Clostridia"]), "assign_taxonomy"),
        "Greengenes2": Assignment("Greengenes2", Taxonomy.from_parts(["Bacteria", "Firmicutes", "Bacilli"]), "assign_taxonomy"),
    }

    assert compute_consensus("16s_v3v4", assignments) == "Bacteria;Firmicutes;Bacilli"


def test_consensus_ignores_bootstrap_suffixes():
    assignments = {
        "SILVA": Assignment("SILVA", Taxonomy.from_parts(["Bacteria (100)", "Pseudomonadota (87)"]), "assign_taxonomy"),
        "RDP": Assignment("RDP", Taxonomy.from_parts(["Bacteria (99)", "Pseudomonadota (54)"]), "assign_taxonomy"),
        "Greengenes2": Assignment("Greengenes2", Taxonomy.from_parts(["Bacteria (100)", "Bacillota (80)"]), "assign_taxonomy"),
    }

    assert compute_consensus("16s_v3v4", assignments) == "Bacteria;Pseudomonadota"


def test_write_long_csv_emits_one_row_per_database(tmp_path):
    asvs = [ASVRecord("ASV_1", "ACGT", 10)]
    dbs = [
        DatabaseConfig("SILVA", tmp_path / "silva.fa.gz"),
        DatabaseConfig("RDP", tmp_path / "rdp.fa.gz"),
        DatabaseConfig("Greengenes2", tmp_path / "gg2.fa.gz"),
    ]
    assignments = {
        "ASV_1": {
            "SILVA": Assignment("SILVA", Taxonomy.from_parts(["Bacteria (100)", "Firmicutes (90)"]), "assign_taxonomy"),
            "RDP": Assignment("RDP", Taxonomy.empty(), "unclassified"),
            "Greengenes2": Assignment("Greengenes2", Taxonomy.from_parts(["Bacteria (100)", "Firmicutes (80)"]), "assign_taxonomy"),
        }
    }
    output = tmp_path / "taxonomy_long.csv"

    write_long_csv(output, "job1", "16s_v3v4", asvs, dbs, assignments)

    with output.open("rt", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert [row["database"] for row in rows] == ["SILVA", "RDP", "Greengenes2"]
    assert rows[0]["phylum"] == "Firmicutes (90)"
    assert rows[0]["consensus_taxonomy"] == "Bacteria;Firmicutes"


def test_load_config_reads_trainset_paths(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
job_dir: jobs
rscript_path: Rscript
markers:
  16s_v3v4:
    label: 16S
    dada2:
      maxN: 0
    databases:
      - name: SILVA
        assign_taxonomy_fasta: refs/silva.fa.gz
"""
    )

    loaded = load_config(config)

    marker = loaded.markers["16s_v3v4"]
    assert marker.dada2 == {"maxN": 0}
    assert marker.databases == [DatabaseConfig("SILVA", Path("refs/silva.fa.gz"))]
