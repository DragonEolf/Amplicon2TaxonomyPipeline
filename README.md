# Amplicon2TaxonomyPipeline

A local web app and command-line pipeline for DADA2-based amplicon taxonomy analysis.

The app accepts FASTQ uploads for 16S V3V4 or ITS, runs DADA2, assigns taxonomy against configured reference databases, writes CSV outputs, and generates a downloadable GenePath-style PDF report.

## What It Produces

Each completed job writes outputs under `jobs/<job_id>/outputs/`:

```text
asvs.fasta
asv_counts.csv
dada2_summary.csv
taxonomy_long.csv
closest_matches.csv
genepath_report.pdf
dada2.log
```

The main end-user output is:

```text
genepath_report.pdf
```

## Project Tree

```text
Amplicon2TaxonomyPipeline/
  README.md
  requirements.txt
  web_app.py
  asv_classifier.py
  dada2_runner.py
  generate_genepath_report.py
  pipeline_errors.py
  pod5_converter.py

  config/
    databases.16s_three_db.yaml
    databases.its_unite.yaml
    databases.example.yaml

  scripts/
    dada2_pipeline.R
    assign_taxonomy.R
    build_multi_sample_summary.py
    run_relaxed_16s_jobs.py
    run_remaining_normal_jobs.py

  taxonomy_pipeline/
    config.py
    models.py
    multi_sample.py
    reference_matcher.py
    utils.py

  templates/
    index.html
    job.html

  tests/
    test_core.py
    test_multi_sample.py
    test_pod5_converter.py
    test_reference_matcher.py
    test_report.py
    test_web.py

  DADA2 databases/
    silva_nr99_v138.2_toSpecies_trainset.fa.gz
    rdp_19_toSpecies_trainset.fa.gz
    gg2_2024_09_toSpecies_trainset.fa.gz
    sh_general_release_dynamic_all_19.02.2025.fasta
```

Important: `DADA2 databases/` is required for real runs, but it is not stored in Git because the files are large.

## Install

Clone the repository:

```bash
git clone https://github.com/DragonEolf/Amplicon2TaxonomyPipeline.git
cd Amplicon2TaxonomyPipeline
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

If your system uses `python3`:

```bash
python3 -m pip install -r requirements.txt
```

Install R separately, then install the required R packages:

```r
install.packages("jsonlite")
install.packages("BiocManager")
BiocManager::install("dada2")
```

## Add Reference Databases

Copy the DADA2 reference database folder into the project root:

```text
Amplicon2TaxonomyPipeline/
  DADA2 databases/
```

For 16S V3V4, the configured databases are:

```text
DADA2 databases/silva_nr99_v138.2_toSpecies_trainset.fa.gz
DADA2 databases/rdp_19_toSpecies_trainset.fa.gz
DADA2 databases/gg2_2024_09_toSpecies_trainset.fa.gz
```

For ITS, the configured database is:

```text
DADA2 databases/sh_general_release_dynamic_all_19.02.2025.fasta
```

The active config files are:

```text
config/databases.16s_three_db.yaml
config/databases.its_unite.yaml
```

## Run The Web App

Start the server:

```bash
uvicorn web_app:app --reload
```

Open this in a browser:

```text
http://127.0.0.1:8000
```

Then:

1. Choose `16S V3V4` or `ITS`.
2. Choose `Single-end` or `Paired-end`.
3. Upload FASTQ files.
4. Choose standard or relaxed ASV sensitivity.
5. Submit the job.
6. Download `genepath_report.pdf` and the CSV outputs from the job page.

## POD5 Input

FASTQ input does not need Dorado.

POD5 input requires Dorado because the app must basecall POD5 into FASTQ before running DADA2.

By default, the app runs:

```bash
dorado basecaller dna_r10.4.1_e8.2_400bps_sup@v5.0.0 input.pod5 --emit-fastq
```

If Dorado is not on your PATH, set:

```bash
export DORADO_BIN=/path/to/dorado
```

You can change the model with:

```bash
export DORADO_MODEL=dna_r10.4.1_e8.2_400bps_sup@v5.0.0
```

On Windows, use the Windows Dorado executable and set `DORADO_BIN` to that `.exe` path.

## Run From Command Line

Classify existing DADA2 ASV outputs:

```bash
python asv_classifier.py \
  --config config/databases.16s_three_db.yaml \
  --marker 16s_v3v4 \
  --asv-fasta outputs/asvs.fasta \
  --count-table outputs/asv_counts.csv \
  --output-csv outputs/taxonomy_long.csv \
  --matches-csv outputs/closest_matches.csv
```

Generate a PDF report from a taxonomy CSV:

```bash
python generate_genepath_report.py \
  outputs/taxonomy_long.csv \
  --matches-csv outputs/closest_matches.csv \
  --database consensus \
  --output outputs/genepath_report.pdf
```

Build multi-sample matrices from completed jobs:

```bash
python scripts/build_multi_sample_summary.py \
  --job-root jobs \
  --asv-output outputs/asv_sample_matrix.csv \
  --taxon-output outputs/taxon_sample_matrix.csv \
  --database consensus \
  --rank genus
```

## Relaxed Mode

The YAML config stores the base DADA2 parameters. When `Relaxed` mode is selected in the web app, `web_app.py` modifies the DADA2 manifest before running R.

For example, relaxed mode sets or adjusts:

```text
maxEE -> at least [10, 10]
minOverlap -> 6
maxMismatch -> 1
trimOverhang -> true
justConcatenate -> true
pool -> true
omegaA -> 1e-20
bandSize -> 32
nbases -> 1e4
chimeraMethod -> consensus
```

## Windows Notes

The code uses Python `pathlib`, so normal paths should work on Windows.

Windows users still need to install:

```text
Python
R
DADA2 through Bioconductor
the DADA2 database files
```

Use:

```powershell
py -m pip install -r requirements.txt
py -m uvicorn web_app:app --reload
```

DADA2 installation can be the hardest Windows step. If Bioconductor/DADA2 installation fails, WSL2 or Docker may be easier.

## Development Checks

Run tests:

```bash
python -m pytest -q
```

Expected result for the current main branch:

```text
29 passed
```
