import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import sentiment  # noqa: E402


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "sector": ["Tech", "Tech", "Energy", "Energy"],
        }
    )


def _headline_scores() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source_date": pd.Timestamp("2020-01-02"),
                "trading_date": pd.Timestamp("2020-01-02"),
                "days_shifted": 0,
                "is_carryover": False,
                "is_near_zero": False,
                "mapping_status": "same_day",
                "ticker": "AAA",
                "sector": "Tech",
                "title": "AAA good news",
                "compound": 0.8,
            },
            {
                "source_date": pd.Timestamp("2020-01-02"),
                "trading_date": pd.Timestamp("2020-01-02"),
                "days_shifted": 0,
                "is_carryover": False,
                "is_near_zero": False,
                "mapping_status": "same_day",
                "ticker": "AAA",
                "sector": "Tech",
                "title": "AAA more good news",
                "compound": 0.8,
            },
            {
                "source_date": pd.Timestamp("2020-01-02"),
                "trading_date": pd.Timestamp("2020-01-02"),
                "days_shifted": 0,
                "is_carryover": False,
                "is_near_zero": False,
                "mapping_status": "same_day",
                "ticker": "AAA",
                "sector": "Tech",
                "title": "AAA third good news",
                "compound": 0.8,
            },
            {
                "source_date": pd.Timestamp("2020-01-02"),
                "trading_date": pd.Timestamp("2020-01-02"),
                "days_shifted": 0,
                "is_carryover": False,
                "is_near_zero": False,
                "mapping_status": "same_day",
                "ticker": "BBB",
                "sector": "Tech",
                "title": "BBB bad news",
                "compound": -0.8,
            },
            {
                "source_date": pd.Timestamp("2020-01-04"),
                "trading_date": pd.Timestamp("2020-01-06"),
                "days_shifted": 2,
                "is_carryover": True,
                "is_near_zero": True,
                "mapping_status": "next_trading_day",
                "ticker": "CCC",
                "sector": "Energy",
                "title": "CCC neutral weekend update",
                "compound": 0.0,
            },
        ]
    )


def test_sector_index_preserves_missing_days_and_evidence_structure():
    ticker_scores = sentiment.ticker_day_sentiment(_headline_scores())
    index = sentiment.sector_sentiment_index(
        ticker_scores,
        _universe(),
        pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2020-01-06"]),
    )

    tech = index.loc[index["date"].eq(pd.Timestamp("2020-01-02")) & index["sector"].eq("Tech")].iloc[0]
    missing = index.loc[index["date"].eq(pd.Timestamp("2020-01-03")) & index["sector"].eq("Tech")].iloc[0]
    energy = index.loc[index["date"].eq(pd.Timestamp("2020-01-06")) & index["sector"].eq("Energy")].iloc[0]

    assert tech["sector_sentiment"] == pytest.approx(0.0)
    assert tech["active_ticker_share"] == pytest.approx(1.0)
    assert tech["headline_count"] == 4
    assert tech["ticker_headline_share_hhi"] == pytest.approx((3 / 4) ** 2 + (1 / 4) ** 2)
    assert tech["cross_ticker_sentiment_std"] > 1.0
    assert bool(missing["missing_sector_day"]) is True
    assert pd.isna(missing["sector_sentiment"])
    assert energy["carryover_share"] == pytest.approx(1.0)


def test_headline_weighting_can_reverse_equal_ticker_signal_diagnostically():
    headline_scores = _headline_scores()
    ticker_scores = sentiment.ticker_day_sentiment(headline_scores)
    index = sentiment.sector_sentiment_index(
        ticker_scores,
        _universe(),
        pd.DatetimeIndex(["2020-01-02", "2020-01-06"]),
    )

    comparison, disagreements = sentiment.weighting_comparison(headline_scores, ticker_scores, index)
    tech = comparison.loc[
        comparison["date"].eq(pd.Timestamp("2020-01-02")) & comparison["sector"].eq("Tech")
    ].iloc[0]

    assert tech["sector_sentiment"] == pytest.approx(0.0)
    assert tech["headline_weighted_sentiment"] == pytest.approx(0.4)
    assert tech["absolute_difference"] == pytest.approx(0.4)
    assert bool(tech["sign_reversal"]) is False
    assert disagreements.iloc[0]["responsible_ticker"] == "AAA"
    assert disagreements.iloc[0]["responsible_ticker_headline_share"] == pytest.approx(0.75)


def test_constituent_influence_reports_leave_one_out_sensitivity():
    ticker_scores = sentiment.ticker_day_sentiment(_headline_scores())
    summary, events = sentiment.constituent_influence(ticker_scores)

    tech_summary = summary.loc[summary["sector"].eq("Tech")].set_index("ticker")

    assert tech_summary.loc["AAA", "maximum_absolute_influence"] == pytest.approx(0.8)
    assert tech_summary.loc["BBB", "maximum_absolute_influence"] == pytest.approx(0.8)
    assert not events.empty
    assert np.isfinite(events["absolute_influence"]).all()
