"""Challenge view helpers and renderer for SignalScope."""

from __future__ import annotations

from dataclasses import dataclass
import html
from pathlib import Path

import pandas as pd
import streamlit as st

from app import charts
from app.data import load_lazy_artifact_cached
from app.funds import format_percent
from app.navigation import set_view


PRIMARY_BASE_METHOD = "Minimum Variance"
ROBUSTNESS_BASE_METHOD = "Maximum Sharpe"
OVERLAY_BASE = "Base"
OVERLAY_STANDARD = "Standard Sentiment"
OVERLAY_PLACEBO = "Matched-Shrinkage Placebo"
OVERLAY_CONFIDENCE = "SignalScope Confidence Lens"
OVERLAY_ORDER = (OVERLAY_BASE, OVERLAY_STANDARD, OVERLAY_PLACEBO, OVERLAY_CONFIDENCE)
OVERLAY_DISPLAY = {
    OVERLAY_BASE: "Base",
    OVERLAY_STANDARD: "Standard sentiment",
    OVERLAY_PLACEBO: "Matched constant",
    OVERLAY_CONFIDENCE: "Confidence",
}
CASE_EXTRA_ATTENUATION = "weak_evidence_more_attenuation_than_placebo"
CASE_EXTRA_PRESERVATION = "strong_evidence_less_attenuation_than_placebo"
RESEARCH_RECOMMENDATION = "REVISE"


@dataclass(frozen=True)
class MatchedStrengthSummary:
    c_match: float
    c_mean: float
    observation_count: int
    standard_abs_tilt_sum: float
    confidence_abs_tilt_sum: float
    placebo_abs_tilt_sum: float
    tilt_difference: float
    below_count: int
    above_count: int
    below_share: float
    above_share: float


@dataclass(frozen=True)
class HypothesisVerdict:
    label: str
    claim: str
    verdict: str
    evidence: str


@dataclass(frozen=True)
class SignalMagnitudeCase:
    case_label: str
    sector: str
    date: str
    direction: str
    z_star: float
    matched_magnitude: float
    confidence_magnitude: float
    matched_multiplier: float
    confidence_multiplier: float
    confidence: float


