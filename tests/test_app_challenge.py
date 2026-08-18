from pathlib import Path

import altair as alt
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import challenge
from app import charts
from app import data


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_artifact(relative: str) -> pd.DataFrame:
    return pd.read_csv(project_root() / relative)


def comparison() -> pd.DataFrame:
    return read_artifact("results/tables/confidence_placebo_comparison.csv")


def turnover() -> pd.DataFrame:
    return read_artifact("results/tables/confidence_placebo_turnover_decomposition.csv")


def selectivity() -> pd.DataFrame:
    return read_artifact("results/tables/confidence_placebo_selectivity.csv")


def cases() -> pd.DataFrame:
    return read_artifact("results/tables/confidence_placebo_cases.csv")


def run_app() -> AppTest:
    app = AppTest.from_file("streamlit_app.py")
    app.run(timeout=25)
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


def click_button_by_label(app: AppTest, label: str) -> AppTest:
    for button in app.button:
        if button.label == label:
            return button.click().run(timeout=25)
    raise AssertionError(f"Button not found: {label}")


def open_stage(app: AppTest, stage: str) -> AppTest:
    return segmented_control_by_label(app, "Journey").select(stage).run(timeout=25)


def test_challenge_artifacts_are_lazy_and_headline_scores_remain_forbidden():
    lazy_paths = {spec.relative_path for spec in data.lazy_registry().values()}
    startup_paths = {spec.relative_path for spec in data.startup_registry()}

    assert Path("results/tables/confidence_placebo_comparison.csv") in lazy_paths
    assert Path("results/tables/confidence_placebo_turnover_decomposition.csv") in lazy_paths
    assert Path("results/tables/confidence_placebo_selectivity.csv") in lazy_paths
    assert Path("results/tables/confidence_placebo_quadrants.csv") in lazy_paths
    assert Path("results/tables/confidence_placebo_cases.csv") in lazy_paths
    assert Path("results/data/headline_sentiment_scores.csv") not in lazy_paths
    assert Path("results/data/headline_sentiment_scores.csv") not in startup_paths
    assert data.expected_startup_size() == data.EXPECTED_STARTUP_BYTES


def test_exact_primary_minimum_variance_metrics_match_saved_artifact():
    rows = challenge.comparison_rows(comparison(), "Minimum Variance").set_index("overlay")

    assert rows.loc["Base", "sharpe_ratio"] == pytest.approx(0.4039909849390289)
    assert rows.loc["Standard Sentiment", "sharpe_ratio"] == pytest.approx(0.3894061998601869)
    assert rows.loc["Matched-Shrinkage Placebo", "sharpe_ratio"] == pytest.approx(0.3952514941026097)
    assert rows.loc["SignalScope Confidence Lens", "sharpe_ratio"] == pytest.approx(0.3918277333346022)
    assert rows.loc["Base", "annualised_return"] == pytest.approx(0.0515178650673677)
    assert rows.loc["Standard Sentiment", "annualised_return"] == pytest.approx(0.0497588116169598)
    assert rows.loc["Matched-Shrinkage Placebo", "annualised_return"] == pytest.approx(0.0504566451973735)
    assert rows.loc["SignalScope Confidence Lens", "annualised_return"] == pytest.approx(0.0500286381113825)
    assert rows.loc["Base", "total_turnover"] == pytest.approx(11.5191438254282)
    assert rows.loc["Standard Sentiment", "total_turnover"] == pytest.approx(12.046789706438036)
    assert rows.loc["Matched-Shrinkage Placebo", "total_turnover"] == pytest.approx(11.802349627041298)
    assert rows.loc["SignalScope Confidence Lens", "total_turnover"] == pytest.approx(11.807426243797446)
    assert challenge.strongest_sharpe_overlay(comparison(), "Minimum Variance") == "Base"
    assert rows["sharpe_ratio"].idxmax() == "Base"


def test_exact_maximum_sharpe_robustness_metrics_match_saved_artifact():
    rows = challenge.comparison_rows(comparison(), "Maximum Sharpe").set_index("overlay")

    assert rows.loc["Base", "sharpe_ratio"] == pytest.approx(0.4690052735775443)
    assert rows.loc["Standard Sentiment", "sharpe_ratio"] == pytest.approx(0.4629411494925627)
    assert rows.loc["Matched-Shrinkage Placebo", "sharpe_ratio"] == pytest.approx(0.4655436690259177)
    assert rows.loc["SignalScope Confidence Lens", "sharpe_ratio"] == pytest.approx(0.4617841817789139)
    assert rows.loc["Base", "total_turnover"] == pytest.approx(24.908840121459143)
    assert rows.loc["Standard Sentiment", "total_turnover"] == pytest.approx(25.058270328965065)
    assert rows.loc["Matched-Shrinkage Placebo", "total_turnover"] == pytest.approx(24.968792497912368)
    assert rows.loc["SignalScope Confidence Lens", "total_turnover"] == pytest.approx(25.006839029807654)
    assert challenge.strongest_sharpe_overlay(comparison(), "Maximum Sharpe") == "Base"


