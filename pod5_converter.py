from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


DEFAULT_DORADO_MODEL = "dna_r10.4.1_e8.2_400bps_sup@v5.0.0"
APP_ROOT = Path(__file__).resolve().parent
PROJECT_DORADO_BIN = APP_ROOT / ".tools" / "dorado" / "bin" / "dorado"


def resolve_executable(executable: str) -> str:
    if Path(executable).is_absolute():
        if Path(executable).exists():
            return executable
        raise FileNotFoundError(f"POD5 basecaller executable does not exist: {executable}")

    if executable == "dorado" and PROJECT_DORADO_BIN.exists():
        return str(PROJECT_DORADO_BIN)

    resolved = shutil.which(executable)
    if resolved:
        return resolved
    raise FileNotFoundError(
        f"POD5 basecaller executable '{executable}' was not found. "
        "Install Dorado or set DORADO_BIN to its executable path."
    )


def pod5_model(default: str = DEFAULT_DORADO_MODEL) -> str:
    return os.environ.get("DORADO_MODEL", default).strip()


def dorado_bin(default: str = "dorado") -> str:
    return os.environ.get("DORADO_BIN", default).strip()


def convert_pod5_to_fastq(
    pod5_path: str | Path,
    output_fastq: str | Path,
    log_path: str | Path,
    model: str | None = None,
    executable: str | None = None,
) -> Path:
    pod5_path = Path(pod5_path)
    output_fastq = Path(output_fastq)
    log_path = Path(log_path)
    chosen_model = (model or pod5_model()).strip()
    chosen_executable = resolve_executable((executable or dorado_bin()).strip())

    if not chosen_model:
        raise ValueError("A Dorado model is required to basecall POD5 into FASTQ.")
    if not pod5_path.exists():
        raise FileNotFoundError(f"POD5 input file does not exist: {pod5_path}")

    output_fastq.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [chosen_executable, "basecaller", chosen_model, str(pod5_path), "--emit-fastq"]

    with output_fastq.open("wt") as fastq_handle, log_path.open("wt") as log_handle:
        log_handle.write("Command: " + " ".join(command) + "\n\n")
        subprocess.run(
            command,
            check=True,
            stdout=fastq_handle,
            stderr=log_handle,
            text=True,
        )

    return output_fastq