def _ensure_required(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise ValueError(f"{name} missing required columns: {sorted(missing)}")


def comparison_rows(comparison: pd.DataFrame, base_method: str = PRIMARY_BASE_METHOD) -> pd.DataFrame:
    _ensure_required(
        comparison,
        {"base_method", "overlay", "annualised_return", "sharpe_ratio", "total_turnover"},
        "confidence_placebo_comparison",
    )
    rows = comparison[
        comparison["base_method"].eq(base_method) & comparison["overlay"].isin(OVERLAY_ORDER)
    ].copy()
    if set(rows["overlay"]) != set(OVERLAY_ORDER):
        raise ValueError(f"Challenge comparison missing overlays for {base_method}.")
    rows["order"] = rows["overlay"].map({overlay: index for index, overlay in enumerate(OVERLAY_ORDER)})
    rows["overlay_display"] = rows["overlay"].map(OVERLAY_DISPLAY)
    rows["sharpe_label"] = rows["sharpe_ratio"].map(lambda value: f"{float(value):.3f}")
    return rows.sort_values("order").reset_index(drop=True)


def metric_value(comparison: pd.DataFrame, base_method: str, overlay: str, column: str) -> float:
    rows = comparison_rows(comparison, base_method)
    match = rows.loc[rows["overlay"].eq(overlay), column]
    if match.empty:
        raise KeyError(f"No {column} value for {base_method} / {overlay}")
    return float(match.iloc[0])


def strongest_sharpe_overlay(comparison: pd.DataFrame, base_method: str = PRIMARY_BASE_METHOD) -> str:
    rows = comparison_rows(comparison, base_method)
    return str(rows.loc[rows["sharpe_ratio"].idxmax(), "overlay"])


def turnover_row(turnover: pd.DataFrame, base_method: str = PRIMARY_BASE_METHOD) -> pd.Series:
    _ensure_required(
        turnover,
        {
            "base_method",
            "standard_total_turnover",
            "confidence_total_turnover",
            "standard_to_confidence_turnover_reduction",
            "constant_shrinkage_explained_percent",
        },
        "confidence_placebo_turnover_decomposition",
    )
    rows = turnover[turnover["base_method"].eq(base_method)]
    if rows.empty:
        raise KeyError(f"No turnover row for {base_method}")
    return rows.iloc[0]


def matched_strength_summary(selectivity: pd.DataFrame) -> MatchedStrengthSummary:
    _ensure_required(
        selectivity,
        {"z_star", "standard_tilt", "placebo_tilt", "confidence_tilt", "confidence", "c_match"},
        "confidence_placebo_selectivity",
    )
    if selectivity["c_match"].nunique() != 1:
        raise ValueError("Challenge selectivity requires one saved C_match value.")
    c_match = float(selectivity["c_match"].iloc[0])
    below = selectivity["confidence"].astype(float) < c_match
    above = selectivity["confidence"].astype(float) > c_match
    confidence_abs = float(selectivity["confidence_tilt"].astype(float).abs().sum())
    placebo_abs = float(selectivity["placebo_tilt"].astype(float).abs().sum())
    return MatchedStrengthSummary(
        c_match=c_match,
        c_mean=float(selectivity["confidence"].astype(float).mean()),
        observation_count=int(len(selectivity)),
        standard_abs_tilt_sum=float(selectivity["standard_tilt"].astype(float).abs().sum()),
        confidence_abs_tilt_sum=confidence_abs,
        placebo_abs_tilt_sum=placebo_abs,
        tilt_difference=float(placebo_abs - confidence_abs),
        below_count=int(below.sum()),
        above_count=int(above.sum()),
        below_share=float(below.mean()),
        above_share=float(above.mean()),
    )


def matched_strength_frame(summary: MatchedStrengthSummary) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "label": ["Confidence", "Matched constant"],
            "absolute_tilt_sum": [
                summary.confidence_abs_tilt_sum,
                summary.placebo_abs_tilt_sum,
            ],
        }
    )


def selectivity_split_frame(summary: MatchedStrengthSummary) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "state": [
                "More conservative than matched constant",
                "More permissive than matched constant",
            ],
            "count": [summary.below_count, summary.above_count],
            "share": [summary.below_share, summary.above_share],
        }
    )


def signal_magnitude(multiplier: float) -> float:
    return abs(float(multiplier) - 1.0)


def signed_signal_magnitude(multiplier: float, z_star: float) -> float:
    direction = 1.0 if float(z_star) >= 0 else -1.0
    return direction * signal_magnitude(multiplier)


def case_to_signal_magnitude(row: pd.Series, case_label: str) -> SignalMagnitudeCase:
    z_star = float(row["z_star"])
    return SignalMagnitudeCase(
        case_label=case_label,
        sector=str(row["sector"]),
        date=str(row["date"]),
        direction="Positive signal" if z_star >= 0 else "Negative signal",
        z_star=z_star,
        matched_magnitude=signal_magnitude(float(row["placebo_multiplier"])),
        confidence_magnitude=signal_magnitude(float(row["confidence_multiplier"])),
        matched_multiplier=float(row["placebo_multiplier"]),
        confidence_multiplier=float(row["confidence_multiplier"]),
        confidence=float(row["confidence"]),
    )


