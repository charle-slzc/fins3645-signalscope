import pathlib
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import etl, features  # noqa: E402


def _price_row(ticker: str, date: str, adj_close: float = 10.0, volume: int = 100) -> dict:
    return {
        "ticker": ticker,
        "date": date,
        "open": adj_close,
        "high": adj_close + 1,
        "low": adj_close - 1,
        "close": adj_close,
        "adjClose": adj_close,
        "volume": volume,
    }


def _equity_row(ticker: str, date: str, adj_close: float = 10.0) -> dict:
    row = _price_row(ticker, date, adj_close)
    row["sector"] = "Tech"
    return row


def _headline(ticker: str, date: str, title: str, sector: str = "Tech") -> dict:
    return {
        "date": pd.Timestamp(date, tz="UTC"),
        "ticker": ticker,
        "sector": sector,
        "title": title,
        "url": f"https://example.com/{ticker}/{title.replace(' ', '-')}",
        "publisher": "Reuters",
    }


def test_crypto_cleaning_caps_sample_and_preserves_native_calendar():
    raw = pd.DataFrame(
        [
            _price_row("BTC-USD", "2023-12-30"),
            _price_row("BTC-USD", "2023-12-31"),
            _price_row("BTC-USD", "2024-01-01"),
        ]
    )

    cleaned, audit = etl.clean_crypto_prices(raw)

    assert cleaned["date"].max() == pd.Timestamp("2023-12-31")
    assert audit.integrity.set_index("check").loc["post_cap_rows_removed", "violation_count"] == 1


def test_duplicate_price_keys_and_duplicate_headlines_are_handled_by_project_rules():
    repeated_price = _equity_row("AAA", "2020-01-02", 10.0)
    cleaned_equity, equity_audit = etl.clean_equity_prices(
        pd.DataFrame([repeated_price, repeated_price.copy()])
    )
    assert len(cleaned_equity) == 1
    assert equity_audit.summary["duplicate_rows_removed"].item() == 1

    conflicting = pd.DataFrame(
        [_equity_row("AAA", "2020-01-02", 10.0), _equity_row("AAA", "2020-01-02", 11.0)]
    )
    with pytest.raises(ValueError, match="conflicting ticker-date"):
        etl.clean_equity_prices(conflicting)

    headlines = pd.DataFrame(
        [
            _headline("AAA", "2020-01-02", "Same headline"),
            {**_headline("AAA", "2020-01-02", "Same headline"), "url": "https://example.com/other"},
            _headline("AAA", "2020-01-02", "Different headline"),
        ]
    )
    cleaned_headlines, headline_audit = etl.clean_news_headlines(headlines)
    assert len(cleaned_headlines) == 2
    assert headline_audit.summary["duplicate_rows_removed"].item() == 1


def test_daily_returns_use_adjusted_close_within_ticker_only():
    prices = pd.DataFrame(
        [
            _equity_row("BBB", "2020-01-03", 60.0),
            _equity_row("AAA", "2020-01-03", 121.0),
            _equity_row("BBB", "2020-01-02", 50.0),
            _equity_row("AAA", "2020-01-02", 110.0),
            _equity_row("AAA", "2020-01-01", 100.0),
        ]
    )

    returns = features.daily_returns(prices)

    assert list(returns[["ticker", "date"]].itertuples(index=False, name=None)) == [
        ("AAA", pd.Timestamp("2020-01-02")),
        ("AAA", pd.Timestamp("2020-01-03")),
        ("BBB", pd.Timestamp("2020-01-03")),
    ]
    assert returns["daily_return"].tolist() == pytest.approx([0.1, 0.1, 0.2])
    assert not returns.duplicated(["ticker", "date"]).any()


def test_friday_to_monday_crypto_return_is_native_before_common_calendar_alignment():
    crypto_prices = pd.DataFrame(
        [
            _price_row("BTC-USD", "2020-01-03", 100.0),
            _price_row("BTC-USD", "2020-01-04", 110.0),
            _price_row("BTC-USD", "2020-01-05", 121.0),
            _price_row("BTC-USD", "2020-01-06", 133.1),
        ]
    )
    equity_returns = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2020-01-03"),
                "ticker": "AAA",
                "sector": "Tech",
                "asset_class": "equity",
                "adjClose": 100.0,
                "daily_return": 0.01,
            },
            {
                "date": pd.Timestamp("2020-01-06"),
                "ticker": "AAA",
                "sector": "Tech",
                "asset_class": "equity",
                "adjClose": 101.0,
                "daily_return": 0.02,
            },
        ]
    )
    crypto_returns = features.daily_returns(crypto_prices, asset_class="crypto")

    panels = features.align_crypto_to_equity_calendar(equity_returns, crypto_returns)

    assert crypto_returns["daily_return"].tolist() == pytest.approx([0.1, 0.1, 0.1])
    assert panels.combined_wide.loc[pd.Timestamp("2020-01-06"), "BTC-USD"] == pytest.approx(0.1)
    assert pd.Timestamp("2020-01-04") not in panels.combined_wide.index
    assert pd.Timestamp("2020-01-05") not in panels.combined_wide.index


def test_common_calendar_alignment_does_not_forward_fill_missing_returns():
    equity_returns = pd.DataFrame(
        [
            {"date": pd.Timestamp("2020-01-03"), "ticker": "AAA", "asset_class": "equity", "adjClose": 1, "daily_return": 0.01},
            {"date": pd.Timestamp("2020-01-06"), "ticker": "AAA", "asset_class": "equity", "adjClose": 1, "daily_return": 0.02},
            {"date": pd.Timestamp("2020-01-07"), "ticker": "AAA", "asset_class": "equity", "adjClose": 1, "daily_return": 0.03},
        ]
    )
    crypto_returns = pd.DataFrame(
        [
            {"date": pd.Timestamp("2020-01-04"), "ticker": "BTC-USD", "asset_class": "crypto", "adjClose": 1, "daily_return": 0.10},
            {"date": pd.Timestamp("2020-01-06"), "ticker": "BTC-USD", "asset_class": "crypto", "adjClose": 1, "daily_return": 0.20},
        ]
    )

    panels = features.align_crypto_to_equity_calendar(equity_returns, crypto_returns)

    assert pd.isna(panels.combined_wide.loc[pd.Timestamp("2020-01-03"), "BTC-USD"])
    assert panels.combined_wide.loc[pd.Timestamp("2020-01-06"), "BTC-USD"] == pytest.approx(0.20)
    assert pd.isna(panels.combined_wide.loc[pd.Timestamp("2020-01-07"), "BTC-USD"])


def test_headline_alignment_uses_same_or_next_equity_trading_day_and_preserves_text():
    calendar = pd.DatetimeIndex(["2020-01-03", "2020-01-06"])
    headlines = pd.DataFrame(
        [
            _headline("AAA", "2020-01-03", "Same-day BIG rally!"),
            _headline("AAA", "2020-01-04", "Saturday news"),
            _headline("AAA", "2020-01-07", "Trailing news"),
        ]
    )
    cleaned, _audit = etl.clean_news_headlines(headlines)

    result = features.align_headlines_to_trading_calendar(cleaned, calendar)
    aligned = result.aligned.set_index("title")

    assert aligned.loc["Same-day BIG rally!", "trading_date"] == pd.Timestamp("2020-01-03")
    assert aligned.loc["Saturday news", "trading_date"] == pd.Timestamp("2020-01-06")
    assert result.unmatched["title"].tolist() == ["Trailing news"]
    assert aligned.loc["Same-day BIG rally!", "text_raw"] == "Same-day BIG rally!"
