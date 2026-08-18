"""Reusable Streamlit primitives for the Phase 4A app foundation."""

from __future__ import annotations

import html
import json

import streamlit as st

from app import charts
from app import design
from app.challenge import render_challenge_page
from app.decision import render_decision_page
from app.evidence import render_evidence_page
from app.signal import render_signal_page
from app.data import ArtifactValidationError, StartupArtifacts
from app.funds import (
    FAMILY_FILTERS,
    METHOD_FILTERS,
    ConcentrationSummary,
    FundKey,
    comparison_frame,
    concentration_summary,
    deterministic_focus_selection,
    default_fund_key,
    display_family,
    effective_holdings,
    estimation_context,
    family_caveat,
    first_live_row,
    focus_includes_key,
    focus_summary,
    full_map_axis_domains,
    fund_key_id,
    fund_key_from_selection_event,
    format_multiple,
    format_percent,
    growth_and_drawdown_from_returns,
    is_broad_near_equal,
    latest_exposure,
    latest_weights,
    method_explanation,
    metric_row,
    peer_comparison,
    relative_peer_metrics,
    rebalance_methodology_lines,
    representative_holdings,
    return_series,
    validate_fund_key,
    validate_comparison_frame,
)
from app.navigation import set_view


SELECTED_FUND_FAMILY_KEY = "selected_fund_family"
SELECTED_FUND_METHOD_KEY = "selected_fund_method"
FAMILY_FILTER_KEY = "fund_family_filter"
METHOD_FILTER_KEY = "fund_method_filter"
FOCUS_SNAPSHOT_KEY = "_fund_focus_snapshot"
FUND_CHANGE_SOURCE_KEY = "_fund_change_source"
FUND_CHART_KEY = "risk_return_map"
LAST_FUND_CHART_EVENT_KEY = "_last_fund_chart_event"


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


def render_section_label(label: str) -> None:
    st.markdown(
        f'<p class="ss-section-label">{html.escape(label)}</p>',
        unsafe_allow_html=True,
    )


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
    css_class = "ss-warning" if warning else "ss-disclosure"
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
    for index, (label, value, helper) in enumerate(items):
        primary_class = " is-primary" if index == 0 else ""
        cells.append(
            f"""
<div class="ss-kpi{primary_class}">
  <p class="ss-kpi-label">{html.escape(label)}</p>
  <p class="ss-kpi-value">{html.escape(value)}</p>
  <p class="ss-kpi-help">{html.escape(helper)}</p>
</div>
"""
        )
    st.markdown(f'<div class="ss-kpi-grid">{"".join(cells)}</div>', unsafe_allow_html=True)


def render_context_strip(items: list[tuple[str, str]]) -> None:
    cells = []
    for value, label in items:
        cells.append(
            f"""
<div class="ss-context-item">
  <strong>{html.escape(value)}</strong>
  <span>{html.escape(label)}</span>
</div>
"""
        )
    st.markdown(f'<div class="ss-context-strip">{"".join(cells)}</div>', unsafe_allow_html=True)


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


def selected_fund(metrics) -> FundKey:
    family = st.session_state.get(SELECTED_FUND_FAMILY_KEY)
    method = st.session_state.get(SELECTED_FUND_METHOD_KEY)
    if family and method:
        try:
            return validate_fund_key(metrics, family, method)
        except (KeyError, ValueError):
            pass
    key = default_fund_key(metrics)
    set_selected_fund(key, source="initialise")
    return key


def set_selected_fund(key: FundKey, source: str = "system") -> None:
    st.session_state[SELECTED_FUND_FAMILY_KEY] = key.family
    st.session_state[SELECTED_FUND_METHOD_KEY] = key.method
    st.session_state[FUND_CHANGE_SOURCE_KEY] = source


def current_chart_key() -> str:
    return FUND_CHART_KEY


def fund_chart_instance_key(
    selected: FundKey,
    family_focus: str,
    method_focus: str,
) -> str:
    """Return a fresh browser chart identity for each authoritative Fund state.

    Streamlit/Vega may preserve browser-side selection state for a keyed chart
    across reruns. Including the app-owned selected FundKey and active focus
    lenses in the component key forces a clean chart instance whenever those
    states change, so stale Vega state cannot keep an old visual highlight.
    """
    return (
        f"{FUND_CHART_KEY}::"
        f"{fund_key_id(selected)}::"
        f"{family_focus}::{method_focus}"
    )