def test_matched_strength_c_match_and_selectivity_distribution():
    summary = challenge.matched_strength_summary(selectivity())

    assert summary.observation_count == 360
    assert summary.c_match == pytest.approx(0.6322361773345248)
    assert summary.c_mean == pytest.approx(0.6591585049725245)
    assert summary.standard_abs_tilt_sum == pytest.approx(27.66598810891609)
    assert summary.confidence_abs_tilt_sum == pytest.approx(17.491438564163516)
    assert summary.placebo_abs_tilt_sum == pytest.approx(17.491438564163516)
    assert summary.tilt_difference == pytest.approx(0.0)
    assert summary.below_count == 148
    assert summary.above_count == 212
    assert summary.below_share == pytest.approx(0.4111111111111111)
    assert summary.above_share == pytest.approx(0.5888888888888889)
    assert challenge.matched_strength_frame(summary)["absolute_tilt_sum"].nunique() == 1
    assert "17.49" in challenge.matched_strength_html(summary)
    assert "0.00" in challenge.matched_strength_html(summary)
    split_html = challenge.selectivity_split_html(summary)
    assert "ss-split-visual" in split_html
    assert "41.1%" in split_html
    assert "58.9%" in split_html


def test_no_returns_used_to_derive_match_where_inferable_from_saved_metadata():
    saved_selectivity = selectivity()
    saved_cases = cases()

    assert challenge.match_uses_signal_only_metadata(saved_selectivity, saved_cases)
    assert not any("return" in column.lower() for column in saved_selectivity.columns)
    assert saved_cases["case_selection_rule"].str.contains(
        "no subsequent returns used", regex=False
    ).all()


def test_hypothesis_verdict_mapping_uses_saved_artifacts():
    verdicts = {item.label: item for item in challenge.hypothesis_verdicts(comparison(), turnover(), selectivity())}

    assert verdicts["H1"].claim == "performance improvement"
    assert verdicts["H1"].verdict == "REJECT"
    assert verdicts["H2"].claim == "reduced sentiment-induced disturbance"
    assert verdicts["H2"].verdict == "SUPPORT"
    assert verdicts["H3"].claim == "dynamic evidence-state distinction"
    assert verdicts["H3"].verdict == "SUPPORT"
    assert verdicts["H4"].claim == "economic necessity"
    assert verdicts["H4"].verdict == "REJECT"


def test_real_extra_attenuation_and_preservation_cases_exist():
    weak, strong = challenge.case_pair(cases(), "Minimum Variance")

    assert weak["case_type"] == "weak_evidence_more_attenuation_than_placebo"
    assert weak["sector"] == "Utilities"
    assert weak["date"] == "2021-06-01"
    assert float(weak["confidence"]) == pytest.approx(0.3407091184837965)
    assert float(weak["c_match"]) == pytest.approx(0.6322361773345248)
    assert float(weak["placebo_multiplier"]) == pytest.approx(1.1264472354669048)
    assert float(weak["confidence_multiplier"]) == pytest.approx(1.0681418236967593)
    assert abs(float(weak["confidence_multiplier"]) - 1.0) < abs(float(weak["placebo_multiplier"]) - 1.0)
    weak_case = challenge.case_to_signal_magnitude(weak, "Extra attenuation")
    assert challenge.signal_magnitude(weak["placebo_multiplier"]) == pytest.approx(0.1264472354669048)
    assert challenge.signal_magnitude(weak["confidence_multiplier"]) == pytest.approx(0.0681418236967593)
    assert weak_case.direction == "Positive signal"
    assert weak_case.matched_magnitude == pytest.approx(0.1264472354669048)
    assert weak_case.confidence_magnitude == pytest.approx(0.0681418236967593)
    assert weak_case.confidence_magnitude < weak_case.matched_magnitude

    assert strong["case_type"] == "strong_evidence_less_attenuation_than_placebo"
    assert strong["sector"] == "Financials"
    assert strong["date"] == "2023-09-01"
    assert float(strong["confidence"]) == pytest.approx(0.8555335717253036)
    assert float(strong["c_match"]) == pytest.approx(0.6322361773345248)
    assert float(strong["placebo_multiplier"]) == pytest.approx(0.8763832501290901)
    assert float(strong["confidence_multiplier"]) == pytest.approx(0.8327234610521587)
    assert abs(float(strong["confidence_multiplier"]) - 1.0) > abs(float(strong["placebo_multiplier"]) - 1.0)
    strong_case = challenge.case_to_signal_magnitude(strong, "Extra preservation")
    assert challenge.signal_magnitude(strong["placebo_multiplier"]) == pytest.approx(0.1236167498709099)
    assert challenge.signal_magnitude(strong["confidence_multiplier"]) == pytest.approx(0.1672765389478413)
    assert strong_case.direction == "Negative signal"
    assert strong_case.matched_magnitude == pytest.approx(0.1236167498709099)
    assert strong_case.confidence_magnitude == pytest.approx(0.1672765389478413)
    assert strong_case.confidence_multiplier < strong_case.matched_multiplier
    assert strong_case.confidence_magnitude > strong_case.matched_magnitude

    frame = challenge.case_signal_magnitude_frame(weak, strong)
    assert "multiplier" not in frame.columns
    assert "signal_magnitude" in frame.columns
    assert "signed_signal_magnitude" in frame.columns
    assert frame.loc[
        frame["sector_date"].eq("Financials / 2023-09-01") & frame["rule"].eq("Confidence"),
        "signed_signal_magnitude",
    ].iloc[0] == pytest.approx(-0.1672765389478413)


