import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import fusion, portfolios  # noqa: E402


def _sector_map() -> pd.DataFrame:
    rows = []
    for sector, prefix in [("Tech", "T"), ("Health", "H")]:
        for idx in range(5):
            rows.append({"ticker": f"{prefix}{idx}", "sector": sector})
    return pd.DataFrame(rows)


def _sector_index(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for date in dates:
        day_number = dates.get_loc(date)
        rows.append(
            {
                "date": date,
                "sector": "Tech",
                "sector_sentiment": 0.01 * day_number,
                "active_ticker_count": 5,
                "headline_count": 5,
                "possible_ticker_count": 5,
                "active_ticker_share": 1.0,
                "missing_sector_day": False,
            }
        )
        rows.append(
            {
                "date": date,
                "sector": "Health",
                "sector_sentiment": -0.01 * day_number,
                "active_ticker_count": 5,
                "headline_count": 5,
                "possible_ticker_count": 5,
                "active_ticker_share": 1.0,
                "missing_sector_day": False,
            }
        )
    return pd.DataFrame(rows)


def _ticker_sentiment(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for date in dates:
        for ticker in ["T0", "T1", "T2", "T3", "T4"]:
            rows.append({"date": date, "ticker": ticker, "sector": "Tech", "ticker_sentiment": 0.2, "headline_count": 1})
        # Health intentionally has narrow breadth: only one observed ticker-day.
        rows.append({"date": date, "ticker": "H0", "sector": "Health", "ticker_sentiment": -0.2, "headline_count": 1})
    return pd.DataFrame(rows)


def _rebalance(cutoff: pd.Timestamp, live: pd.Timestamp) -> pd.DataFrame:
    return pd.DataFrame({"live_rebalance_date": [live], "decision_date": [cutoff]})


def test_confidence_signals_use_only_dates_before_live_rebalance_and_fixed_windows():
    dates = pd.bdate_range("2020-01-01", periods=80)
    cutoff = dates[68]
    live = dates[69]
    sector_index = _sector_index(dates)
    ticker = _ticker_sentiment(dates)
    # Poison future values after cutoff. Correct signals must ignore them.
    sector_index.loc[sector_index["date"].gt(cutoff), "sector_sentiment"] = 99.0
    ticker.loc[ticker["date"].gt(cutoff), "ticker_sentiment"] = 1.0

    signals = fusion.compute_sector_confidence_signals(
        sector_index,
        ticker,
        _sector_map(),
        _rebalance(cutoff, live),
    )
    tech = signals.set_index("sector").loc["Tech"]

    direction_dates = dates[48:69]
    assert tech["signal_cutoff_date"] == cutoff
    assert tech["direction_window_end"] == cutoff
    assert tech["direction_window_start"] == direction_dates[0]
    assert tech["breadth_window_end"] == cutoff
    assert tech["breadth_window_start"] == dates[6]
    assert tech["s21"] == pytest.approx(np.mean([0.01 * dates.get_loc(date) for date in direction_dates]))
    assert tech["signal_cutoff_date"] < tech["live_rebalance_date"]


def test_breadth_denominator_includes_no_news_ticker_days_and_bounds_hold():
    dates = pd.bdate_range("2020-01-01", periods=70)
    signals = fusion.compute_sector_confidence_signals(
        _sector_index(dates),
        _ticker_sentiment(dates),
        _sector_map(),
        _rebalance(dates[68], dates[69]),
    ).set_index("sector")

    assert signals.loc["Tech", "b63"] == pytest.approx(1.0)
    assert signals.loc["Health", "b63"] == pytest.approx(63 / (63 * 5))
    assert signals[["b63", "a21", "confidence"]].ge(0).all().all()
    assert signals[["b63", "a21", "confidence"]].le(1).all().all()


def test_population_vader_dispersion_and_agreement_are_bounded():
    assert fusion.population_vader_dispersion(pd.Series([-1.0, 1.0])) == pytest.approx(1.0)
    assert fusion.population_vader_dispersion(pd.Series([0.4])) == pytest.approx(0.0)
    with pytest.raises(ValueError, match=r"\[-1, 1\]"):
        fusion.population_vader_dispersion(pd.Series([1.2]))

    dates = pd.bdate_range("2020-01-01", periods=70)
    ticker = _ticker_sentiment(dates)
    ticker.loc[ticker["sector"].eq("Tech") & ticker["ticker"].isin(["T0", "T1"]), "ticker_sentiment"] = 1.0
    ticker.loc[ticker["sector"].eq("Tech") & ticker["ticker"].isin(["T2", "T3"]), "ticker_sentiment"] = -1.0
    signals = fusion.compute_sector_confidence_signals(
        _sector_index(dates),
        ticker,
        _sector_map(),
        _rebalance(dates[68], dates[69]),
    )
    assert signals["a21"].between(0, 1).all()
    assert signals["confidence"].between(0, 1).all()


def _base_weights() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"date": pd.Timestamp("2020-04-01"), "fund_family": portfolios.FAMILY_EQUITY, "method": portfolios.METHOD_MIN_VARIANCE, "asset": "T0", "sector": "Tech", "weight": 0.30},
            {"date": pd.Timestamp("2020-04-01"), "fund_family": portfolios.FAMILY_EQUITY, "method": portfolios.METHOD_MIN_VARIANCE, "asset": "T1", "sector": "Tech", "weight": 0.20},
            {"date": pd.Timestamp("2020-04-01"), "fund_family": portfolios.FAMILY_EQUITY, "method": portfolios.METHOD_MIN_VARIANCE, "asset": "H0", "sector": "Health", "weight": 0.50},
            {"date": pd.Timestamp("2020-04-01"), "fund_family": portfolios.FAMILY_EQUITY, "method": portfolios.METHOD_MIN_VARIANCE, "asset": "H1", "sector": "Health", "weight": 0.00},
        ]
    )


