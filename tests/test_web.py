from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from web_app import app, build_job_id, dada2_params_for_mode, r1_prefix, upload_filename_for_job


def test_index_renders_upload_form():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "16S V3V4" in response.text
    assert "FASTQ R1" in response.text
    assert "POD5 to FASTQ" in response.text
    assert "ASV sensitivity" in response.text
    assert "Relaxed" in response.text
    assert "config_path" not in response.text
    assert "Config path" not in response.text


def test_relaxed_mode_sets_looser_dada2_parameters():
    params = dada2_params_for_mode(
        {"maxN": 0, "maxEE": [5, 5], "truncQ": 2, "minOverlap": 12},
        "relaxed",
    )

    assert params["maxN"] == 0
    assert params["maxEE"] == [10, 10]
    assert params["truncQ"] == 2
    assert params["minOverlap"] == 6
    assert params["maxMismatch"] == 1
    assert params["trimOverhang"] is True
    assert params["justConcatenate"] is True
    assert params["pool"] is True
    assert params["omegaA"] == 1e-20
    assert params["bandSize"] == 32
    assert params["nbases"] == 1e4
    assert params["chimeraMethod"] == "consensus"


def test_job_id_uses_marker_mode_r1_prefix_and_timestamp(tmp_path):
    job_id = build_job_id(
        "16s_v3v4",
        "paired",
        "16sBowerwellB1_S7_L001_R1_001.fastq.gz",
        tmp_path,
        now=datetime(2026, 6, 18, 14, 5, 9),
    )

    assert job_id == "16s_v3v4_paired_16sBowerwellB1_S7_L001_20260618_140509"


def test_job_id_adds_suffix_on_collision(tmp_path):
    existing = tmp_path / "its_single_sample_20260618_140509"
    existing.mkdir()

    job_id = build_job_id(
        "its",
        "single",
        "sample_R1.fastq.gz",
        tmp_path,
        now=datetime(2026, 6, 18, 14, 5, 9),
    )

    assert job_id == "its_single_sample_20260618_140509_2"


def test_r1_prefix_strips_common_read_suffixes():
    assert r1_prefix("sample_R1.fastq.gz") == "sample"
    assert r1_prefix("sample-R1-001.fq.gz") == "sample"
    assert r1_prefix("sample.1.fastq") == "sample"
    assert r1_prefix("sample.pod5") == "sample"


def test_upload_filename_for_job_prefers_pod5_filename():
    class Upload:
        def __init__(self, filename):
            self.filename = filename

    assert upload_filename_for_job("pod5", None, Upload("reads.pod5")) == "reads.pod5"
    assert upload_filename_for_job("fastq", Upload("reads.fastq.gz"), None) == "reads.fastq.gz"


def test_fastq_mode_requires_fastq_r1():
    client = TestClient(app)

    response = client.post(
        "/jobs",
        data={"marker": "16s_v3v4", "read_mode": "single", "input_format": "fastq", "sensitivity_mode": "standard"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "FASTQ mode requires an R1 FASTQ file"


def test_pod5_mode_requires_single_end():
    client = TestClient(app)

    response = client.post(
        "/jobs",
        data={"marker": "16s_v3v4", "read_mode": "paired", "input_format": "pod5", "sensitivity_mode": "standard"},
        files={"pod5_file": ("reads.pod5", b"POD5", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "POD5 input currently runs as single-end after FASTQ conversion"
