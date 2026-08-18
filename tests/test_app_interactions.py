from pathlib import Path

from streamlit.testing.v1 import AppTest
import pandas as pd

from app import components
from app import funds


def run_app() -> AppTest:
    app = AppTest.from_file("streamlit_app.py")
    app.run(timeout=15)
    assert not app.exception
    return app


def rendered_text(app: AppTest) -> str:
    return "\n".join(
        [str(item.value) for item in app.markdown]
        + [str(item.value) for item in app.caption]
    )


def click_button_by_label(app: AppTest, label: str) -> AppTest:
    for button in app.button:
        if button.label == label:
            return button.click().run(timeout=20)
    raise AssertionError(f"Button not found: {label}")


def selectbox_by_label(app: AppTest, label: str, occurrence: int = 0):
    matches = [box for box in app.selectbox if box.label == label]
    if len(matches) <= occurrence:
        raise AssertionError(f"Selectbox not found: {label} occurrence {occurrence}")
    return matches[occurrence]


def assert_selected_fund_dropdown_removed(app: AppTest) -> None:
    assert not [box for box in app.selectbox if box.label == "Selected fund"]


def segmented_control_by_label(app: AppTest, label: str):
    for control in app.segmented_control:
        if control.label == label:
            return control
    raise AssertionError(f"Segmented control not found: {label}")


def open_stage(app: AppTest, stage: str) -> AppTest:
    return segmented_control_by_label(app, "Journey").select(stage).run(timeout=20)


def project_artifact(relative: str) -> pd.DataFrame:
    return pd.read_csv(relative)


def session_state_value(app: AppTest, key: str):
    try:
        return app.session_state[key]
    except KeyError:
        return None


def assert_selected_fund_state(app: AppTest, family: str, method: str) -> None:
    assert session_state_value(app, components.SELECTED_FUND_FAMILY_KEY) == family
    assert session_state_value(app, components.SELECTED_FUND_METHOD_KEY) == method


def test_fund_focus_lenses_update_authoritative_selected_fund():
    app = run_app()
    assert_selected_fund_dropdown_removed(app)

    segmented_control_by_label(app, "Family").select("Equity").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Family").value == "Equity"
    assert_selected_fund_state(app, "Equity-only", "Equal Weight")
    assert "Selected: Equity / Equal Weight." in rendered_text(app)
    assert_selected_fund_dropdown_removed(app)

    segmented_control_by_label(app, "Family").select("Crypto").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Family").value == "Crypto"
    assert_selected_fund_state(app, "Crypto-only", "Equal Weight")
    assert "Selected: Crypto / Equal Weight." in rendered_text(app)

    segmented_control_by_label(app, "Family").select("Combined").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Family").value == "Combined"
    assert_selected_fund_state(app, "Combined", "Equal Weight")
    assert "Selected: Combined / Equal Weight." in rendered_text(app)

    segmented_control_by_label(app, "Family").select("All").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Family").value == "All"
    assert_selected_fund_state(app, "Combined", "Equal Weight")


def test_method_filters_combine_with_family_filter():
    app = run_app()
    assert_selected_fund_dropdown_removed(app)

    segmented_control_by_label(app, "Method").select("Equal Weight").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Method").value == "Equal Weight"
    assert_selected_fund_state(app, "Combined", "Equal Weight")

    segmented_control_by_label(app, "Method").select("Minimum Variance").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Method").value == "Minimum Variance"
    assert_selected_fund_state(app, "Equity-only", "Minimum Variance")

    segmented_control_by_label(app, "Method").select("Maximum Sharpe").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Method").value == "Maximum Sharpe"
    assert_selected_fund_state(app, "Equity-only", "Maximum Sharpe")

    segmented_control_by_label(app, "Family").select("Combined").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Family").value == "Combined"
    assert segmented_control_by_label(app, "Method").value == "Maximum Sharpe"
    assert_selected_fund_state(app, "Combined", "Maximum Sharpe")
    assert "Combined / Maximum Sharpe is the only fund matching the active focus." in rendered_text(app)

    segmented_control_by_label(app, "Method").select("All").run(timeout=15)
    assert not app.exception
    assert segmented_control_by_label(app, "Method").value == "All"
    assert_selected_fund_state(app, "Combined", "Maximum Sharpe")


