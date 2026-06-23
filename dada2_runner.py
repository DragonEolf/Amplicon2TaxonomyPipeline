from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def write_manifest(
    path: str | Path,
    marker: str,
    read_mode: str,
    fastq_r1: str | Path,
    output_dir: str | Path,
    dada2_params: dict[str, Any],
    fastq_r2: str | Path | None = None,
) -> Path:
    manifest = {
        "marker": marker,
        "read_mode": read_mode,
        "fastq_r1": str(fastq_r1),
        "fastq_r2": str(fastq_r2) if fastq_r2 else "",
        "output_dir": str(output_dir),
        "asv_fasta": str(Path(output_dir) / "asvs.fasta"),
        "count_table": str(Path(output_dir) / "asv_counts.csv"),
        "summary_table": str(Path(output_dir) / "dada2_summary.csv"),
        "params": dada2_params,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2))
    return path


def run_dada2(
    rscript_path: str,
    script_path: str | Path,
    manifest_path: str | Path,
    log_path: str | Path,
) -> None:
    with Path(log_path).open("wt") as log_handle:
        subprocess.run(
            [rscript_path, str(script_path), str(manifest_path)],
            check=True,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