def case_pair(cases: pd.DataFrame, base_method: str = PRIMARY_BASE_METHOD) -> tuple[pd.Series, pd.Series]:
    _ensure_required(
        cases,
        {
            "case_type",
            "base_method",
            "date",
            "sector",
            "z_star",
            "confidence",
            "c_match",
            "placebo_multiplier",
            "confidence_multiplier",
            "selective_deviation",
            "case_selection_rule",
        },
        "confidence_placebo_cases",
    )
    method_cases = cases[cases["base_method"].eq(base_method)]
    weak = method_cases[method_cases["case_type"].eq(CASE_EXTRA_ATTENUATION)]
    strong = method_cases[method_cases["case_type"].eq(CASE_EXTRA_PRESERVATION)]
    if weak.empty or strong.empty:
        raise KeyError(f"Saved attenuation/preservation case pair missing for {base_method}.")
    return weak.iloc[0], strong.iloc[0]


def case_signal_magnitude_frame(weak: pd.Series, strong: pd.Series) -> pd.DataFrame:
    rows = []
    for case_label, row in [("Extra attenuation", weak), ("Extra preservation", strong)]:
        sector_date = f"{row['sector']} / {row['date']}"
        rows.extend(
            [
                {
                    "case_label": case_label,
                    "sector_date": sector_date,
                    "rule": "Matched constant",
                    "signal_magnitude": signal_magnitude(float(row["placebo_multiplier"])),
                    "signed_signal_magnitude": signed_signal_magnitude(
                        float(row["placebo_multiplier"]),
                        float(row["z_star"]),
                    ),
                    "confidence": float(row["confidence"]),
                },
                {
                    "case_label": case_label,
                    "sector_date": sector_date,
                    "rule": "Confidence",
                    "signal_magnitude": signal_magnitude(float(row["confidence_multiplier"])),
                    "signed_signal_magnitude": signed_signal_magnitude(
                        float(row["confidence_multiplier"]),
                        float(row["z_star"]),
                    ),
                    "confidence": float(row["confidence"]),
                },
            ]
        )
    return pd.DataFrame(rows)


def hypothesis_verdicts(
    comparison: pd.DataFrame,
    turnover: pd.DataFrame,
    selectivity: pd.DataFrame,
) -> list[HypothesisVerdict]:
    primary = comparison_rows(comparison, PRIMARY_BASE_METHOD)
    robust = comparison_rows(comparison, ROBUSTNESS_BASE_METHOD)
    turn_primary = turnover_row(turnover, PRIMARY_BASE_METHOD)
    summary = matched_strength_summary(selectivity)
    base_beats_confidence = (
        metric_value(primary, PRIMARY_BASE_METHOD, OVERLAY_BASE, "sharpe_ratio")
        > metric_value(primary, PRIMARY_BASE_METHOD, OVERLAY_CONFIDENCE, "sharpe_ratio")
    )
    robust_base_beats_confidence = (
        metric_value(robust, ROBUSTNESS_BASE_METHOD, OVERLAY_BASE, "sharpe_ratio")
        > metric_value(robust, ROBUSTNESS_BASE_METHOD, OVERLAY_CONFIDENCE, "sharpe_ratio")
    )
    confidence_reduces_turnover = (
        float(turn_primary["confidence_total_turnover"])
        < float(turn_primary["standard_total_turnover"])
    )
    has_selectivity = summary.below_count > 0 and summary.above_count > 0
    placebo_beats_confidence = (
        metric_value(primary, PRIMARY_BASE_METHOD, OVERLAY_PLACEBO, "sharpe_ratio")
        > metric_value(primary, PRIMARY_BASE_METHOD, OVERLAY_CONFIDENCE, "sharpe_ratio")
    )
    return [
        HypothesisVerdict(
            "H1",
            "performance improvement",
            "REJECT" if base_beats_confidence and robust_base_beats_confidence else "NOT SUPPORTED",
            "Base Sharpe is higher than Confidence in the primary and robustness comparisons.",
        ),
        HypothesisVerdict(
            "H2",
            "reduced sentiment-induced disturbance",
            "SUPPORT" if confidence_reduces_turnover else "NOT SUPPORTED",
            "Confidence turnover is lower than raw Standard sentiment turnover.",
        ),
        HypothesisVerdict(
            "H3",
            "dynamic evidence-state distinction",
            "SUPPORT" if has_selectivity else "NOT SUPPORTED",
            "The saved selectivity panel has observations on both sides of the matched constant.",
        ),
        HypothesisVerdict(
            "H4",
            "economic necessity",
            "REJECT" if placebo_beats_confidence else "NOT SUPPORTED",
            "The matched constant control explains much of the shrinkage effect and has higher primary Sharpe.",
        ),
    ]


