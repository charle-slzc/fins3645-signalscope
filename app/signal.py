"""Signal page helpers and renderer for SignalScope."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import html

import pandas as pd
import streamlit as st

from app import charts
from app.data import load_lazy_artifact_cached
from app.funds import format_percent
from app.navigation import set_view


DEFAULT_SECTOR = "Tech"
DEFAULT_PERIOD = "Recent 2Y"
PERIOD_OPTIONS = (DEFAULT_PERIOD, "All", "2023", "2022", "2021", "2020")
SIGNAL_SECTOR_WIDGET_KEY = "signal_sector_select"
SIGNAL_PERIOD_WIDGET_KEY = "signal_period_select"
SIGNAL_DATE_WIDGET_KEY = "signal_date_select"
SIGNAL_SECTOR_CHANGED_KEY = "_signal_sector_changed"
SIGNAL_PERIOD_CHANGED_KEY = "_signal_period_changed"
SIGNAL_DATE_CHANGED_KEY = "_signal_date_changed"
PENDING_SIGNAL_CONTEXT_KEY = "_pending_signal_context"


@dataclass(frozen=True)
class SignalContext:
    sector: str
    date: str


@dataclass(frozen=True)
class WeightingSummary:
    total_rows: int
    finite_paired_days: int
    missing_or_noncomparable_days: int
    both_nonzero_days: int
    sign_reversal_days: int
    strict_rate_finite_paired: float
    strict_rate_both_nonzero: float
    one_zero_one_nonzero_days: int


def sector_universe(sector_index: pd.DataFrame) -> list[str]:
    sectors = sorted(str(sector) for sector in sector_index["sector"].dropna().unique())
    if not sectors:
        raise ValueError("Sector sentiment index contains no sectors.")
    return sectors


def validate_sector(sector_index: pd.DataFrame, sector: str | None) -> str:
    sectors = sector_universe(sector_index)
    if sector in sectors:
        return str(sector)
    if DEFAULT_SECTOR in sectors:
        return DEFAULT_SECTOR
    return sectors[0]


def signal_series(
    sector_index: pd.DataFrame,
    sector: str,
    period: str = DEFAULT_PERIOD,
) -> pd.DataFrame:
    selected = validate_sector(sector_index, sector)
    frame = sector_index[sector_index["sector"] == selected].copy()
    if frame.empty:
        raise KeyError(f"No sentiment series found for sector: {selected}")
    frame["date"] = pd.to_datetime(frame["date"])
    if period == DEFAULT_PERIOD:
        max_year = int(frame["date"].dt.year.max())
        frame = frame[frame["date"].dt.year >= max_year - 1].copy()
    elif period != "All":
        frame = frame[frame["date"].dt.year.astype(str) == period].copy()
    frame = frame.sort_values("date").reset_index(drop=True)
    if frame.empty:
        raise KeyError(f"No sentiment observations found for {selected} in {period}.")
    return frame


def available_signal_dates(series: pd.DataFrame) -> list[str]:
    return series["date"].dt.date.astype(str).tolist()


def latest_observed_signal_date(series: pd.DataFrame) -> str:
    non_missing = series[~series["missing_sector_day"]]
    if not non_missing.empty:
        return str(non_missing.iloc[-1]["date"].date())
    return str(series.iloc[-1]["date"].date())


def validate_signal_date(
    series: pd.DataFrame,
    requested: str | None,
    *,
    preserve_requested: bool = True,
) -> str:
    dates = available_signal_dates(series)
    if preserve_requested and requested in dates:
        return str(requested)
    default_date = latest_observed_signal_date(series)
    if default_date in dates:
        return default_date
    if requested in dates:
        return str(requested)
    return dates[-1]


def _normalise_period(period: str | None) -> str:
    return str(period) if period in PERIOD_OPTIONS else DEFAULT_PERIOD


def _clear_curated_case_override() -> None:
    st.session_state.pop("evidence_case", None)
    st.session_state.pop(PENDING_SIGNAL_CONTEXT_KEY, None)


def _mark_signal_sector_changed() -> None:
    st.session_state[SIGNAL_SECTOR_CHANGED_KEY] = True


def _mark_signal_period_changed() -> None:
    st.session_state[SIGNAL_PERIOD_CHANGED_KEY] = True


def _mark_signal_date_changed() -> None:
    st.session_state[SIGNAL_DATE_CHANGED_KEY] = True


def set_pending_signal_context(sector: str, selected_date: str, *, curated: bool = False) -> None:
    st.session_state[PENDING_SIGNAL_CONTEXT_KEY] = {
        "sector": sector,
        "date": selected_date,
        "curated": curated,
    }


def _sync_signal_widget_state(
    sector_index: pd.DataFrame,
) -> SignalContext:
    sectors = sector_universe(sector_index)
    pending = st.session_state.pop(PENDING_SIGNAL_CONTEXT_KEY, None)
    if pending:
        sector = validate_sector(sector_index, pending.get("sector"))
        period = _normalise_period(st.session_state.get(SIGNAL_PERIOD_WIDGET_KEY))
        if pending.get("date") not in available_signal_dates(signal_series(sector_index, sector, period)):
            period = "All"
            st.session_state[SIGNAL_PERIOD_WIDGET_KEY] = period
        series = signal_series(sector_index, sector, period)
        selected_date = validate_signal_date(series, pending.get("date"))
        st.session_state["selected_sector"] = sector
        st.session_state["selected_signal_date"] = selected_date
        st.session_state[SIGNAL_SECTOR_WIDGET_KEY] = sector
        st.session_state[SIGNAL_DATE_WIDGET_KEY] = selected_date
        return SignalContext(sector=sector, date=selected_date)

    period = _normalise_period(st.session_state.get(SIGNAL_PERIOD_WIDGET_KEY))
    if st.session_state.pop(SIGNAL_SECTOR_CHANGED_KEY, False):
        sector = validate_sector(sector_index, st.session_state.get(SIGNAL_SECTOR_WIDGET_KEY))
        series = signal_series(sector_index, sector, period)
        selected_date = validate_signal_date(series, None, preserve_requested=False)
        st.session_state["selected_sector"] = sector
        st.session_state["selected_signal_date"] = selected_date
        st.session_state[SIGNAL_DATE_WIDGET_KEY] = selected_date
        _clear_curated_case_override()
        return SignalContext(sector=sector, date=selected_date)

    if st.session_state.pop(SIGNAL_PERIOD_CHANGED_KEY, False):
        sector = validate_sector(sector_index, st.session_state.get(SIGNAL_SECTOR_WIDGET_KEY))
        series = signal_series(sector_index, sector, period)
        selected_date = validate_signal_date(series, None, preserve_requested=False)
        st.session_state["selected_sector"] = sector
        st.session_state["selected_signal_date"] = selected_date
        st.session_state[SIGNAL_DATE_WIDGET_KEY] = selected_date
        _clear_curated_case_override()
        return SignalContext(sector=sector, date=selected_date)

    if st.session_state.pop(SIGNAL_DATE_CHANGED_KEY, False):
        sector = validate_sector(sector_index, st.session_state.get(SIGNAL_SECTOR_WIDGET_KEY))
        series = signal_series(sector_index, sector, period)
        selected_date = validate_signal_date(
            series,
            st.session_state.get(SIGNAL_DATE_WIDGET_KEY),
        )
        st.session_state["selected_sector"] = sector
        st.session_state["selected_signal_date"] = selected_date
        _clear_curated_case_override()
        return SignalContext(sector=sector, date=selected_date)

    sector = validate_sector(sector_index, st.session_state.get("selected_sector"))
    if sector not in sectors:
        sector = validate_sector(sector_index, None)
    series = signal_series(sector_index, sector, period)
    selected_date = validate_signal_date(series, st.session_state.get("selected_signal_date"))
    st.session_state["selected_sector"] = sector
    st.session_state["selected_signal_date"] = selected_date
    st.session_state[SIGNAL_SECTOR_WIDGET_KEY] = sector
    st.session_state[SIGNAL_DATE_WIDGET_KEY] = selected_date
    return SignalContext(sector=sector, date=selected_date)


def selected_signal_row(series: pd.DataFrame, selected_date: str) -> pd.Series:
    matches = series[series["date"].dt.date.astype(str) == selected_date]
    if matches.empty:
        raise KeyError(f"Selected signal date is not in the current series: {selected_date}")
    return matches.iloc[0]


def sentiment_direction_label(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "No observed news"
    value = float(value)
    if value > 0.05:
        return "Positive news lean"
    if value < -0.05:
        return "Negative news lean"
    return "Near neutral"


def evidence_availability_label(row: pd.Series) -> str:
    if bool(row["missing_sector_day"]):
        return "No observed sector news."
    active = int(row["active_ticker_count"])
    possible = int(row["possible_ticker_count"])
    headlines = int(row["headline_count"])
    return f"{active} of {possible} represented companies; {headlines} saved headlines."


def status_banner_html(sector: str, selected_date: str, row: pd.Series) -> str:
    safe_sector = html.escape(sector)
    safe_date = html.escape(selected_date)
    if bool(row["missing_sector_day"]):
        body = "No observed sector news."
    else:
        body = (
            f"Sector sentiment {float(row['sector_sentiment']):+.2f}<br>"
            f"{int(row['active_ticker_count'])} of {int(row['possible_ticker_count'])} "
            "companies represented today"
        )
    return (
        '<div class="ss-disclosure">'
        f"<strong>{safe_sector} · {safe_date}</strong><br>{body}"
        "</div>"
    )


def chart_frame(series: pd.DataFrame, selected_date: str) -> pd.DataFrame:
    frame = series.copy()
    frame["is_selected_date"] = frame["date"].dt.date.astype(str) == selected_date
    return frame


def weighting_summary(weighting_comparison: pd.DataFrame) -> WeightingSummary:
    equal_ticker = weighting_comparison["sector_sentiment"]
    headline_weighted = weighting_comparison["headline_weighted_sentiment"]
    finite = equal_ticker.notna() & headline_weighted.notna()
    both_nonzero = finite & (equal_ticker != 0) & (headline_weighted != 0)
    strict_opposite = both_nonzero & (
        ((equal_ticker > 0) & (headline_weighted < 0))
        | ((equal_ticker < 0) & (headline_weighted > 0))
    )
    one_zero_one_nonzero = finite & (
        ((equal_ticker == 0) & (headline_weighted != 0))
        | ((equal_ticker != 0) & (headline_weighted == 0))
    )
    finite_paired = int(finite.sum())
    both_nonzero_count = int(both_nonzero.sum())
    reversals = int(strict_opposite.sum())
    return WeightingSummary(
        total_rows=int(len(weighting_comparison)),
        finite_paired_days=finite_paired,
        missing_or_noncomparable_days=int((~finite).sum()),
        both_nonzero_days=both_nonzero_count,
        sign_reversal_days=reversals,
        strict_rate_finite_paired=reversals / finite_paired if finite_paired else 0.0,
        strict_rate_both_nonzero=reversals / both_nonzero_count if both_nonzero_count else 0.0,
        one_zero_one_nonzero_days=int(one_zero_one_nonzero.sum()),
    )


def store_signal_context(sector: str, selected_date: str) -> None:
    st.session_state["selected_sector"] = sector
    st.session_state["selected_signal_date"] = selected_date


def current_signal_context(sector_index: pd.DataFrame) -> SignalContext:
    sector = validate_sector(sector_index, st.session_state.get("selected_sector"))
    series = signal_series(sector_index, sector)
    selected_date = validate_signal_date(series, st.session_state.get("selected_signal_date"))
    return SignalContext(sector=sector, date=selected_date)


def render_signal_page(project_root: Path | None = None) -> None:
    root_arg = str(project_root) if project_root else None
    sector_index = load_lazy_artifact_cached("sector_sentiment_index", root_arg)
    weighting_comparison = load_lazy_artifact_cached("sentiment_weighting_comparison", root_arg)

    st.markdown(
        """
