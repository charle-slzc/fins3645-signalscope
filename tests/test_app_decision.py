from pathlib import Path

import altair as alt
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import charts
from app import decision


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_artifact(relative: str) -> pd.DataFrame:
    return pd.read_csv(project_root() / relative)


def metrics() -> pd.DataFrame:
    return read_artifact("results/tables/performance_metrics.csv")


def weights() -> pd.DataFrame:
    return read_artifact("results/data/fund_weights.csv")


def sleeve(label: str, allocation: float = 100.0) -> decision.AllocationSleeve:
    family, method = label.split(" / ", 1)
    return decision.AllocationSleeve(
        family=decision.canonical_family(family),
        method=method,
        allocation_pct=allocation,
    )


def build_summary(sleeves: tuple[decision.AllocationSleeve, ...]):
    snapshot = decision.latest_snapshot_info(weights(), sleeves)
    components = decision.lookthrough_components(weights(), sleeves)
    holdings = decision.aggregate_lookthrough_holdings(components)
    classes = decision.aggregate_asset_classes(holdings)
    summary = decision.structural_summary(sleeves, holdings, classes, snapshot)
    return snapshot, components, holdings, classes, summary


def test_fund_key_and_allocation_validation_states():
    perf = metrics()

    assert decision.key_from_label(perf, "Equity / Equal Weight").family == "Equity-only"
    assert decision.key_from_label(perf, "Crypto / Maximum Sharpe").method == "Maximum Sharpe"

    under = decision.validate_allocation(perf, ["Equity / Equal Weight"], [85.0])
    over = decision.validate_allocation(
        perf,
        ["Equity / Equal Weight", "Crypto / Equal Weight"],
        [90.0, 20.0],
    )
    exact = decision.validate_allocation(
        perf,
        ["Equity / Equal Weight", "Crypto / Equal Weight"],
        [50.0, 50.0],
    )
    duplicate = decision.validate_allocation(
        perf,
        ["Equity / Equal Weight", "Equity / Equal Weight"],
        [50.0, 50.0],
    )
    negative = decision.validate_allocation(perf, ["Equity / Equal Weight"], [-1.0])

    assert not under.valid
    assert under.remaining_pct == pytest.approx(15.0)
    assert "remaining 15.0%" in under.messages[-1]
    assert not over.valid
    assert over.overallocated_pct == pytest.approx(10.0)
    assert "reduce by 10.0%" in over.messages[-1]
    assert exact.valid
    assert exact.total_pct == pytest.approx(100.0)
    assert not duplicate.valid
    assert "unique" in duplicate.messages[0]
    assert not negative.valid
    assert "negative" in " ".join(negative.messages)


def test_one_fund_equity_equal_weight_real_artifact_structure():
    _, _, holdings, classes, summary = build_summary((sleeve("Equity / Equal Weight"),))

    assert len(holdings) == 50
    assert holdings.iloc[0]["lookthrough_weight"] == pytest.approx(0.02)
    assert summary.effective_underlying_holdings == pytest.approx(50.0)
    assert summary.largest_weight == pytest.approx(0.02)
    assert summary.top5_share == pytest.approx(0.10)
    assert classes.set_index("asset_class")["lookthrough_weight"].to_dict() == pytest.approx(
        {"equity": 1.0}
    )


def test_one_fund_crypto_equal_weight_real_artifact_structure():
    _, _, holdings, classes, summary = build_summary((sleeve("Crypto / Equal Weight"),))

    assert len(holdings) == 10
    assert holdings.iloc[0]["lookthrough_weight"] == pytest.approx(0.10)
    assert summary.effective_underlying_holdings == pytest.approx(10.0)
    assert summary.largest_weight == pytest.approx(0.10)
    assert summary.top5_share == pytest.approx(0.50)
    assert classes.set_index("asset_class")["lookthrough_weight"].to_dict() == pytest.approx(
        {"crypto": 1.0}
    )


