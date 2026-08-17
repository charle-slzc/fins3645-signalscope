import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import fusion, placebo, portfolios  # noqa: E402


def _signals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "live_rebalance_date": pd.Timestamp("2021-01-04"),
                "signal_cutoff_date": pd.Timestamp("2020-12-31"),
                "sector": "Tech",
                "z_star": 1.0,
                "b63": 0.25,
                "a21": 0.80,
                "confidence": 0.20,
            },
            {
                "live_rebalance_date": pd.Timestamp("2021-01-04"),
                "signal_cutoff_date": pd.Timestamp("2020-12-31"),
                "sector": "Health",
                "z_star": -1.0,
                "b63": 1.00,
                "a21": 0.80,
                "confidence": 0.80,
            },
            {
                "live_rebalance_date": pd.Timestamp("2021-02-01"),
                "signal_cutoff_date": pd.Timestamp("2021-01-29"),
                "sector": "Tech",
                "z_star": 0.5,
                "b63": 0.50,
                "a21": 1.00,
                "confidence": 0.50,
            },
            {
                "live_rebalance_date": pd.Timestamp("2021-02-01"),
                "signal_cutoff_date": pd.Timestamp("2021-01-29"),
                "sector": "Health",
                "z_star": -0.5,
                "b63": 1.00,
                "a21": 0.50,
                "confidence": 0.50,
            },
        ]
    )


def test_c_mean_and_c_match_use_exact_signal_formula_and_ignore_return_columns():
    signals = _signals()
    poisoned = signals.assign(realised_return=[99.0, -99.0, 50.0, -50.0])

    constants = placebo.calculate_shrinkage_constants(signals)
    poisoned_constants = placebo.calculate_shrinkage_constants(poisoned)

    assert constants.c_mean == pytest.approx(0.50)
    assert constants.c_match == pytest.approx((1.0 * 0.2 + 1.0 * 0.8 + 0.5 * 0.5 + 0.5 * 0.5) / 3.0)
    assert poisoned_constants == constants
    assert constants.placebo_abs_tilt_sum == pytest.approx(constants.confidence_abs_tilt_sum)
    assert abs(constants.aggregate_abs_tilt_difference) < 1e-15


def test_matched_placebo_uses_one_global_constant_and_preserves_direction_bounds():
    constants = placebo.calculate_shrinkage_constants(_signals())
    selectivity = placebo.build_selectivity_table(_signals(), constants)

    assert selectivity["c_match"].nunique() == 1
    assert selectivity["placebo_tilt"].abs().sum() == pytest.approx(selectivity["confidence_tilt"].abs().sum())
    assert np.sign(selectivity["placebo_tilt"]).eq(np.sign(selectivity["standard_tilt"])).all()
    assert np.sign(selectivity["confidence_tilt"]).eq(np.sign(selectivity["standard_tilt"])).all()
    assert selectivity["placebo_tilt"].abs().le(selectivity["standard_tilt"].abs()).all()
    assert selectivity["confidence_tilt"].abs().le(selectivity["standard_tilt"].abs()).all()

    low = selectivity.loc[selectivity["confidence"].lt(constants.c_match)]
    high = selectivity.loc[selectivity["confidence"].gt(constants.c_match)]
    equal = selectivity.loc[selectivity["confidence"].eq(constants.c_match)]
    assert low["confidence_tilt"].abs().lt(low["placebo_tilt"].abs()).all()
    assert high["confidence_tilt"].abs().gt(high["placebo_tilt"].abs()).all()
    assert np.allclose(equal["confidence_tilt"], equal["placebo_tilt"])


def _base_weights_for(method: str) -> pd.DataFrame:
    rows = []
    for date in [pd.Timestamp("2021-01-04"), pd.Timestamp("2021-02-01")]:
        rows.extend(
            [
                {
                    "date": date,
                    "fund_family": portfolios.FAMILY_EQUITY,
                    "method": method,
                    "method_type": "optimisation",
                    "asset": "T0",
                    "asset_class": "equity",
                    "sector": "Tech",
                    "weight": 0.60,
                    "base_weight": 0.60,
                    "pre_normalisation_multiplier": 1.0,
                    "pre_normalisation_weight": 0.60,
                    "overlay": fusion.OVERLAY_BASE,
                    "tilt_strength": 0.10,
                    "base_method": method,
                },
                {
                    "date": date,
                    "fund_family": portfolios.FAMILY_EQUITY,
                    "method": method,
                    "method_type": "optimisation",
                    "asset": "H0",
                    "asset_class": "equity",
                    "sector": "Health",
                    "weight": 0.40,
                    "base_weight": 0.40,
                    "pre_normalisation_multiplier": 1.0,
                    "pre_normalisation_weight": 0.40,
                    "overlay": fusion.OVERLAY_BASE,
                    "tilt_strength": 0.10,
                    "base_method": method,
                },
            ]
        )
    return pd.DataFrame(rows)