<p class="ss-kicker">Signal</p>
<h2 class="ss-stage-title">What does the news say?</h2>
<p class="ss-stage-copy">Sector sentiment summarises the direction of available company news. No news remains missing; it is not treated as neutral.</p>
""",
        unsafe_allow_html=True,
    )

    sectors = sector_universe(sector_index)
    current = _sync_signal_widget_state(sector_index)
    sector_col, period_col = st.columns([1.1, 0.7])
    with sector_col:
        selected_sector = st.selectbox(
            "Sector",
            sectors,
            index=sectors.index(current.sector),
            key=SIGNAL_SECTOR_WIDGET_KEY,
            on_change=_mark_signal_sector_changed,
        )
    with period_col:
        period = st.selectbox(
            "Period",
            PERIOD_OPTIONS,
            key=SIGNAL_PERIOD_WIDGET_KEY,
            on_change=_mark_signal_period_changed,
        )

    series = signal_series(sector_index, selected_sector, period or "All")
    selected_date = validate_signal_date(series, st.session_state.get("selected_signal_date"))
    dates = available_signal_dates(series)
    if st.session_state.get(SIGNAL_DATE_WIDGET_KEY) not in dates:
        st.session_state[SIGNAL_DATE_WIDGET_KEY] = selected_date
    selected_date = st.selectbox(
        "Signal date",
        dates,
        index=dates.index(selected_date),
        key=SIGNAL_DATE_WIDGET_KEY,
        on_change=_mark_signal_date_changed,
        help="This selects the sector-date context carried into Evidence.",
    )
    store_signal_context(selected_sector, selected_date)
    row = selected_signal_row(series, selected_date)

    st.markdown('<p class="ss-section-label">Sector sentiment timeline</p>', unsafe_allow_html=True)
    st.vega_lite_chart(
        chart_frame(series, selected_date),
        charts.sentiment_timeline_spec(),
        width="stretch",
    )
    st.caption("Blue shows sentiment direction. Gold marks underneath show how much same-day evidence existed for each sector-date.")

    st.markdown(status_banner_html(selected_sector, selected_date, row), unsafe_allow_html=True)
    action_col, back_col, _ = st.columns([1.15, 1.1, 2.7])
    with action_col:
        if st.button("Inspect this evidence", type="primary", width="stretch"):
            store_signal_context(selected_sector, selected_date)
            st.session_state["_pending_evidence_context"] = {
                "sector": selected_sector,
                "date": selected_date,
            }
            set_view("Evidence")
            st.rerun()
    with back_col:
        if st.button("Compare funds", width="stretch"):
            set_view("Fund")
            st.rerun()

    with st.expander("Why equal-ticker aggregation?", expanded=False):
        summary = weighting_summary(weighting_comparison)
        st.markdown(
            "\n".join(
                [
                    "Each represented company gets one voice in the sector reading, regardless of how many headlines it generated that day.",
                    f"Strict opposite-sign readings occurred on {summary.sign_reversal_days:,} of {summary.finite_paired_days:,} paired finite sector-days ({format_percent(summary.strict_rate_finite_paired, 2)}).",
                    f"Across all saved sector-day rows, {summary.missing_or_noncomparable_days:,} rows were not comparable because at least one reading was missing. Among rows where both methods had a non-zero direction, the strict reversal rate was {format_percent(summary.strict_rate_both_nonzero, 2)}.",
                    "Lagged sentiment-return relationships were weak in this sample, so the signal is context rather than an alpha claim.",
                ]
            )
        )

    with st.expander("Technical note", expanded=False):
        st.markdown(
            "\n".join(
                [
                    "- Headline sentiment was scored at build time using VADER compound scores.",
                    "- Ticker-day sentiment averages available headline compound scores for that ticker-date.",
                    "- Sector-day sentiment equal-weights represented ticker-days.",
                    "- No-news sector-days remain missing; they are not forward-filled or treated as neutral.",
                    "- Trading overlays use lagged sentiment; this page is the standalone context view.",
                ]
            )
        )
