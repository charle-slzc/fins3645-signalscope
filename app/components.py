"""Reusable Streamlit primitives for the Phase 4A app foundation."""

from __future__ import annotations

import html

import streamlit as st

from app import charts
from app import design
from app.data import ArtifactValidationError, StartupArtifacts, startup_registry
from app.funds import (
    FAMILY_FILTERS,
    METHOD_FILTERS,
    ConcentrationSummary,
    FundKey,
    available_funds,
    comparison_frame,
    concentration_summary,
    default_fund_key,
    display_family,
    effective_holdings,
    family_caveat,
    filter_metrics,
    first_live_row,
    format_multiple,
    format_percent,
    growth_and_drawdown_from_returns,
    latest_exposure,
    latest_weights,
    method_explanation,
    metric_row,
    return_series,
    top_holdings_with_remainder,
    validate_fund_key,
)
from app.navigation import set_view


def install_design_system() -> None:
    st.markdown(design.css(), unsafe_allow_html=True)


def render_artifact_error(error: ArtifactValidationError) -> None:
    st.error(str(error), icon=":material/error:")
    st.caption(
        "The deployed product only reads precomputed results artifacts. It does "
        "not rebuild portfolios, rescore headlines, or download raw hosted data."
    )


def render_truth_labels() -> None:
    labels = "".join(design.truth_label_html(label) for label in design.TRUTH_LABELS)
    st.markdown(f'<div class="ss-label-row">{labels}</div>', unsafe_allow_html=True)