def test_one_fund_combined_equal_weight_real_artifact_structure():
    snapshot, _, holdings, classes, summary = build_summary((sleeve("Combined / Equal Weight"),))

    assert snapshot.aligned is True
    assert snapshot.display_date == "2023-12-01"
    assert len(holdings) == 60
    assert summary.effective_underlying_holdings == pytest.approx(60.0)
    assert summary.largest_weight == pytest.approx(1 / 60)
    assert summary.top5_share == pytest.approx(5 / 60)
    assert summary.largest_asset
    assert decision.format_percent(summary.largest_weight) == "1.7%"
    assert decision.format_percent(summary.top5_share) == "8.3%"
    assert classes.set_index("asset_class")["lookthrough_weight"].to_dict() == pytest.approx(
        {"crypto": 1 / 6, "equity": 5 / 6}
    )
    assert decision.asset_class_strip_html(classes).count("ss-decision-segment") == 2
    assert "Equity" in decision.asset_class_strip_html(classes)
    assert "83.3%" in decision.asset_class_strip_html(classes)
    assert "Crypto" in decision.asset_class_strip_html(classes)
    assert "16.7%" in decision.asset_class_strip_html(classes)


def test_equity_crypto_equal_weight_mix_real_artifact_structure():
    sleeves = (
        sleeve("Equity / Equal Weight", 50.0),
        sleeve("Crypto / Equal Weight", 50.0),
    )
    _, _, holdings, classes, summary = build_summary(sleeves)

    assert len(holdings) == 60
    assert holdings.set_index("asset").loc["ABBV", "lookthrough_weight"] == pytest.approx(0.01)
    assert holdings.set_index("asset").loc["BTC-USD", "lookthrough_weight"] == pytest.approx(0.05)
    assert summary.effective_underlying_holdings == pytest.approx(1 / 0.03)
    assert summary.largest_weight == pytest.approx(0.05)
    assert classes.set_index("asset_class")["lookthrough_weight"].to_dict() == pytest.approx(
        {"crypto": 0.5, "equity": 0.5}
    )
    overlaps = decision.pairwise_overlaps(weights(), sleeves)
    assert len(overlaps) == 1
    assert overlaps[0].overlap == pytest.approx(0.0)


def test_equity_combined_equal_weight_mix_aggregates_overlapping_assets():
    sleeves = (
        sleeve("Equity / Equal Weight", 50.0),
        sleeve("Combined / Equal Weight", 50.0),
    )
    _, components, holdings, classes, summary = build_summary(sleeves)
    abbv_components = components[components["asset"].eq("ABBV")]

    assert abbv_components["lookthrough_weight"].sum() == pytest.approx(0.5 * 0.02 + 0.5 / 60)
    assert holdings.set_index("asset").loc["ABBV", "lookthrough_weight"] == pytest.approx(
        0.5 * 0.02 + 0.5 / 60
    )
    assert len(holdings) == 60
    assert classes.set_index("asset_class")["lookthrough_weight"].to_dict() == pytest.approx(
        {"crypto": 1 / 12, "equity": 11 / 12}
    )
    assert summary.effective_underlying_holdings == pytest.approx(1 / 0.0175)
    assert summary.top5_share == pytest.approx(5 * (0.5 * 0.02 + 0.5 / 60))
    overlaps = decision.pairwise_overlaps(weights(), sleeves)
    assert len(overlaps) == 1
    assert overlaps[0].overlap == pytest.approx(5 / 6)


def test_optimised_multi_fund_mix_is_finite_and_fully_invested():
    sleeves = (
        sleeve("Combined / Maximum Sharpe", 40.0),
        sleeve("Equity / Minimum Variance", 35.0),
        sleeve("Crypto / Minimum Variance", 25.0),
    )
    _, _, holdings, classes, summary = build_summary(sleeves)

    assert holdings["lookthrough_weight"].sum() == pytest.approx(1.0)
    assert classes["lookthrough_weight"].sum() == pytest.approx(1.0)
    assert summary.effective_underlying_holdings > 0
    assert summary.largest_weight > 0
    assert summary.top5_share > summary.largest_weight


