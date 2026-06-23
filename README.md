# DADA2 ASV Taxonomy Pipeline

Skeleton pipeline for taxonomy assignment of DADA2-generated ASVs with a FastAPI upload interface.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

Install external tools separately:

- R with the `dada2` and `jsonlite` packages
- Dorado, if you want to upload POD5 files and basecall them into FASTQ before DADA2

Copy `config/databases.example.yaml` to your own config and edit the DADA2 trainset paths.

POD5 uploads are basecalled with Dorado before the normal single-end FASTQ pipeline runs. By default the app runs:

```bash
dorado basecaller dna_r10.4.1_e8.2_400bps_sup@v5.0.0 input.pod5 --emit-fastq
```

Set `DORADO_BIN` to the Dorado executable path and `DORADO_MODEL` to a different model if needed.

For 16S, the classifier runs DADA2 `assignTaxonomy` once per configured trainset and writes one long-format row per ASV/database. The default 16S goal is three rows per ASV: SILVA, RDP, and Greengenes2.

## Run The Web App

```bash
uvicorn web_app:app --reload
```

Open `http://127.0.0.1:8000`, select `16S V3V4` or `ITS`, choose single-end or paired-end mode, and upload FASTQ files. For POD5 input, choose `POD5 to FASTQ` and `Single-end`; the generated FASTQ is then used by the same pipeline.

## Classify Existing ASVs


```bash
python3 asv_classifier.py \
  --config config/databases.example.yaml \
  --marker 16s_v3v4 \
  --asv-fasta outputs/asvs.fasta \
  --count-table outputs/asv_counts.csv \
  --output-csv outputs/taxonomy_long.csv
```

The output is long format only: one ASV/database row.
