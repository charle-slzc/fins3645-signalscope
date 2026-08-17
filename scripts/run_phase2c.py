"""Build Phase 2C matched-shrinkage placebo falsification artifacts only.

Run from the project root:

    python scripts/run_phase2c.py
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

import pandas as pd

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import etl, features, placebo  # noqa: E402


FROZEN_ARTIFACTS = (
    "results/data/fund_returns.csv",
    "results/data/fund_weights.csv",
    "results/data/headline_sentiment_scores.csv",
    "results/data/ticker_day_sentiment.csv",
    "results/data/sector_sentiment_index.csv",
    "results/data/sector_sentiment_confidence.csv",
    "results/data/fusion_returns.csv",
    "results/data/fusion_weights.csv",
    "results/tables/performance_metrics.csv",
    "results/tables/optimisation_diagnostics.csv",
    "results/tables/sentiment_fusion_comparison.csv",
    "results/tables/confidence_lens_summary.csv",
)

OUTPUTS = {
    "results/data/fusion_placebo_returns.csv": "fusion_placebo_returns",
    "results/data/fusion_placebo_weights.csv": "fusion_placebo_weights",
    "results/tables/confidence_placebo_comparison.csv": "comparison",
    "results/tables/confidence_placebo_selectivity.csv": "selectivity",
    "results/tables/confidence_placebo_quadrants.csv": "quadrants",
    "results/tables/confidence_placebo_sector_year.csv": "sector_year",
    "results/tables/confidence_placebo_cases.csv": "cases",
    "results/tables/confidence_placebo_turnover_decomposition.csv": "turnover_decomposition",
}


def _file_hash(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frozen_hashes() -> dict[str, str]:
    hashes = {}
    for relative in FROZEN_ARTIFACTS:
        path = PROJECT_ROOT / relative
        if not path.exists():
            raise FileNotFoundError(f"required frozen artifact is missing: {relative}")
        hashes[relative] = _file_hash(path)
    return hashes


def _read_csv(relative_name: str) -> pd.DataFrame:
    return pd.read_csv(PROJECT_ROOT / relative_name)


def _write_csv(frame: pd.DataFrame, relative_name: str) -> pathlib.Path:
    output_path = PROJECT_ROOT / relative_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8", date_format="%Y-%m-%d")
    return output_path.relative_to(PROJECT_ROOT)


def main() -> int:
    """Build additive Phase 2C artifacts from frozen Phase 2B outputs."""

    before = _frozen_hashes()
    try:
        sector_confidence = _read_csv("results/data/sector_sentiment_confidence.csv")
        fusion_returns = _read_csv("results/data/fusion_returns.csv")
        fusion_weights = _read_csv("results/data/fusion_weights.csv")

        station1 = etl.build_station1_data()
        return_panels = features.build_return_panels(station1.equities, station1.crypto)

        result = placebo.build_placebo_suite(
            sector_confidence=sector_confidence,
            fusion_returns=fusion_returns,
            fusion_weights=fusion_weights,
            equity_returns=return_panels.equity_returns,
            output_dir=PROJECT_ROOT / "results" / "figures",
        )
        written = [
            _write_csv(getattr(result, attribute), relative_name)
            for relative_name, attribute in OUTPUTS.items()
        ]
    except Exception as exc:  # pragma: no cover - command-line reporting
        print(f"Phase 2C placebo generation failed: {exc}", file=sys.stderr)
        return 1

    after = _frozen_hashes()
    changed = [relative for relative, digest in before.items() if after[relative] != digest]
    if changed:
        print(f"Phase 2C attempted to alter frozen artifacts: {changed}", file=sys.stderr)
        return 1

    constants = result.constants
    print("Phase 2C matched-shrinkage placebo artifacts generated")
    print(f"C_mean: {constants.c_mean:.12f}")
    print(f"C_match: {constants.c_match:.12f}")
    print(f"valid signal observations: {constants.observation_count}")
    print(f"Confidence abs tilt sum: {constants.confidence_abs_tilt_sum:.12f}")
    print(f"Placebo abs tilt sum: {constants.placebo_abs_tilt_sum:.12f}")
    print(f"Difference: {constants.aggregate_abs_tilt_difference:.16f}")
    print("written:")
    for path in written:
        print(f"  {path.as_posix()}")
    print("  results/figures/confidence_vs_constant_shrinkage.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
