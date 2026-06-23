from __future__ import annotations

from pathlib import Path

import pytest

from pod5_converter import convert_pod5_to_fastq, resolve_executable


def test_resolve_executable_reports_missing_binary():
    with pytest.raises(FileNotFoundError, match="Install Dorado"):
        resolve_executable("definitely-not-dorado")


def test_convert_pod5_to_fastq_runs_dorado_basecaller(monkeypatch, tmp_path):
    pod5 = tmp_path / "sample.pod5"
    output = tmp_path / "sample.fastq"
    log = tmp_path / "pod5_to_fastq.log"
    pod5.write_bytes(b"POD5")
    calls = []

    def fake_run(command, check, stdout, stderr, text):
        calls.append((command, check, text))
        stdout.write("@read1\nACGT\n+\n!!!!\n")
        stderr.write("basecalled\n")

    monkeypatch.setattr("pod5_converter.resolve_executable", lambda executable: "/usr/local/bin/dorado")
    monkeypatch.setattr("subprocess.run", fake_run)

    result = convert_pod5_to_fastq(
        pod5_path=pod5,
        output_fastq=output,
        log_path=log,
        model="test-model",
        executable="dorado",
    )

    assert result == output
    assert output.read_text() == "@read1\nACGT\n+\n!!!!\n"
    assert "basecalled" in log.read_text()
    assert calls == [(["/usr/local/bin/dorado", "basecaller", "test-model", str(pod5), "--emit-fastq"], True, True)]
