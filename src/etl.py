"""Station 1 data foundation reused for Part B.

This module cleans the hosted price and headline data without performing any
portfolio, sentiment, or backtest work. The rules mirror the tested Part A data
foundation so Project B is self-contained.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src import data_access


PRICE_COLUMNS = (
    "ticker",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjClose",
    "volume",
)
EQUITY_COLUMNS = (*PRICE_COLUMNS, "sector")
CRYPTO_COLUMNS = PRICE_COLUMNS
HEADLINE_COLUMNS = ("date", "ticker", "sector", "title", "url", "publisher")
OHLC_COLUMNS = ("open", "high", "low", "close")
POSITIVE_PRICE_COLUMNS = (*OHLC_COLUMNS, "adjClose")
NUMERIC_PRICE_COLUMNS = (*POSITIVE_PRICE_COLUMNS, "volume")
CRYPTO_END_DATE = pd.Timestamp("2023-12-31")


@dataclass(frozen=True)
class Station1Audit:
    """Structured audit result for one cleaned source dataset."""

    summary: pd.DataFrame
    nulls: pd.DataFrame
    integrity: pd.DataFrame


@dataclass(frozen=True)
class Station1Data:
    """Clean source datasets plus combined audit tables."""

    equities: pd.DataFrame
    crypto: pd.DataFrame
    headlines: pd.DataFrame
    audit_summary: pd.DataFrame
    null_counts: pd.DataFrame
    integrity_checks: pd.DataFrame


def _confirm_columns(df: pd.DataFrame, required: tuple[str, ...], dataset: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{dataset} is missing required columns: {missing}")


def _normalise_daily_dates(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, utc=True, errors="raise")
    return dates.dt.tz_convert(None).dt.normalize()


def _convert_price_numbers(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    converted = df.copy()
    for column in NUMERIC_PRICE_COLUMNS:
        try:
            converted[column] = pd.to_numeric(converted[column], errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{dataset} has non-numeric values in required numeric column {column!r}"
            ) from exc
    return converted


def _resolve_price_duplicates(
    df: pd.DataFrame,
    dataset: str,
    retained_columns: tuple[str, ...],
) -> tuple[pd.DataFrame, int]:
    exact_duplicate_mask = df.duplicated(list(retained_columns), keep="first")
    exact_duplicates_removed = int(exact_duplicate_mask.sum())
    deduped = df.loc[~exact_duplicate_mask].copy()

    conflicting_keys = deduped.loc[
        deduped.duplicated(["ticker", "date"], keep=False), ["ticker", "date"]
    ].drop_duplicates()
    if not conflicting_keys.empty:
        sample = conflicting_keys.head(5).to_dict("records")
        raise ValueError(
            f"{dataset} has {len(conflicting_keys)} conflicting ticker-date keys; "
            f"sample={sample}; manual investigation is required"
        )
    return deduped.reset_index(drop=True), exact_duplicates_removed


def _date_span(df: pd.DataFrame) -> tuple[pd.Timestamp | pd.NaT, pd.Timestamp | pd.NaT]:
    if df.empty:
        return pd.NaT, pd.NaT
    return df["date"].min(), df["date"].max()


def _price_integrity(df: pd.DataFrame) -> dict[str, int]:
    high_floor = df[list(OHLC_COLUMNS)].max(axis=1)
    low_ceiling = df[list(OHLC_COLUMNS)].min(axis=1)
    return {
        "non_positive_price_rows": int((df[list(POSITIVE_PRICE_COLUMNS)] <= 0).any(axis=1).sum()),
        "ohlc_inconsistent_rows": int(((df["high"] < high_floor) | (df["low"] > low_ceiling)).sum()),
        "negative_volume_rows": int((df["volume"] < 0).sum()),
    }


def _equity_missing_dates(df: pd.DataFrame) -> int:
    trading_dates = pd.Index(df["date"].drop_duplicates())
    counts = df.groupby("ticker")["date"].nunique()
    return int((len(trading_dates) - counts).sum())


def _crypto_missing_dates(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    calendar = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    counts = df.groupby("ticker")["date"].nunique()
    return int((len(calendar) - counts).sum())


def _null_table(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    denominator = len(df)
    for column in df.columns:
        null_count = int(df[column].isna().sum())
        rows.append(
            {
                "dataset": dataset,
                "column": column,
                "null_count": null_count,
                "null_rate": null_count / denominator if denominator else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _integrity_table(dataset: str, checks: dict[str, int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dataset": dataset,
            "check": list(checks.keys()),
            "violation_count": list(checks.values()),
        }
    )


def _summary_row(
    *,
    dataset: str,
    original_rows: int,
    cleaned: pd.DataFrame,
    duplicate_rows_found: int,
    duplicate_rows_removed: int,
    missing_date_count: int | pd.NA,
    integrity_violations: int,
    action_taken: str,
    provenance: str,
) -> pd.DataFrame:
    start_date, end_date = _date_span(cleaned)
    return pd.DataFrame(
        [
            {
                "dataset": dataset,
                "original_rows": int(original_rows),
                "cleaned_rows": int(len(cleaned)),
                "start_date": start_date,
                "end_date": end_date,
                "ticker_count": int(cleaned["ticker"].nunique()) if "ticker" in cleaned else 0,
                "duplicate_rows_found": int(duplicate_rows_found),
                "duplicate_rows_removed": int(duplicate_rows_removed),
                "missing_date_count": missing_date_count,
                "integrity_violations": int(integrity_violations),
                "action_taken": action_taken,
                "provenance": provenance,
            }
        ]
    )


def clean_equity_prices(
    raw: pd.DataFrame,
    provenance: str = "src.data_access.load_equity_prices",
) -> tuple[pd.DataFrame, Station1Audit]:
    """Clean equity OHLCV data and audit it against the observed trading calendar."""

    dataset = "equities"
    _confirm_columns(raw, EQUITY_COLUMNS, dataset)
    original_rows = len(raw)

    cleaned = raw.loc[:, list(EQUITY_COLUMNS)].copy()
    cleaned["date"] = _normalise_daily_dates(cleaned["date"])
    cleaned = _convert_price_numbers(cleaned, dataset)
    cleaned, duplicate_rows = _resolve_price_duplicates(cleaned, dataset, EQUITY_COLUMNS)
    cleaned = cleaned.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)

    integrity_checks = _price_integrity(cleaned)
    integrity_checks["zero_volume_rows_retained"] = int((cleaned["volume"] == 0).sum())
    integrity_checks["missing_trading_dates"] = _equity_missing_dates(cleaned)

    audit = Station1Audit(
        summary=_summary_row(
            dataset=dataset,
            original_rows=original_rows,
            cleaned=cleaned,
            duplicate_rows_found=duplicate_rows,
            duplicate_rows_removed=duplicate_rows,
            missing_date_count=integrity_checks["missing_trading_dates"],
            integrity_violations=sum(
                value
                for key, value in integrity_checks.items()
                if key not in {"zero_volume_rows_retained", "missing_trading_dates"}
            ),
            action_taken=(
                "normalised daily dates; converted numeric price fields; removed "
                "exact duplicate ticker-date rows; raised on conflicting ticker-date "
                "rows; sorted by ticker/date; retained zero-volume observations"
            ),
            provenance=provenance,
        ),
        nulls=_null_table(cleaned, dataset),
        integrity=_integrity_table(dataset, integrity_checks),
    )
    return cleaned, audit


def clean_crypto_prices(
    raw: pd.DataFrame,
    provenance: str = "src.data_access.load_crypto_prices",
) -> tuple[pd.DataFrame, Station1Audit]:
    """Clean crypto OHLCV data, cap it at 2023-12-31, and audit daily coverage."""

    dataset = "crypto"
    _confirm_columns(raw, CRYPTO_COLUMNS, dataset)
    original_rows = len(raw)

    cleaned = raw.loc[:, list(CRYPTO_COLUMNS)].copy()
    cleaned["date"] = _normalise_daily_dates(cleaned["date"])
    cleaned = _convert_price_numbers(cleaned, dataset)
    post_cap_rows = int((cleaned["date"] > CRYPTO_END_DATE).sum())
    cleaned = cleaned.loc[cleaned["date"] <= CRYPTO_END_DATE]
    cleaned, duplicate_rows = _resolve_price_duplicates(cleaned, dataset, CRYPTO_COLUMNS)
    cleaned = cleaned.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)

    integrity_checks = _price_integrity(cleaned)
    integrity_checks["post_cap_rows_removed"] = post_cap_rows
    integrity_checks["missing_daily_dates"] = _crypto_missing_dates(cleaned)

    audit = Station1Audit(
        summary=_summary_row(
            dataset=dataset,
            original_rows=original_rows,
            cleaned=cleaned,
            duplicate_rows_found=duplicate_rows,
            duplicate_rows_removed=duplicate_rows,
            missing_date_count=integrity_checks["missing_daily_dates"],
            integrity_violations=sum(
                value
                for key, value in integrity_checks.items()
                if key not in {"post_cap_rows_removed", "missing_daily_dates"}
            ),
            action_taken=(
                "normalised daily dates; converted numeric price fields; removed "
                "observations after 2023-12-31; removed exact duplicate ticker-date "
                "rows; raised on conflicting ticker-date rows; sorted by ticker/date"
            ),
            provenance=provenance,
        ),
        nulls=_null_table(cleaned, dataset),
        integrity=_integrity_table(dataset, integrity_checks),
    )
    return cleaned, audit


def clean_news_headlines(
    raw: pd.DataFrame,
    provenance: str = "src.data_access.load_news_headlines",
) -> tuple[pd.DataFrame, Station1Audit]:
    """Clean headline metadata without altering headline text or mapping dates."""

    dataset = "headlines"
    _confirm_columns(raw, HEADLINE_COLUMNS, dataset)
    original_rows = len(raw)

    cleaned = raw.loc[:, list(HEADLINE_COLUMNS)].copy()
    cleaned["date"] = _normalise_daily_dates(cleaned["date"])
    cleaned = cleaned.sort_values(["ticker", "date", "title"], kind="mergesort").reset_index(drop=True)

    duplicate_mask = cleaned.duplicated(["ticker", "date", "title"], keep="first")
    duplicate_rows = int(duplicate_mask.sum())
    if duplicate_rows:
        cleaned = cleaned.loc[~duplicate_mask].reset_index(drop=True)

    key_null_rows = int(cleaned[["ticker", "date", "title"]].isna().any(axis=1).sum())
    integrity_checks = {
        "duplicate_headline_key_rows_removed": duplicate_rows,
        "key_null_rows": key_null_rows,
        "publisher_missing_rows_retained": int(cleaned["publisher"].isna().sum()),
    }

    audit = Station1Audit(
        summary=_summary_row(
            dataset=dataset,
            original_rows=original_rows,
            cleaned=cleaned,
            duplicate_rows_found=duplicate_rows,
            duplicate_rows_removed=duplicate_rows,
            missing_date_count=pd.NA,
            integrity_violations=key_null_rows,
            action_taken=(
                "converted UTC timestamps to tz-naive daily dates; sorted by "
                "ticker/date/title; removed duplicates only on ticker-date-title; "
                "preserved text, URLs, publishers, and multiple same-day headlines"
            ),
            provenance=provenance,
        ),
        nulls=_null_table(cleaned, dataset),
        integrity=_integrity_table(dataset, integrity_checks),
    )
    return cleaned, audit


def combine_audits(audits: list[Station1Audit]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Combine per-dataset audit objects into summary, null, and integrity tables."""

    return (
        pd.concat([audit.summary for audit in audits], ignore_index=True),
        pd.concat([audit.nulls for audit in audits], ignore_index=True),
        pd.concat([audit.integrity for audit in audits], ignore_index=True),
    )


