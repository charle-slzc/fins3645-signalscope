import pathlib
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import portfolios  # noqa: E402


def _monthly_returns(values: dict[str, list[float]], start: str = "2020-01-31") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(next(iter(values.values()))), freq="ME")
    return pd.DataFrame(values, index=dates)


def _daily_business_returns(rows: int = 70) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=rows)
    return pd.DataFrame(
        {
            "AAA": np.linspace(0.001, 0.002, rows),
            "BBB": np.linspace(0.002, 0.001, rows),
        },
        index=dates,
    )


def test_method_types_keep_equal_weight_as_benchmark_only():
    assert portfolios.method_type(portfolios.METHOD_EQUAL_WEIGHT) == "benchmark"
    assert portfolios.method_type(portfolios.METHOD_MIN_VARIANCE) == "optimisation"
    assert portfolios.method_type(portfolios.METHOD_MAX_SHARPE) == "optimisation"
    assert portfolios.METHOD_EQUAL_WEIGHT not in portfolios.OPTIMISATION_METHODS


def test_oos_weights_are_long_only_fully_invested_and_live_after_estimation_window():
    returns = _monthly_returns(
        {
            "AAA": [0.01, 0.01, 0.01, 0.02, 0.02, 0.02],
            "BBB": [0.02, -0.01, 0.03, 0.01, -0.02, 0.01],
        }
    )

    result = portfolios.oos_backtest(
        returns,
        method=portfolios.METHOD_EQUAL_WEIGHT,
        fund_family=portfolios.FAMILY_EQUITY,
        estimation_window=3,
        periods_per_year=252,
    )

    first_diag = result.diagnostics.iloc[0]
    assert result.first_live_date == returns.index[3]
    assert first_diag["estimation_start"] == returns.index[0]
    assert first_diag["estimation_end"] == returns.index[2]
    assert first_diag["decision_date"] == returns.index[2]
    assert first_diag["live_rebalance_date"] == returns.index[3]
    assert (result.fund_weights["weight"] >= 0).all()
    assert (result.fund_weights["weight"] <= 1).all()
    sums = result.fund_weights.groupby(["date", "fund_family", "method"])["weight"].sum()
    assert np.allclose(sums.to_numpy(dtype=float), 1.0)


def test_monthly_rebalance_uses_first_possible_date_then_month_changes():
    returns = _daily_business_returns(rows=70)

    result = portfolios.oos_backtest(
        returns,
        method=portfolios.METHOD_EQUAL_WEIGHT,
        fund_family=portfolios.FAMILY_EQUITY,
        estimation_window=3,
        periods_per_year=252,
    )

    rebalance_dates = pd.DatetimeIndex(result.diagnostics["live_rebalance_date"])
    assert rebalance_dates[0] == returns.index[3]
    assert rebalance_dates[1:].to_period("M").is_unique
    assert all(date.day <= 7 for date in rebalance_dates[1:])


def test_max_sharpe_does_not_use_live_return_in_estimation_window():
    returns = _monthly_returns(
        {
            "AAA": [0.01, 0.01, 0.01, 0.01, 0.01],
            "BBB": [-0.01, -0.01, -0.01, 1.00, 1.00],
        }
    )

    result = portfolios.oos_backtest(
        returns,
        method=portfolios.METHOD_MAX_SHARPE,
        fund_family=portfolios.FAMILY_EQUITY,
        estimation_window=3,
        periods_per_year=252,
    )
    first_weights = result.fund_weights.loc[result.fund_weights["date"].eq(returns.index[3])]

    assert first_weights.set_index("asset").loc["BBB", "weight"] < 0.10
    assert result.diagnostics.iloc[0]["estimation_end"] == returns.index[2]


def test_turnover_and_transaction_cost_are_deducted_on_rebalance_date():
    returns = _monthly_returns(
        {
            "AAA": [0.01, 0.01, 0.02, 0.02],
            "BBB": [0.01, 0.01, 0.04, 0.04],
        }
    )

    result = portfolios.oos_backtest(
        returns,
        method=portfolios.METHOD_EQUAL_WEIGHT,
        fund_family=portfolios.FAMILY_EQUITY,
        estimation_window=2,
        periods_per_year=252,
        transaction_cost_rate=0.001,
    )
    first = result.fund_returns.iloc[0]

    assert portfolios.calculate_turnover(None, pd.Series({"AAA": 0.5, "BBB": 0.5})) == pytest.approx(1.0)
    assert first["turnover"] == pytest.approx(1.0)
    assert first["transaction_cost"] == pytest.approx(0.001)
    assert first["net_return"] == pytest.approx(first["gross_return"] - 0.001)


