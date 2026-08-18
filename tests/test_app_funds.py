import json
import math
from pathlib import Path

import altair as alt
import pandas as pd
import pytest

from app import funds
from app import charts


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


def test_family_method_filters_are_composable_and_visible():
    metrics = pd.read_csv(project_root() / "results/tables/performance_metrics.csv")

    assert len(funds.filter_metrics(metrics, "All", "All")) == 9

    equity = funds.filter_metrics(metrics, "Equity", "All")
    crypto = funds.filter_metrics(metrics, "Crypto", "All")
    combined = funds.filter_metrics(metrics, "Combined", "All")
    assert set(equity["fund_family"]) == {"Equity-only"}
    assert set(crypto["fund_family"]) == {"Crypto-only"}
    assert set(combined["fund_family"]) == {"Combined"}
    assert len(equity) == len(crypto) == len(combined) == 3

    equal_weight = funds.filter_metrics(metrics, "All", "Equal Weight")
    min_variance = funds.filter_metrics(metrics, "All", "Minimum Variance")
    max_sharpe = funds.filter_metrics(metrics, "All", "Maximum Sharpe")
    assert set(equal_weight["method"]) == {"Equal Weight"}
    assert set(min_variance["method"]) == {"Minimum Variance"}
    assert set(max_sharpe["method"]) == {"Maximum Sharpe"}
    assert len(equal_weight) == len(min_variance) == len(max_sharpe) == 3

    single = funds.filter_metrics(metrics, "Combined", "Maximum Sharpe")
    assert len(single) == 1
    assert single.iloc[0]["fund_family"] == "Combined"
    assert single.iloc[0]["method"] == "Maximum Sharpe"


def test_chart_input_is_non_empty_for_required_filter_states():
    metrics = pd.read_csv(project_root() / "results/tables/performance_metrics.csv")
    cases = [
        ("All", "All", 9),
        ("Equity", "All", 3),
        ("Crypto", "All", 3),
        ("Combined", "All", 3),
        ("All", "Equal Weight", 3),
        ("All", "Minimum Variance", 3),
        ("All", "Maximum Sharpe", 3),
        ("Combined", "Maximum Sharpe", 1),
    ]

    for family_filter, method_filter, expected_rows in cases:
        filtered = funds.filter_metrics(metrics, family_filter, method_filter)
        selected = funds.available_funds(filtered)[0]
        chart_input = funds.comparison_frame(filtered, selected)

        assert len(chart_input) == expected_rows
        assert chart_input["is_selected"].sum() == 1
        assert selected.label in set(chart_input["fund_label"])
        assert {"return_pct", "volatility_pct", "family_label", "method", "fund_key"}.issubset(
            chart_input.columns
        )


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


def test_comparison_frame_marks_selected_fund_and_stable_key():
    metrics = pd.DataFrame(
        {
            "fund_family": ["Combined", "Combined"],
            "method": ["Equal Weight", "Maximum Sharpe"],
            "method_type": ["benchmark", "optimisation"],
            "net_annualised_return": [0.1, 0.2],
            "net_annualised_volatility": [0.3, 0.4],
            "net_max_drawdown": [-0.2, -0.3],
        }
    )
    frame = funds.comparison_frame(metrics, funds.FundKey("Combined", "Maximum Sharpe"))

    assert frame["fund_key"].tolist() == ["Combined|Equal Weight", "Combined|Maximum Sharpe"]
    assert frame["is_selected"].tolist() == [False, True]


def test_filtered_selection_preserves_or_replaces_authoritative_key_deterministically():
    metrics = pd.read_csv(project_root() / "results/tables/performance_metrics.csv")

    selected = funds.FundKey("Combined", "Equal Weight")
    preserved, preserved_frame = funds.deterministic_filtered_selection(
        metrics, selected, "All", "All"
    )
    assert preserved == selected
    assert len(preserved_frame) == 9

    replacement, replacement_frame = funds.deterministic_filtered_selection(
        metrics, selected, "Crypto", "Equal Weight"
    )
    assert replacement == funds.FundKey("Crypto-only", "Equal Weight")
    assert replacement_frame[["fund_family", "method"]].drop_duplicates().values.tolist() == [
        ["Crypto-only", "Equal Weight"]
    ]

    retained, retained_frame = funds.deterministic_filtered_selection(
        metrics, funds.FundKey("Crypto-only", "Equal Weight"), "All", "All"
    )
    assert retained == funds.FundKey("Crypto-only", "Equal Weight")
    assert len(retained_frame) == 9


