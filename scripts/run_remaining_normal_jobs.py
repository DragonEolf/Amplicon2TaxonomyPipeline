from __future__ import annotations

import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path
import sys

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from asv_classifier import classify_from_files
from dada2_runner import run_dada2, write_manifest
from taxonomy_pipeline.config import load_config
from taxonomy_pipeline.utils import ensure_directory, safe_filename
from web_app import DADA2_SCRIPT, dada2_params_for_mode, write_status


STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


SAMPLES = [
    {
        "label": "ITS_18S-G019731_S26",
        "marker": "its",
        "config": APP_ROOT / "config" / "databases.its_unite.yaml",
        "r1": Path("/Users/krishnaiitm/Desktop/Metagenoics data/ITS/18S-G019731_S26_L001_R1_001.fastq.gz"),
        "r2": Path("/Users/krishnaiitm/Desktop/Metagenoics data/ITS/18S-G019731_S26_L001_R2_001.fastq.gz"),
    },
    {
        "label": "16sBowerwellB1_S7",
        "marker": "16s_v3v4",
        "config": APP_ROOT / "config" / "databases.16s_two_db.yaml",
        "r1": Path("/Users/krishnaiitm/Desktop/Metagenoics data/borewell1/16sBowerwellB1_S7_L001_R1_001.fastq.gz"),
        "r2": Path("/Users/krishnaiitm/Desktop/Metagenoics data/borewell1/16sBowerwellB1_S7_L001_R2_001.fastq.gz"),
    },
    {
        "label": "16sBowerwellB2_S8",
        "marker": "16s_v3v4",
        "config": APP_ROOT / "config" / "databases.16s_two_db.yaml",
        "r1": Path("/Users/krishnaiitm/Desktop/Metagenoics data/Borewell2/16sBowerwellB2_S8_L001_R1_001.fastq.gz"),
        "r2": Path("/Users/krishnaiitm/Desktop/Metagenoics data/Borewell2/16sBowerwellB2_S8_L001_R2_001.fastq.gz"),
    },
    {
        "label": "16sNtcBottle_S13",
        "marker": "16s_v3v4",
        "config": APP_ROOT / "config" / "databases.16s_two_db.yaml",
        "r1": Path("/Users/krishnaiitm/Desktop/Metagenoics data/NTC 1/16sNtcBottle_S13_L001_R1_001.fastq.gz"),
        "r2": Path("/Users/krishnaiitm/Desktop/Metagenoics data/NTC 1/16sNtcBottle_S13_L001_R2_001.fastq.gz"),
    },
    {
        "label": "16sRiverB5_S11",
        "marker": "16s_v3v4",
        "config": APP_ROOT / "config" / "databases.16s_two_db.yaml",
        "r1": Path("/Users/krishnaiitm/Desktop/Metagenoics data/River/16sRiverB5_S11_L001_R1_001.fastq.gz"),
        "r2": Path("/Users/krishnaiitm/Desktop/Metagenoics data/River/16sRiverB5_S11_L001_R2_001.fastq.gz"),
    },
    {
        "label": "16sOpenTank1B3_S9",
        "marker": "16s_v3v4",
        "config": APP_ROOT / "config" / "databases.16s_two_db.yaml",
        "r1": Path("/Users/krishnaiitm/Desktop/Metagenoics data/opentank/16sOpenTank1B3_S9_L001_R1_001.fastq.gz"),
        "r2": Path("/Users/krishnaiitm/Desktop/Metagenoics data/opentank/16sOpenTank1B3_S9_L001_R2_001.fastq.gz"),
    },
    {
        "label": "16sOpenTank2B4_S10",
        "marker": "16s_v3v4",
        "config": APP_ROOT / "config" / "databases.16s_two_db.yaml",
        "r1": Path("/Users/krishnaiitm/Desktop/Metagenoics data/opentank2/16sOpenTank2B4_S10_L001_R1_001.fastq.gz"),
        "r2": Path("/Users/krishnaiitm/Desktop/Metagenoics data/opentank2/16sOpenTank2B4_S10_L001_R2_001.fastq.gz"),
    },
    {
        "label": "16sStool31759B6_S12",
        "marker": "16s_v3v4",
        "config": APP_ROOT / "config" / "databases.16s_two_db.yaml",
        "r1": Path("/Users/krishnaiitm/Desktop/Metagenoics data/stoolnosummary/16sStool31759B6_S12_L001_R1_001.fastq.gz"),
        "r2": Path("/Users/krishnaiitm/Desktop/Metagenoics data/stoolnosummary/16sStool31759B6_S12_L001_R2_001.fastq.gz"),
    },
]


def main() -> None:
    for sample in SAMPLES[1:]:
        run_sample(sample)


def run_sample(sample: dict[str, object]) -> None:
    label = str(sample["label"])
    marker = str(sample["marker"])
    config_path = Path(sample["config"])
    source_r1 = Path(sample["r1"])
    source_r2 = Path(sample["r2"])
    for source in (source_r1, source_r2):
        if not source.exists():
            raise FileNotFoundError(source)

    config = load_config(config_path)
    job_id = safe_filename(f"{marker}_paired_{label}_normal_{STAMP}")
    job_dir = ensure_directory(config.job_dir / job_id)
    input_dir = ensure_directory(job_dir / "inputs")
    output_dir = ensure_directory(job_dir / "outputs")

    r1_path = input_dir / source_r1.name
    r2_path = input_dir / source_r2.name
    if not r1_path.exists():
        shutil.copy2(source_r1, r1_path)
    if not r2_path.exists():
        shutil.copy2(source_r2, r2_path)

    print(f"START {job_id}", flush=True)
    write_status(job_dir, state="running", message="Running DADA2 in normal mode", job_id=job_id)
    try:
        marker_config = config.markers[marker]
        manifest_path = write_manifest(
            path=job_dir / "manifest.json",
            marker=marker,
            read_mode="paired",
            fastq_r1=r1_path,
            fastq_r2=r2_path,
            output_dir=output_dir,
            dada2_params=dada2_params_for_mode(marker_config.dada2, "standard"),
        )
        run_dada2(config.rscript_path, DADA2_SCRIPT, manifest_path, output_dir / "dada2.log")

        write_status(job_dir, state="running", message="Classifying ASVs with min_boot=0", job_id=job_id)
        classify_from_files(
            config_path=config_path,
            marker=marker,
            asv_fasta=output_dir / "asvs.fasta",
            count_table=output_dir / "asv_counts.csv",
            output_csv=output_dir / "taxonomy_long.csv",
            job_id=job_id,
            work_dir=job_dir / "tmp_minboot0",
            min_boot=0,
        )
    except Exception as exc:
        (output_dir / "error.log").write_text(traceback.format_exc())
        write_status(job_dir, state="failed", message=str(exc), job_id=job_id)
        print(f"FAILED {job_id}: {exc}", flush=True)
        return

    summary = {
        "job_id": job_id,
        "state": "completed",
        "message": "Job completed in normal mode with min_boot=0 taxonomy",
    }
    (job_dir / "status.json").write_text(json.dumps(summary, indent=2))
    print(f"DONE {job_id}", flush=True)


if __name__ == "__main__":
    main()