def test_unique_focus_updates_authoritative_state_and_risk_target():
    app = run_app()

    segmented_control_by_label(app, "Family").select("Crypto").run(timeout=20)
    segmented_control_by_label(app, "Method").select("Equal Weight").run(timeout=20)
    assert not app.exception
    assert_selected_fund_state(app, "Crypto-only", "Equal Weight")
    assert "Crypto / Equal Weight is the only fund matching the active focus." in rendered_text(app)

    app = click_button_by_label(app, "Open fact sheet")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Risk"
    assert "**Crypto / Equal Weight**" in rendered_text(app)

    app = open_stage(app, "Fund")
    segmented_control_by_label(app, "Family").select("Combined").run(timeout=20)
    segmented_control_by_label(app, "Method").select("Maximum Sharpe").run(timeout=20)
    assert not app.exception
    assert_selected_fund_state(app, "Combined", "Maximum Sharpe")
    app = click_button_by_label(app, "Open fact sheet")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Risk"
    assert "**Combined / Maximum Sharpe**" in rendered_text(app)


def test_fund_focus_transitions_preserve_selection_on_return_to_all():
    app = run_app()

    segmented_control_by_label(app, "Family").select("Crypto").run(timeout=20)
    segmented_control_by_label(app, "Method").select("Equal Weight").run(timeout=20)
    assert not app.exception
    assert_selected_fund_state(app, "Crypto-only", "Equal Weight")

    segmented_control_by_label(app, "Family").select("All").run(timeout=20)
    segmented_control_by_label(app, "Method").select("All").run(timeout=20)
    assert not app.exception
    assert_selected_fund_state(app, "Crypto-only", "Equal Weight")
    assert "One fund matches the active filters." not in rendered_text(app)
    assert "Selected: Crypto / Equal Weight." in rendered_text(app)

    segmented_control_by_label(app, "Family").select("Combined").run(timeout=20)
    segmented_control_by_label(app, "Method").select("Maximum Sharpe").run(timeout=20)
    assert not app.exception
    assert_selected_fund_state(app, "Combined", "Maximum Sharpe")
    assert "Combined / Maximum Sharpe is the only fund matching the active focus." in rendered_text(app)

    segmented_control_by_label(app, "Family").select("All").run(timeout=20)
    segmented_control_by_label(app, "Method").select("All").run(timeout=20)
    assert not app.exception
    assert_selected_fund_state(app, "Combined", "Maximum Sharpe")
    assert "One fund matches the active filters." not in rendered_text(app)
    assert "Selected: Combined / Maximum Sharpe." in rendered_text(app)


def test_chart_click_precedence_rules_ignore_stale_chart_after_explicit_widgets():
    selected = funds.FundKey("Combined", "Equal Weight")
    clicked = funds.FundKey("Crypto-only", "Equal Weight")

    assert components.chart_click_should_update(
        clicked,
        selected,
        event_identity="Crypto-only|Equal Weight|{}",
        last_event_identity=None,
    )
    assert not components.chart_click_should_update(
        clicked,
        selected,
        event_identity="Crypto-only|Equal Weight|{}",
        last_event_identity="Crypto-only|Equal Weight|{}",
    )
    assert not components.chart_click_should_update(
        None,
        selected,
        event_identity=None,
        last_event_identity=None,
    )
    assert not components.chart_click_should_update(
        selected,
        selected,
        event_identity="Combined|Equal Weight|{}",
        last_event_identity=None,
    )
    assert not components.chart_click_should_update(
        clicked,
        selected,
        event_identity="Crypto-only|Equal Weight|{}",
        last_event_identity=None,
        focus_changed=True,
    )


def test_chart_selection_event_syncs_authoritative_fund_state_once(monkeypatch):
    state = {
        components.FUND_CHART_KEY: {
            "selection": {
                "fund_pick": {"fund_key": ["Crypto-only|Equal Weight"]},
            }
        },
        components.SELECTED_FUND_FAMILY_KEY: "Combined",
        components.SELECTED_FUND_METHOD_KEY: "Equal Weight",
    }
    monkeypatch.setattr(components.st, "session_state", state)
    perf = project_artifact("results/tables/performance_metrics.csv")

    changed = components.sync_selected_fund_from_chart(perf)

    assert changed is True
    assert state[components.SELECTED_FUND_FAMILY_KEY] == "Crypto-only"
    assert state[components.SELECTED_FUND_METHOD_KEY] == "Equal Weight"
    assert state[components.FUND_CHANGE_SOURCE_KEY] == "chart"
    assert state[components.LAST_FUND_CHART_EVENT_KEY]

    state[components.SELECTED_FUND_FAMILY_KEY] = "Combined"
    state[components.SELECTED_FUND_METHOD_KEY] = "Maximum Sharpe"
    stale_changed = components.sync_selected_fund_from_chart(perf)

    assert stale_changed is False
    assert state[components.SELECTED_FUND_FAMILY_KEY] == "Combined"
    assert state[components.SELECTED_FUND_METHOD_KEY] == "Maximum Sharpe"


