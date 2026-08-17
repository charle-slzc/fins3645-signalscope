"""Reusable Streamlit primitives for the Phase 4A app foundation."""

from __future__ import annotations

import html

import streamlit as st

from app import design
from app.data import ArtifactValidationError, StartupArtifacts, startup_registry
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


def render_fund_shell(artifacts: StartupArtifacts) -> None:
    metrics = artifacts.frames["performance_metrics"]
    fund_count = len(metrics[["fund_family", "method"]].drop_duplicates())

    st.markdown(
        f"""
<div class="signalscope-shell">
  <p class="ss-kicker">Evidence-first decision cockpit</p>
  <h1 class="ss-hero-title">{design.APP_TITLE}</h1>
  <p class="ss-hero-line">{design.CORE_LINE}</p>
  <p class="ss-value">{design.VALUE_PROPOSITION}</p>
</div>
""",
        unsafe_allow_html=True,
    )
    render_truth_labels()

    action_left, action_right, _ = st.columns([1, 1, 3])
    with action_left:
        if st.button("Compare funds", type="primary", use_container_width=True):
            set_view("Fund")
            st.rerun()
    with action_right:
        if st.button("Inspect evidence", use_container_width=True):
            set_view("Evidence")
            st.rerun()

    st.markdown('<div class="ss-structure-grid">', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        render_panel(
            title="Fund Comparison Canvas",
            body=(
                f"{fund_count} precomputed fund definitions are available. "
                "Phase 4B will place the interactive risk-return comparison here."
            ),
            accent="signal",
        )
    with right:
        render_panel(
            title="Signal Versus Evidence Trace",
            body=(
                "Phase 4C will connect sentiment direction, ticker coverage, "
                "agreement, confidence, and allocation effect in this space."
            ),
            accent="evidence",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    render_startup_status(artifacts)


def render_active_stage(stage: str, artifacts: StartupArtifacts) -> None:
    if stage == "Fund":
        render_fund_shell(artifacts)
    elif stage == "Risk":
        render_future_stage(
            "Risk",
            "What am I buying, and what risks come with it?",
            "Phase 4B",
            "The selected fund state, holdings source, exposure source, and first-live-date source are loaded and ready for fact sheets.",
        )
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