def match_uses_signal_only_metadata(selectivity: pd.DataFrame, cases: pd.DataFrame) -> bool:
    forbidden_fragments = ("return", "sharpe", "performance", "drawdown")
    has_forbidden_columns = any(
        fragment in column.lower()
        for column in selectivity.columns
        for fragment in forbidden_fragments
    )
    rules = cases["case_selection_rule"].dropna().astype(str)
    saved_rule_ok = not rules.empty and rules.str.contains("no subsequent returns used", regex=False).all()
    return (not has_forbidden_columns) and saved_rule_ok


def format_signal_direction(z_star: float) -> str:
    if z_star > 0:
        return f"positive signal direction ({z_star:.3f})"
    if z_star < 0:
        return f"negative signal direction ({z_star:.3f})"
    return "near-neutral signal direction (0.000)"


def _verdict_html(rows: list[tuple[str, str, str, str]]) -> str:
    html_rows = []
    for number, question, answer, evidence in rows:
        html_rows.append(
            f"""
<div class="ss-verdict-row">
  <div class="ss-verdict-number">{html.escape(number)}</div>
  <div>
    <div class="ss-verdict-question">{html.escape(question)}</div>
    <div class="ss-verdict-evidence">{html.escape(evidence)}</div>
  </div>
  <div class="ss-verdict-answer">{html.escape(answer)}</div>
</div>
"""
        )
    return f'<div class="ss-verdict-stack">{"".join(html_rows)}</div>'


def matched_strength_html(summary: MatchedStrengthSummary) -> str:
    return f"""
<div class="ss-equality-strip">
  <div>
    <span>Confidence</span>
    <strong>{summary.confidence_abs_tilt_sum:.2f}</strong>
  </div>
  <i>=</i>
  <div>
    <span>Matched constant</span>
    <strong>{summary.placebo_abs_tilt_sum:.2f}</strong>
  </div>
  <div>
    <span>Difference</span>
    <strong>{summary.tilt_difference:.2f}</strong>
  </div>
</div>
"""


def selectivity_split_html(summary: MatchedStrengthSummary) -> str:
    below_width = max(0.0, min(100.0, summary.below_share * 100.0))
    above_width = max(0.0, min(100.0, summary.above_share * 100.0))
    return f"""
<div class="ss-split-visual" aria-label="Where Confidence differed">
  <div class="ss-split-track">
    <span class="is-conservative" style="width: {below_width:.3f}%"></span>
    <span class="is-permissive" style="width: {above_width:.3f}%"></span>
  </div>
  <div class="ss-split-labels">
    <div><strong>{format_percent(summary.below_share, 1)}</strong><span>{summary.below_count} of {summary.observation_count}<br>more conservative than the matched constant</span></div>
    <div><strong>{format_percent(summary.above_share, 1)}</strong><span>{summary.above_count} of {summary.observation_count}<br>more permissive than the matched constant</span></div>
  </div>
</div>
"""


def _magnitude_value_html(label: str, magnitude: float, z_star: float) -> str:
    prefix = "+" if z_star >= 0 else "&larr; "
    return f"""
<div class="ss-magnitude-value">
  <span>{html.escape(label)}</span>
  <strong>{prefix}{format_percent(magnitude, 1)}</strong>
</div>
"""