def test_chart_event_for_already_selected_fund_is_consumed_and_cannot_reassert_later(monkeypatch):
    state = {
        components.FUND_CHART_KEY: {
            "selection": {
                "fund_pick": {"fund_key": ["Combined|Equal Weight"]},
            }
        },
        components.SELECTED_FUND_FAMILY_KEY: "Combined",
        components.SELECTED_FUND_METHOD_KEY: "Equal Weight",
    }
    monkeypatch.setattr(components.st, "session_state", state)
    perf = project_artifact("results/tables/performance_metrics.csv")

    # Clicking the already-selected point changes no FundKey, but the browser
    # event must still be consumed.
    changed = components.sync_selected_fund_from_chart(perf)
    assert changed is False
    consumed_identity = state[components.LAST_FUND_CHART_EVENT_KEY]
    assert consumed_identity

    # A later focus/navigation change must not let that stale browser event
    # overwrite the newer authoritative FundKey.
    state[components.SELECTED_FUND_FAMILY_KEY] = "Crypto-only"
    state[components.SELECTED_FUND_METHOD_KEY] = "Maximum Sharpe"
    stale_changed = components.sync_selected_fund_from_chart(perf)

    assert stale_changed is False
    assert state[components.SELECTED_FUND_FAMILY_KEY] == "Crypto-only"
    assert state[components.SELECTED_FUND_METHOD_KEY] == "Maximum Sharpe"
    assert state[components.LAST_FUND_CHART_EVENT_KEY] == consumed_identity


def test_decision_starting_fund_uses_current_authoritative_fund_key():
    app = run_app()

    segmented_control_by_label(app, "Family").select("Combined").run(timeout=20)
    segmented_control_by_label(app, "Method").select("Maximum Sharpe").run(timeout=20)
    assert not app.exception

    app = open_stage(app, "Decision")
    assert not app.exception
    assert selectbox_by_label(app, "Sleeve 1").value == "Combined / Maximum Sharpe"


def test_manual_selected_fund_syncs_to_risk_fact_sheet():
    app = run_app()

    segmented_control_by_label(app, "Family").select("Crypto").run(timeout=15)
    segmented_control_by_label(app, "Method").select("Maximum Sharpe").run(timeout=15)
    assert not app.exception
    assert_selected_fund_state(app, "Crypto-only", "Maximum Sharpe")

    app = click_button_by_label(app, "Open fact sheet")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Risk"
    risk_markdown = "\n".join(str(item.value) for item in app.markdown)
    assert "**Crypto / Maximum Sharpe**" in risk_markdown

    app = click_button_by_label(app, "Compare funds")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Fund"
    assert_selected_fund_state(app, "Crypto-only", "Maximum Sharpe")
    assert "Selected: Crypto / Maximum Sharpe." in rendered_text(app)


def test_decision_user_allocation_is_not_overwritten_by_later_fund_focus_change():
    app = run_app()
    segmented_control_by_label(app, "Family").select("Crypto").run(timeout=20)
    segmented_control_by_label(app, "Method").select("Equal Weight").run(timeout=20)
    assert_selected_fund_state(app, "Crypto-only", "Equal Weight")

    app = open_stage(app, "Decision")
    assert selectbox_by_label(app, "Sleeve 1").value == "Crypto / Equal Weight"
    selectbox_by_label(app, "Sleeve 1").select("Equity / Equal Weight").run(timeout=25)
    assert not app.exception
    assert selectbox_by_label(app, "Sleeve 1").value == "Equity / Equal Weight"

    app = open_stage(app, "Fund")
    segmented_control_by_label(app, "Family").select("Combined").run(timeout=20)
    segmented_control_by_label(app, "Method").select("Maximum Sharpe").run(timeout=20)
    assert_selected_fund_state(app, "Combined", "Maximum Sharpe")

    app = open_stage(app, "Decision")
    assert selectbox_by_label(app, "Sleeve 1").value == "Equity / Equal Weight"


