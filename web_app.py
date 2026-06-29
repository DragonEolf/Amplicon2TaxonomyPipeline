from __future__ import annotations

import json
import re
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from asv_classifier import classify_from_files
from dada2_runner import run_dada2, write_manifest
from generate_genepath_report import build_report_data, collapse_asv_records, draw_report, read_rows
from pipeline_errors import PipelineError, classify_failure_message, friendly_exception_message
from pod5_converter import convert_pod5_to_fastq
from taxonomy_pipeline.config import load_config
from taxonomy_pipeline.utils import ensure_directory, safe_filename


APP_ROOT = Path(__file__).resolve().parent
MARKER_CONFIGS = {
    "16s_v3v4": APP_ROOT / "config" / "databases.16s_three_db.yaml",
    "its": APP_ROOT / "config" / "databases.its_unite.yaml",
}
DADA2_SCRIPT = APP_ROOT / "scripts" / "dada2_pipeline.R"

app = FastAPI(title="ASV Taxonomy Pipeline")
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    marker: str = Form(...),
    read_mode: str = Form(...),
    input_format: str = Form("fastq"),
    sensitivity_mode: str = Form("standard"),
    fastq_r1: UploadFile | None = File(None),
    fastq_r2: UploadFile | None = File(None),
    pod5_file: UploadFile | None = File(None),
):
    config_path = config_path_for_marker(marker)
    if config_path is None:
        raise HTTPException(status_code=400, detail="Invalid marker")
    if read_mode not in {"single", "paired"}:
        raise HTTPException(status_code=400, detail="Invalid read mode")
    if input_format not in {"fastq", "pod5"}:
        raise HTTPException(status_code=400, detail="Invalid input format")
    if sensitivity_mode not in {"standard", "relaxed"}:
        raise HTTPException(status_code=400, detail="Invalid ASV sensitivity mode")
    if input_format == "fastq":
        if fastq_r1 is None:
            raise HTTPException(status_code=400, detail="FASTQ mode requires an R1 FASTQ file")
        if read_mode == "paired" and fastq_r2 is None:
            raise HTTPException(status_code=400, detail="Paired-end mode requires an R2 FASTQ file")
    else:
        if pod5_file is None:
            raise HTTPException(status_code=400, detail="POD5 mode requires a POD5 file")
        if read_mode != "single":
            raise HTTPException(status_code=400, detail="POD5 input currently runs as single-end after FASTQ conversion")

    config = load_config(config_path)
    source_filename = upload_filename_for_job(input_format, fastq_r1, pod5_file)
    job_id = build_job_id(marker, read_mode, source_filename, config.job_dir)
    job_dir = ensure_directory(config.job_dir / job_id)
    input_dir = ensure_directory(job_dir / "inputs")
    output_dir = ensure_directory(job_dir / "outputs")

    pod5_path = None
    r1_path = input_dir / safe_filename(fastq_r1.filename or "R1.fastq.gz") if fastq_r1 else input_dir / "pod5_basecalled.fastq"
    if fastq_r1 is not None:
        await save_upload(fastq_r1, r1_path)
    r2_path = None
    if fastq_r2 is not None:
        r2_path = input_dir / safe_filename(fastq_r2.filename or "R2.fastq.gz")
        await save_upload(fastq_r2, r2_path)
    if pod5_file is not None:
        pod5_path = input_dir / safe_filename(pod5_file.filename or "input.pod5")
        await save_upload(pod5_file, pod5_path)

    write_status(job_dir, state="queued", message="Job queued", job_id=job_id)
    background_tasks.add_task(
        run_pipeline_job,
        job_id,
        job_dir,
        config_path,
        marker,
        read_mode,
        input_format,
        sensitivity_mode,
        r1_path,
        r2_path,
        pod5_path,
    )
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.get("/jobs/{job_id}")
def job_status(request: Request, job_id: str):
    job_dir = job_dir_for_id(job_id)
    status = read_status(job_dir)
    outputs = sorted([path.name for path in (job_dir / "outputs").glob("*")]) if (job_dir / "outputs").exists() else []
    return templates.TemplateResponse(
        request,
        "job.html",
        {"job_id": job_id, "status": status, "outputs": outputs},
    )


@app.get("/jobs/{job_id}/download/{filename}")
def download(job_id: str, filename: str):
    job_dir = job_dir_for_id(job_id)
    candidate = (job_dir / "outputs" / filename).resolve()
    outputs_dir = (job_dir / "outputs").resolve()
    if outputs_dir not in candidate.parents or not candidate.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    return FileResponse(candidate, filename=filename)


def config_path_for_marker(marker: str) -> Path | None:
    return MARKER_CONFIGS.get(marker)


def job_dir_for_id(job_id: str) -> Path:
    for config_path in MARKER_CONFIGS.values():
        config = load_config(config_path)
        candidate = config.job_dir / job_id
        if candidate.exists():
            return candidate
    return load_config(MARKER_CONFIGS["16s_v3v4"]).job_dir / job_id


def build_job_id(marker: str, read_mode: str, r1_filename: str, job_root: Path, now: datetime | None = None) -> str:
    now = now or datetime.now()
    prefix = r1_prefix(r1_filename)
    base = safe_job_part(f"{marker}_{read_mode}_{prefix}_{now:%Y%m%d_%H%M%S}")
    candidate = base
    counter = 2
    while (job_root / candidate).exists():
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def upload_filename_for_job(input_format: str, fastq_r1: UploadFile | None, pod5_file: UploadFile | None) -> str:
    if input_format == "pod5":
        return pod5_file.filename if pod5_file and pod5_file.filename else "input.pod5"
    return fastq_r1.filename if fastq_r1 and fastq_r1.filename else "R1.fastq.gz"


