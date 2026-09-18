from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from paper2_model0.validation import summarize_phase_regions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="outputs/validation_protocol_v0.1/phase_maps_all.csv",
    )
    parser.add_argument(
        "--output",
        default="outputs/validation_protocol_v0.1/phase_region_summary.csv",
    )
    args = parser.parse_args()

    phase_df = pd.read_csv(args.input)
    summary = summarize_phase_regions(phase_df)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(path, index=False)
    print(f"Wrote {len(summary)} rows to {path}")


if __name__ == "__main__":
    main()