def test_fund_and_risk_navigation_buttons_work():
    app = run_app()

    app = click_button_by_label(app, "Inspect evidence")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Evidence"

    app = open_stage(app, "Fund")
    assert not app.exception
    app = click_button_by_label(app, "Open fact sheet")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Risk"

    app = click_button_by_label(app, "Compare funds")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Fund"

    app = click_button_by_label(app, "Open fact sheet")
    assert not app.exception
    app = click_button_by_label(app, "Inspect signal next")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Signal"


def test_all_journey_stages_are_reachable():
    app = run_app()
    stages = ["Fund", "Risk", "Signal", "Evidence", "Decision", "Challenge"]

    for stage in stages:
        app = open_stage(app, stage)
        assert not app.exception
        assert segmented_control_by_label(app, "Journey").value == stage


def test_signal_sector_switch_and_signal_to_evidence_context():
    app = run_app()

    app = open_stage(app, "Signal")
    assert not app.exception
    assert selectbox_by_label(app, "Sector").value == "Tech"

    selectbox_by_label(app, "Sector").select("Industrials").run(timeout=20)
    assert not app.exception
    assert selectbox_by_label(app, "Sector").value == "Industrials"
    signal_markdown = rendered_text(app)
    assert "Industrials ·" in signal_markdown
    assert "No news remains missing; it is not treated as neutral." in signal_markdown

    app = click_button_by_label(app, "Inspect this evidence")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Evidence"
    assert selectbox_by_label(app, "Sector").value == "Industrials"
    evidence_markdown = rendered_text(app)
    assert "SignalScope Evidence Lens" in evidence_markdown
    assert "Evidence confidence is not probability" in evidence_markdown


def test_signal_selector_and_status_banner_use_same_sector_for_all_core_sectors():
    for sector in ["Materials", "Tech", "Industrials", "RealEstate"]:
        app = open_stage(run_app(), "Signal")
        selectbox_by_label(app, "Sector").select(sector).run(timeout=20)
        assert not app.exception
        assert selectbox_by_label(app, "Sector").value == sector
        text = rendered_text(app)
        assert f"{sector} ·" in text
        other_core = {"Materials", "Tech", "Industrials", "RealEstate"} - {sector}
        assert not any(f"{other} ·" in text for other in other_core)


def test_signal_default_date_is_observed_but_no_news_can_be_selected():
    sector_index = project_artifact("results/data/sector_sentiment_index.csv")
    materials = sector_index[sector_index["sector"] == "Materials"].copy()
    materials["date"] = pd.to_datetime(materials["date"])
    latest_observed = (
        materials.loc[~materials["missing_sector_day"]]
        .sort_values("date")
        .iloc[-1]["date"]
        .date()
        .isoformat()
    )
    missing_date = (
        materials.loc[materials["missing_sector_day"]]
        .sort_values("date")
        .iloc[-1]["date"]
        .date()
        .isoformat()
    )

    app = open_stage(run_app(), "Signal")
    selectbox_by_label(app, "Sector").select("Materials").run(timeout=20)
    assert not app.exception
    assert selectbox_by_label(app, "Signal date").value == latest_observed
    assert "No observed sector news." not in rendered_text(app)

    selectbox_by_label(app, "Period").select("All").run(timeout=20)
    assert not app.exception
    selectbox_by_label(app, "Signal date").select(missing_date).run(timeout=20)
    assert not app.exception
    assert selectbox_by_label(app, "Signal date").value == missing_date
    text = rendered_text(app)
    assert f"Materials · {missing_date}" in text
    assert "No observed sector news." in text


def test_signal_to_evidence_preserves_selected_sector_for_core_sectors():
    for sector in ["Materials", "Tech", "Industrials", "RealEstate"]:
        app = open_stage(run_app(), "Signal")
        selectbox_by_label(app, "Sector").select(sector).run(timeout=20)
        assert not app.exception
        selected_signal_date = selectbox_by_label(app, "Signal date").value

        app = click_button_by_label(app, "Inspect this evidence")
        assert not app.exception
        assert segmented_control_by_label(app, "Journey").value == "Evidence"
        assert selectbox_by_label(app, "Sector").value == sector
        evidence_text = rendered_text(app)
        assert f"<strong>{sector} /" in evidence_text
        if selectbox_by_label(app, "Evidence date").value != selected_signal_date:
            assert "Signal date" in evidence_text


