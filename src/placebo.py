"""Phase 2C matched-shrinkage placebo falsification for Confidence Lens.

This module is additive. It consumes frozen Phase 1, Phase 2A, and Phase 2B
artifacts and writes only Phase 2C outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import fusion, portfolios


OVERLAY_PLACEBO = "Matched-Shrinkage Placebo"
PRIMARY_BASE_METHODS = (portfolios.METHOD_MIN_VARIANCE, portfolios.METHOD_MAX_SHARPE)
TOLERANCE = 1e-12


@dataclass(frozen=True)
class ShrinkageConstants:
    """Non-dynamic confidence constants and the aggregate-match proof."""

    c_mean: float
    c_match: float
    observation_count: int
    standard_abs_tilt_sum: float
    confidence_abs_tilt_sum: float
    placebo_abs_tilt_sum: float
    aggregate_abs_tilt_difference: float


@dataclass(frozen=True)
class PlaceboResult:
    """Phase 2C output artifacts."""

    constants: ShrinkageConstants
    fusion_placebo_returns: pd.DataFrame
    fusion_placebo_weights: pd.DataFrame
    comparison: pd.DataFrame
    selectivity: pd.DataFrame
    quadrants: pd.DataFrame
    sector_year: pd.DataFrame
    cases: pd.DataFrame
    turnover_decomposition: pd.DataFrame


def _valid_signal_observations(sector_confidence: pd.DataFrame) -> pd.DataFrame:
    required = {"live_rebalance_date", "sector", "z_star", "confidence"}
    missing = required - set(sector_confidence.columns)
    if missing:
        raise ValueError(f"sector_confidence missing required columns: {sorted(missing)}")
    signals = sector_confidence.copy()
    signals["live_rebalance_date"] = pd.to_datetime(signals["live_rebalance_date"])
    for column in ["z_star", "confidence"]:
        signals[column] = pd.to_numeric(signals[column], errors="coerce")
    valid = signals.loc[signals["z_star"].notna() & signals["confidence"].notna()].copy()
    if valid.empty:
        raise ValueError("no valid rebalance-sector observations for matched shrinkage")
    if valid["confidence"].lt(-TOLERANCE).any() or valid["confidence"].gt(1.0 + TOLERANCE).any():
        raise ValueError("confidence values must lie in [0, 1]")
    return valid.sort_values(["live_rebalance_date", "sector"]).reset_index(drop=True)


def calculate_shrinkage_constants(
    sector_confidence: pd.DataFrame,
    *,
    tilt_strength: float = fusion.PRIMARY_TILT,
) -> ShrinkageConstants:
    """Calculate C_mean and C_match without realised return information."""

    valid = _valid_signal_observations(sector_confidence)
    abs_z = valid["z_star"].abs()
    denominator = float(abs_z.sum())
    if denominator <= 0:
        raise ValueError("cannot match shrinkage when all absolute z_star values are zero")

    c_mean = float(valid["confidence"].mean())
    c_match = float((abs_z * valid["confidence"]).sum() / denominator)
    confidence_abs = float((tilt_strength * valid["z_star"] * valid["confidence"]).abs().sum())
    placebo_abs = float((tilt_strength * valid["z_star"] * c_match).abs().sum())
    standard_abs = float((tilt_strength * valid["z_star"]).abs().sum())
    return ShrinkageConstants(
        c_mean=c_mean,
        c_match=c_match,
        observation_count=int(len(valid)),
        standard_abs_tilt_sum=standard_abs,
        confidence_abs_tilt_sum=confidence_abs,
        placebo_abs_tilt_sum=placebo_abs,
        aggregate_abs_tilt_difference=float(placebo_abs - confidence_abs),
    )


def build_selectivity_table(
    sector_confidence: pd.DataFrame,
    constants: ShrinkageConstants,
    *,
    tilt_strength: float = fusion.PRIMARY_TILT,
    tolerance: float = 1e-10,
) -> pd.DataFrame:
    """Create the rebalance-sector placebo-vs-Confidence selectivity panel."""

    valid = _valid_signal_observations(sector_confidence)
    output = valid.copy()
    if "signal_cutoff_date" not in output.columns:
        output["signal_cutoff_date"] = pd.NaT
    output["signal_cutoff_date"] = pd.to_datetime(output["signal_cutoff_date"])
    output["standard_tilt"] = tilt_strength * output["z_star"]
    output["placebo_tilt"] = tilt_strength * output["z_star"] * constants.c_match
    output["confidence_tilt"] = tilt_strength * output["z_star"] * output["confidence"]
    output["c_match"] = constants.c_match
    output["confidence_minus_placebo_tilt"] = output["confidence_tilt"] - output["placebo_tilt"]
    output["selective_deviation"] = output["confidence_minus_placebo_tilt"].abs()
    output["standard_multiplier"] = 1.0 + output["standard_tilt"]
    output["placebo_multiplier"] = 1.0 + output["placebo_tilt"]
    output["confidence_multiplier"] = 1.0 + output["confidence_tilt"]
    output["confidence_group"] = np.select(
        [
            output["confidence"].lt(constants.c_match - tolerance),
            output["confidence"].gt(constants.c_match + tolerance),
        ],
        ["C < C_match", "C > C_match"],
        default="C ~= C_match",
    )
    columns = [
        "live_rebalance_date",
        "signal_cutoff_date",
        "sector",
        "z_star",
        "standard_tilt",
        "placebo_tilt",
        "confidence_tilt",
        "b63",
        "a21",
        "confidence",
        "c_match",
        "confidence_minus_placebo_tilt",
        "selective_deviation",
        "standard_multiplier",
        "placebo_multiplier",
        "confidence_multiplier",
        "confidence_group",
    ]
    available = [column for column in columns if column in output.columns]
    return output.loc[:, available].sort_values(["live_rebalance_date", "sector"]).reset_index(drop=True)


def apply_matched_placebo_overlay(
    base_weights: pd.DataFrame,
    selectivity: pd.DataFrame,
    *,
    c_match: float,
    tilt_strength: float = fusion.PRIMARY_TILT,
) -> pd.DataFrame:
    """Apply one global matched-shrinkage constant to sector sentiment direction."""

    required = {"date", "asset", "sector", "weight", "fund_family", "method"}
    missing = required - set(base_weights.columns)
    if missing:
        raise ValueError(f"base_weights missing required columns: {sorted(missing)}")
    if not (0.0 <= c_match <= 1.0):
        raise ValueError("c_match must lie in [0, 1]")

    signals = selectivity.loc[:, ["live_rebalance_date", "sector", "z_star"]].copy()
    signals["live_rebalance_date"] = pd.to_datetime(signals["live_rebalance_date"])
    signals["selected_multiplier"] = 1.0 + tilt_strength * signals["z_star"] * c_match

    rows: list[pd.DataFrame] = []
    for date, group in base_weights.groupby("date", sort=True):
        signal = signals.loc[signals["live_rebalance_date"].eq(pd.Timestamp(date))]
        multiplier = signal.set_index("sector")["selected_multiplier"].to_dict()
        working = group.copy()
        working["pre_normalisation_multiplier"] = working["sector"].map(multiplier).fillna(1.0)
        working["pre_normalisation_weight"] = working["weight"] * working["pre_normalisation_multiplier"]
        normalised = working.set_index("asset")["pre_normalisation_weight"]
        normalised = normalised.clip(lower=0.0)
        total = float(normalised.sum())
        if total <= 0 or not np.isfinite(total):
            raise ValueError("placebo weights must have positive finite total")
        working["base_weight"] = working["weight"]
        working["weight"] = normalised.div(total).reindex(working["asset"]).to_numpy()
        working["overlay"] = OVERLAY_PLACEBO
        working["tilt_strength"] = tilt_strength
        working["c_match"] = c_match
        rows.append(working)

    output = pd.concat(rows, ignore_index=True)
    if output["weight"].lt(-1e-10).any():
        raise ValueError("placebo weights must remain long-only")
    sums = output.groupby(["date", "fund_family", "method", "overlay"])["weight"].sum()
    if not np.allclose(sums.to_numpy(dtype=float), 1.0):
        raise ValueError("placebo weights must remain fully invested")
    return output.sort_values(["date", "asset"]).reset_index(drop=True)


def _metric_rows(returns: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    shape_rows = []
    for keys, group in weights.groupby(["base_method", "overlay", "date"], sort=True):
        base_method, overlay, date = keys
        asset_weights = group["weight"].astype(float)
        sector_weights = group.groupby("sector", sort=True)["weight"].sum()
        shape_rows.append(
            {
                "base_method": base_method,
                "overlay": overlay,
                "date": date,
                "effective_number_holdings": 1.0 / float((asset_weights**2).sum())
                if (asset_weights**2).sum() > 0
                else np.nan,
                "maximum_single_asset_weight": float(asset_weights.max()),
                "maximum_sector_weight": float(sector_weights.max()),
                "sector_concentration_hhi": float((sector_weights**2).sum()),
            }
        )
    shape = pd.DataFrame(shape_rows)
    rows = []
    for keys, group in returns.groupby(["base_method", "overlay"], sort=True):
        base_method, overlay = keys
        group = group.sort_values("date").set_index("date")
        metrics = portfolios.performance_metrics(
            group["net_return"],
            periods_per_year=portfolios.ANNUALISATION[portfolios.FAMILY_EQUITY],
        )
        shape_group = shape.loc[shape["base_method"].eq(base_method) & shape["overlay"].eq(overlay)]
        rebalances = group.loc[group["turnover"].gt(0)]
        rows.append(
            {
                "base_method": base_method,
                "overlay": overlay,
                "annualised_return": metrics["annualised_return"],
                "annualised_volatility": metrics["annualised_volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "max_drawdown": metrics["max_drawdown"],
                "total_turnover": float(group["turnover"].sum()),
                "average_rebalance_turnover": float(rebalances["turnover"].mean()) if not rebalances.empty else 0.0,
                "transaction_cost_drag": float(group["transaction_cost"].sum()),
                "effective_number_holdings": float(shape_group["effective_number_holdings"].mean()),
                "maximum_single_asset_weight": float(shape_group["maximum_single_asset_weight"].max()),
                "maximum_sector_weight": float(shape_group["maximum_sector_weight"].max()),
                "sector_concentration_hhi": float(shape_group["sector_concentration_hhi"].mean()),
                "number_of_rebalances": int(group["turnover"].gt(0).sum()),
                "observation_count": int(group["net_return"].dropna().shape[0]),
                "sample_start": group.index.min(),
                "sample_end": group.index.max(),
            }
        )

    metrics = pd.DataFrame(rows)
    increments = []
    for base_method, group in metrics.groupby("base_method", sort=True):
        lookup = group.set_index("overlay")
        pairs = [
            ("Placebo minus Base", OVERLAY_PLACEBO, fusion.OVERLAY_BASE),
            ("Confidence Lens minus Base", fusion.OVERLAY_CONFIDENCE, fusion.OVERLAY_BASE),
            ("Confidence Lens minus Standard", fusion.OVERLAY_CONFIDENCE, fusion.OVERLAY_STANDARD),
            ("Confidence Lens minus Placebo", fusion.OVERLAY_CONFIDENCE, OVERLAY_PLACEBO),
        ]
        for label, left_name, right_name in pairs:
            left = lookup.loc[left_name]
            right = lookup.loc[right_name]
            row = {"base_method": base_method, "overlay": label}
            for column in [
                "annualised_return",
                "annualised_volatility",
                "sharpe_ratio",
                "max_drawdown",
                "total_turnover",
                "average_rebalance_turnover",
                "transaction_cost_drag",
                "effective_number_holdings",
                "maximum_single_asset_weight",
                "maximum_sector_weight",
                "sector_concentration_hhi",
            ]:
                row[column] = left[column] - right[column]
            row["number_of_rebalances"] = int(left["number_of_rebalances"])
            row["observation_count"] = int(left["observation_count"])
            row["sample_start"] = left["sample_start"]
            row["sample_end"] = left["sample_end"]
            increments.append(row)
    return pd.concat([metrics, pd.DataFrame(increments)], ignore_index=True).sort_values(
        ["base_method", "overlay"]
    ).reset_index(drop=True)


def _quadrants(selectivity: pd.DataFrame) -> pd.DataFrame:
    b_median = float(selectivity["b63"].median())
    a_median = float(selectivity["a21"].median())
    working = selectivity.copy()
    breadth_label = np.where(working["b63"].ge(b_median), "High Breadth", "Low Breadth")
    agreement_label = np.where(working["a21"].ge(a_median), "High Agreement", "Low Agreement")
    working["quadrant"] = pd.Series(breadth_label, index=working.index) + " / " + pd.Series(
        agreement_label,
        index=working.index,
    )
    total = len(working)
    return (
        working.groupby("quadrant", sort=True)
        .agg(
            observation_count=("quadrant", "size"),
            average_b63=("b63", "mean"),
            average_a21=("a21", "mean"),
            average_confidence=("confidence", "mean"),
            average_abs_standard_tilt=("standard_tilt", lambda s: s.abs().mean()),
            average_abs_placebo_tilt=("placebo_tilt", lambda s: s.abs().mean()),
            average_abs_confidence_tilt=("confidence_tilt", lambda s: s.abs().mean()),
            average_selective_deviation=("selective_deviation", "mean"),
        )
        .reset_index()
        .assign(sample_percent=lambda df: 100.0 * df["observation_count"] / total)
        .loc[
            :,
            [
                "quadrant",
                "observation_count",
                "sample_percent",
                "average_b63",
                "average_a21",
                "average_confidence",
                "average_abs_standard_tilt",
                "average_abs_placebo_tilt",
                "average_abs_confidence_tilt",
                "average_selective_deviation",
            ],
        ]
    )


def _sector_year(selectivity: pd.DataFrame) -> pd.DataFrame:
    working = selectivity.copy()
    working["year"] = pd.to_datetime(working["live_rebalance_date"]).dt.year
    year = (
        working.groupby("year", sort=True)
        .agg(
            average_confidence=("confidence", "mean"),
            average_selective_deviation=("selective_deviation", "mean"),
            observation_count=("year", "size"),
        )
        .reset_index()
        .rename(columns={"year": "bucket"})
    )
    year["scope"] = "year"
    sector = (
        working.groupby("sector", sort=True)
        .agg(
            average_confidence=("confidence", "mean"),
            average_selective_deviation=("selective_deviation", "mean"),
            proportion_c_below_c_match=("confidence_group", lambda s: float((s == "C < C_match").mean())),
            observation_count=("sector", "size"),
        )
        .reset_index()
        .rename(columns={"sector": "bucket"})
    )
    sector["scope"] = "sector"
    year["proportion_c_below_c_match"] = np.nan
    return pd.concat([year, sector], ignore_index=True).loc[
        :,
        [
            "scope",
            "bucket",
            "observation_count",
            "average_confidence",
            "average_selective_deviation",
            "proportion_c_below_c_match",
        ],
    ]


def _sector_weights(weights: pd.DataFrame) -> pd.DataFrame:
    return (
        weights.groupby(["base_method", "overlay", "date", "sector"], sort=True)["weight"]
        .sum()
        .reset_index()
        .rename(columns={"date": "live_rebalance_date", "weight": "sector_weight"})
    )


def _case_rows(selectivity: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    sector_weights = _sector_weights(weights)
    piv = sector_weights.pivot_table(
        index=["base_method", "live_rebalance_date", "sector"],
        columns="overlay",
        values="sector_weight",
        aggfunc="first",
    ).reset_index()

    rows = []
    for base_method in PRIMARY_BASE_METHODS:
        method_weights = piv.loc[piv["base_method"].eq(base_method)]
        merged = selectivity.merge(method_weights, on=["live_rebalance_date", "sector"], how="left")
        merged["base_method"] = base_method
        merged["abs_gap"] = merged["confidence_minus_placebo_tilt"].abs()
        base_exposure = merged.get(fusion.OVERLAY_BASE, pd.Series(np.nan, index=merged.index))
        informative = merged.loc[base_exposure.fillna(0.0).gt(0.01)].copy()
        case_pool = informative if not informative.empty else merged
        weak = case_pool.loc[case_pool["confidence"].lt(case_pool["c_match"])].sort_values(
            ["abs_gap", "selective_deviation"],
            ascending=False,
        )
        strong = case_pool.loc[case_pool["confidence"].gt(case_pool["c_match"])].sort_values(
            ["abs_gap", "selective_deviation"],
            ascending=False,
        )
        neutral = case_pool.sort_values(["abs_gap", "selective_deviation"], ascending=True)
        misleading = case_pool.loc[
            (case_pool["confidence"].gt(case_pool["c_match"]))
            & (case_pool["b63"].lt(case_pool["b63"].median()))
        ].sort_values(["abs_gap", "confidence"], ascending=False)
        specs = [
            ("weak_evidence_more_attenuation_than_placebo", weak),
            ("strong_evidence_less_attenuation_than_placebo", strong),
            ("neutral_confidence_similar_to_placebo", neutral),
            ("skeptical_counterexample_dynamic_may_be_unnecessary", misleading if not misleading.empty else neutral),
        ]
        for case_type, frame in specs:
            if frame.empty:
                continue
            row = frame.iloc[0]
            rows.append(
                {
                    "case_type": case_type,
                    "base_method": base_method,
                    "date": row["live_rebalance_date"],
                    "sector": row["sector"],
                    "z_star": row["z_star"],
                    "b63": row["b63"],
                    "a21": row["a21"],
                    "confidence": row["confidence"],
                    "c_match": row["c_match"],
                    "standard_multiplier": row["standard_multiplier"],
                    "placebo_multiplier": row["placebo_multiplier"],
                    "confidence_multiplier": row["confidence_multiplier"],
                    "base_sector_weight": row.get(fusion.OVERLAY_BASE, np.nan),
                    "standard_sector_weight": row.get(fusion.OVERLAY_STANDARD, np.nan),
                    "placebo_sector_weight": row.get(OVERLAY_PLACEBO, np.nan),
                    "confidence_sector_weight": row.get(fusion.OVERLAY_CONFIDENCE, np.nan),
                    "confidence_minus_placebo_tilt": row["confidence_minus_placebo_tilt"],
                    "selective_deviation": row["selective_deviation"],
                    "case_selection_rule": "deterministic from signal/evidence state only; no subsequent returns used",
                }
            )
    return pd.DataFrame(rows).sort_values(["base_method", "case_type"]).reset_index(drop=True)


def _turnover_decomposition(comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for base_method, group in comparison.groupby("base_method", sort=True):
        lookup = group.set_index("overlay")
        base = float(lookup.loc[fusion.OVERLAY_BASE, "total_turnover"])
        standard = float(lookup.loc[fusion.OVERLAY_STANDARD, "total_turnover"])
        placebo = float(lookup.loc[OVERLAY_PLACEBO, "total_turnover"])
        confidence = float(lookup.loc[fusion.OVERLAY_CONFIDENCE, "total_turnover"])
        standard_inc = standard - base
        placebo_inc = placebo - base
        confidence_inc = confidence - base
        observed_reduction = standard_inc - confidence_inc
        placebo_reduction = standard_inc - placebo_inc
        explained = placebo_reduction / observed_reduction if abs(observed_reduction) > TOLERANCE else np.nan
        rows.append(
            {
                "base_method": base_method,
                "base_total_turnover": base,
                "standard_total_turnover": standard,
                "placebo_total_turnover": placebo,
                "confidence_total_turnover": confidence,
                "incremental_turnover_standard_vs_base": standard_inc,
                "incremental_turnover_placebo_vs_base": placebo_inc,
                "incremental_turnover_confidence_vs_base": confidence_inc,
                "standard_to_confidence_turnover_reduction": observed_reduction,
                "standard_to_placebo_turnover_reduction": placebo_reduction,
                "constant_shrinkage_explained_share": explained,
                "constant_shrinkage_explained_percent": 100.0 * explained if pd.notna(explained) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _plot_placebo_figure(selectivity: pd.DataFrame, quadrants: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c_match = float(selectivity["c_match"].iloc[0])

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.8), gridspec_kw={"width_ratios": [1.05, 1.2]})
    ax = axes[0]
    observed = selectivity.sort_values("confidence")
    ax.scatter(
        observed["confidence"],
        observed["confidence"].abs(),
        s=18,
        color="#009E73",
        alpha=0.42,
        label="Confidence Lens",
    )
    ax.axhline(c_match, color="#D55E00", linewidth=2.2, label="Matched placebo")
    ax.plot([0, 1], [0, 1], color="#009E73", linewidth=1.5, alpha=0.7)
    ax.set_title("Dynamic vs Constant Shrinkage")
    ax.set_xlabel("Evidence confidence C")
    ax.set_ylabel("Absolute tilt as share of Standard")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, loc="upper left")

    ax = axes[1]
    order = [
        "High Breadth / High Agreement",
        "High Breadth / Low Agreement",
        "Low Breadth / High Agreement",
        "Low Breadth / Low Agreement",
    ]
    plot = quadrants.set_index("quadrant").reindex(order).dropna(how="all").reset_index()
    y = np.arange(len(plot))
    ax.barh(y - 0.18, plot["average_abs_placebo_tilt"], height=0.32, color="#D55E00", label="Placebo")
    ax.barh(y + 0.18, plot["average_abs_confidence_tilt"], height=0.32, color="#009E73", label="Confidence Lens")
    ax.set_yticks(y)
    ax.set_yticklabels(plot["quadrant"], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_title("Average Absolute Tilt by Evidence State")
    ax.set_xlabel("Absolute pre-normalisation tilt")
    ax.grid(True, axis="x", alpha=0.25)
    ax.legend(frameon=False, loc="lower right")

    fig.suptitle("Matched Shrinkage Holds Average Signal Strength Constant")
    fig.text(
        0.01,
        0.01,
        "Sample: 2021-2023 monthly rebalance-sector observations. Source: Project B Phase 2B frozen signals.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def build_placebo_suite(
    *,
    sector_confidence: pd.DataFrame,
    fusion_returns: pd.DataFrame,
    fusion_weights: pd.DataFrame,
    equity_returns: pd.DataFrame,
    output_dir: Path | None = None,
    tilt_strength: float = fusion.PRIMARY_TILT,
) -> PlaceboResult:
    """Build the complete Phase 2C matched-shrinkage falsification artifacts."""

    constants = calculate_shrinkage_constants(sector_confidence, tilt_strength=tilt_strength)
    selectivity = build_selectivity_table(sector_confidence, constants, tilt_strength=tilt_strength)

    base_existing = fusion_returns.loc[
        fusion_returns["tilt_strength"].eq(tilt_strength)
        & fusion_returns["overlay"].isin([fusion.OVERLAY_BASE, fusion.OVERLAY_STANDARD, fusion.OVERLAY_CONFIDENCE])
        & fusion_returns["base_method"].isin(PRIMARY_BASE_METHODS)
    ].copy()
    weights_existing = fusion_weights.loc[
        fusion_weights["tilt_strength"].eq(tilt_strength)
        & fusion_weights["overlay"].isin([fusion.OVERLAY_BASE, fusion.OVERLAY_STANDARD, fusion.OVERLAY_CONFIDENCE])
        & fusion_weights["base_method"].isin(PRIMARY_BASE_METHODS)
    ].copy()
    base_existing["date"] = pd.to_datetime(base_existing["date"])
    weights_existing["date"] = pd.to_datetime(weights_existing["date"])

    all_returns = [base_existing]
    all_weights = [weights_existing]
    for method in PRIMARY_BASE_METHODS:
        method_base_weights = weights_existing.loc[
            weights_existing["base_method"].eq(method) & weights_existing["overlay"].eq(fusion.OVERLAY_BASE)
        ].copy()
        method_base_returns = base_existing.loc[
            base_existing["base_method"].eq(method) & base_existing["overlay"].eq(fusion.OVERLAY_BASE)
        ].copy()
        placebo_weights = apply_matched_placebo_overlay(
            method_base_weights,
            selectivity,
            c_match=constants.c_match,
            tilt_strength=tilt_strength,
        )
        placebo_weights["base_method"] = method
        placebo_returns, _turnover = fusion.backtest_overlay_returns(
            method,
            placebo_weights,
            method_base_returns,
            equity_returns,
            overlay=OVERLAY_PLACEBO,
            tilt_strength=tilt_strength,
        )
        all_weights.append(placebo_weights)
        all_returns.append(placebo_returns)

    placebo_returns_all = pd.concat(all_returns, ignore_index=True).sort_values(
        ["base_method", "overlay", "date"]
    ).reset_index(drop=True)
    placebo_weights_all = pd.concat(all_weights, ignore_index=True).sort_values(
        ["base_method", "overlay", "date", "asset"]
    ).reset_index(drop=True)

    date_counts = placebo_returns_all.groupby(["base_method", "overlay"])["date"].nunique().unstack()
    if date_counts.nunique(axis=1).ne(1).any():
        raise ValueError("all four portfolio states must share identical OOS date counts")
    for base_method, group in placebo_returns_all.groupby("base_method", sort=True):
        dates_by_overlay = {
            overlay: set(pd.to_datetime(frame["date"]))
            for overlay, frame in group.groupby("overlay", sort=True)
        }
        if len({frozenset(dates) for dates in dates_by_overlay.values()}) != 1:
            raise ValueError(f"all four portfolio states must share identical OOS dates for {base_method}")

    comparison = _metric_rows(placebo_returns_all, placebo_weights_all)
    quadrants = _quadrants(selectivity)
    sector_year = _sector_year(selectivity)
    cases = _case_rows(selectivity, placebo_weights_all)
    turnover = _turnover_decomposition(
        comparison.loc[
            comparison["overlay"].isin(
                [fusion.OVERLAY_BASE, fusion.OVERLAY_STANDARD, OVERLAY_PLACEBO, fusion.OVERLAY_CONFIDENCE]
            )
        ]
    )

    if output_dir is not None:
        _plot_placebo_figure(selectivity, quadrants, output_dir / "confidence_vs_constant_shrinkage.png")

    return PlaceboResult(
        constants=constants,
        fusion_placebo_returns=placebo_returns_all,
        fusion_placebo_weights=placebo_weights_all,
        comparison=comparison,
        selectivity=selectivity,
        quadrants=quadrants,
        sector_year=sector_year,
        cases=cases,
        turnover_decomposition=turnover,
    )


__all__ = [
    "OVERLAY_PLACEBO",
    "PlaceboResult",
    "ShrinkageConstants",
    "apply_matched_placebo_overlay",
    "build_placebo_suite",
    "build_selectivity_table",
    "calculate_shrinkage_constants",
]