def _chart_event_payload(event) -> dict:
    if event is None:
        return {}
    if isinstance(event, dict):
        return event
    if hasattr(event, "to_dict"):
        maybe = event.to_dict()
        return maybe if isinstance(maybe, dict) else {}
    selection = getattr(event, "selection", None)
    if isinstance(selection, dict):
        return {"selection": selection}
    return {}


def chart_event_identity(event, clicked_key: FundKey | None) -> str | None:
    if clicked_key is None:
        return None
    payload = _chart_event_payload(event)
    try:
        encoded = json.dumps(payload, sort_keys=True, default=str)
    except TypeError:
        encoded = repr(payload)
    return f"{fund_key_id(clicked_key)}|{encoded}"


def sync_selected_fund_from_chart(metrics) -> bool:
    event = st.session_state.get(current_chart_key())
    key = fund_key_from_selection_event(event, metrics, charts.FUND_SELECTION_NAME)
    previous = selected_fund(metrics)
    identity = chart_event_identity(event, key)
    if not chart_click_should_update(
        clicked_key=key,
        selected=previous,
        event_identity=identity,
        last_event_identity=st.session_state.get(LAST_FUND_CHART_EVENT_KEY),
    ):
        return False
    set_selected_fund(key, source="chart")
    st.session_state[LAST_FUND_CHART_EVENT_KEY] = identity
    return True


def chart_click_should_update(
    clicked_key: FundKey | None,
    selected: FundKey,
    event_identity: str | None,
    last_event_identity: str | None,
    focus_changed: bool = False,
) -> bool:
    return (
        clicked_key is not None
        and clicked_key != selected
        and event_identity is not None
        and event_identity != last_event_identity
        and not focus_changed
    )


def render_fund_controls(metrics) -> tuple[FundKey, str, str, bool]:
    current = selected_fund(metrics)
    st.markdown('<div class="ss-control-title">Focus lenses</div>', unsafe_allow_html=True)
    family_col, method_col = st.columns(2)
    with family_col:
        family_kwargs = {}
        if FAMILY_FILTER_KEY not in st.session_state:
            family_kwargs["default"] = "All"
        family_filter = st.segmented_control(
            "Family",
            FAMILY_FILTERS,
            selection_mode="single",
            key=FAMILY_FILTER_KEY,
            **family_kwargs,
        )
    with method_col:
        method_kwargs = {}
        if METHOD_FILTER_KEY not in st.session_state:
            method_kwargs["default"] = "All"
        method_filter = st.segmented_control(
            "Method",
            METHOD_FILTERS,
            selection_mode="single",
            key=METHOD_FILTER_KEY,
            **method_kwargs,
        )

    filter_state = (family_filter or "All", method_filter or "All")
    previous_focus_state = st.session_state.get(FOCUS_SNAPSHOT_KEY)
    focus_changed = previous_focus_state is not None and filter_state != previous_focus_state
    st.session_state[FOCUS_SNAPSHOT_KEY] = filter_state
    resolved = deterministic_focus_selection(metrics, current, *filter_state)
    if resolved != current:
        set_selected_fund(resolved, source="focus")
    return selected_fund(metrics), filter_state[0], filter_state[1], focus_changed


def render_metric_interpretation() -> None:
    with st.expander("How to read this comparison", expanded=False):
        st.markdown(
            "\n".join(
                [
                    "- **Annualised return**: historical OOS return, not expected return.",
                    "- **Volatility**: annualised variability of returns.",
                    "- **Sharpe**: return per unit of volatility.",
                    "- **Max drawdown**: worst peak-to-trough fall.",
                    "- **Turnover**: trading intensity and potential cost drag.",
                    "- **Effective holdings**: how concentrated the fund behaves.",
                ]
            )
        )