def test_chart_frame_selected_flag_and_direct_label_source_follow_authoritative_key():
    metrics = pd.read_csv(project_root() / "results/tables/performance_metrics.csv")
    selected = funds.FundKey("Combined", "Equal Weight")
    frame = funds.comparison_frame(funds.filter_metrics(metrics, "All", "All"), selected)

    highlighted = frame[frame["is_selected"]]

    assert len(frame) == 9
    assert highlighted["fund_key"].tolist() == [funds.fund_key_id(selected)]
    assert highlighted["fund_label"].tolist() == ["Combined / Equal Weight"]


def test_risk_return_axis_domains_are_adaptive_only_for_small_filter_states():
    metrics = pd.read_csv(project_root() / "results/tables/performance_metrics.csv")

    full_frame = funds.comparison_frame(metrics, funds.FundKey("Combined", "Equal Weight"))
    assert funds.risk_return_axis_domains(full_frame) == (None, None)

    single_frame = funds.comparison_frame(
        funds.filter_metrics(metrics, "Crypto", "Equal Weight"),
        funds.FundKey("Crypto-only", "Equal Weight"),
    )
    x_domain, y_domain = funds.risk_return_axis_domains(single_frame)
    row = single_frame.iloc[0]
    assert len(single_frame) == 1
    assert x_domain[0] < row["volatility_pct"] < x_domain[1]
    assert y_domain[0] < row["return_pct"] < y_domain[1]
    assert x_domain[1] - x_domain[0] > 0.02
    assert y_domain[1] - y_domain[0] > 0.02

    small_frame = funds.comparison_frame(
        funds.filter_metrics(metrics, "Combined", "All"),
        funds.FundKey("Combined", "Maximum Sharpe"),
    )
    x_domain, y_domain = funds.risk_return_axis_domains(small_frame)
    assert len(small_frame) == 3
    assert x_domain[0] <= small_frame["volatility_pct"].min()
    assert x_domain[1] >= small_frame["volatility_pct"].max()
    assert y_domain[0] <= small_frame["return_pct"].min()
    assert y_domain[1] >= small_frame["return_pct"].max()


def test_chart_selection_event_parsing_handles_native_shapes():
    metrics = pd.DataFrame(
        {
            "fund_family": ["Combined", "Crypto-only"],
            "method": ["Maximum Sharpe", "Equal Weight"],
        }
    )

    list_event = {
        "selection": {
            "fund_pick": [{"fund_family": "Combined", "method": "Maximum Sharpe"}]
        }
    }
    dict_event = {
        "selection": {
            "fund_pick": {"fund_family": ["Crypto-only"], "method": ["Equal Weight"]}
        }
    }
    key_event = {"selection": {"fund_pick": {"fund_key": ["Combined|Maximum Sharpe"]}}}

    assert funds.fund_key_from_selection_event(list_event, metrics).label == (
        "Combined / Maximum Sharpe"
    )
    assert funds.fund_key_from_selection_event(key_event, metrics).label == (
        "Combined / Maximum Sharpe"
    )
    assert funds.fund_key_from_selection_event(dict_event, metrics).label == (
        "Crypto / Equal Weight"
    )
    assert funds.fund_key_from_selection_event({"selection": {"fund_pick": []}}, metrics) is None
    assert (
        funds.fund_key_from_selection_event(
            {"selection": {"fund_pick": [{"fund_family": "Equity-only", "method": "Missing"}]}},
            metrics,
        )
        is None
    )


def test_risk_return_spec_defines_native_selection_and_dark_labels():
    spec = charts.risk_return_spec()

    json.dumps(spec)
    alt.Chart.from_dict(spec, validate=True)
    assert spec["layer"][0]["encoding"]["x"]["field"] == "volatility_pct"
    assert spec["layer"][0]["encoding"]["y"]["field"] == "return_pct"
    assert spec["layer"][0]["encoding"]["x"]["axis"]["format"] == ".1%"
    assert spec["layer"][0]["encoding"]["y"]["axis"]["format"] == ".1%"
    assert spec["layer"][0]["encoding"]["x"]["axis"]["tickCount"] == 5
    assert spec["layer"][0]["params"][0]["name"] == charts.FUND_SELECTION_NAME
    assert spec["layer"][0]["params"][0]["select"]["fields"] == ["fund_key"]
    assert spec["config"]["axis"]["labelColor"]
    assert spec["config"]["legend"]["labelColor"]
    assert spec["layer"][0]["encoding"]["tooltip"][0]["title"] == "Fund"
    assert "Historical OOS annualised return" in {
        item["title"] for item in spec["layer"][0]["encoding"]["tooltip"]
    }


