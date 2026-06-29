# How To Use This Pipeline

This is a quick setup guide for someone who wants to clone and run the Amplicon2TaxonomyPipeline project.

## 1. Download The Code

```bash
git clone https://github.com/DragonEolf/Amplicon2TaxonomyPipeline.git
cd Amplicon2TaxonomyPipeline
```

## 2. Install Python Packages

```bash
python -m pip install -r requirements.txt
```

If that does not work, try:

```bash
python3 -m pip install -r requirements.txt
```

## 3. Install R And DADA2

Install R first.

Then open R and run:

```r
install.packages("jsonlite")
install.packages("BiocManager")
BiocManager::install("dada2")
```

## 4. Add The DADA2 Database Files

Create or copy this folder into the project root:

```text
DADA2 databases/
```

It should contain these files:

```text
silva_nr99_v138.2_toSpecies_trainset.fa.gz
rdp_19_toSpecies_trainset.fa.gz
gg2_2024_09_toSpecies_trainset.fa.gz
sh_general_release_dynamic_all_19.02.2025.fasta
```

The project should look like this:

```text
Amplicon2TaxonomyPipeline/
  web_app.py
  config/
  DADA2 databases/
```

## 5. Run The Web App

```bash
uvicorn web_app:app --reload
```

Then open this in a browser:

```text
http://127.0.0.1:8000
```

## 6. Use The App

Upload FASTQ files.

Choose `16S V3V4` or `ITS`.

Choose single-end or paired-end mode.

Run the job.

## 7. Download Outputs

After the job finishes, download the outputs from the job page.

Main outputs:

```text
genepath_report.pdf
taxonomy_long.csv
closest_matches.csv
asvs.fasta
asv_counts.csv
```

The final PDF report is:

```text
genepath_report.pdf
```

## POD5 Note

If you want to upload `.pod5` files, install Dorado separately.

You may also need to set `DORADO_BIN` to the Dorado executable path.

For normal FASTQ uploads, Dorado is not needed.