def test_pairwise_overlap_formula_and_missing_assets_as_zero():
    saved = weights()
    eq = sleeve("Equity / Equal Weight", 50.0)
    combined = sleeve("Combined / Equal Weight", 50.0)
    crypto = sleeve("Crypto / Equal Weight", 50.0)

    overlaps = decision.pairwise_overlaps(saved, (eq, combined, crypto))
    lookup = {(item.fund_a, item.fund_b): item.overlap for item in overlaps}

    assert lookup[("Equity / Equal Weight", "Combined / Equal Weight")] == pytest.approx(5 / 6)
    assert lookup[("Equity / Equal Weight", "Crypto / Equal Weight")] == pytest.approx(0.0)

    synthetic = pd.DataFrame(
        {
            "date": ["2023-12-01"] * 4,
            "fund_family": ["Equity-only", "Equity-only", "Crypto-only", "Crypto-only"],
            "method": ["Equal Weight", "Equal Weight", "Equal Weight", "Equal Weight"],
            "method_type": ["benchmark"] * 4,
            "asset": ["A", "B", "B", "C"],
            "asset_class": ["equity", "equity", "crypto", "crypto"],
            "weight": [0.7, 0.3, 0.2, 0.8],
            "live_rebalance_date": ["2023-12-01"] * 4,
            "decision_date": ["2023-11-30"] * 4,
        }
    )
    synthetic_overlap = decision.pairwise_overlaps(synthetic, (eq, crypto))[0]
    assert synthetic_overlap.overlap == pytest.approx(0.2)


def test_snapshot_consistency_and_invalid_weights_are_detected():
    good = weights()
    sleeves = (sleeve("Equity / Equal Weight"), sleeve("Crypto / Equal Weight"))
    snapshot = decision.latest_snapshot_info(good, sleeves)

    assert snapshot.aligned is True
    assert snapshot.display_date == "2023-12-01"

    bad = good.copy()
    mask = (
        bad["fund_family"].eq("Equity-only")
        & bad["method"].eq("Equal Weight")
        & bad["date"].eq("2023-12-01")
        & bad["asset"].eq("ABBV")
    )
    bad.loc[mask, "weight"] = 0.03
    with pytest.raises(ValueError, match="sum"):
        decision.latest_snapshot_info(bad, (sleeve("Equity / Equal Weight"),))

    with pytest.raises(KeyError):
        decision.lookthrough_components(good, (decision.AllocationSleeve("Combined", "Missing", 100.0),))


def test_decision_narrative_grammar_direct_labels_and_active_chart_specs_are_valid():
    single = sleeve("Combined / Equal Weight")
    _, _, single_holdings, single_classes, single_summary = build_summary((single,))
    single_narrative = decision.decision_narrative(single_summary, [])

    assert "Your 1 fund sleeve resolves to 83.3% equity and 16.7% crypto" in single_narrative
    assert "Your 1 fund sleeves" not in single_narrative
    assert "Combined / Equal Weight" in decision.sleeve_strip_html((single,))
    assert "100.0%" in decision.sleeve_strip_html((single,))
    broad_display = decision.holdings_display(single_holdings)
    assert broad_display.mode == "broad"
    assert len(broad_display.visible) == 8
    assert broad_display.remainder_count == 52
    assert broad_display.remainder_weight == pytest.approx(52 / 60)
    assert decision.format_percent_one(broad_display.remainder_weight) == "86.7%"
    assert "Other holdings" not in set(broad_display.visible["asset"])

    sleeves = (
        sleeve("Equity / Equal Weight", 50.0),
        sleeve("Crypto / Equal Weight", 50.0),
    )
    _, _, holdings, classes, summary = build_summary(sleeves)
    overlaps = decision.pairwise_overlaps(weights(), sleeves)
    narrative = decision.decision_narrative(summary, overlaps)

    assert "2 fund sleeves resolve to 50.0% equity and 50.0% crypto" in narrative
    assert "2 fund sleeve resolves" not in narrative
    assert "latest saved snapshot" in narrative
    assert "overlapping selected pair" in narrative

    overlapping_sleeves = (
        sleeve("Equity / Equal Weight", 50.0),
        sleeve("Combined / Equal Weight", 50.0),
    )
    _, _, _, _, overlapping_summary = build_summary(overlapping_sleeves)
    overlapping_narrative = decision.decision_narrative(
        overlapping_summary,
        decision.pairwise_overlaps(weights(), overlapping_sleeves),
    )
    assert "shares 83.3% of its latest saved fund-weight profiles" in overlapping_narrative
    assert "shares 83% of its latest saved fund-weight profiles" not in overlapping_narrative

    specs = [
        charts.decision_holdings_spec(),
        charts.decision_overlap_spec(),
        charts.decision_method_exposure_spec(),
    ]
    for spec in specs:
        spec_with_data = {"data": {"values": []}, **spec}
        alt.Chart.from_dict(spec_with_data, validate=True)


