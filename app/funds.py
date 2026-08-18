"""Deterministic Fund and Risk view helpers for SignalScope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


FAMILY_ORDER = ("Equity-only", "Crypto-only", "Combined")
METHOD_ORDER = ("Equal Weight", "Minimum Variance", "Maximum Sharpe")
FAMILY_FILTERS = ("All", "Equity", "Crypto", "Combined")
METHOD_FILTERS = ("All",) + METHOD_ORDER
DEFAULT_FUND = ("Combined", "Equal Weight")
ALL_FOCUS = ("All", "All")

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


@dataclass(frozen=True)
class PeerComparison:
    family_label: str
    selected_return: float
    selected_volatility: float
    selected_sharpe: float
    family_median_return: float
    family_median_volatility: float
    family_median_sharpe: float
    family_peer_count: int
    other_family_peer_count: int

    @property
    def heading(self) -> str:
        return (
            f"Position within the {self.family_peer_count}-fund {self.family_label} family"
            f" ({self.other_family_peer_count} other peer"
            f"{'' if self.other_family_peer_count == 1 else 's'})"
        )


@dataclass(frozen=True)
class RelativeMetric:
    label: str
    selected_value: float
    family_median: float
    family_minimum: float
    family_maximum: float
    selected_position: float
    median_position: float
    selected_text: str
    median_text: str
    context: str


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


def fund_key_id(key: FundKey) -> str:
    return f"{key.family}|{key.method}"


def fund_key_from_id(metrics: pd.DataFrame, key_id: str | None) -> FundKey | None:
    if not key_id or "|" not in str(key_id):
        return None
    family, method = str(key_id).split("|", 1)
    try:
        return validate_fund_key(metrics, family, method)
    except (KeyError, ValueError):
        return None


def focus_matches(metrics: pd.DataFrame, family_filter: str, method_filter: str) -> list[FundKey]:
    filtered = filter_metrics(metrics, family_filter, method_filter)
    if filtered.empty:
        return []
    return available_funds(filtered)


def focus_includes_key(key: FundKey, family_filter: str, method_filter: str) -> bool:
    family_matches = family_filter == "All" or key.family == canonical_family(family_filter)
    method_matches = method_filter == "All" or key.method == method_filter
    return family_matches and method_matches


def focus_for_key(key: FundKey) -> tuple[str, str]:
    return display_family(key.family), key.method


def deterministic_focus_selection(
    metrics: pd.DataFrame,
    current: FundKey,
    family_filter: str,
    method_filter: str,
) -> FundKey:
    """Resolve selected fund after a focus-lens change.

    If the focus has one match, that fund becomes selected. If the focus has
    multiple matches, preserve the current selection when possible; otherwise
    choose the first matching fund in canonical family/method order.
    """
    options = focus_matches(metrics, family_filter, method_filter)
    if not options:
        return current
    if len(options) == 1:
        return options[0]
    if current in options:
        return current
    return options[0]


def focus_match_count(metrics: pd.DataFrame, family_filter: str, method_filter: str) -> int:
    return len(focus_matches(metrics, family_filter, method_filter))


def focus_summary(
    metrics: pd.DataFrame,
    family_filter: str,
    method_filter: str,
) -> tuple[int, FundKey | None]:
    matches = focus_matches(metrics, family_filter, method_filter)
    if len(matches) == 1:
        return 1, matches[0]
    return len(matches), None


def full_map_axis_domains(metrics: pd.DataFrame) -> tuple[list[float], list[float]]:
    frame = comparison_frame(metrics, default_fund_key(metrics))
    return (
        _padded_domain(frame["volatility_pct"], lower_bound=0.0),
        _padded_domain(frame["return_pct"]),
    )


def comparison_frame(
    metrics: pd.DataFrame,
    selected: FundKey,
    family_filter: str = "All",
    method_filter: str = "All",
) -> pd.DataFrame:
    frame = metrics.copy()
    frame["family_label"] = frame["fund_family"].map(display_family)
    frame["fund_label"] = frame["family_label"] + " / " + frame["method"]
    frame["fund_key"] = frame["fund_family"] + "|" + frame["method"]
    frame["is_selected"] = (frame["fund_family"] == selected.family) & (
        frame["method"] == selected.method
    )
    frame["is_focus_match"] = [
        focus_includes_key(FundKey(row.fund_family, row.method), family_filter, method_filter)
        for row in frame.itertuples(index=False)
    ]
    frame["return_pct"] = frame["net_annualised_return"]
    frame["volatility_pct"] = frame["net_annualised_volatility"]
    frame["drawdown_pct"] = frame["net_max_drawdown"]
    return frame


def validate_comparison_frame(
    frame: pd.DataFrame,
    selected: FundKey,
    expected_fund_count: int | None = 9,
) -> None:
    required = {"fund_family", "method", "fund_key", "is_selected", "is_focus_match"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Comparison frame missing columns: {sorted(missing)}")
    if expected_fund_count is not None and len(frame) != expected_fund_count:
        raise ValueError(
            f"Comparison frame must contain {expected_fund_count} funds; found {len(frame)}."
        )
    if frame["fund_key"].duplicated().any():
        raise ValueError("Comparison frame contains duplicate fund_key rows.")
    expected_keys = frame["fund_family"].astype(str) + "|" + frame["method"].astype(str)
    if not frame["fund_key"].astype(str).equals(expected_keys):
        raise ValueError("Comparison frame fund_key values do not match family/method identities.")
    for column in ("is_selected", "is_focus_match"):
        if not frame[column].map(lambda value: isinstance(value, (bool, np.bool_))).all():
            raise ValueError(f"Comparison frame {column} values must be boolean.")
    selected_rows = frame[frame["is_selected"]]
    if len(selected_rows) != 1:
        raise ValueError("Comparison frame must contain exactly one selected fund.")
    if str(selected_rows.iloc[0]["fund_key"]) != fund_key_id(selected):
        raise ValueError("Selected row does not match the authoritative FundKey.")


def _padded_domain(
    values: pd.Series,
    floor: float = 0.025,
    lower_bound: float | None = None,
) -> list[float]:
    clean = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return [0.0, 1.0]
    minimum = float(clean.min())
    maximum = float(clean.max())
    if abs(maximum - minimum) < 1e-12:
        centre = minimum
        padding = max(abs(centre) * 0.08, floor)
        low = centre - padding
        high = centre + padding
    else:
        span = maximum - minimum
        padding = max(span * 0.35, floor)
        low = minimum - padding
        high = maximum + padding
    if lower_bound is not None:
        low = max(lower_bound, low)
    if high <= low:
        high = low + floor * 2
    return [low, high]


def _first_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        return _first_scalar(value[0])
    return str(value)


def _event_as_dict(event: Any) -> dict[str, Any]:
    if event is None:
        return {}
    if isinstance(event, dict):
        return event
    if hasattr(event, "to_dict"):
        maybe = event.to_dict()
        return maybe if isinstance(maybe, dict) else {}
    selection = getattr(event, "selection", None)
    if isinstance(selection, dict):
        return {"selection": selection}
    return {}


def fund_key_from_selection_event(
    event: Any,
    metrics: pd.DataFrame,
    selection_name: str = "fund_pick",
) -> FundKey | None:
    """Extract a fund key from a native Streamlit Vega-Lite selection event."""
    payload = _event_as_dict(event)
    selection = payload.get("selection")
    if not isinstance(selection, dict):
        return None

    selected = selection.get(selection_name)
    if not selected:
        return None

    fund_key: str | None = None
    fund_family: str | None = None
    method: str | None = None
    if isinstance(selected, list):
        if not selected or not isinstance(selected[0], dict):
            return None
        point = selected[0]
        fund_key = _first_scalar(point.get("fund_key"))
        fund_family = _first_scalar(point.get("fund_family"))
        method = _first_scalar(point.get("method"))
    elif isinstance(selected, dict):
        fund_key = _first_scalar(selected.get("fund_key"))
        fund_family = _first_scalar(selected.get("fund_family"))
        method = _first_scalar(selected.get("method"))

    if fund_key:
        matches = metrics.copy()
        if "fund_key" not in matches.columns:
            matches["fund_key"] = matches["fund_family"] + "|" + matches["method"]
        row = matches[matches["fund_key"] == fund_key]
        if not row.empty:
            return validate_fund_key(metrics, str(row.iloc[0]["fund_family"]), str(row.iloc[0]["method"]))

    if not fund_family or not method:
        return None
    try:
        return validate_fund_key(metrics, fund_family, method)
    except (KeyError, ValueError):
        return None


def metric_row(metrics: pd.DataFrame, key: FundKey) -> pd.Series:
    matches = metrics[(metrics["fund_family"] == key.family) & (metrics["method"] == key.method)]
    if matches.empty:
        raise KeyError(f"Metrics not found for {key.label}")
    return matches.iloc[0]


def peer_comparison(metrics: pd.DataFrame, key: FundKey) -> PeerComparison:
    selected = metric_row(metrics, key)
    peers = metrics[metrics["fund_family"] == key.family]
    if peers.empty:
        raise KeyError(f"Peer metrics not found for {key.label}")
    return PeerComparison(
        family_label=display_family(key.family),
        selected_return=float(selected["net_annualised_return"]),
        selected_volatility=float(selected["net_annualised_volatility"]),
        selected_sharpe=float(selected["net_sharpe_ratio"]),
        family_median_return=float(peers["net_annualised_return"].median()),
        family_median_volatility=float(peers["net_annualised_volatility"].median()),
        family_median_sharpe=float(peers["net_sharpe_ratio"].median()),
        family_peer_count=int(len(peers)),
        other_family_peer_count=max(int(len(peers)) - 1, 0),
    )


def _position_in_range(value: float, minimum: float, maximum: float) -> float:
    if not np.isfinite(value) or not np.isfinite(minimum) or not np.isfinite(maximum):
        return 0.5
    if abs(maximum - minimum) < 1e-12:
        return 0.5
    return float(np.clip((value - minimum) / (maximum - minimum), 0.0, 1.0))


def relative_peer_metrics(metrics: pd.DataFrame, key: FundKey) -> list[RelativeMetric]:
    selected = metric_row(metrics, key)
    peers = metrics[metrics["fund_family"] == key.family]
    if peers.empty:
        raise KeyError(f"Peer metrics not found for {key.label}")

    specs = (
        (
            "Return",
            "net_annualised_return",
            lambda value: format_percent(value),
            "Higher historical OOS return came with its own risk path.",
        ),
        (
            "Volatility",
            "net_annualised_volatility",
            lambda value: format_percent(value),
            "Lower volatility means less variation, not automatically a better fund.",
        ),
        (
            "Sharpe",
            "net_sharpe_ratio",
            lambda value: f"{value:.2f}",
            "Return per unit of volatility within the same fund family.",
        ),
    )
    relative = []
    for label, column, formatter, context in specs:
        selected_value = float(selected[column])
        family_median = float(peers[column].median())
        family_minimum = float(peers[column].min())
        family_maximum = float(peers[column].max())
        relative.append(
            RelativeMetric(
                label=label,
                selected_value=selected_value,
                family_median=family_median,
                family_minimum=family_minimum,
                family_maximum=family_maximum,
                selected_position=_position_in_range(
                    selected_value, family_minimum, family_maximum
                ),
                median_position=_position_in_range(family_median, family_minimum, family_maximum),
                selected_text=formatter(selected_value),
                median_text=formatter(family_median),
                context=context,
            )
        )
    return relative


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


def is_broad_near_equal(summary: ConcentrationSummary) -> bool:
    if summary.asset_count <= 0:
        return False
    effective_share = summary.effective_holdings / summary.asset_count
    return effective_share >= 0.75 and summary.top_weight <= 0.12


def representative_holdings(weights: pd.DataFrame, top_n: int = 6) -> pd.DataFrame:
    display = weights[weights["weight"].abs() > 1e-8].copy()
    display = display.sort_values(["weight", "asset"], ascending=[False, True]).reset_index(drop=True)
    return display.head(top_n).copy()


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


def estimation_context(method: str, estimation_window: int | float) -> tuple[str, str]:
    if method == "Equal Weight":
        return ("Benchmark", "no optimisation estimation window")
    return (f"{int(estimation_window)}", "trailing estimation observations")


def rebalance_methodology_lines(key: FundKey, row: pd.Series) -> list[str]:
    common = [
        "- Historical out-of-sample backtest, not a forecast or personalised investment advice.",
        "- Long-only, fully invested, no leverage.",
        "- 10 bps transaction cost per dollar of turnover, already deducted in net returns.",
        "- 0% annual risk-free-rate convention for Sharpe calculations.",
        f"- OOS sample: {row['sample_start']} to {row['sample_end']}.",
        f"- Annualisation convention: {int(row['periods_per_year'])} periods per year.",
        f"- {family_caveat(key.family)}",
    ]
    if key.method == "Equal Weight":
        method_line = (
            "- Equal Weight is a benchmark with no optimiser estimation window; "
            "the first live date is aligned for OOS comparability."
        )
    else:
        method_line = (
            "- Monthly rebalance using saved weights estimated from trailing "
            "historical observations."
        )
    return [common[0], "- " + method_explanation(key.method), method_line, *common[1:]]


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