def r1_prefix(filename: str) -> str:
    name = Path(safe_filename(filename)).name
    for suffix in (
        ".pod5",
        ".fastq.gz",
        ".fq.gz",
        ".fastq",
        ".fq",
        ".gz",
    ):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break
    name = re.sub(r"([._-])R?1([._-]0*01)?$", "", name, flags=re.IGNORECASE)
    return name or "R1"


def safe_job_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    return cleaned or "job"


async def save_upload(upload: UploadFile, path: Path) -> None:
    with path.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            handle.write(chunk)


def run_pipeline_job(
    job_id: str,
    job_dir: Path,
    config_path: str,
    marker: str,
    read_mode: str,
    input_format: str,
    sensitivity_mode: str,
    r1_path: Path,
    r2_path: Path | None,
    pod5_path: Path | None,
) -> None:
    try:
        config = load_config(config_path)
        output_dir = ensure_directory(job_dir / "outputs")
        marker_config = config.markers[marker]
        if input_format == "pod5":
            if pod5_path is None:
                raise PipelineError("Failed because POD5 input was selected but no POD5 file was saved.")
            write_status(job_dir, state="running", message="Basecalling POD5 to FASTQ", job_id=job_id)
            try:
                convert_pod5_to_fastq(
                    pod5_path=pod5_path,
                    output_fastq=r1_path,
                    log_path=output_dir / "pod5_to_fastq.log",
                )
            except Exception as exc:
                raise PipelineError(pod5_failure_message(exc), detail=str(exc)) from exc

        write_status(job_dir, state="running", message="Running DADA2", job_id=job_id)
        manifest_path = write_manifest(
            path=job_dir / "manifest.json",
            marker=marker,
            read_mode=read_mode,
            fastq_r1=r1_path,
            fastq_r2=r2_path,
            output_dir=output_dir,
            dada2_params=dada2_params_for_mode(marker_config.dada2, sensitivity_mode),
        )
        run_dada2(config.rscript_path, DADA2_SCRIPT, manifest_path, output_dir / "dada2.log")

        write_status(job_dir, state="running", message="Classifying ASVs", job_id=job_id)
        asv_fasta = output_dir / "asvs.fasta"
        count_table = output_dir / "asv_counts.csv"
        try:
            taxonomy_csv = output_dir / "taxonomy_long.csv"
            classify_from_files(
                config_path=config_path,
                marker=marker,
                asv_fasta=asv_fasta,
                count_table=count_table,
                output_csv=taxonomy_csv,
                job_id=job_id,
                work_dir=job_dir / "tmp",
                min_boot=0,
            )
            generate_pdf_report(taxonomy_csv, output_dir / "genepath_report.pdf", job_id, marker)
        except Exception as exc:
            raise PipelineError(classify_failure_message(exc, asv_fasta, count_table), detail=str(exc)) from exc
        write_status(job_dir, state="completed", message="Job completed", job_id=job_id)
    except Exception as exc:
        output_dir = ensure_directory(job_dir / "outputs")
        (output_dir / "error.log").write_text(traceback.format_exc())
        write_status(job_dir, state="failed", message=friendly_exception_message(exc), job_id=job_id)


def pod5_failure_message(exc: BaseException) -> str:
    if isinstance(exc, FileNotFoundError):
        text = str(exc)
        if "basecaller executable" in text or "Dorado" in text:
            return "Failed because the POD5 basecaller was not found. Install Dorado or set DORADO_BIN."
        return "Failed because the POD5 input file was not found."
    return "Failed while converting POD5 to FASTQ. See outputs/pod5_to_fastq.log for technical details."


def dada2_params_for_mode(base_params: dict[str, Any], sensitivity_mode: str) -> dict[str, Any]:
    params = deepcopy(base_params)
    params["sensitivityMode"] = sensitivity_mode
    if sensitivity_mode != "relaxed":
        return params

    params["maxN"] = 0
    max_ee = params.get("maxEE", [2, 2])
    if isinstance(max_ee, list):
        params["maxEE"] = [max(10, int(value)) for value in max_ee]
    else:
        params["maxEE"] = max(10, int(max_ee))
    params["truncQ"] = 2
    params["minOverlap"] = 6
    params["maxMismatch"] = 1
    params["trimOverhang"] = True
    params["justConcatenate"] = True
    params["pool"] = True
    params["omegaA"] = 1e-20
    params["bandSize"] = 32
    params["nbases"] = 1e4
    params["chimeraMethod"] = "consensus"
    return params


def generate_pdf_report(taxonomy_csv: Path, output_pdf: Path, sample_id: str, marker: str) -> None:
    database = "UNITE" if marker == "its" else "consensus"
    title = "ITS Metagenomics Report" if marker == "its" else "16S Metagenomics Report"
    rows = read_rows(taxonomy_csv)
    records = collapse_asv_records(rows, database=database, min_bootstrap=50.0)
    if not records:
        raise PipelineError("Failed because no taxonomy rows were available for the PDF report.")
    report = build_report_data(records)
    draw_report(output_pdf, sample_id, report, title)


def write_status(job_dir: Path, state: str, message: str, job_id: str) -> None:
    payload = {"job_id": job_id, "state": state, "message": message}
    (job_dir / "status.json").write_text(json.dumps(payload, indent=2))


def read_status(job_dir: Path) -> dict[str, str]:
    path = job_dir / "status.json"
    if not path.exists():
        return {"state": "missing", "message": "Job not found"}
    return json.loads(path.read_text())