def test_decision_module_does_not_construct_custom_performance():
    source = (project_root() / "app" / "decision.py").read_text(encoding="utf-8")
    forbidden_tokens = (
        "fund_returns",
        "net_return",
        "gross_return",
        "growth_net",
        "drawdown",
        "net_sharpe",
        "run_backtest",
        "scipy.optimize",
        "transaction_cost",
        "load_equity_prices",
        "load_crypto_prices",
        "load_news_headlines",
        "SentimentIntensityAnalyzer",
        "nltk",
    )
    for token in forbidden_tokens:
        assert token not in source


def run_app() -> AppTest:
    app = AppTest.from_file("streamlit_app.py")
    app.run(timeout=20)
    assert not app.exception
    return app


def rendered_text(app: AppTest) -> str:
    return "\n".join(
        [str(item.value) for item in app.markdown]
        + [str(item.value) for item in app.caption]
    )


def segmented_control_by_label(app: AppTest, label: str):
    for control in app.segmented_control:
        if control.label == label:
            return control
    raise AssertionError(f"Segmented control not found: {label}")


def selectbox_by_label(app: AppTest, label: str):
    for box in app.selectbox:
        if box.label == label:
            return box
    raise AssertionError(f"Selectbox not found: {label}")


def number_input_by_label(app: AppTest, label: str, occurrence: int = 0):
    matches = [item for item in app.number_input if item.label == label]
    if len(matches) <= occurrence:
        raise AssertionError(f"Number input not found: {label} occurrence {occurrence}")
    return matches[occurrence]


def allocation_input(app: AppTest, sleeve_number: int):
    return number_input_by_label(app, "Allocation %", occurrence=sleeve_number - 1)


def button_labels(app: AppTest) -> list[str]:
    return [button.label for button in app.button]


def click_button_by_label(app: AppTest, label: str) -> AppTest:
    for button in app.button:
        if button.label == label:
            return button.click().run(timeout=25)
    raise AssertionError(f"Button not found: {label}")


def click_button_by_label_occurrence(app: AppTest, label: str, occurrence: int) -> AppTest:
    matches = [button for button in app.button if button.label == label]
    if len(matches) <= occurrence:
        raise AssertionError(f"Button not found: {label} occurrence {occurrence}")
    return matches[occurrence].click().run(timeout=25)


def open_stage(app: AppTest, stage: str) -> AppTest:
    return segmented_control_by_label(app, "Journey").select(stage).run(timeout=25)


def test_decision_initial_state_inherits_selected_fund_context():
    app = run_app()
    app = segmented_control_by_label(app, "Family").select("Crypto").run(timeout=20)
    assert not app.exception

    app = open_stage(app, "Decision")

    assert selectbox_by_label(app, "Sleeve 1").value == "Crypto / Equal Weight"
    assert allocation_input(app, 1).value == 100.0
    text = rendered_text(app)
    assert "What does this allocation actually become?" in text
    assert "Latest saved holdings snapshot: 1 Dec 2023" in text
    assert "Allocation already totals 100.0%." in text
    assert "Normalise to 100%" not in button_labels(app)


def test_decision_invalid_and_valid_allocation_app_states():
    app = open_stage(run_app(), "Decision")

    app = allocation_input(app, 1).set_value(90.0).run(timeout=25)
    assert not app.exception
    text = rendered_text(app)
    assert "Allocated: 90.0%" in text
    assert "Look-through withheld" in text
    assert "Normalise to 100%" in button_labels(app)

    app = allocation_input(app, 1).set_value(100.0).run(timeout=25)
    app = click_button_by_label(app, "Add fund sleeve")
    assert not app.exception
    app = allocation_input(app, 1).set_value(100.0).run(timeout=25)
    app = allocation_input(app, 2).set_value(10.0).run(timeout=25)
    assert "Overallocated: 10.0%" in rendered_text(app)
    assert "Look-through withheld" in rendered_text(app)
    assert "Normalise to 100%" in button_labels(app)

    app = allocation_input(app, 1).set_value(50.0).run(timeout=25)
    app = allocation_input(app, 2).set_value(50.0).run(timeout=25)
    assert not app.exception
    text = rendered_text(app)
    assert "Allocation anatomy" in text
    assert "FUND COUNT != UNDERLYING DIVERSIFICATION" in text
    assert "holdings overlap" in text.lower()
    assert "Normalise to 100%" not in button_labels(app)