def test_risk_return_spec_accepts_adaptive_domains_and_single_fund_size():
    spec = charts.risk_return_spec(
        x_domain=[0.75, 0.87],
        y_domain=[0.29, 0.39],
        single_fund=True,
    )

    json.dumps(spec)
    alt.Chart.from_dict(spec, validate=True)
    point_encoding = spec["layer"][0]["encoding"]
    assert point_encoding["x"]["scale"] == {
        "zero": False,
        "nice": False,
        "domain": [0.75, 0.87],
    }
    assert point_encoding["y"]["scale"] == {
        "zero": False,
        "nice": False,
        "domain": [0.29, 0.39],
    }
    assert point_encoding["size"]["condition"]["value"] == 180


def test_growth_drawdown_and_holdings_axes_use_non_ambiguous_labels():
    growth = charts.growth_spec()
    drawdown = charts.drawdown_spec()
    holdings = charts.holdings_spec(pd.DataFrame({"asset": ["A", "B"], "weight": [0.02, 0.02]}))

    assert growth["encoding"]["x"]["axis"]["format"] == "%b %Y"
    assert drawdown["encoding"]["x"]["axis"]["format"] == "%b %Y"
    assert holdings["encoding"]["x"]["axis"]["format"] == ".1%"
    assert holdings["encoding"]["x"]["axis"]["tickCount"] == 5


def test_equal_weight_estimation_context_does_not_imply_optimiser_window():
    value, label = funds.estimation_context("Equal Weight", 252)

    assert value == "Benchmark"
    assert label == "no optimisation estimation window"
    assert "no optimiser estimation window" in "\n".join(
        funds.rebalance_methodology_lines(
            funds.FundKey("Combined", "Equal Weight"),
            pd.Series(
                {
                    "sample_start": "2021-01-04",
                    "sample_end": "2023-12-29",
                    "periods_per_year": 252,
                }
            ),
        )
    )


def test_combined_equal_weight_latest_exposure_matches_saved_weights():
    root = project_root()
    exposure = pd.read_csv(root / "results/tables/asset_class_exposure.csv")
    weights = pd.read_csv(root / "results/data/fund_weights.csv")
    key = funds.FundKey("Combined", "Equal Weight")

    latest_exposure = funds.latest_exposure(exposure, key)
    latest_weights = funds.latest_weights(weights, key)

    assert latest_exposure.set_index("asset_class")["exposure"].to_dict() == pytest.approx(
        {"crypto": 1 / 6, "equity": 5 / 6}
    )
    assert latest_weights.groupby("asset_class")["weight"].sum().to_dict() == pytest.approx(
        {"crypto": 1 / 6, "equity": 5 / 6}
    )


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


def test_broad_near_equal_detection_and_representative_holdings():
    weights = pd.DataFrame(
        {
            "date": ["2021-01-01"] * 5,
            "asset": ["A", "B", "C", "D", "E"],
            "asset_class": ["equity"] * 5,
            "weight": [0.2, 0.2, 0.2, 0.2, 0.2],
        }
    )
    summary = funds.concentration_summary(weights)
    representative = funds.representative_holdings(weights, top_n=3)

    assert funds.is_broad_near_equal(summary) is False
    assert representative["asset"].tolist() == ["A", "B", "C"]


def test_large_broad_near_equal_fund_is_detected():
    weights = pd.DataFrame(
        {
            "date": ["2021-01-01"] * 20,
            "asset": [f"A{i:02d}" for i in range(20)],
            "asset_class": ["equity"] * 20,
            "weight": [0.05] * 20,
        }
    )
    summary = funds.concentration_summary(weights)

    assert funds.is_broad_near_equal(summary) is True


def test_peer_comparison_uses_family_medians():
    metrics = pd.DataFrame(
        {
            "fund_family": ["Combined", "Combined", "Combined", "Equity-only"],
            "method": ["Equal Weight", "Minimum Variance", "Maximum Sharpe", "Equal Weight"],
            "net_annualised_return": [0.1, 0.2, 0.3, 0.9],
            "net_annualised_volatility": [0.4, 0.5, 0.6, 0.9],
            "net_sharpe_ratio": [0.25, 0.4, 0.5, 1.0],
        }
    )

    peer = funds.peer_comparison(metrics, funds.FundKey("Combined", "Minimum Variance"))

    assert peer.selected_return == 0.2
    assert peer.family_median_return == 0.2
    assert peer.family_median_volatility == 0.5
    assert peer.family_median_sharpe == 0.4
    assert peer.family_peer_count == 3
    assert peer.other_family_peer_count == 2
    assert peer.heading == "Position within the 3-fund Combined family (2 other peers)"

    relative = funds.relative_peer_metrics(metrics, funds.FundKey("Combined", "Minimum Variance"))

    assert [metric.label for metric in relative] == ["Return", "Volatility", "Sharpe"]
    assert relative[0].selected_text == "20.0%"
    assert relative[0].median_text == "20.0%"
    assert math.isclose(relative[0].selected_position, 0.5)
    assert "not automatically a better fund" in relative[1].context


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
