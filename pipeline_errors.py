from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


class PipelineError(RuntimeError):
    """User-facing pipeline failure with optional diagnostic detail."""

    def __init__(self, message: str, *, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


def friendly_exception_message(exc: BaseException) -> str:
    if isinstance(exc, PipelineError):
        return exc.message
    if isinstance(exc, FileNotFoundError):
        return "Failed because a required input, executable, or database file was not found."
    if isinstance(exc, subprocess.CalledProcessError):
        return "Failed because an external analysis step did not complete successfully."
    return "Failed because the pipeline encountered an unexpected error."


def dada2_failure_message(log_path: str | Path, output_dir: str | Path) -> str:
    log_text = read_tail(log_path)
    summary = read_dada2_summary(Path(output_dir) / "dada2_summary.csv")

    if summary and all(row.get("filtered", 0) == 0 for row in summary):
        return "Failed because no reads passed DADA2 filtering. The reads may be too low quality, too short after trimming, or contain too many ambiguous N bases."
    if re.search(r"no reads passed the filter", log_text, re.IGNORECASE):
        return "Failed because no reads passed DADA2 filtering. The reads may be too low quality, too short after trimming, or contain too many ambiguous N bases."
    if re.search(r"zero ASVs|produced zero ASVs", log_text, re.IGNORECASE):
        return "Failed because no ASVs were produced after denoising and chimera removal."
    if re.search(r"merge produced zero ASVs|nrow\(mergers\).*0", log_text, re.IGNORECASE):
        return "Failed because paired reads could not be merged into ASVs. The forward and reverse reads may not overlap enough or may disagree too much."
    if re.search(r"learnErrors|derepFastq|dada\(", log_text, re.IGNORECASE):
        return "Failed during DADA2 denoising. Check read quality and whether enough filtered reads remain to learn an error model."
    if re.search(r"cannot open|No such file|does not exist", log_text, re.IGNORECASE):
        return "Failed because DADA2 could not read one of the FASTQ input files."
    if re.search(r"not in gzip format|invalid compressed data|unexpected end of file", log_text, re.IGNORECASE):
        return "Failed because one of the FASTQ files appears to be corrupt or not valid gzip data."
    return "Failed while running DADA2. See outputs/dada2.log for technical details."


def classify_failure_message(exc: BaseException, asv_fasta: str | Path, count_table: str | Path) -> str:
    if isinstance(exc, PipelineError):
        return exc.message
    if isinstance(exc, FileNotFoundError):
        text = str(exc)
        if "trainset" in text or "assignTaxonomy" in text:
            return "Failed because a configured taxonomy reference database file was not found."
        return "Failed because a required ASV or taxonomy input file was not found."
    if not Path(asv_fasta).exists() or not Path(count_table).exists():
        return "Failed because DADA2 did not produce the ASV files needed for taxonomy assignment."
    if isinstance(exc, subprocess.CalledProcessError):
        return "Failed during taxonomy assignment. The ASV FASTA or taxonomy database may be incompatible with DADA2 assignTaxonomy."
    return "Failed while classifying ASVs. See outputs/error.log for technical details."


def ensure_asv_outputs(asv_fasta: str | Path, count_table: str | Path) -> None:
    fasta = Path(asv_fasta)
    counts = Path(count_table)
    if not fasta.exists() or not counts.exists():
        raise PipelineError("Failed because DADA2 did not produce the ASV files needed for taxonomy assignment.")
    if not any(line.startswith(">") for line in fasta.read_text(errors="replace").splitlines()):
        raise PipelineError("Failed because no ASVs were produced.")
    if not read_dada2_counts(counts):
        raise PipelineError("Failed because no ASVs were produced.")


def read_tail(path: str | Path, limit: int = 12000) -> str:
    path = Path(path)
    if not path.exists():
        return ""
    text = path.read_text(errors="replace")
    return text[-limit:]


def read_dada2_summary(path: Path) -> list[dict[str, int]]:
    if not path.exists():
        return []
    rows: list[dict[str, int]] = []
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parsed: dict[str, int] = {}
            for key in ("input", "filtered"):
                try:
                    parsed[key] = int(float(row.get(key, 0) or 0))
                except ValueError:
                    parsed[key] = 0
            rows.append(parsed)
    return rows


def read_dada2_counts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("rt", newline="") as handle:
        return list(csv.DictReader(handle))
