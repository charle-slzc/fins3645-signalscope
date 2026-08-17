"""Phase 2B look-ahead-safe sentiment fusion and Confidence Lens.

This module consumes frozen Phase 1 portfolio outputs and Phase 2A sentiment
artifacts. It does not rescore headlines, rebuild sector sentiment, or alter the
portfolio optimiser. All trading signals are formed through the base portfolio's
decision date, which is the final trading day before the new weights go live.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import portfolios


OVERLAY_BASE = "Base"
OVERLAY_STANDARD = "Standard Sentiment"
OVERLAY_CONFIDENCE = "SignalScope Confidence Lens"
PRIMARY_TILT = 0.10
SENSITIVITY_TILTS = (0.05, 0.10, 0.20)
DIRECTION_WINDOW = 21
BREADTH_WINDOW = 63
Z_CLIP = 2.0
MATERIAL_ATTENUATION = 0.25


@dataclass(frozen=True)
class FusionResult:
    """Phase 2B output artifacts."""

    sector_confidence: pd.DataFrame
    fusion_returns: pd.DataFrame
    fusion_weights: pd.DataFrame
    fusion_comparison: pd.DataFrame
    confidence_summary: pd.DataFrame
    attenuation_cases: pd.DataFrame
    sensitivity_analysis: pd.DataFrame


def _trading_calendar_from_sector_index(sector_index: pd.DataFrame) -> pd.DatetimeIndex:
    calendar = pd.DatetimeIndex(pd.to_datetime(sector_index["date"]).drop_duplicates()).sort_values()
    if calendar.empty:
        raise ValueError("sector sentiment index must contain trading dates")
    return calendar


def _window_dates(calendar: pd.DatetimeIndex, cutoff: pd.Timestamp, window: int) -> pd.DatetimeIndex:
    eligible = calendar[calendar <= pd.Timestamp(cutoff)]
    if len(eligible) < window:
        return eligible
    return eligible[-window:]


def _sector_universe(sector_map: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "sector"}
    missing = required - set(sector_map.columns)
    if missing:
        raise ValueError(f"sector_map missing required columns: {sorted(missing)}")
    universe = sector_map.loc[:, ["ticker", "sector"]].drop_duplicates().sort_values(["sector", "ticker"])
    conflicts = universe.groupby("ticker")["sector"].nunique()
    conflicts = conflicts[conflicts > 1]
    if not conflicts.empty:
        raise ValueError(f"ticker has conflicting sector labels: {conflicts.index[:5].tolist()}")
    return universe.reset_index(drop=True)


def population_vader_dispersion(values: pd.Series) -> float:
    """Population dispersion for VADER compound scores in [-1, 1]."""

    scores = pd.Series(values).dropna().astype(float)
    if scores.empty:
        return np.nan
    if scores.lt(-1.0).any() or scores.gt(1.0).any():
        raise ValueError("VADER compound scores must lie in [-1, 1]")
    dispersion = float(scores.std(ddof=0))
    if dispersion < -1e-12 or dispersion > 1.0 + 1e-12:
        raise ValueError("population VADER dispersion must be bounded in [0, 1]")
    return min(max(dispersion, 0.0), 1.0)


def compute_sector_confidence_signals(
    sector_index: pd.DataFrame,
    ticker_day_sentiment: pd.DataFrame,
    sector_map: pd.DataFrame,
    rebalance_dates: pd.DataFrame,
    *,
    direction_window: int = DIRECTION_WINDOW,
    breadth_window: int = BREADTH_WINDOW,
    z_clip: float = Z_CLIP,
) -> pd.DataFrame:
    """Build S21, B63, A21, and C using data through each signal cutoff only."""

    required_rebalance = {"live_rebalance_date", "decision_date"}
    missing = required_rebalance - set(rebalance_dates.columns)
    if missing:
        raise ValueError(f"rebalance_dates missing required columns: {sorted(missing)}")

    sector = sector_index.copy()
    sector["date"] = pd.to_datetime(sector["date"])
    ticker = ticker_day_sentiment.copy()
    ticker["date"] = pd.to_datetime(ticker["date"])
    universe = _sector_universe(sector_map)
    sectors = sorted(universe["sector"].unique())
    possible_tickers = universe.groupby("sector")["ticker"].nunique().to_dict()
    calendar = _trading_calendar_from_sector_index(sector)

    ticker_dispersion = (
        ticker.groupby(["date", "sector"], sort=True)["ticker_sentiment"]
        .agg(population_vader_dispersion)
        .rename("d_day")
        .reset_index()
    )

    rebalance = rebalance_dates.loc[:, ["live_rebalance_date", "decision_date"]].drop_duplicates().copy()
    rebalance["live_rebalance_date"] = pd.to_datetime(rebalance["live_rebalance_date"])
    rebalance["decision_date"] = pd.to_datetime(rebalance["decision_date"])
    rebalance = rebalance.sort_values(["live_rebalance_date", "decision_date"]).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for _, rebal in rebalance.iterrows():
        live_date = pd.Timestamp(rebal["live_rebalance_date"])
        cutoff = pd.Timestamp(rebal["decision_date"])
        if not cutoff < live_date:
            raise ValueError("signal cutoff must be before live rebalance date")

        direction_dates = _window_dates(calendar, cutoff, direction_window)
        breadth_dates = _window_dates(calendar, cutoff, breadth_window)
        direction_frame = sector.loc[sector["date"].isin(direction_dates)]
        breadth_frame = ticker.loc[ticker["date"].isin(breadth_dates)]
        disagreement_frame = ticker_dispersion.loc[ticker_dispersion["date"].isin(direction_dates)]

        s21_by_sector = direction_frame.groupby("sector", sort=True)["sector_sentiment"].mean()
        d21_by_sector = disagreement_frame.groupby("sector", sort=True)["d_day"].mean()
        s21_values = s21_by_sector.reindex(sectors)
        usable = s21_values.dropna()
        if len(usable) >= 2:
            std = float(usable.std(ddof=0))
            if std > 0:
                z_values = (s21_values - float(usable.mean())) / std
            else:
                z_values = pd.Series(0.0, index=s21_values.index)
        else:
            z_values = pd.Series(np.nan, index=s21_values.index)
        z_star_values = z_values.clip(-z_clip, z_clip)

        observed_pairs = breadth_frame.groupby("sector", sort=True)["ticker"].nunique()
        # Numerator is observed ticker-days, not distinct tickers: count one
        # observed ticker-day per sector/ticker/date row in the frozen ticker-day artifact.
        observed_ticker_days = breadth_frame.groupby("sector", sort=True).size()

        for sector_name in sectors:
            possible = int(possible_tickers[sector_name]) * len(breadth_dates)
            observed = int(observed_ticker_days.get(sector_name, 0))
            b63 = observed / possible if possible else np.nan
            d21 = d21_by_sector.get(sector_name, np.nan)
            a21 = np.nan if pd.isna(d21) else 1.0 - float(d21)
            if pd.notna(a21):
                a21 = min(max(a21, 0.0), 1.0)
            confidence = b63 * a21 if pd.notna(b63) and pd.notna(a21) else np.nan
            z_star = z_star_values.get(sector_name, np.nan)
            raw_tilt = PRIMARY_TILT * z_star if pd.notna(z_star) else 0.0
            confidence_tilt = raw_tilt * confidence if pd.notna(confidence) else 0.0
            rows.append(
                {
                    "live_rebalance_date": live_date,
                    "signal_cutoff_date": cutoff,
                    "sector": sector_name,
                    "s21": s21_values.get(sector_name, np.nan),
                    "z_score": z_values.get(sector_name, np.nan),
                    "z_star": z_star,
                    "b63": b63,
                    "a21": a21,
                    "confidence": confidence,
                    "standard_multiplier": 1.0 + raw_tilt,
                    "confidence_multiplier": 1.0 + confidence_tilt,
                    "raw_tilt": raw_tilt,
                    "confidence_adjusted_tilt": confidence_tilt,
                    "direction_window_observation_count": int(
                        direction_frame.loc[direction_frame["sector"].eq(sector_name), "sector_sentiment"].notna().sum()
                    ),
                    "breadth_observed_ticker_days": observed,
                    "breadth_possible_ticker_days": possible,
                    "disagreement_observation_count": int(
                        disagreement_frame.loc[disagreement_frame["sector"].eq(sector_name), "d_day"].notna().sum()
                    ),
                    "direction_window_start": direction_dates.min() if len(direction_dates) else pd.NaT,
                    "direction_window_end": direction_dates.max() if len(direction_dates) else pd.NaT,
                    "breadth_window_start": breadth_dates.min() if len(breadth_dates) else pd.NaT,
                    "breadth_window_end": breadth_dates.max() if len(breadth_dates) else pd.NaT,
                }
            )

    output = pd.DataFrame(rows)
    bounded = output[["b63", "a21", "confidence"]].dropna()
    if not bounded.empty and ((bounded < -1e-12) | (bounded > 1.0 + 1e-12)).any().any():
        raise ValueError("B63, A21, and confidence must lie in [0, 1]")
    return output.sort_values(["live_rebalance_date", "sector"]).reset_index(drop=True)


def _normalise_weights(weights: pd.Series) -> pd.Series:
    total = float(weights.sum())
    if total <= 0 or not np.isfinite(total):
        raise ValueError("overlay weights must have positive finite total before normalisation")
    cleaned = weights / total
    if cleaned.lt(-1e-10).any():
        raise ValueError("overlay weights must remain long-only")
    return cleaned.clip(lower=0.0) / cleaned.clip(lower=0.0).sum()


def apply_sector_overlay(
    base_weights: pd.DataFrame,
    sector_confidence: pd.DataFrame,
    *,
    overlay: str,
    tilt_strength: float = PRIMARY_TILT,
) -> pd.DataFrame:
    """Apply Standard or Confidence multipliers to rebalance weights."""

    if overlay not in {OVERLAY_STANDARD, OVERLAY_CONFIDENCE}:
        raise ValueError(f"unknown overlay: {overlay}")
    required = {"date", "asset", "sector", "weight", "fund_family", "method"}
    missing = required - set(base_weights.columns)
    if missing:
        raise ValueError(f"base_weights missing required columns: {sorted(missing)}")

    signals = sector_confidence.copy()
    signals["live_rebalance_date"] = pd.to_datetime(signals["live_rebalance_date"])
    if tilt_strength == PRIMARY_TILT:
        signals["standard_tilt"] = signals["raw_tilt"]
        signals["confidence_tilt"] = signals["confidence_adjusted_tilt"]
    else:
        z = signals["z_star"].fillna(0.0)
        c = signals["confidence"].fillna(0.0)
        signals["standard_tilt"] = tilt_strength * z
        signals["confidence_tilt"] = tilt_strength * z * c
    signals["selected_multiplier"] = np.where(
        overlay == OVERLAY_STANDARD,
        1.0 + signals["standard_tilt"],
        1.0 + signals["confidence_tilt"],
    )

    rows: list[pd.DataFrame] = []
    for date, group in base_weights.groupby("date", sort=True):
        signal = signals.loc[signals["live_rebalance_date"].eq(pd.Timestamp(date))]
        multiplier = signal.set_index("sector")["selected_multiplier"].to_dict()
        working = group.copy()
        working["pre_normalisation_multiplier"] = working["sector"].map(multiplier).fillna(1.0)
        working["pre_normalisation_weight"] = working["weight"] * working["pre_normalisation_multiplier"]
        working["overlay_weight"] = _normalise_weights(working.set_index("asset")["pre_normalisation_weight"]).reindex(
            working["asset"]
        ).to_numpy()
        working["overlay"] = overlay
        working["tilt_strength"] = tilt_strength
        rows.append(working)
    output = pd.concat(rows, ignore_index=True)
    output["base_weight"] = output["weight"]
    output["weight"] = output["overlay_weight"]
    return output.drop(columns=["overlay_weight"]).sort_values(["date", "overlay", "asset"]).reset_index(drop=True)


def _base_rebalance_weights(
    fund_weights: pd.DataFrame,
    sector_map: pd.DataFrame,
    method: str,
) -> pd.DataFrame:
    weights = fund_weights.loc[
        fund_weights["fund_family"].eq(portfolios.FAMILY_EQUITY) & fund_weights["method"].eq(method)
    ].copy()
    weights["date"] = pd.to_datetime(weights["date"])
    sector_lookup = _sector_universe(sector_map).set_index("ticker")["sector"]
    weights["sector"] = weights["asset"].map(sector_lookup)
    if weights["sector"].isna().any():
        missing = sorted(weights.loc[weights["sector"].isna(), "asset"].unique())
        raise ValueError(f"missing sector for assets: {missing[:5]}")
    return weights.sort_values(["date", "asset"]).reset_index(drop=True)


def _base_returns(fund_returns: pd.DataFrame, method: str) -> pd.DataFrame:
    returns = fund_returns.loc[
        fund_returns["fund_family"].eq(portfolios.FAMILY_EQUITY) & fund_returns["method"].eq(method)
    ].copy()
    returns["date"] = pd.to_datetime(returns["date"])
    returns["live_rebalance_date"] = pd.to_datetime(returns["live_rebalance_date"])
    returns["decision_date"] = pd.to_datetime(returns["decision_date"])
    return returns.sort_values("date").reset_index(drop=True)


def _equity_return_wide(equity_returns: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "ticker", "daily_return"}
    missing = required - set(equity_returns.columns)
    if missing:
        raise ValueError(f"equity_returns missing required columns: {sorted(missing)}")
    working = equity_returns.copy()
    working["date"] = pd.to_datetime(working["date"])
    return working.pivot(index="date", columns="ticker", values="daily_return").sort_index().sort_index(axis=1)


def _weights_for_dates(rebalance_weights: pd.DataFrame, returns_dates: pd.DatetimeIndex) -> dict[pd.Timestamp, pd.Series]:
    weights_by_date = {
        pd.Timestamp(date): group.set_index("asset")["weight"].astype(float)
        for date, group in rebalance_weights.groupby("date", sort=True)
    }
    rebalance_dates = sorted(weights_by_date)
    current = None
    mapped: dict[pd.Timestamp, pd.Series] = {}
    for date in returns_dates:
        eligible = [rebalance for rebalance in rebalance_dates if rebalance <= pd.Timestamp(date)]
        if eligible:
            current = weights_by_date[eligible[-1]]
        if current is None:
            continue
        mapped[pd.Timestamp(date)] = current
    return mapped


def backtest_overlay_returns(
    base_method: str,
    overlay_weights: pd.DataFrame,
    base_returns: pd.DataFrame,
    equity_returns: pd.DataFrame,
    *,
    overlay: str,
    tilt_strength: float,
    transaction_cost_rate: float = portfolios.TRANSACTION_COST_RATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Backtest overlay weights over the paired base OOS dates."""

    wide = _equity_return_wide(equity_returns)
    paired_dates = pd.DatetimeIndex(base_returns["date"])
    weight_map = _weights_for_dates(overlay_weights, paired_dates)
    previous_weights: pd.Series | None = None
    return_rows = []
    turnover_rows = []
    for date in paired_dates:
        current_weights = weight_map[pd.Timestamp(date)]
        rebalancing = bool(overlay_weights["date"].eq(pd.Timestamp(date)).any())
        turnover = 0.0
        transaction_cost = 0.0
        if rebalancing:
            turnover = portfolios.calculate_turnover(previous_weights, current_weights)
            transaction_cost = transaction_cost_rate * turnover
            previous_weights = current_weights
            turnover_rows.append(
                {
                    "base_method": base_method,
                    "overlay": overlay,
                    "tilt_strength": tilt_strength,
                    "live_rebalance_date": date,
                    "turnover": turnover,
                    "transaction_cost": transaction_cost,
                    "transaction_cost_rate": transaction_cost_rate,
                }
            )
        live_returns = wide.loc[pd.Timestamp(date), current_weights.index]
        missing_count = int(live_returns.isna().sum())
        gross_return = np.nan if missing_count else float(live_returns.to_numpy(dtype=float) @ current_weights.to_numpy())
        net_return = np.nan if pd.isna(gross_return) else gross_return - transaction_cost
        return_rows.append(
            {
                "date": date,
                "base_method": base_method,
                "overlay": overlay,
                "tilt_strength": tilt_strength,
                "gross_return": gross_return,
                "turnover": turnover,
                "transaction_cost": transaction_cost,
                "net_return": net_return,
                "missing_return_asset_count": missing_count,
            }
        )
    returns = pd.DataFrame(return_rows)
    returns["growth_net"] = (1.0 + returns["net_return"].fillna(0.0)).cumprod()
    returns["drawdown_net"] = returns["growth_net"] / returns["growth_net"].cummax() - 1.0
    return returns, pd.DataFrame(turnover_rows)