def _existing_fusion_weights() -> pd.DataFrame:
    frames = []
    for method in [portfolios.METHOD_MIN_VARIANCE, portfolios.METHOD_MAX_SHARPE]:
        base = _base_weights_for(method)
        frames.append(base)
        for overlay in [fusion.OVERLAY_STANDARD, fusion.OVERLAY_CONFIDENCE]:
            over = base.copy()
            over["overlay"] = overlay
            over["weight"] = np.where(over["sector"].eq("Tech"), 0.61, 0.39)
            frames.append(over)
    return pd.concat(frames, ignore_index=True)


def _existing_fusion_returns() -> pd.DataFrame:
    rows = []
    for method in [portfolios.METHOD_MIN_VARIANCE, portfolios.METHOD_MAX_SHARPE]:
        for overlay in [fusion.OVERLAY_BASE, fusion.OVERLAY_STANDARD, fusion.OVERLAY_CONFIDENCE]:
            for date in [pd.Timestamp("2021-01-04"), pd.Timestamp("2021-02-01")]:
                rows.append(
                    {
                        "date": date,
                        "gross_return": 0.01,
                        "turnover": 1.0 if date == pd.Timestamp("2021-01-04") else 0.10,
                        "transaction_cost": 0.001 if date == pd.Timestamp("2021-01-04") else 0.0001,
                        "net_return": 0.009 if date == pd.Timestamp("2021-01-04") else 0.0099,
                        "missing_return_asset_count": 0,
                        "base_method": method,
                        "overlay": overlay,
                        "tilt_strength": 0.10,
                        "growth_net": 1.0,
                        "drawdown_net": 0.0,
                    }
                )
    return pd.DataFrame(rows)


def test_placebo_overlay_weights_are_long_only_global_and_fully_invested():
    constants = placebo.calculate_shrinkage_constants(_signals())
    selectivity = placebo.build_selectivity_table(_signals(), constants)
    base = _base_weights_for(portfolios.METHOD_MIN_VARIANCE)

    weights = placebo.apply_matched_placebo_overlay(base, selectivity, c_match=constants.c_match)

    assert weights["overlay"].eq(placebo.OVERLAY_PLACEBO).all()
    assert weights["c_match"].nunique() == 1
    assert weights["weight"].ge(0).all()
    assert np.allclose(weights.groupby("date")["weight"].sum().to_numpy(dtype=float), 1.0)
    assert weights.groupby(["date", "sector"])["pre_normalisation_multiplier"].nunique().max() == 1


def test_placebo_suite_four_states_share_dates_and_costs_use_final_overlay_turnover():
    equity_returns = pd.DataFrame(
        [
            {"date": date, "ticker": asset, "daily_return": 0.01}
            for date in [pd.Timestamp("2021-01-04"), pd.Timestamp("2021-02-01")]
            for asset in ["T0", "H0"]
        ]
    )

    result = placebo.build_placebo_suite(
        sector_confidence=_signals(),
        fusion_returns=_existing_fusion_returns(),
        fusion_weights=_existing_fusion_weights(),
        equity_returns=equity_returns,
    )

    for method, group in result.fusion_placebo_returns.groupby("base_method"):
        date_sets = {
            overlay: tuple(frame["date"])
            for overlay, frame in group.groupby("overlay", sort=True)
        }
        assert len(set(date_sets.values())) == 1

    placebo_returns = result.fusion_placebo_returns.loc[
        result.fusion_placebo_returns["overlay"].eq(placebo.OVERLAY_PLACEBO)
    ]
    first_rows = placebo_returns.loc[placebo_returns["date"].eq(pd.Timestamp("2021-01-04"))]
    assert first_rows["turnover"].eq(1.0).all()
    assert first_rows["transaction_cost"].eq(portfolios.TRANSACTION_COST_RATE).all()
    assert np.allclose(first_rows["net_return"], first_rows["gross_return"] - first_rows["transaction_cost"])
    sums = result.fusion_placebo_weights.groupby(["base_method", "overlay", "date"])["weight"].sum()
    assert np.allclose(sums.to_numpy(dtype=float), 1.0)


def test_phase2c_output_contract_does_not_overlap_frozen_phase2b_outputs():
    from scripts import run_phase2c

    assert set(run_phase2c.OUTPUTS).isdisjoint(set(run_phase2c.FROZEN_ARTIFACTS))
