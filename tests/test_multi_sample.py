from __future__ import annotations

from taxonomy_pipeline.multi_sample import build_multi_sample_tables


def write_taxonomy(path, job_id, rows):
    path.parent.mkdir(parents=True)
    path.write_text(
        "job_id,asv_id,sequence,reads,percent_abundance,marker,database,kingdom,phylum,class,order,family,genus,species,match_type,identity,consensus_taxonomy\n"
        + "\n".join(
            ",".join(
                [
                    job_id,
                    row["asv_id"],
                    row["sequence"],
                    str(row["reads"]),
                    "100",
                    "16s_v3v4",
                    "SILVA",
                    "Bacteria",
                    "Firmicutes",
                    "Bacilli",
                    "",
                    "",
                    row["genus"],
                    "",
                    "assign_taxonomy",
                    "",
                    f"Bacteria;Firmicutes;Bacilli;;;;{row['genus']}",
                ]
            )
            for row in rows
        )
        + "\n"
    )


def test_build_multi_sample_tables_counts_asvs_and_taxa(tmp_path):
    sample_a = tmp_path / "sample_a" / "outputs" / "taxonomy_long.csv"
    sample_b = tmp_path / "sample_b" / "outputs" / "taxonomy_long.csv"
    write_taxonomy(sample_a, "sample_a", [{"asv_id": "ASV_1", "sequence": "ACGT", "reads": 8, "genus": "Bacillus"}])
    write_taxonomy(
        sample_b,
        "sample_b",
        [
            {"asv_id": "ASV_1", "sequence": "ACGT", "reads": 2, "genus": "Bacillus"},
            {"asv_id": "ASV_2", "sequence": "TTTT", "reads": 5, "genus": "Listeria"},
        ],
    )

    asv_rows, taxon_rows = build_multi_sample_tables([sample_a, sample_b], database="SILVA", rank="genus")

    assert asv_rows[0]["asv_id"] == "ASV_1"
    assert asv_rows[0]["sample_a"] == "8"
    assert asv_rows[0]["sample_b"] == "2"
    assert asv_rows[0]["sample_a_percent"] == "100.000000"
    assert asv_rows[0]["sample_b_percent"] == "28.571429"
    assert taxon_rows[0]["taxon"] == "Bacillus"
    assert taxon_rows[0]["total_reads"] == "10"
