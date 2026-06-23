from __future__ import annotations

import argparse
from pathlib import Path

from taxonomy_pipeline.multi_sample import discover_taxonomy_csvs, write_multi_sample_tables


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ASV and taxon matrices across completed jobs.")
    parser.add_argument("--job-root", type=Path, default=Path("jobs"))
    parser.add_argument("--asv-output", type=Path, default=Path("outputs/asv_sample_matrix.csv"))
    parser.add_argument("--taxon-output", type=Path, default=Path("outputs/taxon_sample_matrix.csv"))
    parser.add_argument("--database", default="consensus")
    parser.add_argument("--rank", default="genus")
    args = parser.parse_args()

    taxonomy_csvs = discover_taxonomy_csvs(args.job_root)
    if not taxonomy_csvs:
        raise SystemExit(f"No taxonomy_long.csv files found under {args.job_root}")

    write_multi_sample_tables(
        taxonomy_csvs,
        asv_output=args.asv_output,
        taxon_output=args.taxon_output,
        database=args.database,
        rank=args.rank,
    )
    print(f"Wrote {args.asv_output}")
    print(f"Wrote {args.taxon_output}")


if __name__ == "__main__":
    main()
