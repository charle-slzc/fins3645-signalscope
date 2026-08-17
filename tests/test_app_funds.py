import math
from pathlib import Path

import pandas as pd
import pytest

from app import funds


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_available_funds_contains_expected_nine_combinations():
    metrics = pd.read_csv(project_root() / "results/tables/performance_metrics.csv")

    combinations = {(key.family, key.method) for key in funds.available_funds(metrics)}

    assert combinations == {
        (family, method)
        for family in funds.FAMILY_ORDER
        for method in funds.METHOD_ORDER
    }


def test_validate_fund_key_accepts_display_family_and_rejects_missing_method():
    metrics = pd.DataFrame(
        {
            "fund_family": ["Combined"],
            "method": ["Minimum Variance"],
        }
    )

    key = funds.validate_fund_key(metrics, "Combined", "Minimum Variance")

    assert key.label == "Combined / Minimum Variance"
    with pytest.raises(KeyError):
        funds.validate_fund_key(metrics, "Combined", "Maximum Sharpe")


def test_growth_and_drawdown_are_derived_from_precomputed_net_returns():
    returns = pd.DataFrame(
        {
            "date": ["2021-01-03", "2021-01-01", "2021-01-02"],
            "net_return": [0.05, 0.10, -0.20],
        }
    )

    path = funds.growth_and_drawdown_from_returns(returns)

    assert path["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2021-01-01",
        "2021-01-02",
        "2021-01-03",
    ]
    assert path["growth_net_display"].round(6).tolist() == [1.1, 0.88, 0.924]
    assert path["drawdown_net_display"].round(6).tolist() == [0.0, -0.2, -0.16]


def test_latest_weights_effective_holdings_and_concentration_summary():
    key = funds.FundKey("Combined", "Maximum Sharpe")
    weights = pd.DataFrame(
        {
            "date": ["2021-01-01", "2021-02-01", "2021-02-01"],
            "fund_family": ["Combined", "Combined", "Combined"],
            "method": ["Maximum Sharpe", "Maximum Sharpe", "Maximum Sharpe"],
            "asset": ["OLD", "A", "B"],
            "asset_class": ["equity", "equity", "crypto"],
            "weight": [1.0, 0.75, 0.25],
        }
    )

    latest = funds.latest_weights(weights, key)
    summary = funds.concentration_summary(latest)

    assert latest["asset"].tolist() == ["A", "B"]
    assert math.isclose(funds.effective_holdings(latest), 1.6)
    assert summary.top_asset == "A"
    assert math.isclose(summary.top_weight, 0.75)
    assert summary.is_concentrated is True
    assert summary.is_low_diversification is True


def test_top_holdings_adds_display_remainder_without_changing_input():
    weights = pd.DataFrame(
        {
            "date": ["2021-01-01"] * 4,
            "asset": ["A", "B", "C", "D"],
            "asset_class": ["equity"] * 4,
            "weight": [0.4, 0.3, 0.2, 0.1],
        }
    )

    display = funds.top_holdings_with_remainder(weights, top_n=2)

    assert display["asset"].tolist() == ["A", "B", "Other holdings"]
    assert math.isclose(display.loc[2, "weight"], 0.3)
    assert weights["asset"].tolist() == ["A", "B", "C", "D"]


def test_latest_exposure_lookup_and_missing_fund_error():
    key = funds.FundKey("Combined", "Equal Weight")
    exposure = pd.DataFrame(
        {
            "date": ["2021-01-01", "2021-02-01", "2021-02-01"],
            "fund_family": ["Combined", "Combined", "Combined"],
            "method": ["Equal Weight", "Equal Weight", "Equal Weight"],
            "asset_class": ["equity", "equity", "crypto"],
            "exposure": [1.0, 0.8, 0.2],
        }
    )

    latest = funds.latest_exposure(exposure, key)

    assert latest["date"].dt.strftime("%Y-%m-%d").unique().tolist() == ["2021-02-01"]
    assert set(latest["asset_class_label"]) == {"Equity", "Crypto"}
    with pytest.raises(KeyError):
        funds.latest_exposure(exposure, funds.FundKey("Equity-only", "Equal Weight"))

