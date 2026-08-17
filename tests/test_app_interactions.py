from streamlit.testing.v1 import AppTest


def run_app() -> AppTest:
    app = AppTest.from_file("streamlit_app.py")
    app.run(timeout=15)
    assert not app.exception
    return app


def test_fund_filters_update_selected_visible_fund():
    app = run_app()

    app.segmented_control[1].select("Equity").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[1].value == "Equity"
    assert app.selectbox[0].value.startswith("Equity /")

    app.segmented_control[1].select("Crypto").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[1].value == "Crypto"
    assert app.selectbox[0].value.startswith("Crypto /")

    app.segmented_control[1].select("Combined").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[1].value == "Combined"
    assert app.selectbox[0].value.startswith("Combined /")

    app.segmented_control[1].select("All").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[1].value == "All"


def test_method_filters_combine_with_family_filter():
    app = run_app()

    app.segmented_control[2].select("Equal Weight").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[2].value == "Equal Weight"
    assert app.selectbox[0].value.endswith("/ Equal Weight")

    app.segmented_control[2].select("Minimum Variance").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[2].value == "Minimum Variance"
    assert app.selectbox[0].value.endswith("/ Minimum Variance")

    app.segmented_control[2].select("Maximum Sharpe").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[2].value == "Maximum Sharpe"
    assert app.selectbox[0].value.endswith("/ Maximum Sharpe")

    app.segmented_control[1].select("Combined").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[1].value == "Combined"
    assert app.segmented_control[2].value == "Maximum Sharpe"
    assert app.selectbox[0].value == "Combined / Maximum Sharpe"

    app.segmented_control[2].select("All").run(timeout=15)
    assert not app.exception
    assert app.segmented_control[2].value == "All"
    assert app.selectbox[0].value.startswith("Combined /")


def test_manual_selected_fund_syncs_to_risk_fact_sheet():
    app = run_app()

    app.selectbox[0].select("Crypto / Maximum Sharpe").run(timeout=15)
    assert not app.exception
    assert app.selectbox[0].value == "Crypto / Maximum Sharpe"

    app.button[1].click().run(timeout=15)
    assert not app.exception
    assert app.segmented_control[0].value == "Risk"
    risk_markdown = "\n".join(str(item.value) for item in app.markdown)
    assert "**Crypto / Maximum Sharpe**" in risk_markdown


def test_fund_and_risk_navigation_buttons_work():
    app = run_app()

    app.button[0].click().run(timeout=15)
    assert not app.exception
    assert app.segmented_control[0].value == "Evidence"

    app.segmented_control[0].select("Fund").run(timeout=15)
    assert not app.exception
    app.button[1].click().run(timeout=15)
    assert not app.exception
    assert app.segmented_control[0].value == "Risk"

    app.button[0].click().run(timeout=15)
    assert not app.exception
    assert app.segmented_control[0].value == "Fund"

    app.button[1].click().run(timeout=15)
    assert not app.exception
    app.button[1].click().run(timeout=15)
    assert not app.exception
    assert app.segmented_control[0].value == "Signal"


def test_all_journey_stages_are_reachable():
    app = run_app()
    stages = ["Fund", "Risk", "Signal", "Evidence", "Decision", "Challenge"]

    for stage in stages:
        app.segmented_control[0].select(stage).run(timeout=15)
        assert not app.exception
        assert app.segmented_control[0].value == stage