def render_peer_context(metrics, selected: FundKey) -> None:
    peer = peer_comparison(metrics, selected)
    lines = []
    for metric in relative_peer_metrics(metrics, selected):
        selected_left = f"{metric.selected_position * 100:.3f}%"
        median_left = f"{metric.median_position * 100:.3f}%"
        lines.append(
            f"""
<div class="ss-relative-line">
  <div class="ss-relative-label">{html.escape(metric.label)}</div>
  <div class="ss-relative-track" aria-hidden="true">
    <span class="ss-relative-median" style="left: {median_left};"></span>
    <span class="ss-relative-selected" style="left: {selected_left};"></span>
  </div>
  <div class="ss-relative-values">
    selected {html.escape(metric.selected_text)}<br />
    family median {html.escape(metric.median_text)}
  </div>
</div>
<p class="ss-peer-note">{html.escape(metric.context)}</p>
"""
        )
    st.markdown(
        f"""
<div class="ss-peer-card">
  <p class="ss-peer-title">{html.escape(peer.heading)}</p>
  <div class="ss-peer-grid">{"".join(lines)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_fund_shell(artifacts: StartupArtifacts) -> None:
    metrics = artifacts.frames["performance_metrics"]

    st.markdown(
        f"""
<div class="signalscope-shell">
  <p class="ss-kicker">Evidence-first decision cockpit</p>
  <div class="ss-wordmark">{design.brand_mark_html()}<h1 class="ss-hero-title">{design.APP_TITLE}</h1></div>
  <p class="ss-hero-line">{design.CORE_LINE}</p>
  <p class="ss-value">Compare the nine investable historical OOS funds, then open a fact sheet to inspect risk, holdings, concentration, and costs.</p>
  {design.signal_evidence_trace_html()}
</div>
""",
        unsafe_allow_html=True,
    )
    render_truth_labels()

    action_right, _ = st.columns([1.1, 3.9])
    with action_right:
        if st.button("Inspect evidence", width="stretch"):
            set_view("Evidence")
            st.rerun()

    _, control_area, _ = st.columns([0.06, 0.88, 0.06])
    with control_area:
        st.markdown('<div class="ss-control-frame">', unsafe_allow_html=True)
        selected, family_focus, method_focus, focus_changed = render_fund_controls(metrics)
        st.markdown("</div>", unsafe_allow_html=True)

    chart_frame = comparison_frame(metrics, selected, family_focus, method_focus)
    validate_comparison_frame(chart_frame, selected)
    x_domain, y_domain = full_map_axis_domains(metrics)
    render_section_label("Risk-return map")
    st.markdown('<div class="ss-chart-frame">', unsafe_allow_html=True)
    match_count, unique_match = focus_summary(metrics, family_focus, method_focus)
    st.caption(
        "Focus controls emphasise matching funds while preserving all nine funds for context."
    )
    if unique_match is not None:
        st.caption(f"{unique_match.label} is the only fund matching the active focus.")
    elif focus_includes_key(selected, family_focus, method_focus):
        st.caption(f"Selected: {selected.label}. Active focus matches {match_count} funds.")
    else:
        st.caption(
            f"Selected: {selected.label}. The selected point is outside the active focus; "
            "focus-matching points remain emphasised."
        )
    chart_event = st.vega_lite_chart(
        chart_frame,
        charts.risk_return_spec(
            x_domain=x_domain,
            y_domain=y_domain,
        ),
        width="stretch",
        key=fund_chart_instance_key(selected, family_focus, method_focus),
        on_select="rerun",
        selection_mode=charts.FUND_SELECTION_NAME,
    )
    clicked_key = fund_key_from_selection_event(chart_event, metrics, charts.FUND_SELECTION_NAME)
    event_identity = chart_event_identity(chart_event, clicked_key)
    if chart_click_should_update(
        clicked_key=clicked_key,
        selected=selected,
        event_identity=event_identity,
        last_event_identity=st.session_state.get(LAST_FUND_CHART_EVENT_KEY),
        focus_changed=focus_changed,
    ):
        st.session_state[LAST_FUND_CHART_EVENT_KEY] = event_identity
        set_selected_fund(clicked_key, source="chart")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    selected_cols = st.columns([1.6, 0.72, 2.4])
    with selected_cols[0]:
        st.markdown(f"**Selected:** {selected.label}")
    with selected_cols[1]:
        if st.button("Open fact sheet", type="primary", width="stretch"):
            set_view("Risk")
            st.rerun()
    st.markdown(
        '<p class="ss-read-guide">Read the map as a tradeoff between historical OOS return and annualised volatility. '
        'The highlighted point is selected for inspection; upper-right is not automatically better because drawdown, turnover, and concentration also matter.</p>',
        unsafe_allow_html=True,
    )
    render_metric_interpretation()
    render_section_label("Relative position")
    render_peer_context(metrics, selected)


def render_concentration(summary: ConcentrationSummary) -> None:
    if summary.is_concentrated:
        st.markdown(
            f"""
<div class="ss-concentration-flag">
  <strong>Concentration flag.</strong> Largest holding is {html.escape(summary.top_asset)}
  at {format_percent(summary.top_weight)}. This is an inspection heuristic, not a forecast or a verdict.
</div>
""",
            unsafe_allow_html=True,
        )
    if summary.is_low_diversification:
        st.markdown(
            f"""
<div class="ss-concentration-flag">
  <strong>Diversification flag.</strong> Effective holdings are {summary.effective_holdings:.1f},
  below the five-holding inspection threshold.
</div>
""",
            unsafe_allow_html=True,
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
    broad_fund = is_broad_near_equal(concentration)
    holdings_display = representative_holdings(latest, top_n=8 if broad_fund else 10)
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

    render_section_label("Key performance")
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

    render_section_label("Risk context")
    estimation_value, estimation_label = estimation_context(
        key.method, first_live["estimation_window"]
    )
    render_context_strip(
        [
            (first_live["first_live_date"], "first live OOS date"),
            (format_multiple(row["total_turnover"]), "total turnover"),
            (estimation_value, estimation_label),
        ]
    )
    render_caveat(family_caveat(key.family))

    st.subheader("Growth of $1")
    st.vega_lite_chart(path, charts.growth_spec(), width="stretch")
    st.caption("Shows how $1 compounded through the historical out-of-sample window.")

    st.subheader("Drawdown")
    st.vega_lite_chart(path, charts.drawdown_spec(), width="stretch")

    render_section_label("Portfolio structure")
    holdings_left, holdings_right = st.columns([1.25, 0.9])
    with holdings_left:
        st.vega_lite_chart(holdings_display, charts.holdings_spec(holdings_display), width="stretch")
        if broad_fund:
            st.markdown(
                f"""
<div class="ss-holdings-note">
  Broad, near-equal portfolio. {concentration.asset_count} holdings,
  {concentration.effective_holdings:.1f} effective holdings, largest weight {format_percent(concentration.top_weight)}.
  Representative positions are shown; remaining weights are similar.
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Top saved positions shown. Concentration is a product inspection flag, not an automatic judgement.")
    with holdings_right:
        if broad_fund:
            render_context_strip(
                [
                    (str(concentration.asset_count), "holdings"),
                    (f"{concentration.effective_holdings:.1f}", "effective holdings"),
                    (format_percent(concentration.top_weight), f"largest: {concentration.top_asset}"),
                    (concentration.latest_date, "latest saved date"),
                ]
            )
        else:
            render_concentration(concentration)
            render_context_strip(
                [
                    (format_percent(concentration.top_weight), f"largest: {concentration.top_asset}"),
                    (f"{concentration.effective_holdings:.1f}", "effective holdings"),
                    (concentration.latest_date, "latest saved date"),
                ]
            )

    render_section_label("Asset-class exposure")
    if key.family == "Combined":
        segments = []
        exposure_for_bar = exposure_latest.copy()
        exposure_for_bar["display_order"] = exposure_for_bar["asset_class_label"].map(
            {"Crypto": 0, "Equity": 1}
        )
        for exposure_row in exposure_for_bar.sort_values("display_order").itertuples(index=False):
            sleeve_class = (
                "ss-exposure-equity"
                if exposure_row.asset_class_label == "Equity"
                else "ss-exposure-crypto"
            )
            segments.append(
                f'<div class="ss-exposure-segment {sleeve_class}" style="width: {max(exposure_row.exposure * 100, 4):.3f}%;">'
                f'{html.escape(exposure_row.asset_class_label)} {format_percent(exposure_row.exposure)}</div>'
            )
        st.markdown(f'<div class="ss-exposure-bar">{"".join(segments)}</div>', unsafe_allow_html=True)
    else:
        only = exposure_latest.iloc[0]
        st.markdown(
            f'<div class="ss-single-exposure">{format_percent(float(only["exposure"]), 0)} '
            f'{html.escape(str(only["asset_class_label"]))}</div>',
            unsafe_allow_html=True,
        )

    with st.expander("Historical OOS Methodology", expanded=False):
        st.markdown("\n".join(rebalance_methodology_lines(key, row)))

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
        render_signal_page()
    elif stage == "Evidence":
        render_evidence_page(artifacts)
    elif stage == "Decision":
        render_decision_page(artifacts)
    elif stage == "Challenge":
        render_challenge_page()