def _case_html(case_data: SignalMagnitudeCase, interpretation: str) -> str:
    return f"""
<div class="ss-challenge-case">
  <span>{html.escape(case_data.case_label)}</span>
  <strong>{html.escape(case_data.sector)} / {html.escape(case_data.date)}</strong>
  <p>{html.escape(case_data.direction)}. Signal magnitude is measured from neutral, so negative-direction preservation is read from distance from zero, not raw multiplier ordering.</p>
  <div class="ss-magnitude-row">
    {_magnitude_value_html("Matched constant", case_data.matched_magnitude, case_data.z_star)}
    {_magnitude_value_html("Confidence", case_data.confidence_magnitude, case_data.z_star)}
  </div>
  <p>{html.escape(interpretation)}</p>
</div>
"""


def render_challenge_page(project_root: Path | None = None) -> None:
    root_arg = str(project_root) if project_root else None
    comparison = load_lazy_artifact_cached("confidence_placebo_comparison", root_arg)
    turnover = load_lazy_artifact_cached("confidence_placebo_turnover_decomposition", root_arg)
    selectivity = load_lazy_artifact_cached("confidence_placebo_selectivity", root_arg)
    quadrants = load_lazy_artifact_cached("confidence_placebo_quadrants", root_arg)
    cases = load_lazy_artifact_cached("confidence_placebo_cases", root_arg)

    primary_rows = comparison_rows(comparison, PRIMARY_BASE_METHOD)
    robustness_rows = comparison_rows(comparison, ROBUSTNESS_BASE_METHOD)
    primary_turnover = turnover_row(turnover, PRIMARY_BASE_METHOD)
    robustness_turnover = turnover_row(turnover, ROBUSTNESS_BASE_METHOD)
    summary = matched_strength_summary(selectivity)
    weak_case, strong_case = case_pair(cases, PRIMARY_BASE_METHOD)
    weak_case_data = case_to_signal_magnitude(weak_case, "Extra attenuation")
    strong_case_data = case_to_signal_magnitude(strong_case, "Extra preservation")

    base_sharpe = metric_value(comparison, PRIMARY_BASE_METHOD, OVERLAY_BASE, "sharpe_ratio")
    standard_sharpe = metric_value(comparison, PRIMARY_BASE_METHOD, OVERLAY_STANDARD, "sharpe_ratio")
    placebo_sharpe = metric_value(comparison, PRIMARY_BASE_METHOD, OVERLAY_PLACEBO, "sharpe_ratio")
    confidence_sharpe = metric_value(comparison, PRIMARY_BASE_METHOD, OVERLAY_CONFIDENCE, "sharpe_ratio")

    st.markdown(
        """
<p class="ss-kicker">Challenge</p>
<h2 class="ss-stage-title">Does the cleverer model actually earn its complexity?</h2>
<p class="ss-stage-copy">SignalScope tried to falsify its own Confidence Lens. The test asks whether a simpler constant rule can explain the economic effect.</p>
<div class="ss-challenge-thesis">Look beneath the headline number: price-based portfolio construction remains primary; news sentiment is secondary; Confidence only governs how that weak textual signal is used.</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        _verdict_html(
            [
                (
                    "01",
                    "Did sentiment beat Base?",
                    "NO",
                    f"Primary {PRIMARY_BASE_METHOD} Sharpe: Base {base_sharpe:.3f}, Standard {standard_sharpe:.3f}, matched constant {placebo_sharpe:.3f}, Confidence {confidence_sharpe:.3f}.",
                ),
                (
                    "02",
                    "Did Confidence reduce the disturbance caused by raw sentiment?",
                    "YES",
                    f"Turnover fell from {float(primary_turnover['standard_total_turnover']):.3f} under Standard sentiment to {float(primary_turnover['confidence_total_turnover']):.3f} under Confidence.",
                ),
                (
                    "03",
                    "Was dynamic Confidence economically necessary?",
                    "NOT CLEARLY",
                    "The simpler constant control reproduced slightly more than the turnover reduction achieved by Confidence. This weakens the case that dynamic Confidence was economically necessary.",
                ),
            ]
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<p class="ss-section-label">Primary comparison</p>', unsafe_allow_html=True)
    st.vega_lite_chart(primary_rows, charts.challenge_performance_spec(), width="stretch")
    st.caption(
        "Adding headline sentiment did not improve the primary fund's OOS Sharpe. Base remained strongest on Sharpe."
    )

    st.markdown('<p class="ss-section-label">Matched-strength control</p>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="ss-match-statement">
  <strong>What if every sentiment signal was simply made smaller by the same amount?</strong>
  SignalScope created a matched constant-shrinkage control whose total signal strength exactly equals Confidence in the saved artifact.
</div>
""",
        unsafe_allow_html=True,
    )
    st.vega_lite_chart(matched_strength_frame(summary), charts.challenge_matched_strength_spec(), width="stretch")
    st.caption(
        "Same total signal strength: Confidence 17.49 = matched constant 17.49. Difference: 0.00."
    )
    st.markdown(matched_strength_html(summary), unsafe_allow_html=True)

    st.markdown(
        """
<div class="ss-survived">
  <strong>WHAT SURVIVED?</strong>
  <span>Same total signal strength. Different decisions about where to trust it. Confidence did not improve the primary fund's OOS Sharpe, and a simpler constant rule reproduced the economic shrinkage. What remains is a narrower selective-governance role: changing where the weak textual signal is muted or preserved.</span>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<p class="ss-section-label">Where Confidence differed</p>', unsafe_allow_html=True)
    st.markdown(selectivity_split_html(summary), unsafe_allow_html=True)
    st.caption(
        f"{format_percent(summary.below_share, 1)} of valid observations were more conservative than the matched constant; "
        f"{format_percent(summary.above_share, 1)} were more permissive. These are evidence states, not good/bad labels."
    )

    st.markdown('<p class="ss-section-label">Two saved cases</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="ss-case-pair">
  {_case_html(weak_case_data, "Weak evidence caused Confidence to mute more of the positive signal than the matched constant.")}
  {_case_html(strong_case_data, "Stronger evidence caused Confidence to preserve more of the negative signal than the matched constant.")}
</div>
""",
        unsafe_allow_html=True,
    )
    st.vega_lite_chart(case_signal_magnitude_frame(weak_case, strong_case), charts.challenge_case_magnitude_spec(), width="stretch")

    st.markdown('<p class="ss-section-label">Recommendation</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="ss-match-statement">
  <strong>{RESEARCH_RECOMMENDATION}</strong>
  Keep the Evidence Lens as a transparent signal-governance layer, but do not claim that it creates alpha or that its extra complexity is economically necessary.
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption(
        "Confidence did not make sentiment an alpha source. Its surviving value is selective signal governance: weakening poorly supported signals while preserving better-supported ones."
    )

    with st.expander("Research verdicts", expanded=False):
        verdict_frame = pd.DataFrame(
            [
                {
                    "Hypothesis": verdict.label,
                    "Claim": verdict.claim,
                    "Verdict": verdict.verdict,
                    "Evidence": verdict.evidence,
                }
                for verdict in hypothesis_verdicts(comparison, turnover, selectivity)
            ]
        )
        st.dataframe(verdict_frame, hide_index=True, width="stretch")

    with st.expander("Does the conclusion depend on the base optimiser?", expanded=False):
        st.vega_lite_chart(robustness_rows, charts.challenge_performance_spec(), width="stretch")
        st.markdown(
            f"""
- Maximum Sharpe Base Sharpe: `{metric_value(comparison, ROBUSTNESS_BASE_METHOD, OVERLAY_BASE, "sharpe_ratio"):.12f}`.
- Maximum Sharpe Standard Sentiment Sharpe: `{metric_value(comparison, ROBUSTNESS_BASE_METHOD, OVERLAY_STANDARD, "sharpe_ratio"):.12f}`.
- Maximum Sharpe Matched Constant Sharpe: `{metric_value(comparison, ROBUSTNESS_BASE_METHOD, OVERLAY_PLACEBO, "sharpe_ratio"):.12f}`.
- Maximum Sharpe Confidence Sharpe: `{metric_value(comparison, ROBUSTNESS_BASE_METHOD, OVERLAY_CONFIDENCE, "sharpe_ratio"):.12f}`.
- Confidence turnover is `{float(robustness_turnover["confidence_total_turnover"]):.12f}` versus Standard turnover `{float(robustness_turnover["standard_total_turnover"]):.12f}`.
"""
        )
        st.caption("The robustness comparison points in the same direction: Base Sharpe remains higher than sentiment variants.")

    with st.expander("How the challenge works", expanded=False):
        st.markdown(
            "The matching constant is the weighted mean confidence needed to match total absolute signal tilt. "
            "It is derived from saved signal magnitude and evidence confidence fields, not from OOS return performance."
        )
        st.latex(r"C_{match} = \frac{\sum_i |Z^*_i| C_i}{\sum_i |Z^*_i|}")
        st.latex(r"\text{Matched multiplier}_i = 1 + 0.10 \times Z^*_i \times C_{match}")
        st.latex(r"\text{Confidence multiplier}_i = 1 + 0.10 \times Z^*_i \times C_i")
        st.markdown(
            f"""
- Saved `C_match`: `{summary.c_match:.16f}`.
- Saved mean confidence: `{summary.c_mean:.16f}`.
- Valid rebalance-sector observations: `{summary.observation_count}`.
- Standard absolute tilt sum: `{summary.standard_abs_tilt_sum:.14f}`.
- Confidence absolute tilt sum: `{summary.confidence_abs_tilt_sum:.15f}`.
- Matched constant absolute tilt sum: `{summary.placebo_abs_tilt_sum:.15f}`.
- Difference: `{summary.tilt_difference:.16f}`.
- Standard turnover: `{float(primary_turnover["standard_total_turnover"]):.15f}`.
- Confidence turnover: `{float(primary_turnover["confidence_total_turnover"]):.15f}`.
- Confidence reduction: `{float(primary_turnover["standard_to_confidence_turnover_reduction"]):.16f}`.
- Constant-shrinkage share of that reduction: `{float(primary_turnover["constant_shrinkage_explained_percent"]):.13f}%`.
- Utilities raw multipliers: matched constant `{float(weak_case["placebo_multiplier"]):.6f}`, Confidence `{float(weak_case["confidence_multiplier"]):.6f}`.
- Financials raw multipliers: matched constant `{float(strong_case["placebo_multiplier"]):.6f}`, Confidence `{float(strong_case["confidence_multiplier"]):.6f}`.
- The saved case-selection rule states: `{html.escape(str(weak_case["case_selection_rule"]))}`.
- Signal-only metadata check: `{"passed" if match_uses_signal_only_metadata(selectivity, cases) else "not passed"}`.
"""
        )
        st.dataframe(
            quadrants[
                [
                    "quadrant",
                    "observation_count",
                    "average_confidence",
                    "average_abs_placebo_tilt",
                    "average_abs_confidence_tilt",
                    "average_selective_deviation",
                ]
            ],
            hide_index=True,
            width="stretch",
        )

    action_left, action_mid, action_right, _ = st.columns([1.0, 1.12, 0.95, 1.6])
    with action_left:
        if st.button("Back to Decision", width="stretch"):
            set_view("Decision")
            st.rerun()
    with action_mid:
        if st.button("Inspect Evidence Lens", type="primary", width="stretch"):
            set_view("Evidence")
            st.rerun()
    with action_right:
        if st.button("Compare funds", width="stretch"):
            set_view("Fund")
            st.rerun()