def _base_as_fusion_returns(base_method: str, base_returns: pd.DataFrame, tilt_strength: float) -> pd.DataFrame:
    output = base_returns.loc[
        :,
        ["date", "gross_return", "turnover", "transaction_cost", "net_return", "missing_return_asset_count"],
    ].copy()
    output["base_method"] = base_method
    output["overlay"] = OVERLAY_BASE
    output["tilt_strength"] = tilt_strength
    output["growth_net"] = (1.0 + output["net_return"].fillna(0.0)).cumprod()
    output["drawdown_net"] = output["growth_net"] / output["growth_net"].cummax() - 1.0
    return output


def _base_as_fusion_weights(base_method: str, base_weights: pd.DataFrame, tilt_strength: float) -> pd.DataFrame:
    output = base_weights.copy()
    output["base_weight"] = output["weight"]
    output["pre_normalisation_multiplier"] = 1.0
    output["pre_normalisation_weight"] = output["weight"]
    output["overlay"] = OVERLAY_BASE
    output["tilt_strength"] = tilt_strength
    output["base_method"] = base_method
    return output


def _weight_shape_metrics(weights: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in weights.groupby(["base_method", "overlay", "tilt_strength", "date"], sort=True):
        base_method, overlay, tilt_strength, date = keys
        values = group["weight"].astype(float)
        sector_weights = group.groupby("sector", sort=True)["weight"].sum()
        rows.append(
            {
                "base_method": base_method,
                "overlay": overlay,
                "tilt_strength": tilt_strength,
                "date": date,
                "effective_number_holdings": 1.0 / float((values**2).sum()) if (values**2).sum() > 0 else np.nan,
                "maximum_single_asset_weight": float(values.max()),
                "maximum_sector_weight": float(sector_weights.max()),
                "sector_hhi": float((sector_weights**2).sum()),
            }
        )
    return pd.DataFrame(rows)


def _comparison_metrics(returns: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    shape = _weight_shape_metrics(weights)
    rows = []
    for keys, group in returns.groupby(["base_method", "overlay", "tilt_strength"], sort=True):
        base_method, overlay, tilt_strength = keys
        group = group.sort_values("date").set_index("date")
        metrics = portfolios.performance_metrics(group["net_return"], periods_per_year=portfolios.ANNUALISATION[portfolios.FAMILY_EQUITY])
        shape_group = shape.loc[
            shape["base_method"].eq(base_method)
            & shape["overlay"].eq(overlay)
            & shape["tilt_strength"].eq(tilt_strength)
        ]
        rows.append(
            {
                "base_method": base_method,
                "overlay": overlay,
                "tilt_strength": tilt_strength,
                "annualised_return": metrics["annualised_return"],
                "annualised_volatility": metrics["annualised_volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "max_drawdown": metrics["max_drawdown"],
                "total_turnover": float(group["turnover"].sum()),
                "average_rebalance_turnover": float(group.loc[group["turnover"].gt(0), "turnover"].mean()),
                "transaction_cost_drag": float(group["transaction_cost"].sum()),
                "effective_number_holdings": float(shape_group["effective_number_holdings"].mean()),
                "maximum_single_asset_weight": float(shape_group["maximum_single_asset_weight"].max()),
                "maximum_sector_weight": float(shape_group["maximum_sector_weight"].max()),
                "sector_concentration_hhi": float(shape_group["sector_hhi"].mean()),
                "number_of_rebalances": int(group["turnover"].gt(0).sum()),
                "observation_count": int(group["net_return"].dropna().shape[0]),
                "sample_start": group.index.min(),
                "sample_end": group.index.max(),
            }
        )
    metrics = pd.DataFrame(rows)
    increments = []
    for (base_method, tilt_strength), method_group in metrics.groupby(["base_method", "tilt_strength"], sort=True):
        base = method_group.loc[method_group["overlay"].eq(OVERLAY_BASE)].iloc[0]
        standard = method_group.loc[method_group["overlay"].eq(OVERLAY_STANDARD)].iloc[0]
        confidence = method_group.loc[method_group["overlay"].eq(OVERLAY_CONFIDENCE)].iloc[0]
        for label, left, right in [
            ("Standard minus Base", standard, base),
            ("Confidence Lens minus Base", confidence, base),
            ("Confidence Lens minus Standard", confidence, standard),
        ]:
            row = {
                "base_method": base_method,
                "overlay": label,
                "tilt_strength": tilt_strength,
            }
            for column in [
                "annualised_return",
                "annualised_volatility",
                "sharpe_ratio",
                "max_drawdown",
                "total_turnover",
                "transaction_cost_drag",
                "effective_number_holdings",
                "maximum_single_asset_weight",
                "maximum_sector_weight",
                "sector_concentration_hhi",
            ]:
                row[column] = left[column] - right[column]
            row["average_rebalance_turnover"] = left["average_rebalance_turnover"] - right["average_rebalance_turnover"]
            row["number_of_rebalances"] = left["number_of_rebalances"]
            row["observation_count"] = left["observation_count"]
            row["sample_start"] = left["sample_start"]
            row["sample_end"] = left["sample_end"]
            increments.append(row)
    return pd.concat([metrics, pd.DataFrame(increments)], ignore_index=True).sort_values(
        ["base_method", "tilt_strength", "overlay"]
    ).reset_index(drop=True)


def _sector_allocation_changes(weights: pd.DataFrame) -> pd.DataFrame:
    sector_weights = (
        weights.groupby(["base_method", "overlay", "tilt_strength", "date", "sector"], sort=True)["weight"]
        .sum()
        .reset_index()
    )
    base = sector_weights.loc[sector_weights["overlay"].eq(OVERLAY_BASE)].rename(columns={"weight": "base_sector_weight"})
    merged = sector_weights.merge(
        base.loc[:, ["base_method", "tilt_strength", "date", "sector", "base_sector_weight"]],
        on=["base_method", "tilt_strength", "date", "sector"],
        how="left",
    )
    merged["sector_weight_change"] = merged["weight"] - merged["base_sector_weight"]
    return merged


def _confidence_summary(
    sector_confidence: pd.DataFrame,
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    comparison: pd.DataFrame,
    *,
    tilt_strength: float = PRIMARY_TILT,
) -> pd.DataFrame:
    signals = sector_confidence.copy()
    signals["materially_attenuated"] = (
        signals["raw_tilt"].abs().gt(0)
        & ((signals["raw_tilt"].abs() - signals["confidence_adjusted_tilt"].abs()) / signals["raw_tilt"].abs()).ge(
            MATERIAL_ATTENUATION
        )
    )
    changes = _sector_allocation_changes(weights.loc[weights["tilt_strength"].eq(tilt_strength)])
    standard_changes = changes.loc[changes["overlay"].eq(OVERLAY_STANDARD), ["base_method", "date", "sector", "sector_weight_change"]].rename(
        columns={"sector_weight_change": "standard_sector_change"}
    )
    confidence_changes = changes.loc[
        changes["overlay"].eq(OVERLAY_CONFIDENCE), ["base_method", "date", "sector", "sector_weight_change"]
    ].rename(columns={"sector_weight_change": "confidence_sector_change"})
    change_comp = standard_changes.merge(confidence_changes, on=["base_method", "date", "sector"], how="inner")
    rows = []
    for base_method in sorted(weights["base_method"].unique()):
        method_changes = change_comp.loc[change_comp["base_method"].eq(base_method)]
        comp = comparison.loc[
            comparison["base_method"].eq(base_method) & comparison["tilt_strength"].eq(tilt_strength)
        ]
        base_turnover = float(comp.loc[comp["overlay"].eq(OVERLAY_BASE), "total_turnover"].iloc[0])
        standard_turnover = float(comp.loc[comp["overlay"].eq(OVERLAY_STANDARD), "total_turnover"].iloc[0])
        confidence_turnover = float(comp.loc[comp["overlay"].eq(OVERLAY_CONFIDENCE), "total_turnover"].iloc[0])
        rows.append(
            {
                "base_method": base_method,
                "tilt_strength": tilt_strength,
                "average_confidence": signals["confidence"].mean(),
                "confidence_p10": signals["confidence"].quantile(0.10),
                "confidence_p25": signals["confidence"].quantile(0.25),
                "confidence_median": signals["confidence"].quantile(0.50),
                "confidence_p75": signals["confidence"].quantile(0.75),
                "confidence_p90": signals["confidence"].quantile(0.90),
                "b63_mean": signals["b63"].mean(),
                "b63_p10": signals["b63"].quantile(0.10),
                "b63_median": signals["b63"].quantile(0.50),
                "b63_p90": signals["b63"].quantile(0.90),
                "a21_mean": signals["a21"].mean(),
                "a21_p10": signals["a21"].quantile(0.10),
                "a21_median": signals["a21"].quantile(0.50),
                "a21_p90": signals["a21"].quantile(0.90),
                "b63_a21_pearson": signals[["b63", "a21"]].corr(method="pearson").iloc[0, 1],
                "b63_a21_spearman": signals[["b63", "a21"]].corr(method="spearman").iloc[0, 1],
                "share_materially_attenuated": signals["materially_attenuated"].mean(),
                "mean_absolute_raw_tilt": signals["raw_tilt"].abs().mean(),
                "mean_absolute_confidence_adjusted_tilt": signals["confidence_adjusted_tilt"].abs().mean(),
                "tilt_magnitude_reduction": 1.0
                - signals["confidence_adjusted_tilt"].abs().mean() / signals["raw_tilt"].abs().replace(0, np.nan).mean(),
                "incremental_turnover_standard_vs_base": standard_turnover - base_turnover,
                "incremental_turnover_confidence_vs_base": confidence_turnover - base_turnover,
                "standard_p95_abs_sector_change": method_changes["standard_sector_change"].abs().quantile(0.95),
                "confidence_p95_abs_sector_change": method_changes["confidence_sector_change"].abs().quantile(0.95),
                "confidence_reduces_extreme_sector_changes": bool(
                    method_changes["confidence_sector_change"].abs().quantile(0.95)
                    < method_changes["standard_sector_change"].abs().quantile(0.95)
                ),
                "share_confidence_below_0_10": signals["confidence"].lt(0.10).mean(),
                "suppresses_nearly_every_signal": bool(signals["confidence"].lt(0.10).mean() > 0.90),
            }
        )
    return pd.DataFrame(rows)


def _attenuation_cases(
    sector_confidence: pd.DataFrame,
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    comparison: pd.DataFrame,
) -> pd.DataFrame:
    changes = _sector_allocation_changes(weights.loc[weights["tilt_strength"].eq(PRIMARY_TILT)])
    standard = changes.loc[changes["overlay"].eq(OVERLAY_STANDARD)].rename(columns={"sector_weight_change": "standard_change"})
    confidence = changes.loc[changes["overlay"].eq(OVERLAY_CONFIDENCE)].rename(columns={"sector_weight_change": "confidence_change"})
    merged = standard.loc[:, ["base_method", "date", "sector", "standard_change"]].merge(
        confidence.loc[:, ["base_method", "date", "sector", "confidence_change"]],
        on=["base_method", "date", "sector"],
        how="inner",
    )
    signals = sector_confidence.rename(columns={"live_rebalance_date": "date"})
    merged = merged.merge(
        signals.loc[:, ["date", "sector", "z_star", "b63", "a21", "confidence", "raw_tilt", "confidence_adjusted_tilt"]],
        on=["date", "sector"],
        how="left",
    )
    merged["attenuation_ratio"] = 1.0 - merged["confidence_change"].abs() / merged["standard_change"].abs().replace(0, np.nan)

    rows = []
    for base_method, group in merged.groupby("base_method", sort=True):
        large = group.loc[group["standard_change"].abs().ge(group["standard_change"].abs().quantile(0.90))]
        if not large.empty:
            row = large.sort_values("attenuation_ratio", ascending=False).iloc[0]
            rows.append({**row.to_dict(), "case_type": "large_standard_change_attenuated"})
        high_conf = group.loc[group["confidence"].ge(group["confidence"].quantile(0.90))]
        informative_high_conf = high_conf.loc[high_conf["standard_change"].abs().gt(1e-10)]
        if not informative_high_conf.empty:
            high_conf = informative_high_conf
        if not high_conf.empty:
            row = high_conf.assign(gap=(high_conf["standard_change"] - high_conf["confidence_change"]).abs()).sort_values("gap").iloc[0]
            rows.append({**row.drop(labels=["gap"]).to_dict(), "case_type": "high_confidence_similar_overlay"})
        method_returns = returns.loc[
            returns["base_method"].eq(base_method) & returns["tilt_strength"].eq(PRIMARY_TILT)
        ]
        piv = method_returns.pivot(index="date", columns="overlay", values="net_return")
        if {OVERLAY_STANDARD, OVERLAY_CONFIDENCE}.issubset(piv.columns):
            worse = (piv[OVERLAY_CONFIDENCE] - piv[OVERLAY_STANDARD]).sort_values().head(1)
            if not worse.empty:
                date = worse.index[0]
                row_source = group.loc[group["date"].eq(date)]
                if not row_source.empty:
                    row = row_source.sort_values("confidence_change", key=lambda s: s.abs(), ascending=False).iloc[0]
                    rows.append(
                        {
                            **row.to_dict(),
                            "case_type": "confidence_worse_than_standard_daily_return",
                            "confidence_minus_standard_net_return": worse.iloc[0],
                        }
                    )
        method_comp = comparison.loc[
            comparison["base_method"].eq(base_method) & comparison["tilt_strength"].eq(PRIMARY_TILT)
        ]
        std = method_comp.loc[method_comp["overlay"].eq(OVERLAY_STANDARD)].iloc[0]
        conf = method_comp.loc[method_comp["overlay"].eq(OVERLAY_CONFIDENCE)].iloc[0]
        rows.append(
            {
                "base_method": base_method,
                "date": pd.NaT,
                "sector": "ALL",
                "standard_change": np.nan,
                "confidence_change": np.nan,
                "z_star": np.nan,
                "b63": np.nan,
                "a21": np.nan,
                "confidence": np.nan,
                "raw_tilt": np.nan,
                "confidence_adjusted_tilt": np.nan,
                "attenuation_ratio": np.nan,
                "case_type": "confidence_fails_to_improve_summary"
                if conf["sharpe_ratio"] <= std["sharpe_ratio"]
                else "confidence_improves_summary",
                "confidence_minus_standard_sharpe": conf["sharpe_ratio"] - std["sharpe_ratio"],
                "confidence_minus_standard_return": conf["annualised_return"] - std["annualised_return"],
                "confidence_minus_standard_turnover": conf["total_turnover"] - std["total_turnover"],
            }
        )
    return pd.DataFrame(rows).sort_values(["base_method", "case_type", "date"], na_position="last").reset_index(drop=True)


def _plot_outputs(
    returns: pd.DataFrame,
    comparison: pd.DataFrame,
    sector_confidence: pd.DataFrame,
    attenuation_cases: pd.DataFrame,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    primary = returns.loc[
        returns["base_method"].eq(portfolios.METHOD_MIN_VARIANCE) & returns["tilt_strength"].eq(PRIMARY_TILT)
    ].copy()
    pivot = primary.pivot(index="date", columns="overlay", values="growth_net")
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for label, color in [(OVERLAY_BASE, "#4C566A"), (OVERLAY_STANDARD, "#0072B2"), (OVERLAY_CONFIDENCE, "#009E73")]:
        if label in pivot:
            ax.plot(pivot.index, pivot[label], label=label, linewidth=2.0, color=color)
    ax.set_title("Equity Minimum Variance Growth of $1")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1, net of turnover costs")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "fusion_growth_min_variance.png", dpi=180)
    plt.close(fig)

    comp = comparison.loc[
        comparison["tilt_strength"].eq(PRIMARY_TILT)
        & comparison["overlay"].isin([OVERLAY_BASE, OVERLAY_STANDARD, OVERLAY_CONFIDENCE])
    ].copy()
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.4), sharey=True)
    for ax, metric, title in [
        (axes[0], "sharpe_ratio", "Sharpe ratio"),
        (axes[1], "total_turnover", "Total turnover"),
    ]:
        labels = comp["base_method"] + "\n" + comp["overlay"].str.replace("SignalScope ", "", regex=False)
        ax.barh(labels, comp[metric], color="#6B8E9E")
        ax.set_title(title)
        ax.grid(True, axis="x", alpha=0.25)
    fig.suptitle("Fusion Performance and Trading Behaviour")
    fig.tight_layout()
    fig.savefig(output_dir / "fusion_performance_comparison.png", dpi=180)
    plt.close(fig)

    decomp = sector_confidence.groupby("live_rebalance_date", sort=True).agg(
        z_abs=("z_star", lambda s: s.abs().mean()),
        b63=("b63", "mean"),
        a21=("a21", "mean"),
        confidence=("confidence", "mean"),
        effective_abs_tilt=("confidence_adjusted_tilt", lambda s: s.abs().mean()),
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for col, label in [
        ("z_abs", "|Sentiment direction Z*|"),
        ("b63", "Breadth B63"),
        ("a21", "Agreement A21"),
        ("confidence", "Confidence C"),
        ("effective_abs_tilt", "|Effective tilt|"),
    ]:
        ax.plot(decomp.index, decomp[col], label=label, linewidth=1.8)
    ax.set_title("SignalScope Confidence Lens Decomposition")
    ax.set_xlabel("Rebalance date")
    ax.set_ylabel("Average sector value")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / "confidence_lens_decomposition.png", dpi=180)
    plt.close(fig)

    case_rows = attenuation_cases.loc[attenuation_cases["case_type"].eq("large_standard_change_attenuated")]
    if not case_rows.empty:
        case = case_rows.iloc[0]
        fig, ax = plt.subplots(figsize=(7.4, 4.4))
        ax.bar(
            ["Standard sector change", "Confidence Lens change"],
            [case["standard_change"], case["confidence_change"]],
            color=["#D55E00", "#009E73"],
        )
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_title(f"Real Attenuation Case: {case['base_method']} / {case['sector']}")
        ax.set_ylabel("Sector weight change vs base")
        ax.grid(True, axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_dir / "confidence_lens_attenuation_case.png", dpi=180)
        plt.close(fig)


def build_fusion_suite(
    *,
    fund_returns: pd.DataFrame,
    fund_weights: pd.DataFrame,
    sector_index: pd.DataFrame,
    ticker_day_sentiment: pd.DataFrame,
    equity_returns: pd.DataFrame,
    sector_map: pd.DataFrame,
    output_dir: Path | None = None,
    base_methods: tuple[str, ...] = (portfolios.METHOD_MIN_VARIANCE, portfolios.METHOD_MAX_SHARPE),
    sensitivity_tilts: tuple[float, ...] = SENSITIVITY_TILTS,
) -> FusionResult:
    """Build primary and sensitivity sentiment-fusion comparisons."""

    fund_returns = fund_returns.copy()
    fund_returns["date"] = pd.to_datetime(fund_returns["date"])
    fund_returns["live_rebalance_date"] = pd.to_datetime(fund_returns["live_rebalance_date"])
    fund_returns["decision_date"] = pd.to_datetime(fund_returns["decision_date"])
    fund_weights = fund_weights.copy()
    fund_weights["date"] = pd.to_datetime(fund_weights["date"])
    fund_weights["live_rebalance_date"] = pd.to_datetime(fund_weights["live_rebalance_date"])
    fund_weights["decision_date"] = pd.to_datetime(fund_weights["decision_date"])

    primary_rebalances = (
        fund_weights.loc[
            fund_weights["fund_family"].eq(portfolios.FAMILY_EQUITY)
            & fund_weights["method"].eq(portfolios.METHOD_MIN_VARIANCE),
            ["date", "decision_date"],
        ]
        .drop_duplicates()
        .rename(columns={"date": "live_rebalance_date"})
    )
    sector_confidence = compute_sector_confidence_signals(
        sector_index,
        ticker_day_sentiment,
        sector_map,
        primary_rebalances,
    )

    all_returns = []
    all_weights = []
    all_turnovers = []
    for method in base_methods:
        base_returns = _base_returns(fund_returns, method)
        base_weights = _base_rebalance_weights(fund_weights, sector_map, method)
        for tilt in sensitivity_tilts:
            base_r = _base_as_fusion_returns(method, base_returns, tilt)
            base_w = _base_as_fusion_weights(method, base_weights, tilt)
            all_returns.append(base_r)
            all_weights.append(base_w)
            for overlay in [OVERLAY_STANDARD, OVERLAY_CONFIDENCE]:
                over_w = apply_sector_overlay(base_weights, sector_confidence, overlay=overlay, tilt_strength=tilt)
                over_w["base_method"] = method
                over_r, over_turn = backtest_overlay_returns(
                    method,
                    over_w,
                    base_returns,
                    equity_returns,
                    overlay=overlay,
                    tilt_strength=tilt,
                )
                all_weights.append(over_w)
                all_returns.append(over_r)
                all_turnovers.append(over_turn)

    fusion_returns = pd.concat(all_returns, ignore_index=True).sort_values(
        ["base_method", "tilt_strength", "overlay", "date"]
    )
    fusion_weights = pd.concat(all_weights, ignore_index=True).sort_values(
        ["base_method", "tilt_strength", "overlay", "date", "asset"]
    )
    comparison = _comparison_metrics(fusion_returns, fusion_weights)
    confidence_summary = _confidence_summary(sector_confidence, fusion_weights, fusion_returns, comparison)
    attenuation_cases = _attenuation_cases(sector_confidence, fusion_weights, fusion_returns, comparison)
    sensitivity = comparison.loc[
        comparison["overlay"].isin([OVERLAY_BASE, OVERLAY_STANDARD, OVERLAY_CONFIDENCE])
    ].sort_values(["base_method", "tilt_strength", "overlay"]).reset_index(drop=True)

    if output_dir is not None:
        _plot_outputs(fusion_returns, comparison, sector_confidence, attenuation_cases, output_dir)

    return FusionResult(
        sector_confidence=sector_confidence.reset_index(drop=True),
        fusion_returns=fusion_returns.reset_index(drop=True),
        fusion_weights=fusion_weights.reset_index(drop=True),
        fusion_comparison=comparison.reset_index(drop=True),
        confidence_summary=confidence_summary.reset_index(drop=True),
        attenuation_cases=attenuation_cases.reset_index(drop=True),
        sensitivity_analysis=sensitivity.reset_index(drop=True),
    )


__all__ = [
    "BREADTH_WINDOW",
    "DIRECTION_WINDOW",
    "OVERLAY_BASE",
    "OVERLAY_CONFIDENCE",
    "OVERLAY_STANDARD",
    "PRIMARY_TILT",
    "FusionResult",
    "apply_sector_overlay",
    "backtest_overlay_returns",
    "build_fusion_suite",
    "compute_sector_confidence_signals",
    "population_vader_dispersion",
]