def test_performance_metrics_use_requested_annualisation_factor():
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    returns = pd.Series([0.01] * 10, index=dates)

    equity = portfolios.performance_metrics(returns, periods_per_year=252)
    crypto = portfolios.performance_metrics(returns, periods_per_year=365)

    assert equity["annualised_return"] == pytest.approx((1.01**10) ** (252 / 10) - 1)
    assert crypto["annualised_return"] == pytest.approx((1.01**10) ** (365 / 10) - 1)
    assert crypto["annualised_return"] > equity["annualised_return"]


def test_solver_failure_falls_back_to_equal_weight_and_records_diagnostic(monkeypatch):
    returns = _monthly_returns(
        {
            "AAA": [0.01, 0.02, 0.01, 0.02],
            "BBB": [0.02, 0.01, 0.02, 0.01],
        }
    )

    def fail_minimize(*_args, **_kwargs):
        return SimpleNamespace(success=False, status=9, message="forced failure", x=np.array([0.5, 0.5]))

    monkeypatch.setattr(portfolios.scipy_opt, "minimize", fail_minimize)
    result = portfolios.oos_backtest(
        returns,
        method=portfolios.METHOD_MIN_VARIANCE,
        fund_family=portfolios.FAMILY_EQUITY,
        estimation_window=2,
        periods_per_year=252,
    )

    assert bool(result.diagnostics.iloc[0]["fallback_used"]) is True
    assert "forced failure" in result.diagnostics.iloc[0]["fallback_reason"]
    first_weights = result.fund_weights.loc[result.fund_weights["date"].eq(returns.index[2])]
    assert first_weights.set_index("asset")["weight"].to_dict() == pytest.approx({"AAA": 0.5, "BBB": 0.5})


def test_optimisation_methods_are_distinguishable_on_synthetic_dataset():
    returns = _monthly_returns(
        {
            "LOWVOL": [0.001, 0.0011, 0.0009, 0.0010, 0.0012, 0.0011],
            "HIGHMU": [0.03, -0.005, 0.035, -0.004, 0.030, -0.006],
            "NEG": [-0.01, -0.012, -0.009, -0.011, -0.010, -0.012],
            "MID": [0.006, 0.004, 0.005, 0.006, 0.004, 0.005],
        }
    )

    outputs = {
        method: portfolios.oos_backtest(
            returns,
            method=method,
            fund_family=portfolios.FAMILY_EQUITY,
            estimation_window=4,
            periods_per_year=252,
        )
        for method in portfolios.METHODS
    }
    weights = {
        method: result.fund_weights.loc[result.fund_weights["date"].eq(returns.index[4])]
        .set_index("asset")["weight"]
        .sort_index()
        for method, result in outputs.items()
    }

    assert not np.allclose(weights[portfolios.METHOD_EQUAL_WEIGHT], weights[portfolios.METHOD_MIN_VARIANCE])
    assert not np.allclose(weights[portfolios.METHOD_EQUAL_WEIGHT], weights[portfolios.METHOD_MAX_SHARPE])
    assert not np.allclose(weights[portfolios.METHOD_MIN_VARIANCE], weights[portfolios.METHOD_MAX_SHARPE])


def test_combined_asset_class_exposure_reconciles_to_weights():
    returns = _monthly_returns(
        {
            "AAA": [0.01, 0.01, 0.02, 0.02],
            "BBB": [0.02, 0.02, 0.01, 0.01],
            "BTC-USD": [0.03, -0.01, 0.04, -0.02],
        }
    )
    asset_map = {"AAA": "equity", "BBB": "equity", "BTC-USD": "crypto"}

    result = portfolios.oos_backtest(
        returns,
        method=portfolios.METHOD_EQUAL_WEIGHT,
        fund_family=portfolios.FAMILY_COMBINED,
        estimation_window=2,
        periods_per_year=252,
        asset_class_map=asset_map,
    )
    exposures = result.asset_class_exposure.groupby(["date", "fund_family", "method"])["exposure"].sum()
    weights = result.fund_weights.groupby(["date", "fund_family", "method"])["weight"].sum()

    assert np.allclose(exposures.to_numpy(dtype=float), 1.0)
    pd.testing.assert_series_equal(exposures, weights.rename("exposure"))
    first_exposure = result.asset_class_exposure.loc[
        result.asset_class_exposure["date"].eq(returns.index[2])
    ].set_index("asset_class")["exposure"]
    assert first_exposure.loc["equity"] == pytest.approx(2 / 3)
    assert first_exposure.loc["crypto"] == pytest.approx(1 / 3)