def load_clean_equities() -> pd.DataFrame:
    """Load equity prices through data_access and return the clean frame."""

    cleaned, _audit = clean_equity_prices(data_access.load_equity_prices())
    return cleaned


def load_clean_crypto() -> pd.DataFrame:
    """Load crypto prices through data_access and return the clean frame."""

    cleaned, _audit = clean_crypto_prices(data_access.load_crypto_prices())
    return cleaned


def load_clean_headlines() -> pd.DataFrame:
    """Load news headlines through data_access and return the clean frame."""

    cleaned, _audit = clean_news_headlines(data_access.load_news_headlines())
    return cleaned


def build_station1_data() -> Station1Data:
    """Load all Station 1 sources, clean them, and return combined audit tables."""

    equities, equity_audit = clean_equity_prices(data_access.load_equity_prices())
    crypto, crypto_audit = clean_crypto_prices(data_access.load_crypto_prices())
    headlines, headline_audit = clean_news_headlines(data_access.load_news_headlines())
    audit_summary, null_counts, integrity_checks = combine_audits(
        [equity_audit, crypto_audit, headline_audit]
    )
    return Station1Data(
        equities=equities,
        crypto=crypto,
        headlines=headlines,
        audit_summary=audit_summary,
        null_counts=null_counts,
        integrity_checks=integrity_checks,
    )


__all__ = [
    "CRYPTO_END_DATE",
    "Station1Audit",
    "Station1Data",
    "build_station1_data",
    "clean_crypto_prices",
    "clean_equity_prices",
    "clean_news_headlines",
    "combine_audits",
    "load_clean_crypto",
    "load_clean_equities",
    "load_clean_headlines",
]