def _sector_confidence(c_tech: float = 0.5, c_health: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"live_rebalance_date": pd.Timestamp("2020-04-01"), "sector": "Tech", "z_star": 1.0, "confidence": c_tech, "raw_tilt": 0.10, "confidence_adjusted_tilt": 0.10 * c_tech},
            {"live_rebalance_date": pd.Timestamp("2020-04-01"), "sector": "Health", "z_star": -1.0, "confidence": c_health, "raw_tilt": -0.10, "confidence_adjusted_tilt": -0.10 * c_health},
        ]
    )


def test_standard_and_confidence_multiplier_formulas_are_exact_and_long_only():
    base = _base_weights()
    standard = fusion.apply_sector_overlay(base, _sector_confidence(), overlay=fusion.OVERLAY_STANDARD)
    confidence = fusion.apply_sector_overlay(base, _sector_confidence(), overlay=fusion.OVERLAY_CONFIDENCE)

    assert standard.set_index("sector").loc["Tech", "pre_normalisation_multiplier"].iloc[0] == pytest.approx(1.10)
    assert standard.set_index("sector").loc["Health", "pre_normalisation_multiplier"].iloc[0] == pytest.approx(0.90)
    assert confidence.set_index("sector").loc["Tech", "pre_normalisation_multiplier"].iloc[0] == pytest.approx(1.05)
    assert confidence.set_index("sector").loc["Health", "pre_normalisation_multiplier"].iloc[0] == pytest.approx(1.00)
    assert standard["weight"].ge(0).all()
    assert confidence["weight"].ge(0).all()
    assert standard["weight"].sum() == pytest.approx(1.0)
    assert confidence["weight"].sum() == pytest.approx(1.0)
    assert standard.loc[standard["asset"].eq("H1"), "weight"].item() == pytest.approx(0.0)


def test_confidence_extremes_and_tilt_direction_constraints():
    base = _base_weights()
    c_one = fusion.apply_sector_overlay(base, _sector_confidence(1.0, 1.0), overlay=fusion.OVERLAY_CONFIDENCE)
    standard = fusion.apply_sector_overlay(base, _sector_confidence(1.0, 1.0), overlay=fusion.OVERLAY_STANDARD)
    pd.testing.assert_series_equal(
        c_one.set_index("asset")["weight"].sort_index(),
        standard.set_index("asset")["weight"].sort_index(),
        check_names=False,
    )

    c_zero = fusion.apply_sector_overlay(base, _sector_confidence(0.0, 0.0), overlay=fusion.OVERLAY_CONFIDENCE)
    pd.testing.assert_series_equal(
        c_zero.set_index("asset")["weight"].sort_index(),
        base.set_index("asset")["weight"].sort_index(),
        check_names=False,
    )
    signals = _sector_confidence(0.25, 0.75)
    assert np.sign(signals["raw_tilt"]).eq(np.sign(signals["confidence_adjusted_tilt"])).all()
    assert signals["confidence_adjusted_tilt"].abs().le(signals["raw_tilt"].abs()).all()


def test_within_sector_relative_weights_are_preserved_before_global_renormalisation():
    standard = fusion.apply_sector_overlay(_base_weights(), _sector_confidence(), overlay=fusion.OVERLAY_STANDARD)
    tech = standard.loc[standard["sector"].eq("Tech")].set_index("asset")
    assert tech.loc["T0", "pre_normalisation_weight"] / tech.loc["T1", "pre_normalisation_weight"] == pytest.approx(1.5)
    assert tech.loc["T0", "weight"] / tech.loc["T1", "weight"] == pytest.approx(1.5)


def test_overlay_backtest_costs_use_final_overlay_turnover_and_dates_are_paired():
    base_returns = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-04-01", "2020-04-02", "2020-05-01"]),
            "net_return": [0.01, 0.01, 0.01],
            "gross_return": [0.011, 0.01, 0.01],
            "turnover": [1.0, 0.0, 0.2],
            "transaction_cost": [0.001, 0.0, 0.0002],
            "missing_return_asset_count": [0, 0, 0],
        }
    )
    equity_returns = pd.DataFrame(
        [
            {"date": pd.Timestamp(date), "ticker": asset, "daily_return": 0.01}
            for date in ["2020-04-01", "2020-04-02", "2020-05-01"]
            for asset in ["T0", "T1", "H0", "H1"]
        ]
    )
    weights = fusion.apply_sector_overlay(_base_weights(), _sector_confidence(), overlay=fusion.OVERLAY_STANDARD)
    returns, turnover = fusion.backtest_overlay_returns(
        portfolios.METHOD_MIN_VARIANCE,
        weights,
        base_returns,
        equity_returns,
        overlay=fusion.OVERLAY_STANDARD,
        tilt_strength=0.10,
    )

    assert list(returns["date"]) == list(base_returns["date"])
    assert turnover.iloc[0]["turnover"] == pytest.approx(1.0)
    assert turnover.iloc[0]["transaction_cost"] == pytest.approx(0.001)
    assert returns.iloc[0]["net_return"] == pytest.approx(returns.iloc[0]["gross_return"] - 0.001)