def render_panel(title: str, body: str, accent: str = "control") -> None:
    safe_title = html.escape(title)
    safe_body = html.escape(body)
    accent_class = {
        "signal": "ss-signal-bar",
        "evidence": "ss-evidence-bar",
        "control": "ss-control-bar",
    }.get(accent, "ss-control-bar")
    st.markdown(
        f"""
<div class="ss-panel">
  <h3>{safe_title}</h3>
  <p>{safe_body}</p>
  <div class="{accent_class}"></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_caveat(text: str, warning: bool = False) -> None:
    css_class = "ss-warning" if warning else "ss-caveat"
    st.markdown(
        f'<div class="{css_class}">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def render_method_badges(family: str, method: str, method_type: str) -> None:
    badges = (
        display_family(family),
        method,
        "Benchmark" if method_type == "benchmark" else "Optimisation",
    )
    html_badges = "".join(
        f'<span class="ss-method-badge">{html.escape(label)}</span>' for label in badges
    )
    st.markdown(html_badges, unsafe_allow_html=True)


def render_kpi_grid(items: list[tuple[str, str, str]]) -> None:
    cells = []
    for label, value, helper in items:
        cells.append(
            f"""
<div class="ss-kpi">
  <p class="ss-kpi-label">{html.escape(label)}</p>
  <p class="ss-kpi-value">{html.escape(value)}</p>
  <p class="ss-kpi-help">{html.escape(helper)}</p>
</div>
"""
        )
    st.markdown(f'<div class="ss-kpi-grid">{"".join(cells)}</div>', unsafe_allow_html=True)


def render_mini_grid(items: list[tuple[str, str]]) -> None:
    cells = []
    for value, label in items:
        cells.append(
            f"""
<div class="ss-mini">
  <strong>{html.escape(value)}</strong>
  <span>{html.escape(label)}</span>
</div>
"""
        )
    st.markdown(f'<div class="ss-mini-grid">{"".join(cells)}</div>', unsafe_allow_html=True)


def render_stage_header(stage: str, question: str, status: str) -> None:
    st.markdown(
        f"""
<p class="ss-kicker">{html.escape(stage)}</p>
<h2 class="ss-stage-title">{html.escape(question)}</h2>
<p class="ss-stage-copy">{html.escape(status)}</p>
""",
        unsafe_allow_html=True,
    )


def render_future_stage(stage: str, question: str, phase: str, detail: str) -> None:
    render_stage_header(
        stage=stage,
        question=question,
        status=f"{phase} will add the production interaction for this stage.",
    )
    render_panel(
        title="Foundation Ready",
        body=detail,
        accent="control",
    )


def render_startup_status(artifacts: StartupArtifacts) -> None:
    registry = startup_registry()
    loaded_files = len(registry)
    actual_mb = artifacts.total_bytes / 1_000_000
    expected_mb = artifacts.expected_bytes / 1_000_000
    st.caption(
        f"Startup evidence pack loaded: {loaded_files} compact CSV artifacts, "
        f"{artifacts.total_bytes:,} bytes ({actual_mb:.2f} MB). "
        f"Approved budget: {artifacts.expected_bytes:,} bytes ({expected_mb:.2f} MB)."
    )


def selected_fund(metrics) -> FundKey:
    family = st.session_state.get("selected_fund_family")
    method = st.session_state.get("selected_fund_method")
    if family and method:
        try:
            return validate_fund_key(metrics, family, method)
        except (KeyError, ValueError):
            pass
    key = default_fund_key(metrics)
    st.session_state["selected_fund_family"] = key.family
    st.session_state["selected_fund_method"] = key.method
    return key


def set_selected_fund(key: FundKey) -> None:
    st.session_state["selected_fund_family"] = key.family
    st.session_state["selected_fund_method"] = key.method


def fund_options_from_metrics(metrics) -> list[FundKey]:
    return available_funds(metrics)


def render_fund_controls(metrics) -> tuple[FundKey, object]:
    current = selected_fund(metrics)
    family_col, method_col = st.columns(2)
    with family_col:
        family_kwargs = {}
        if "fund_family_filter" not in st.session_state:
            family_kwargs["default"] = "All"
        family_filter = st.segmented_control(
            "Family",
            FAMILY_FILTERS,
            selection_mode="single",
            key="fund_family_filter",
            **family_kwargs,
        )
    with method_col:
        method_kwargs = {}
        if "fund_method_filter" not in st.session_state:
            method_kwargs["default"] = "All"
        method_filter = st.segmented_control(
            "Method",
            METHOD_FILTERS,
            selection_mode="single",
            key="fund_method_filter",
            **method_kwargs,
        )

    filtered = filter_metrics(metrics, family_filter or "All", method_filter or "All")
    if filtered.empty:
        st.warning("No funds match the current filters. Showing all funds instead.")
        filtered = metrics.copy()

    options = fund_options_from_metrics(filtered)
    if current not in options:
        current = options[0]
        set_selected_fund(current)

    labels = [option.label for option in options]
    selected_label = st.selectbox(
        "Selected fund",
        labels,
        index=labels.index(current.label),
        help="The selected fund is highlighted in Fund and opens in Risk.",
    )
    selected_index = labels.index(selected_label)
    selected = options[selected_index]
    set_selected_fund(selected)
    return selected, filtered


def render_metric_interpretation() -> None:
    render_mini_grid(
        [
            ("Annualised return", "historical OOS return, not expected return"),
            ("Volatility", "how much daily returns varied, annualised"),
            ("Sharpe", "return per unit of volatility"),
            ("Max drawdown", "worst peak-to-trough fall"),
            ("Turnover", "trading intensity and potential cost drag"),
            ("Effective holdings", "how concentrated the fund behaves"),
        ]
    )


def ranking_frame(metrics):
    ranked = metrics.copy()
    ranked["family_label"] = ranked["fund_family"].map(display_family)
    ranked["fund_label"] = ranked["family_label"] + " / " + ranked["method"]
    ranked["drawdown_abs"] = ranked["net_max_drawdown"].abs()
    return ranked


def render_ranked_funds(metrics, rank_by: str) -> None:
    rank_map = {
        "Sharpe": ("net_sharpe_ratio", False),
        "Annualised return": ("net_annualised_return", False),
        "Max drawdown": ("drawdown_abs", True),
        "Volatility": ("net_annualised_volatility", True),
        "Turnover": ("total_turnover", True),
    }
    ranked = ranking_frame(metrics)
    column, ascending = rank_map[rank_by]
    ranked = ranked.sort_values(column, ascending=ascending)
    rows = []
    for row in ranked.itertuples(index=False):
        rows.append(
            f"""
<div class="ss-fund-row">
  <strong>{html.escape(row.fund_label)}</strong>
  <span>Return {format_percent(row.net_annualised_return)}</span>
  <span>Vol {format_percent(row.net_annualised_volatility)}</span>
  <span>Sharpe {row.net_sharpe_ratio:.2f}</span>
  <span>Max DD {format_percent(row.net_max_drawdown)}</span>
  <span>Turnover {format_multiple(row.total_turnover)}</span>
</div>
"""
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def render_fund_shell(artifacts: StartupArtifacts) -> None:
    metrics = artifacts.frames["performance_metrics"]
    selected = selected_fund(metrics)

    st.markdown(
        f"""
<div class="signalscope-shell">
  <p class="ss-kicker">Evidence-first decision cockpit</p>
  <h1 class="ss-hero-title">{design.APP_TITLE}</h1>
  <p class="ss-hero-line">{design.CORE_LINE}</p>
  <p class="ss-value">Compare the nine investable historical OOS funds, then open a fact sheet to inspect risk, holdings, concentration, and costs.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    render_truth_labels()

    action_left, action_right, _ = st.columns([1.1, 1.1, 2.8])
    with action_left:
        if st.button("Open fact sheet", type="primary", width="stretch"):
            set_view("Risk")
            st.rerun()
    with action_right:
        if st.button("Inspect evidence", width="stretch"):
            set_view("Evidence")
            st.rerun()

    selected, filtered = render_fund_controls(metrics)
    chart_frame = comparison_frame(filtered, selected)
    st.caption(f"Selected: {selected.label}. Equal Weight is a benchmark; optimisation methods are not automatically superior.")
    st.vega_lite_chart(chart_frame, charts.risk_return_spec(), width="stretch")
    render_caveat(
        "Read the map as a tradeoff between historical return and annualised volatility. "
        "The highlighted point is selected for inspection; upper-right is not automatically better because drawdown, turnover, and concentration also matter."
    )

    st.subheader("Metric Language")
    render_metric_interpretation()

    st.subheader("Comparison Snapshot")
    rank_by = st.selectbox(
        "Rank by",
        ("Sharpe", "Annualised return", "Max drawdown", "Volatility", "Turnover"),
        index=0,
    )
    render_ranked_funds(filtered, rank_by)

    st.divider()
    render_startup_status(artifacts)


def render_concentration(summary: ConcentrationSummary) -> None:
    render_mini_grid(
        [
            (summary.top_asset, f"largest holding at {format_percent(summary.top_weight)}"),
            (f"{summary.effective_holdings:.1f}", "effective number of holdings"),
            (summary.latest_date, "latest saved holdings date"),
        ]
    )
    if summary.is_concentrated:
        render_caveat(
            "Concentration warning: this saved portfolio has more than 25% in one asset. "
            "Review holdings before interpreting the optimisation as diversified.",
            warning=True,
        )
    if summary.is_low_diversification:
        render_caveat(
            "Diversification warning: the portfolio behaves like fewer than five equally weighted holdings.",
            warning=True,
        )


def render_risk_fact_sheet(artifacts: StartupArtifacts) -> None:
    metrics = artifacts.frames["performance_metrics"]
    returns = artifacts.frames["fund_returns"]
    weights = artifacts.frames["fund_weights"]
    exposure = artifacts.frames["asset_class_exposure"]
    first_live_dates = artifacts.frames["first_live_dates"]

    key = selected_fund(metrics)
    row = metric_row(metrics, key)
    first_live = first_live_row(first_live_dates, key)
    latest = latest_weights(weights, key)
    concentration = concentration_summary(latest)
    holdings_display = top_holdings_with_remainder(latest, top_n=10)
    exposure_latest = latest_exposure(exposure, key)
    path = growth_and_drawdown_from_returns(return_series(returns, key))

    render_stage_header(
        "Risk",
        "What am I actually buying?",
        "A fact sheet for the selected precomputed fund, using historical out-of-sample net returns and saved holdings.",
    )
    render_method_badges(key.family, key.method, row["method_type"])
    st.markdown(f"**{key.label}**")
    st.caption(method_explanation(key.method))

    render_kpi_grid(
        [
            (
                "Annualised return",
                format_percent(row["net_annualised_return"]),
                "historical OOS return, not expected return",
            ),
            (
                "Volatility",
                format_percent(row["net_annualised_volatility"]),
                "how much daily returns varied, annualised",
            ),
            ("Sharpe", f"{row['net_sharpe_ratio']:.2f}", "return per unit of volatility"),
            (
                "Max drawdown",
                format_percent(row["net_max_drawdown"]),
                "worst peak-to-trough fall",
            ),
        ]
    )

    left, right = st.columns([1.35, 0.9])
    with left:
        st.subheader("Growth Of $1")
        st.vega_lite_chart(path, charts.growth_spec(), width="stretch")
        st.caption("Built from the saved net OOS fund return series. Transaction costs are already reflected.")
    with right:
        st.subheader("Fund Context")
        render_mini_grid(
            [
                (first_live["first_live_date"], "first live OOS date"),
                (format_multiple(row["total_turnover"]), "total turnover"),
                (f"{int(first_live['estimation_window'])}", "trailing estimation observations"),
            ]
        )
        render_caveat(family_caveat(key.family))

    st.subheader("Drawdown")
    st.vega_lite_chart(path, charts.drawdown_spec(), width="stretch")

    st.subheader("What The Fund Owns")
    holdings_left, holdings_right = st.columns([1.25, 0.9])
    with holdings_left:
        st.vega_lite_chart(holdings_display, charts.holdings_spec(holdings_display), width="stretch")
        st.caption("Small numerical weights are hidden only in this display; the saved weight artifact is unchanged.")
    with holdings_right:
        render_concentration(concentration)

    st.subheader("Asset-Class Exposure")
    st.vega_lite_chart(exposure_latest, charts.exposure_spec(), width="stretch")
    exposure_text = ", ".join(
        f"{row.asset_class_label}: {format_percent(row.exposure)}"
        for row in exposure_latest.itertuples(index=False)
    )
    st.caption(f"Latest saved exposure: {exposure_text}.")

    with st.expander("Method And Cost Disclosure", expanded=False):
        st.markdown(
            "\n".join(
                [
                    "- Historical out-of-sample backtest, not a forecast or personalised investment advice.",
                    "- Long-only, fully invested, no leverage.",
                    "- Monthly rebalance using saved weights estimated from trailing historical observations.",
                    "- 10 bps transaction cost per dollar of turnover, already deducted in net returns.",
                    "- 0% annual risk-free-rate convention for Sharpe calculations.",
                    f"- OOS sample: {row['sample_start']} to {row['sample_end']}.",
                    f"- Annualisation convention: {int(row['periods_per_year'])} periods per year.",
                    f"- {family_caveat(key.family)}",
                ]
            )
        )

    action_left, action_right, _ = st.columns([1.15, 1.15, 2.7])
    with action_left:
        if st.button("Compare funds", width="stretch"):
            set_view("Fund")
            st.rerun()
    with action_right:
        if st.button("Inspect signal next", type="primary", width="stretch"):
            set_view("Signal")
            st.rerun()


def render_active_stage(stage: str, artifacts: StartupArtifacts) -> None:
    if stage == "Fund":
        render_fund_shell(artifacts)
    elif stage == "Risk":
        render_risk_fact_sheet(artifacts)
    elif stage == "Signal":
        render_future_stage(
            "Signal",
            "What does the news say across equity sectors?",
            "Phase 4C",
            "The shell is intentionally not loading the sector sentiment time series until the Signal stage is implemented.",
        )
    elif stage == "Evidence":
        render_future_stage(
            "Evidence",
            "How well does the available evidence support the sentiment reading?",
            "Phase 4C",
            "The startup layer includes compact diagnostic cases; the full evidence-confidence artifact remains a later lazy load.",
        )
    elif stage == "Decision":
        render_future_stage(
            "Decision",
            "What allocation would I choose, and how would it have behaved historically?",
            "Phase 4D",
            "The foundation has fund return and weight artifacts ready for precomputed historical blends without new optimisation.",
        )
    elif stage == "Challenge":
        render_future_stage(
            "Challenge",
            "Did the sentiment innovation really add investment value?",
            "Phase 4E",
            "The challenge view will load falsification artifacts only when this stage is built and opened.",
        )
