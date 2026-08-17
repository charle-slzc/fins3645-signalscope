"""Data features required for Project B Phase 1.

The return functions preserve native calendars before any cross-asset alignment.
Headline functions stop at cleaning/alignment and raw text assembly; sentiment
scoring is intentionally outside this phase.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


RETURN_COLUMNS = ("date", "ticker", "asset_class", "adjClose", "daily_return")
TEXT_COLUMNS = ("date", "ticker", "sector", "title", "url", "publisher")


@dataclass(frozen=True)
class ReturnPanels:
    """Native and common-calendar return panels."""

    equity_returns: pd.DataFrame
    crypto_returns: pd.DataFrame
    equity_wide: pd.DataFrame
    crypto_native_wide: pd.DataFrame
    combined_wide: pd.DataFrame


@dataclass(frozen=True)
class HeadlineAlignment:
    """Headline-level same/next-trading-day alignment outputs."""

    aligned: pd.DataFrame
    unmatched: pd.DataFrame
    audit: pd.DataFrame


def _confirm_columns(df: pd.DataFrame, required: tuple[str, ...], dataset: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{dataset} is missing required columns: {missing}")


def _normalise_asset_class(asset_class: str | None, prices: pd.DataFrame) -> str:
    if asset_class is not None:
        return asset_class
    return "equity" if "sector" in prices.columns else "crypto"


def _check_unique_ticker_dates(df: pd.DataFrame, dataset: str) -> None:
    duplicate_keys = df.loc[
        df.duplicated(["ticker", "date"], keep=False), ["ticker", "date"]
    ].drop_duplicates()
    if not duplicate_keys.empty:
        sample = duplicate_keys.head(5).to_dict("records")
        raise ValueError(
            f"{dataset} has {len(duplicate_keys)} duplicate ticker-date keys; "
            f"sample={sample}; returns require unique ticker-date observations"
        )


def daily_returns(
    prices: pd.DataFrame,
    price_col: str = "adjClose",
    asset_class: str | None = None,
) -> pd.DataFrame:
    """Calculate simple daily returns within ticker on the native price calendar."""

    dataset = _normalise_asset_class(asset_class, prices)
    _confirm_columns(prices, ("date", "ticker", price_col), dataset)

    working_columns = ["date", "ticker", price_col]
    if "sector" in prices.columns:
        working_columns.append("sector")

    returns = prices.loc[:, working_columns].copy()
    returns["date"] = pd.to_datetime(returns["date"], errors="raise")
    returns[price_col] = pd.to_numeric(returns[price_col], errors="raise")
    _check_unique_ticker_dates(returns, dataset)

    returns = returns.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    returns["daily_return"] = returns.groupby("ticker", sort=False)[price_col].pct_change()
    returns = returns.loc[returns["daily_return"].notna()].copy()
    returns["asset_class"] = dataset
    returns = returns.rename(columns={price_col: "adjClose"})

    output_columns = list(RETURN_COLUMNS)
    if "sector" in returns.columns:
        output_columns.insert(3, "sector")
    return returns.loc[:, output_columns].reset_index(drop=True)


def _return_wide(returns: pd.DataFrame, dataset: str) -> pd.DataFrame:
    _confirm_columns(returns, ("date", "ticker", "daily_return"), dataset)
    _check_unique_ticker_dates(returns, dataset)
    wide = returns.pivot(index="date", columns="ticker", values="daily_return")
    return wide.sort_index().sort_index(axis=1)


def align_crypto_to_equity_calendar(
    equity_returns: pd.DataFrame,
    crypto_returns: pd.DataFrame,
) -> ReturnPanels:
    """Align already-computed crypto returns to observed equity return dates."""

    equity_tickers = set(equity_returns["ticker"].dropna().unique())
    crypto_tickers = set(crypto_returns["ticker"].dropna().unique())
    collisions = sorted(equity_tickers & crypto_tickers)
    if collisions:
        raise ValueError(f"equity and crypto ticker names collide: {collisions[:5]}")

    equity_wide = _return_wide(equity_returns, "equity returns")
    crypto_native_wide = _return_wide(crypto_returns, "crypto returns")
    equity_calendar = equity_wide.index.sort_values()
    aligned_crypto = crypto_native_wide.reindex(equity_calendar)
    combined_wide = equity_wide.join(aligned_crypto, how="left")

    return ReturnPanels(
        equity_returns=equity_returns.sort_values(["ticker", "date"]).reset_index(drop=True),
        crypto_returns=crypto_returns.sort_values(["ticker", "date"]).reset_index(drop=True),
        equity_wide=equity_wide,
        crypto_native_wide=crypto_native_wide,
        combined_wide=combined_wide,
    )


def build_return_panels(equity_prices: pd.DataFrame, crypto_prices: pd.DataFrame) -> ReturnPanels:
    """Build native return frames and the equity-calendar combined return panel."""

    equity_returns = daily_returns(equity_prices, asset_class="equity")
    crypto_returns = daily_returns(crypto_prices, asset_class="crypto")
    return align_crypto_to_equity_calendar(equity_returns, crypto_returns)


def _trading_calendar_index(trading_calendar) -> pd.DatetimeIndex:
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.Series(trading_calendar), errors="raise"))
    if getattr(calendar.dtype, "tz", None) is not None:
        calendar = calendar.tz_convert(None)
    calendar = calendar.normalize().drop_duplicates().sort_values()
    if calendar.empty:
        raise ValueError("trading_calendar must contain at least one observed trading date")
    return calendar


def _validate_ticker_sector(frame: pd.DataFrame) -> None:
    conflicts = frame.groupby("ticker")["sector"].nunique(dropna=False)
    conflicts = conflicts[conflicts > 1]
    if not conflicts.empty:
        raise ValueError(f"ticker has conflicting sector labels: {conflicts.index[:5].tolist()}")


def align_headlines_to_trading_calendar(
    headlines: pd.DataFrame,
    trading_calendar,
) -> HeadlineAlignment:
    """Map cleaned headlines to the same or next observed equity trading date."""

    _confirm_columns(headlines, TEXT_COLUMNS, "headlines")
    calendar = _trading_calendar_index(trading_calendar)

    working = headlines.loc[:, list(TEXT_COLUMNS)].copy()
    working["source_date"] = pd.to_datetime(working["date"], errors="raise").dt.normalize()
    working["text_raw"] = working["title"]

    positions = calendar.searchsorted(pd.DatetimeIndex(working["source_date"]), side="left")
    is_matched = positions < len(calendar)

    trading_dates = pd.Series(pd.NaT, index=working.index, dtype="datetime64[ns]")
    trading_dates.loc[is_matched] = calendar.take(positions[is_matched])
    working["trading_date"] = trading_dates
    working["days_shifted"] = (working["trading_date"] - working["source_date"]).dt.days
    working["was_non_trading_day"] = working["days_shifted"].fillna(0).ne(0)
    working["mapping_status"] = "aligned"
    working.loc[working["days_shifted"].eq(0), "mapping_status"] = "same_day"
    working.loc[working["days_shifted"].gt(0), "mapping_status"] = "next_trading_day"
    working.loc[~is_matched, "mapping_status"] = "after_sample_end"

    output_columns = [
        "source_date",
        "trading_date",
        "days_shifted",
        "was_non_trading_day",
        "mapping_status",
        "ticker",
        "sector",
        "title",
        "text_raw",
        "url",
        "publisher",
    ]
    aligned = working.loc[is_matched, output_columns].reset_index(drop=True)
    unmatched = working.loc[~is_matched, output_columns].reset_index(drop=True)

    audit = pd.DataFrame(
        [
            {"metric": "input_rows", "value": int(len(headlines))},
            {"metric": "aligned_rows", "value": int(len(aligned))},
            {"metric": "unmatched_after_sample_end_rows", "value": int(len(unmatched))},
            {
                "metric": "non_trading_day_rows_shifted",
                "value": int(aligned["was_non_trading_day"].sum()),
            },
            {
                "metric": "maximum_days_shifted",
                "value": int(aligned["days_shifted"].max()) if not aligned.empty else 0,
            },
        ]
    )
    return HeadlineAlignment(aligned=aligned, unmatched=unmatched, audit=audit)


def assemble_headline_panel(headlines: pd.DataFrame, trading_calendar) -> pd.DataFrame:
    """Build one ticker-sector text row per trading day with aligned headlines."""

    if "trading_date" in headlines.columns and "source_date" in headlines.columns:
        aligned = headlines.copy()
    else:
        aligned = align_headlines_to_trading_calendar(headlines, trading_calendar).aligned
    if aligned.empty:
        return pd.DataFrame(
            columns=[
                "trading_date",
                "ticker",
                "sector",
                "headline_count",
                "text_raw",
                "distinct_publisher_count",
                "missing_publisher_count",
                "source_date_min",
                "source_date_max",
                "non_trading_day_headline_count",
                "maximum_days_shifted",
            ]
        )

    _validate_ticker_sector(aligned)
    prepared = aligned.copy()
    prepared = prepared.sort_values(["trading_date", "ticker", "sector", "source_date", "title"])

    panel = (
        prepared.groupby(["trading_date", "ticker", "sector"], sort=True)
        .agg(
            headline_count=("title", "size"),
            text_raw=("text_raw", "\n".join),
            distinct_publisher_count=("publisher", "nunique"),
            missing_publisher_count=("publisher", lambda s: int(s.isna().sum())),
            source_date_min=("source_date", "min"),
            source_date_max=("source_date", "max"),
            non_trading_day_headline_count=("was_non_trading_day", "sum"),
            maximum_days_shifted=("days_shifted", "max"),
        )
        .reset_index()
    )
    panel["non_trading_day_headline_count"] = panel["non_trading_day_headline_count"].astype(int)
    panel["maximum_days_shifted"] = panel["maximum_days_shifted"].astype(int)
    return panel


__all__ = [
    "ReturnPanels",
    "HeadlineAlignment",
    "align_crypto_to_equity_calendar",
    "align_headlines_to_trading_calendar",
    "assemble_headline_panel",
    "build_return_panels",
    "daily_returns",
]
