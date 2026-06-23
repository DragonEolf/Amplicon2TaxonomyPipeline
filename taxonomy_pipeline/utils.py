from __future__ import annotations

import gzip
import os
from pathlib import Path
from typing import Iterator, TextIO


def normalize_sequence(sequence: str) -> str:
    return "".join(sequence.split()).upper()


def open_text(path: str | Path) -> TextIO:
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("rt")


def parse_fasta(path: str | Path) -> Iterator[tuple[str, str]]:
    header: str | None = None
    chunks: list[str] = []
    with open_text(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, normalize_sequence("".join(chunks))
                header = line[1:].strip()
                chunks = []
            else:
                chunks.append(line)
    if header is not None:
        yield header, normalize_sequence("".join(chunks))


def ensure_directory(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(name: str) -> str:
    keep = []
    for char in os.path.basename(name):
        if char.isalnum() or char in {".", "_", "-"}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep) or "upload.fastq"
