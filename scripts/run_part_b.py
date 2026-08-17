"""Reproduce Project B Phase 1 portfolio outputs.

Run from the project root:

    python scripts/run_part_b.py

This script builds Phase 1 portfolios, Phase 2A diagnostic sentiment artifacts,
and Phase 2B look-ahead-safe sentiment fusion artifacts. It deliberately does
not build Streamlit views.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import etl, features, fusion, portfolios, sentiment  # noqa: E402


OUTPUTS = {
    "results/data/fund_returns.csv": "fund_returns",
    "results/data/fund_weights.csv": "fund_weights",
    "results/tables/performance_metrics.csv": "performance_metrics",
    "results/tables/optimisation_diagnostics.csv": "diagnostics",
    "results/tables/portfolio_turnover.csv": "turnover",
    "results/tables/asset_class_exposure.csv": "asset_class_exposure",
    "results/tables/first_live_dates.csv": "first_live_dates",
}

SENTIMENT_OUTPUTS = {
    "results/data/headline_sentiment_scores.csv": "headline_scores",
    "results/data/ticker_day_sentiment.csv": "ticker_day_sentiment",
    "results/data/sector_sentiment_index.csv": "sector_sentiment_index",
    "results/tables/sentiment_sector_month_diagnostics.csv": "sector_month_diagnostics",
    "results/tables/sentiment_candidate_cases.csv": "candidate_cases",
    "results/tables/sentiment_weighting_comparison.csv": "weighting_comparison",
    "results/tables/sentiment_weighting_disagreements.csv": "weighting_disagreements",
    "results/tables/sentiment_constituent_influence.csv": "constituent_influence",
    "results/tables/sentiment_constituent_influence_events.csv": "constituent_influence_events",
    "results/tables/sentiment_disagreement_examples.csv": "disagreement_examples",
    "results/tables/sentiment_carryover_diagnostic.csv": "carryover_diagnostic",
    "results/tables/sentiment_vader_failure_taxonomy.csv": "vader_failure_taxonomy",
    "results/tables/sentiment_return_validation.csv": "return_validation",
    "results/tables/sentiment_temporal_stability.csv": "temporal_stability",
    "results/tables/sentiment_innovation_reconnaissance.csv": "innovation_reconnaissance",
    "results/tables/sentiment_insight_register.csv": "insight_register",
}

FUSION_OUTPUTS = {
    "results/data/sector_sentiment_confidence.csv": "sector_confidence",
    "results/data/fusion_returns.csv": "fusion_returns",
    "results/data/fusion_weights.csv": "fusion_weights",
    "results/tables/sentiment_fusion_comparison.csv": "fusion_comparison",
    "results/tables/confidence_lens_summary.csv": "confidence_summary",
    "results/tables/confidence_lens_attenuation_cases.csv": "attenuation_cases",
    "results/tables/fusion_sensitivity_analysis.csv": "sensitivity_analysis",
}


def _write_csv(frame: pd.DataFrame, relative_name: str) -> pathlib.Path:
    output_path = PROJECT_ROOT / relative_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8", date_format="%Y-%m-%d")
    return output_path.relative_to(PROJECT_ROOT)


def main() -> int:
    """Build clean data, return panels, and Phase 1 OOS portfolio artifacts."""

    try:
        station1 = etl.build_station1_data()
        return_panels = features.build_return_panels(station1.equities, station1.crypto)
        suite = portfolios.build_portfolio_suite(return_panels)
        sentiment_suite = sentiment.build_sentiment_diagnostics(
            station1.headlines,
            station1.equities,
            return_panels.equity_returns,
        )
        fusion_suite = fusion.build_fusion_suite(
            fund_returns=suite.fund_returns,
            fund_weights=suite.fund_weights,
            sector_index=sentiment_suite.sector_sentiment_index,
            ticker_day_sentiment=sentiment_suite.ticker_day_sentiment,
            equity_returns=return_panels.equity_returns,
            sector_map=station1.equities.loc[:, ["ticker", "sector"]],
            output_dir=PROJECT_ROOT / "results" / "figures",
        )
        written = [
            _write_csv(getattr(suite, attribute), relative_name)
            for relative_name, attribute in OUTPUTS.items()
        ]
        written.extend(
            _write_csv(getattr(sentiment_suite, attribute), relative_name)
            for relative_name, attribute in SENTIMENT_OUTPUTS.items()
        )
        written.extend(
            _write_csv(getattr(fusion_suite, attribute), relative_name)
            for relative_name, attribute in FUSION_OUTPUTS.items()
        )
    except Exception as exc:  # pragma: no cover - command-line reporting
        print(f"Project B Phase 1 generation failed: {exc}", file=sys.stderr)
        return 1

    print("Project B Phase 1, Phase 2A, and Phase 2B outputs generated")
    print(f"equity returns: {return_panels.equity_wide.shape}")
    print(f"crypto native returns: {return_panels.crypto_native_wide.shape}")
    print(f"combined returns: {return_panels.combined_wide.shape}")
    print("written:")
    for path in written:
        print(f"  {path.as_posix()}")
    print("first live dates:")
    for _, row in suite.first_live_dates.iterrows():
        print(f"  {row['fund_family']} / {row['method']}: {pd.Timestamp(row['first_live_date']).date()}")
    fallback_counts = (
        suite.diagnostics.groupby(["fund_family", "method"], sort=True)["fallback_used"]
        .sum()
        .astype(int)
    )
    print("fallback counts:")
    for (family, method), count in fallback_counts.items():
        print(f"  {family} / {method}: {count}")
    print("sentiment diagnostics:")
    print(f"  headline scores: {sentiment_suite.headline_scores.shape}")
    print(f"  ticker-day sentiment: {sentiment_suite.ticker_day_sentiment.shape}")
    print(f"  sector sentiment index: {sentiment_suite.sector_sentiment_index.shape}")
    print(f"  insight register: {sentiment_suite.insight_register.shape}")
    print("fusion diagnostics:")
    print(f"  sector confidence: {fusion_suite.sector_confidence.shape}")
    print(f"  fusion returns: {fusion_suite.fusion_returns.shape}")
    print(f"  fusion weights: {fusion_suite.fusion_weights.shape}")
    print(f"  fusion comparison: {fusion_suite.fusion_comparison.shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
