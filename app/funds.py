"""Deterministic Fund and Risk view helpers for SignalScope."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


FAMILY_ORDER = ("Equity-only", "Crypto-only", "Combined")
METHOD_ORDER = ("Equal Weight", "Minimum Variance", "Maximum Sharpe")
FAMILY_FILTERS = ("All", "Equity", "Crypto", "Combined")
METHOD_FILTERS = ("All",) + METHOD_ORDER
DEFAULT_FUND = ("Combined", "Equal Weight")

CONCENTRATION_WEIGHT_THRESHOLD = 0.25
EFFECTIVE_HOLDINGS_THRESHOLD = 5.0


@dataclass(frozen=True)
class FundKey:
    family: str
    method: str

    @property
    def label(self) -> str:
        return f"{display_family(self.family)} / {self.method}"


@dataclass(frozen=True)
class ConcentrationSummary:
    latest_date: str
    top_asset: str
    top_weight: float
    effective_holdings: float
    asset_count: int
    is_concentrated: bool
    is_low_diversification: bool


def display_family(family: str) -> str:
    if family == "Equity-only":
        return "Equity"
    if family == "Crypto-only":
        return "Crypto"
    return family


def canonical_family(label: str) -> str:
    mapping = {
        "Equity": "Equity-only",
        "Crypto": "Crypto-only",
        "Combined": "Combined",
        "Equity-only": "Equity-only",
        "Crypto-only": "Crypto-only",
    }
    try:
        return mapping[label]
    except KeyError as exc:
        raise ValueError(f"Unknown fund family: {label}") from exc


def fund_sort_key(row: pd.Series) -> tuple[int, int]:
    return (
        FAMILY_ORDER.index(row["fund_family"]),
        METHOD_ORDER.index(row["method"]),
    )


def available_funds(metrics: pd.DataFrame) -> list[FundKey]:
    required = {"fund_family", "method"}
    missing = required.difference(metrics.columns)
    if missing:
        raise ValueError(f"Performance metrics missing columns: {sorted(missing)}")

    funds = metrics[["fund_family", "method"]].drop_duplicates().copy()
    funds["family_order"] = funds["fund_family"].map({v: i for i, v in enumerate(FAMILY_ORDER)})
    funds["method_order"] = funds["method"].map({v: i for i, v in enumerate(METHOD_ORDER)})
    funds = funds.sort_values(["family_order", "method_order"])
    return [FundKey(row.fund_family, row.method) for row in funds.itertuples(index=False)]


def validate_fund_key(metrics: pd.DataFrame, family: str, method: str) -> FundKey:
    canonical = canonical_family(family)
    matches = metrics[(metrics["fund_family"] == canonical) & (metrics["method"] == method)]
    if matches.empty:
        raise KeyError(f"Unknown fund selection: {display_family(canonical)} / {method}")
    return FundKey(canonical, method)


def default_fund_key(metrics: pd.DataFrame) -> FundKey:
    try:
        return validate_fund_key(metrics, DEFAULT_FUND[0], DEFAULT_FUND[1])
    except KeyError:
        funds = available_funds(metrics)
        if not funds:
            raise KeyError("No funds are available in performance_metrics.csv")
        return funds[0]


def filter_metrics(metrics: pd.DataFrame, family_filter: str, method_filter: str) -> pd.DataFrame:
    filtered = metrics.copy()
    if family_filter != "All":
        filtered = filtered[filtered["fund_family"] == canonical_family(family_filter)]
    if method_filter != "All":
        filtered = filtered[filtered["method"] == method_filter]
    return filtered.reset_index(drop=True)


def comparison_frame(metrics: pd.DataFrame, selected: FundKey) -> pd.DataFrame:
    frame = metrics.copy()
    frame["family_label"] = frame["fund_family"].map(display_family)
    frame["fund_label"] = frame["family_label"] + " / " + frame["method"]
    frame["selected"] = (frame["fund_family"] == selected.family) & (frame["method"] == selected.method)
    frame["return_pct"] = frame["net_annualised_return"]
    frame["volatility_pct"] = frame["net_annualised_volatility"]
    frame["drawdown_pct"] = frame["net_max_drawdown"]
    return frame


def metric_row(metrics: pd.DataFrame, key: FundKey) -> pd.Series:
    matches = metrics[(metrics["fund_family"] == key.family) & (metrics["method"] == key.method)]
    if matches.empty:
        raise KeyError(f"Metrics not found for {key.label}")
    return matches.iloc[0]


def return_series(fund_returns: pd.DataFrame, key: FundKey) -> pd.DataFrame:
    required = {"date", "fund_family", "method", "net_return"}
    missing = required.difference(fund_returns.columns)
    if missing:
        raise ValueError(f"Fund returns missing columns: {sorted(missing)}")
    series = fund_returns[
        (fund_returns["fund_family"] == key.family) & (fund_returns["method"] == key.method)
    ].copy()
    if series.empty:
        raise KeyError(f"Return path not found for {key.label}")
    series["date"] = pd.to_datetime(series["date"])
    series = series.sort_values("date").reset_index(drop=True)
    return series


def growth_and_drawdown_from_returns(returns: pd.DataFrame) -> pd.DataFrame:
    if "net_return" not in returns.columns:
        raise ValueError("Return path must include net_return.")
    path = returns.copy()
    path["date"] = pd.to_datetime(path["date"])
    path = path.sort_values("date").reset_index(drop=True)
    growth = (1.0 + path["net_return"].astype(float)).cumprod()
    running_peak = growth.cummax()
    drawdown = growth / running_peak - 1.0
    path["growth_net_display"] = growth
    path["drawdown_net_display"] = drawdown
    return path


def latest_weights(fund_weights: pd.DataFrame, key: FundKey) -> pd.DataFrame:
    required = {"date", "fund_family", "method", "asset", "asset_class", "weight"}
    missing = required.difference(fund_weights.columns)
    if missing:
        raise ValueError(f"Fund weights missing columns: {sorted(missing)}")
    weights = fund_weights[
        (fund_weights["fund_family"] == key.family) & (fund_weights["method"] == key.method)
    ].copy()
    if weights.empty:
        raise KeyError(f"Weights not found for {key.label}")
    weights["date"] = pd.to_datetime(weights["date"])
    latest_date = weights["date"].max()
    latest = weights[weights["date"] == latest_date].copy()
    latest["abs_weight"] = latest["weight"].abs()
    return latest.sort_values(["weight", "asset"], ascending=[False, True]).reset_index(drop=True)


def effective_holdings(weights: pd.DataFrame) -> float:
    weight_sum_squares = float(np.square(weights["weight"].astype(float)).sum())
    if weight_sum_squares <= 0:
        return float("nan")
    return 1.0 / weight_sum_squares


def concentration_summary(weights: pd.DataFrame) -> ConcentrationSummary:
    if weights.empty:
        raise ValueError("Cannot summarise concentration for empty weights.")
    top = weights.loc[weights["weight"].idxmax()]
    effective = effective_holdings(weights)
    top_weight = float(top["weight"])
    return ConcentrationSummary(
        latest_date=pd.to_datetime(top["date"]).date().isoformat(),
        top_asset=str(top["asset"]),
        top_weight=top_weight,
        effective_holdings=effective,
        asset_count=int(len(weights)),
        is_concentrated=top_weight > CONCENTRATION_WEIGHT_THRESHOLD,
        is_low_diversification=effective < EFFECTIVE_HOLDINGS_THRESHOLD,
    )


def top_holdings_with_remainder(weights: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    display = weights[weights["weight"].abs() > 1e-8].copy()
    display = display.sort_values(["weight", "asset"], ascending=[False, True]).reset_index(drop=True)
    top = display.head(top_n).copy()
    remainder = display.iloc[top_n:]
    if not remainder.empty and float(remainder["weight"].sum()) > 1e-6:
        top = pd.concat(
            [
                top,
                pd.DataFrame(
                    {
                        "asset": ["Other holdings"],
                        "asset_class": ["mixed"],
                        "weight": [float(remainder["weight"].sum())],
                        "date": [display["date"].iloc[0]],
                    }
                ),
            ],
            ignore_index=True,
        )
    return top


def latest_exposure(asset_class_exposure: pd.DataFrame, key: FundKey) -> pd.DataFrame:
    required = {"date", "fund_family", "method", "asset_class", "exposure"}
    missing = required.difference(asset_class_exposure.columns)
    if missing:
        raise ValueError(f"Asset-class exposure missing columns: {sorted(missing)}")
    exposure = asset_class_exposure[
        (asset_class_exposure["fund_family"] == key.family)
        & (asset_class_exposure["method"] == key.method)
    ].copy()
    if exposure.empty:
        raise KeyError(f"Exposure not found for {key.label}")
    exposure["date"] = pd.to_datetime(exposure["date"])
    latest_date = exposure["date"].max()
    latest = exposure[exposure["date"] == latest_date].copy()
    latest["asset_class_label"] = latest["asset_class"].str.title()
    return latest.sort_values("asset_class_label").reset_index(drop=True)


def first_live_row(first_live_dates: pd.DataFrame, key: FundKey) -> pd.Series:
    matches = first_live_dates[
        (first_live_dates["fund_family"] == key.family) & (first_live_dates["method"] == key.method)
    ]
    if matches.empty:
        raise KeyError(f"First-live date not found for {key.label}")
    return matches.iloc[0]


def method_explanation(method: str) -> str:
    if method == "Equal Weight":
        return "Benchmark fund: each eligible asset receives the same target weight."
    if method == "Minimum Variance":
        return "Optimisation fund: weights target the lowest historical portfolio variance under long-only constraints."
    if method == "Maximum Sharpe":
        return "Optimisation fund: weights target higher historical return per unit of risk under long-only constraints."
    return "Systematic fund built from precomputed out-of-sample results."


def family_caveat(family: str) -> str:
    if family == "Combined":
        return (
            "Combined funds use the equity trading calendar. Weekend-only crypto moves "
            "are not represented as continuous seven-day crypto P&L in this combined series."
        )
    if family == "Crypto-only":
        return "Crypto-only funds use the native seven-day crypto calendar in the saved backtest."
    return "Equity-only funds use the observed equity trading calendar in the saved backtest."


def format_percent(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def format_multiple(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}x"