def test_challenge_static_copy_keeps_guardrails():
    source = (project_root() / "app" / "challenge.py").read_text(encoding="utf-8")

    forbidden_positive_claims = (
        "superior Sharpe",
        "predictive improvement",
        "validated",
        "proved",
        "scientifically confirmed",
        "performed well despite",
    )
    forbidden_runtime_tokens = (
        "src.data_access",
        "load_equity_prices",
        "load_crypto_prices",
        "load_news_headlines",
        "nltk",
        "SentimentIntensityAnalyzer",
        "scipy.optimize",
        "run_backtest",
    )
    for token in forbidden_positive_claims + forbidden_runtime_tokens:
        assert token not in source
    assert "explains {float(primary_turnover['constant_shrinkage_explained_percent']):.1f}%" not in source
    assert "The matched constant control explains 102.1%" not in source
    assert "The simpler constant control reproduced slightly more than the turnover reduction achieved by Confidence." in source
    assert "probability" not in source.lower()
    assert "correlation" not in source.lower()
    assert "overlap" not in source.lower()
    assert "do not claim that it creates alpha" in source
    assert "economically necessary" in source


def test_challenge_chart_specs_validate():
    specs = [
        charts.challenge_performance_spec(),
        charts.challenge_matched_strength_spec(),
        charts.challenge_selectivity_split_spec(),
        charts.challenge_case_magnitude_spec(),
    ]
    for spec in specs:
        alt.Chart.from_dict({"data": {"values": []}, **spec}, validate=True)


def test_challenge_app_renders_primary_sections_and_navigation():
    app = open_stage(run_app(), "Challenge")
    text = rendered_text(app)

    assert not app.exception
    assert "Does the cleverer model actually earn its complexity?" in text
    assert "Did sentiment beat Base?" in text
    assert "NO" in text
    assert "Did Confidence reduce the disturbance caused by raw sentiment?" in text
    assert "YES" in text
    assert "Was dynamic Confidence economically necessary?" in text
    assert "NOT CLEARLY" in text
    assert "Adding headline sentiment did not improve the primary fund's OOS Sharpe." in text
    assert "The simpler constant control reproduced slightly more than the turnover reduction achieved by Confidence." in text
    assert "explains 102.1%" not in text
    assert "Constant-shrinkage share of that reduction: `102.1208820678576%`" in text
    assert "Same total signal strength: Confidence 17.49 = matched constant 17.49. Difference: 0.00." in text
    assert "WHAT SURVIVED?" in text
    assert "What remains is a narrower selective-governance role" in text
    assert "ss-split-visual" in text
    assert "41.1% of valid observations were more conservative than the matched constant; 58.9% were more permissive." in text
    assert "Utilities / 2021-06-01" in text
    assert "+12.6%" in text
    assert "+6.8%" in text
    assert "Weak evidence caused Confidence to mute more of the positive signal than the matched constant." in text
    assert "Financials / 2023-09-01" in text
    assert "&larr; 12.4%" in text
    assert "&larr; 16.7%" in text
    assert "Stronger evidence caused Confidence to preserve more of the negative signal than the matched constant." in text
    assert "REVISE" in text
    assert [item.label for item in app.expander] == [
        "Research verdicts",
        "Does the conclusion depend on the base optimiser?",
        "How the challenge works",
    ]
    assert len(app.latex) == 3

    decision_app = click_button_by_label(app, "Back to Decision")
    assert segmented_control_by_label(decision_app, "Journey").value == "Decision"
    challenge_app = open_stage(decision_app, "Challenge")
    evidence_app = click_button_by_label(challenge_app, "Inspect Evidence Lens")
    assert segmented_control_by_label(evidence_app, "Journey").value == "Evidence"
    challenge_app = open_stage(evidence_app, "Challenge")
    fund_app = click_button_by_label(challenge_app, "Compare funds")
    assert segmented_control_by_label(fund_app, "Journey").value == "Fund"


def test_decision_to_challenge_and_all_stages_still_render():
    app = open_stage(run_app(), "Decision")
    app = click_button_by_label(app, "Challenge the model")

    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Challenge"
    assert "Phase 4E" not in rendered_text(app)

    for stage in ["Fund", "Risk", "Signal", "Evidence", "Decision", "Challenge"]:
        app = open_stage(app, stage)
        assert not app.exception