def test_decision_combined_equal_weight_app_anatomy_and_remainder():
    app = open_stage(run_app(), "Decision")
    text = rendered_text(app)

    assert not app.exception
    assert selectbox_by_label(app, "Sleeve 1").value == "Combined / Equal Weight"
    assert "FUND WRAPPERS" in text
    assert "ASSET CLASSES" in text
    assert "UNDERLYING HOLDINGS" in text
    assert "Combined / Equal Weight" in text
    assert "100.0%" in text
    assert "Equity" in text
    assert "83.3%" in text
    assert "Crypto" in text
    assert "16.7%" in text
    assert "52 additional holdings" in text
    assert "86.7% combined. This is a compact remainder, not one security." in text
    assert "Other holdings" not in text
    assert "60.0 effective underlying holdings" in text


def test_decision_equal_weight_structural_contrast_app_states():
    app = open_stage(run_app(), "Decision")
    app = selectbox_by_label(app, "Sleeve 1").select("Equity / Equal Weight").run(timeout=25)
    app = click_button_by_label(app, "Add fund sleeve")
    app = selectbox_by_label(app, "Sleeve 2").select("Crypto / Equal Weight").run(timeout=25)
    app = allocation_input(app, 1).set_value(50.0).run(timeout=25)
    app = allocation_input(app, 2).set_value(50.0).run(timeout=25)
    assert not app.exception
    text = rendered_text(app)
    assert "2 fund sleeves resolve to 50.0% equity and 50.0% crypto" in text
    assert "2 fund sleeves, but 0.0% of their latest weight profiles overlap." in text

    app = open_stage(run_app(), "Decision")
    app = selectbox_by_label(app, "Sleeve 1").select("Equity / Equal Weight").run(timeout=25)
    app = click_button_by_label(app, "Add fund sleeve")
    app = selectbox_by_label(app, "Sleeve 2").select("Combined / Equal Weight").run(timeout=25)
    app = allocation_input(app, 1).set_value(50.0).run(timeout=25)
    app = allocation_input(app, 2).set_value(50.0).run(timeout=25)
    assert not app.exception
    text = rendered_text(app)
    assert "2 fund sleeves resolve to 91.7% equity and 8.3% crypto" in text
    assert "2 fund sleeves, but 83.3% of their latest weight profiles overlap." in text


def test_decision_three_funds_remove_and_navigation_paths():
    app = open_stage(run_app(), "Decision")

    app = click_button_by_label(app, "Add fund sleeve")
    app = click_button_by_label(app, "Add fund sleeve")
    assert not app.exception
    assert "Remove sleeve 1" not in button_labels(app)
    assert "Remove sleeve 2" not in button_labels(app)
    assert "Remove sleeve 3" not in button_labels(app)
    assert button_labels(app).count("Remove") == 3
    app = selectbox_by_label(app, "Sleeve 3").select("Crypto / Minimum Variance").run(timeout=25)
    app = selectbox_by_label(app, "Sleeve 1").select("Combined / Maximum Sharpe").run(timeout=25)
    app = allocation_input(app, 1).set_value(40.0).run(timeout=25)
    app = allocation_input(app, 2).set_value(35.0).run(timeout=25)
    app = allocation_input(app, 3).set_value(25.0).run(timeout=25)
    assert "Most overlapping pair" in rendered_text(app)

    app = click_button_by_label_occurrence(app, "Remove", 2)
    assert not app.exception
    assert len([box for box in app.selectbox if box.label.startswith("Sleeve ")]) == 2

    evidence_app = click_button_by_label(app, "Inspect evidence")
    assert segmented_control_by_label(evidence_app, "Journey").value == "Evidence"

    app = open_stage(run_app(), "Decision")
    app = click_button_by_label(app, "Compare funds")
    assert segmented_control_by_label(app, "Journey").value == "Fund"
    app = open_stage(run_app(), "Decision")
    app = click_button_by_label(app, "Open fact sheet")
    assert segmented_control_by_label(app, "Journey").value == "Risk"
    app = open_stage(run_app(), "Decision")
    app = click_button_by_label(app, "Challenge the model")
    assert segmented_control_by_label(app, "Journey").value == "Challenge"
    assert "Does the cleverer model actually earn its complexity?" in rendered_text(app)
    assert "Phase 4E" not in rendered_text(app)


def test_existing_product_stages_still_render_after_decision_addition():
    app = run_app()
    for stage in ["Fund", "Risk", "Signal", "Evidence", "Decision", "Challenge"]:
        app = open_stage(app, stage)
        assert not app.exception