def test_evidence_back_to_signal_preserves_context():
    app = run_app()

    app = open_stage(app, "Evidence")
    assert not app.exception
    selectbox_by_label(app, "Sector").select("RealEstate").run(timeout=20)
    assert not app.exception
    selectbox_by_label(app, "Evidence date").select("2021-11-01").run(timeout=20)
    assert not app.exception

    app = click_button_by_label(app, "Back to signal")
    assert not app.exception
    assert segmented_control_by_label(app, "Journey").value == "Signal"
    assert selectbox_by_label(app, "Sector").value == "RealEstate"
    assert "RealEstate · 2021-11-01" in rendered_text(app)


def test_evidence_curated_case_shortcuts_render_empirical_cases():
    app = run_app()

    app = open_stage(app, "Evidence")
    assert not app.exception

    app = click_button_by_label(app, "Load neutrality case")
    assert not app.exception
    neutral_markdown = rendered_text(app)
    assert "Neutrality is not always consensus." in neutral_markdown
    assert "Industrials, 2020-07-09" in neutral_markdown
    assert "MMM -0.6808" in neutral_markdown
    assert "pre-OOS sentiment diagnostic examples" in neutral_markdown
    assert "before the saved OOS portfolio Confidence Lens period" in neutral_markdown

    app = click_button_by_label(app, "Load volume case")
    assert not app.exception
    volume_markdown = rendered_text(app)
    assert "More headlines do not necessarily mean broader evidence." in volume_markdown
    assert "Tech, 2020-07-24" in volume_markdown
    assert "INTC produced 63.6%" in volume_markdown
    assert "Pre-OOS sentiment diagnostic example" in volume_markdown

    app = click_button_by_label(app, "Load attenuation case")
    assert not app.exception
    attenuation_markdown = rendered_text(app)
    assert "Same news direction. Less portfolio movement." in attenuation_markdown
    assert "RealEstate / 2021-11-01" in attenuation_markdown
    assert "Saved Minimum Variance attenuation case: RealEstate / 2021-11-01." in attenuation_markdown
    assert "Saved realized sector-weight changes are available" not in attenuation_markdown
    assert "primary allocation-effect bars are not shown" not in attenuation_markdown
    assert "confidence 0.340" in attenuation_markdown


def test_signal_copy_matches_discrete_gold_mark_geometry():
    app = open_stage(run_app(), "Signal")
    text = rendered_text(app)

    assert "Gold marks underneath show how much same-day evidence existed for each sector-date." in text
    assert "Gold dots underneath" not in text


def test_design_uses_global_chrome_safe_shell_spacing():
    source = Path("app/design.py").read_text(encoding="utf-8")

    assert "--ss-top-safe" in source
    assert "env(safe-area-inset-top, 0px)" in source
    assert "padding-top: calc(var(--ss-top-safe)" in source


def test_curated_case_does_not_control_signal_after_manual_sector_change():
    app = open_stage(run_app(), "Evidence")
    app = click_button_by_label(app, "Load neutrality case")
    app = click_button_by_label(app, "Back to signal")
    assert not app.exception
    assert selectbox_by_label(app, "Sector").value == "Industrials"

    selectbox_by_label(app, "Sector").select("Materials").run(timeout=20)
    assert not app.exception
    text = rendered_text(app)
    assert selectbox_by_label(app, "Sector").value == "Materials"
    assert "Materials ·" in text
    assert "Industrials ·" not in text
    assert session_state_value(app, "evidence_case") is None

    app = open_stage(app, "Evidence")
    app = click_button_by_label(app, "Load attenuation case")
    app = click_button_by_label(app, "Back to signal")
    assert not app.exception
    assert selectbox_by_label(app, "Sector").value == "RealEstate"

    selectbox_by_label(app, "Sector").select("Tech").run(timeout=20)
    assert not app.exception
    text = rendered_text(app)
    assert selectbox_by_label(app, "Sector").value == "Tech"
    assert "Tech ·" in text
    assert "RealEstate ·" not in text
    assert session_state_value(app, "evidence_case") is None
