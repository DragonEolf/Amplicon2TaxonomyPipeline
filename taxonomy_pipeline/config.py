from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DatabaseConfig:
    name: str
    assign_taxonomy_fasta: Path


@dataclass(frozen=True)
class MarkerConfig:
    label: str
    databases: list[DatabaseConfig]
    dada2: dict[str, Any]


@dataclass(frozen=True)
class PipelineConfig:
    job_dir: Path
    rscript_path: str
    markers: dict[str, MarkerConfig]


def load_config(path: str | Path) -> PipelineConfig:
    with Path(path).open("rt") as handle:
        raw = yaml.safe_load(handle) or {}

    markers: dict[str, MarkerConfig] = {}
    for marker_key, marker_raw in (raw.get("markers") or {}).items():
        dbs = []
        for db_raw in marker_raw.get("databases", []):
            dbs.append(
                DatabaseConfig(
                    name=str(db_raw["name"]),
                    assign_taxonomy_fasta=Path(db_raw["assign_taxonomy_fasta"]),
                )
            )
        markers[marker_key] = MarkerConfig(
            label=str(marker_raw.get("label", marker_key)),
            databases=dbs,
            dada2=dict(marker_raw.get("dada2") or {}),
        )

    return PipelineConfig(
        job_dir=Path(raw.get("job_dir", "jobs")),
        rscript_path=str(raw.get("rscript_path", "Rscript")),
        markers=markers,
    )
