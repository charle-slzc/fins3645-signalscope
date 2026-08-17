"""Evidence Lens helpers and renderer for SignalScope."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import html

import pandas as pd
import streamlit as st

from app import charts
from app.data import StartupArtifacts, load_lazy_artifact_cached
from app.funds import format_percent
from app.navigation import set_view
from app.signal import DEFAULT_SECTOR, set_pending_signal_context, store_signal_context


ATTENUATION_BASE_METHOD = "Minimum Variance"
NEUTRALITY_CASE_DATE = "2020-07-09"
NEUTRALITY_CASE_SECTOR = "Industrials"
CONSENSUS_CASE_DATE = "2021-02-25"
CONSENSUS_CASE_SECTOR = "Materials"
VOLUME_CASE_DATE = "2020-07-24"
VOLUME_CASE_SECTOR = "Tech"
ATTENUATION_CASE_DATE = "2021-11-01"
ATTENUATION_CASE_SECTOR = "RealEstate"
EVIDENCE_SECTOR_WIDGET_KEY = "evidence_sector_select"
EVIDENCE_DATE_WIDGET_KEY = "evidence_date_select"
EVIDENCE_SECTOR_CHANGED_KEY = "_evidence_sector_changed"
EVIDENCE_DATE_CHANGED_KEY = "_evidence_date_changed"
PENDING_EVIDENCE_CONTEXT_KEY = "_pending_evidence_context"


@dataclass(frozen=True)
class EvidenceContext:
    sector: str
    live_rebalance_date: str
    requested_signal_date: str | None = None
    date_status: str = "matched"


def confidence_sectors(confidence: pd.DataFrame) -> list[str]:
    sectors = sorted(str(sector) for sector in confidence["sector"].dropna().unique())
    if not sectors:
        raise ValueError("Confidence artifact contains no sectors.")
    return sectors


def validate_evidence_sector(confidence: pd.DataFrame, sector: str | None) -> str:
    sectors = confidence_sectors(confidence)
    if sector in sectors:
        return str(sector)
    if DEFAULT_SECTOR in sectors:
        return DEFAULT_SECTOR
    return sectors[0]


def evidence_dates(confidence: pd.DataFrame, sector: str) -> list[str]:
    frame = confidence[confidence["sector"] == sector].copy()
    if frame.empty:
        raise KeyError(f"No confidence observations found for sector: {sector}")
    frame["live_rebalance_date"] = pd.to_datetime(frame["live_rebalance_date"])
    return frame.sort_values("live_rebalance_date")["live_rebalance_date"].dt.date.astype(str).tolist()


def prior_or_first_evidence_date(confidence: pd.DataFrame, sector: str, requested: str | None) -> str:
    dates = evidence_dates(confidence, sector)
    if requested in dates:
        return str(requested)
    if not requested:
        return dates[-1]
    target = pd.Timestamp(requested)
    dated = pd.Series(pd.to_datetime(dates))
    prior = dated[dated <= target]
    if not prior.empty:
        return str(prior.iloc[-1].date())
    return str(dated.iloc[0].date())


def evidence_date_status(confidence: pd.DataFrame, sector: str, requested: str | None) -> str:
    if not requested:
        return "default_latest"
    dates = evidence_dates(confidence, sector)
    if requested in dates:
        return "matched"
    requested_date = pd.Timestamp(requested)
    if requested_date < pd.Timestamp(dates[0]):
        return "before_oos"
    if requested_date > pd.Timestamp(dates[-1]):
        return "after_oos"
    return "between_rebalances"


def confidence_row(confidence: pd.DataFrame, sector: str, live_rebalance_date: str) -> pd.Series:
    matches = confidence[
        (confidence["sector"] == sector)
        & (confidence["live_rebalance_date"] == live_rebalance_date)
    ]
    if matches.empty:
        raise KeyError(f"No confidence row for {sector} on {live_rebalance_date}")
    return matches.iloc[0]


def current_evidence_context(confidence: pd.DataFrame) -> EvidenceContext:
    sector = validate_evidence_sector(confidence, st.session_state.get("selected_sector"))
    requested = st.session_state.get("selected_signal_date")
    selected = prior_or_first_evidence_date(confidence, sector, requested)
    return EvidenceContext(
        sector=sector,
        live_rebalance_date=selected,
        requested_signal_date=requested,
        date_status=evidence_date_status(confidence, sector, requested),
    )


def set_pending_evidence_context(sector: str, selected_date: str) -> None:
    st.session_state[PENDING_EVIDENCE_CONTEXT_KEY] = {
        "sector": sector,
        "date": selected_date,
    }


def _mark_evidence_sector_changed() -> None:
    st.session_state[EVIDENCE_SECTOR_CHANGED_KEY] = True


def _mark_evidence_date_changed() -> None:
    st.session_state[EVIDENCE_DATE_CHANGED_KEY] = True


def _sync_evidence_widget_state(confidence: pd.DataFrame) -> EvidenceContext:
    pending = st.session_state.pop(PENDING_EVIDENCE_CONTEXT_KEY, None)
    if pending:
        sector = validate_evidence_sector(confidence, pending.get("sector"))
        requested = pending.get("date")
        selected = prior_or_first_evidence_date(confidence, sector, requested)
        st.session_state["selected_sector"] = sector
        st.session_state["selected_signal_date"] = requested
        st.session_state["selected_evidence_date"] = selected
        st.session_state[EVIDENCE_SECTOR_WIDGET_KEY] = sector
        st.session_state[EVIDENCE_DATE_WIDGET_KEY] = selected
        return EvidenceContext(
            sector=sector,
            live_rebalance_date=selected,
            requested_signal_date=requested,
            date_status=evidence_date_status(confidence, sector, requested),
        )

    if st.session_state.pop(EVIDENCE_SECTOR_CHANGED_KEY, False):
        sector = validate_evidence_sector(confidence, st.session_state.get(EVIDENCE_SECTOR_WIDGET_KEY))
        requested = st.session_state.get("selected_signal_date")
        selected = prior_or_first_evidence_date(confidence, sector, requested)
        st.session_state["selected_sector"] = sector
        st.session_state["selected_evidence_date"] = selected
        st.session_state[EVIDENCE_DATE_WIDGET_KEY] = selected
        return EvidenceContext(
            sector=sector,
            live_rebalance_date=selected,
            requested_signal_date=requested,
            date_status=evidence_date_status(confidence, sector, requested),
        )

    if st.session_state.pop(EVIDENCE_DATE_CHANGED_KEY, False):
        sector = validate_evidence_sector(confidence, st.session_state.get(EVIDENCE_SECTOR_WIDGET_KEY))
        selected = prior_or_first_evidence_date(
            confidence,
            sector,
            st.session_state.get(EVIDENCE_DATE_WIDGET_KEY),
        )
        st.session_state["selected_sector"] = sector
        st.session_state["selected_signal_date"] = selected
        st.session_state["selected_evidence_date"] = selected
        return EvidenceContext(
            sector=sector,
            live_rebalance_date=selected,
            requested_signal_date=selected,
            date_status=evidence_date_status(confidence, sector, selected),
        )

    context = current_evidence_context(confidence)
    st.session_state[EVIDENCE_SECTOR_WIDGET_KEY] = context.sector
    st.session_state[EVIDENCE_DATE_WIDGET_KEY] = context.live_rebalance_date
    st.session_state["selected_evidence_date"] = context.live_rebalance_date
    return context


def direction_label(z_star: float) -> str:
    if z_star > 0.25:
        return "Positive trading signal"
    if z_star < -0.25:
        return "Negative trading signal"
    return "Near-neutral trading signal"


def breadth_label(row: pd.Series) -> str:
    return f"{float(row['b63']) * 100:.1f}% trailing evidence coverage"


def breadth_detail(row: pd.Series) -> str:
    observed = int(row["breadth_observed_ticker_days"])
    possible = int(row["breadth_possible_ticker_days"])
    return (
        f"{observed} of {possible} possible company-days had news over the "
        "trailing 63 trading days"
    )


def agreement_label(a21: float) -> str:
    if a21 >= 0.85:
        return "Signals were aligned"
    if a21 >= 0.70:
        return "Signals were mixed"
    return "Signals strongly disagreed"


def confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "Strong evidence support"
    if confidence >= 0.50:
        return "Moderate evidence support"
    return "Weak evidence support"


def rail_position(value: float, minimum: float = -2.0, maximum: float = 2.0) -> float:
    if maximum <= minimum:
        return 50.0
    return max(0.0, min(100.0, (float(value) - minimum) / (maximum - minimum) * 100.0))


def confidence_cells(confidence_value: float, cell_count: int = 10) -> str:
    filled = int(round(max(0.0, min(1.0, confidence_value)) * cell_count))
    cells = []
    for index in range(cell_count):
        css_class = "ss-evidence-cell is-filled" if index < filled else "ss-evidence-cell is-missing"
        cells.append(f'<span class="{css_class}"></span>')
    return "".join(cells)


def allocation_effect_frame(row: pd.Series, attenuation: pd.Series | None = None) -> pd.DataFrame:
    if attenuation is not None and not pd.isna(attenuation.get("standard_change")):
        raw = float(attenuation["standard_change"])
        adjusted = float(attenuation["confidence_change"])
        raw_source = "standard_change"
        adjusted_source = "confidence_change"
        labels = [
            "Raw sentiment sector allocation change",
            "Evidence-adjusted sector allocation change",
        ]
    else:
        raw = float(row["raw_tilt"])
        adjusted = float(row["confidence_adjusted_tilt"])
        raw_source = "raw_tilt"
        adjusted_source = "confidence_adjusted_tilt"
        labels = [
            "Raw pre-normalisation tilt",
            "Evidence-adjusted pre-normalisation tilt",
        ]
    return pd.DataFrame(
        {
            "label": labels,
            "kind": ["raw", "confidence"],
            "effect": [raw, adjusted],
            "source": [raw_source, adjusted_source],
        }
    )


def get_neutrality_case(disagreement_examples: pd.DataFrame) -> pd.Series:
    matches = disagreement_examples[
        (disagreement_examples["date"] == NEUTRALITY_CASE_DATE)
        & (disagreement_examples["sector"] == NEUTRALITY_CASE_SECTOR)
    ]
    if matches.empty:
        raise KeyError("Saved neutrality/cancellation case is missing.")
    return matches.iloc[0]


def get_consensus_case(disagreement_examples: pd.DataFrame) -> pd.Series:
    matches = disagreement_examples[
        (disagreement_examples["date"] == CONSENSUS_CASE_DATE)
        & (disagreement_examples["sector"] == CONSENSUS_CASE_SECTOR)
    ]
    if matches.empty:
        raise KeyError("Saved consensus-neutral case is missing.")
    return matches.iloc[0]


def get_volume_case(candidate_cases: pd.DataFrame) -> pd.Series:
    matches = candidate_cases[
        (candidate_cases["date"] == VOLUME_CASE_DATE)
        & (candidate_cases["sector"] == VOLUME_CASE_SECTOR)
    ]
    if matches.empty:
        raise KeyError("Saved volume/breadth case is missing.")
    return matches.iloc[0]


def get_attenuation_case(attenuation_cases: pd.DataFrame) -> pd.Series:
    matches = attenuation_cases[
        (attenuation_cases["date"] == ATTENUATION_CASE_DATE)
        & (attenuation_cases["sector"] == ATTENUATION_CASE_SECTOR)
        & (attenuation_cases["base_method"] == ATTENUATION_BASE_METHOD)
    ]
    if matches.empty:
        raise KeyError("Saved attenuation case is missing.")
    return matches.iloc[0]


def ticker_case_rows(ticker_day_sentiment: pd.DataFrame, sector: str, date: str) -> pd.DataFrame:
    rows = ticker_day_sentiment[
        (ticker_day_sentiment["sector"] == sector)
        & (ticker_day_sentiment["date"] == date)
    ].copy()
    if rows.empty:
        raise KeyError(f"No ticker-day sentiment rows for {sector} on {date}")
    rows = rows.sort_values("ticker").reset_index(drop=True)
    midpoint = (len(rows) - 1) / 2
    rows["lane"] = [index - midpoint for index in range(len(rows))]
    return rows


def render_lens_flow(row: pd.Series) -> None:
    z_star = float(row["z_star"])
    confidence_value = float(row["confidence"])
    direction_position = rail_position(z_star)
    confidence_position = rail_position(confidence_value, 0.0, 1.0)
    st.markdown(
        f"""
<div class="ss-lens-flow">
  <div class="ss-lens-step">
    <div>
      <div class="ss-lens-label">WHAT THE NEWS SAYS</div>
      <div class="ss-lens-title">Sentiment direction</div>
    </div>
    <div>
      <div class="ss-direction-rail"><span class="ss-direction-marker" style="left: {direction_position:.3f}%"></span></div>
      <p class="ss-lens-copy">{html.escape(direction_label(z_star))}. Built from the saved 21-day sector signal used by the trading overlay; this is different from the daily Signal-page reading.</p>
    </div>
  </div>
  <div class="ss-lens-step">
    <div>
      <div class="ss-lens-label">HOW MUCH OF THE SECTOR WAS OBSERVED</div>
      <div class="ss-lens-title">Ticker coverage</div>
    </div>
    <div>
      <div class="ss-evidence-cells">{confidence_cells(float(row["b63"]))}</div>
      <p class="ss-lens-copy">{html.escape(breadth_label(row))}. {html.escape(breadth_detail(row))}. This is trailing breadth, not same-day company count.</p>
    </div>
  </div>
  <div class="ss-lens-step">
    <div>
      <div class="ss-lens-label">DID THE TICKERS AGREE?</div>
      <div class="ss-lens-title">Agreement</div>
    </div>
    <div>
      <div class="ss-confidence-rail"><span class="ss-confidence-marker" style="left: {rail_position(float(row["a21"]), 0.0, 1.0):.3f}%"></span></div>
      <p class="ss-lens-copy">{html.escape(agreement_label(float(row["a21"])))} across the trailing agreement window.</p>
    </div>
  </div>
  <div class="ss-lens-step">
    <div>
      <div class="ss-lens-label">EVIDENCE CONFIDENCE</div>
      <div class="ss-lens-title">Evidence support</div>
    </div>
    <div>
      <div class="ss-confidence-rail"><span class="ss-confidence-marker" style="left: {confidence_position:.3f}%"></span></div>
      <p class="ss-lens-copy">{html.escape(confidence_label(confidence_value))}. Evidence confidence describes how broad and internally consistent the observed news evidence is.</p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _case_button(label: str, case_key: str, sector: str, date: str) -> None:
    if st.button(label, width="stretch"):
        st.session_state["evidence_case"] = case_key
        store_signal_context(sector, date)
        set_pending_signal_context(sector, date, curated=True)
        set_pending_evidence_context(sector, date)
        st.rerun()


def render_neutrality_case(disagreement_examples: pd.DataFrame, ticker_day_sentiment: pd.DataFrame) -> None:
    consensus = get_consensus_case(disagreement_examples)
    cancellation = get_neutrality_case(disagreement_examples)
    st.markdown('<p class="ss-case-title">Neutrality is not always consensus.</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="ss-case-copy">The average is flat, but the companies disagree. These are pre-OOS sentiment diagnostic examples, not portfolio allocation decisions or a prevalence claim.</p>',
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        st.caption(f"Consensus neutral: {CONSENSUS_CASE_SECTOR}, {CONSENSUS_CASE_DATE}")
        rows = ticker_case_rows(ticker_day_sentiment, CONSENSUS_CASE_SECTOR, CONSENSUS_CASE_DATE)
        st.vega_lite_chart(rows, charts.constituent_axis_spec(), width="stretch")
        st.caption(
            f"Sector sentiment {float(consensus['sector_sentiment']):.6f}; observed tickers {int(consensus['active_ticker_count'])}; headlines {int(consensus['headline_count'])}."
        )
    with right:
        st.caption(f"Cancellation: {NEUTRALITY_CASE_SECTOR}, {NEUTRALITY_CASE_DATE}")
        rows = ticker_case_rows(ticker_day_sentiment, NEUTRALITY_CASE_SECTOR, NEUTRALITY_CASE_DATE)
        st.vega_lite_chart(rows, charts.constituent_axis_spec(), width="stretch")
        st.caption(
            f"Sector sentiment {float(cancellation['sector_sentiment']):.6f}; MMM {float(cancellation['lowest_ticker_sentiment']):.4f}; CAT +{float(cancellation['highest_ticker_sentiment']):.4f}."
        )
    with st.expander("Technical detail for this case", expanded=False):
        st.markdown(
            f"Industrials cross-ticker dispersion is {float(cancellation['cross_ticker_sentiment_std']):.6f}; Materials comparison dispersion is {float(consensus['cross_ticker_sentiment_std']):.6f}."
        )


def render_volume_case(candidate_cases: pd.DataFrame, ticker_day_sentiment: pd.DataFrame) -> None:
    case = get_volume_case(candidate_cases)
    rows = ticker_case_rows(ticker_day_sentiment, VOLUME_CASE_SECTOR, VOLUME_CASE_DATE)
    dominant = str(case["dominant_ticker"])
    headline_count = int(case["headline_count"])
    dominant_count = int(rows.loc[rows["ticker"] == dominant, "headline_count"].iloc[0])
    possible_count = int(round(len(rows) / float(case["active_ticker_share"])))
    missing_count = max(possible_count - len(rows), 0)
    dots = "".join(
        f'<span class="ss-headline-dot{" is-dominant" if index < dominant_count else ""}"></span>'
        for index in range(headline_count)
    )
    slots = "".join(
        f'<span class="ss-ticker-slot is-observed">{html.escape(str(row.ticker))}<br>{int(row.headline_count)} headlines</span>'
        for row in rows.itertuples(index=False)
    )
    slots += "".join('<span class="ss-ticker-slot">No news</span>' for _ in range(missing_count))
    st.markdown('<p class="ss-case-title">More headlines do not necessarily mean broader evidence.</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
<p class="ss-case-copy">Pre-OOS sentiment diagnostic example: {VOLUME_CASE_SECTOR}, {VOLUME_CASE_DATE}. Lots of headlines. Much of the evidence came from one company.</p>
<div class="ss-headline-pile">{dots}</div>
<div class="ss-ticker-slots">{slots}</div>
""",
        unsafe_allow_html=True,
    )
    st.caption(
        f"{headline_count} headlines; {format_percent(float(case['active_ticker_share']), 0)} active ticker share; {dominant} produced {format_percent(float(case['dominant_ticker_headline_share']), 1)} of headlines."
    )
    with st.expander("Technical detail for this case", expanded=False):
        st.markdown(
            f"Ticker headline-share HHI is {float(case['ticker_headline_share_hhi']):.6f}; sector sentiment is {float(case['sector_sentiment']):.6f}."
        )


def render_attenuation_case(attenuation_cases: pd.DataFrame) -> None:
    case = get_attenuation_case(attenuation_cases)
    frame = pd.DataFrame(
        {
            "label": ["Raw sector change", "Evidence-adjusted sector change"],
            "kind": ["raw", "confidence"],
            "effect": [float(case["standard_change"]), float(case["confidence_change"])],
            "source": ["standard_change", "confidence_change"],
        }
    )
    st.markdown('<p class="ss-case-title">Same news direction. Less portfolio movement.</p>', unsafe_allow_html=True)
    st.vega_lite_chart(frame, charts.allocation_effect_spec(), width="stretch")
    st.caption(
        f"{ATTENUATION_BASE_METHOD} / {ATTENUATION_CASE_SECTOR} / {ATTENUATION_CASE_DATE}: raw sector allocation change {format_percent(float(case['standard_change']), 2)}, evidence-adjusted sector allocation change {format_percent(float(case['confidence_change']), 2)}, confidence {float(case['confidence']):.3f}."
    )


def date_transition_message(context: EvidenceContext) -> str | None:
    requested = context.requested_signal_date
    selected = context.live_rebalance_date
    if context.date_status in {"matched", "default_latest"}:
        return None
    if context.date_status == "before_oos":
        return (
            f"Signal date {requested} is a sentiment diagnostic date before the saved "
            f"OOS portfolio Confidence Lens period. Portfolio allocation effects are "
            f"evaluated only at saved rebalance dates; showing first available "
            f"rebalance {selected} for the Lens."
        )
    if context.date_status == "after_oos":
        return (
            f"Signal date {requested} is after the final saved Confidence Lens "
            f"rebalance. Showing final saved rebalance {selected} for portfolio "
            "evidence context."
        )
    return (
        f"Signal date {requested} is not a saved rebalance date. Portfolio allocation "
        f"effects are evaluated only at saved rebalance dates; showing prior saved "
        f"rebalance {selected} for the Lens."
    )


def render_curated_cases(
    startup_artifacts: StartupArtifacts,
    attenuation_cases: pd.DataFrame,
    ticker_day_sentiment: pd.DataFrame,
) -> None:
    disagreement_examples = startup_artifacts.frames["sentiment_disagreement_examples"]
    candidate_cases = startup_artifacts.frames["sentiment_candidate_cases"]
    st.markdown('<p class="ss-section-label">See why this matters</p>', unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<div class="ss-case-action"><p class="ss-case-title">Neutrality vs cancellation</p><p class="ss-case-copy">A flat sector average can hide offsetting company signals.</p></div>', unsafe_allow_html=True)
        _case_button("Load neutrality case", "neutrality", NEUTRALITY_CASE_SECTOR, NEUTRALITY_CASE_DATE)
    with col_b:
        st.markdown('<div class="ss-case-action"><p class="ss-case-title">Volume vs breadth</p><p class="ss-case-copy">Many headlines can still be concentrated in one company.</p></div>', unsafe_allow_html=True)
        _case_button("Load volume case", "volume", VOLUME_CASE_SECTOR, VOLUME_CASE_DATE)
    with col_c:
        st.markdown('<div class="ss-case-action"><p class="ss-case-title">Confidence attenuation</p><p class="ss-case-copy">A positive signal can be used more cautiously when evidence support is weak.</p></div>', unsafe_allow_html=True)
        _case_button("Load attenuation case", "attenuation", ATTENUATION_CASE_SECTOR, ATTENUATION_CASE_DATE)

    selected_case = st.session_state.get("evidence_case", "attenuation")
    if selected_case == "neutrality":
        render_neutrality_case(disagreement_examples, ticker_day_sentiment)
    elif selected_case == "volume":
        render_volume_case(candidate_cases, ticker_day_sentiment)
    else:
        render_attenuation_case(attenuation_cases)


def render_evidence_page(startup_artifacts: StartupArtifacts, project_root: Path | None = None) -> None:
    root_arg = str(project_root) if project_root else None
    confidence = load_lazy_artifact_cached("sector_sentiment_confidence", root_arg)
    attenuation_cases = load_lazy_artifact_cached("confidence_lens_attenuation_cases", root_arg)
    ticker_day_sentiment = load_lazy_artifact_cached("ticker_day_sentiment", root_arg)

    st.markdown(
        """
<p class="ss-kicker">Evidence</p>
<h2 class="ss-stage-title">How well supported is this reading?</h2>
<p class="ss-stage-copy">Direction tells us what the news says. Evidence confidence tells us how much breadth and agreement support using that direction.</p>
""",
        unsafe_allow_html=True,
    )

    context = _sync_evidence_widget_state(confidence)
    sectors = confidence_sectors(confidence)
    sector_col, date_col = st.columns([1.1, 0.9])
    with sector_col:
        selected_sector = st.selectbox(
            "Sector",
            sectors,
            index=sectors.index(context.sector),
            key=EVIDENCE_SECTOR_WIDGET_KEY,
            on_change=_mark_evidence_sector_changed,
        )
    dates = evidence_dates(confidence, selected_sector)
    selected_date = prior_or_first_evidence_date(
        confidence,
        selected_sector,
        st.session_state.get("selected_signal_date"),
    )
    if st.session_state.get(EVIDENCE_DATE_WIDGET_KEY) not in dates:
        st.session_state[EVIDENCE_DATE_WIDGET_KEY] = selected_date
    with date_col:
        selected_date = st.selectbox(
            "Evidence date",
            dates,
            index=dates.index(selected_date),
            key=EVIDENCE_DATE_WIDGET_KEY,
            on_change=_mark_evidence_date_changed,
            help="Saved monthly rebalance-sector confidence observations.",
        )
    requested_signal_date = st.session_state.get("selected_signal_date")
    context = EvidenceContext(
        sector=selected_sector,
        live_rebalance_date=selected_date,
        requested_signal_date=requested_signal_date,
        date_status=evidence_date_status(confidence, selected_sector, requested_signal_date),
    )
    st.session_state["selected_evidence_date"] = selected_date
    row = confidence_row(confidence, selected_sector, selected_date)

    st.markdown(
        f"""
<div class="ss-disclosure">
  <strong>{html.escape(selected_sector)} / {html.escape(selected_date)}</strong>
  uses sentiment available through {html.escape(str(row["signal_cutoff_date"]))}. Evidence confidence is not probability, truth, or return-prediction confidence.
</div>
""",
        unsafe_allow_html=True,
    )
    transition = date_transition_message(context)
    if transition:
        st.markdown(
            f'<div class="ss-disclosure">{html.escape(transition)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="ss-section-label">SignalScope Evidence Lens</p>', unsafe_allow_html=True)
    render_lens_flow(row)

    st.markdown('<p class="ss-section-label">Allocation effect</p>', unsafe_allow_html=True)
    matching_case = attenuation_cases[
        (attenuation_cases["date"] == selected_date)
        & (attenuation_cases["sector"] == selected_sector)
        & (attenuation_cases["base_method"] == ATTENUATION_BASE_METHOD)
    ]
    attenuation = matching_case.iloc[0] if not matching_case.empty else None
    if attenuation is not None:
        effect_frame = allocation_effect_frame(row, attenuation)
        st.vega_lite_chart(effect_frame, charts.allocation_effect_spec(), width="stretch")
        st.caption(
            "Bars show saved sector allocation changes for the curated attenuation case. This is a portfolio disturbance view, not a return forecast."
        )
    else:
        st.markdown(
            """
<div class="ss-disclosure">
  Saved realized sector-weight changes are available for curated attenuation cases.
  For this selected rebalance, the compact Confidence Lens artifact contains
  pre-normalisation tilt values only, so primary allocation-effect bars are not shown.
</div>
""",
            unsafe_allow_html=True,
        )
        with st.expander("Technical tilt values for this rebalance", expanded=False):
            st.markdown(
                f"- Raw pre-normalisation tilt: `{float(row['raw_tilt']):.6f}`\n"
                f"- Evidence-adjusted pre-normalisation tilt: `{float(row['confidence_adjusted_tilt']):.6f}`"
            )

    action_left, action_right, _ = st.columns([1.1, 1.1, 2.8])
    with action_left:
        if st.button("Back to signal", width="stretch"):
            store_signal_context(selected_sector, selected_date)
            set_pending_signal_context(selected_sector, selected_date)
            set_view("Signal")
            st.rerun()
    with action_right:
        if st.button("Compare funds", width="stretch"):
            set_view("Fund")
            st.rerun()

    render_curated_cases(startup_artifacts, attenuation_cases, ticker_day_sentiment)

    with st.expander("How this works", expanded=False):
        st.markdown(
            "\n".join(
                [
                    "- Sentiment: VADER compound score baseline, computed at build time only.",
                    "- Ticker-day: mean available headline compound scores for each represented company-day.",
                    "- Sector-day: equal-weight represented ticker-days; each represented company gets one voice.",
                    "- No news: missing, not neutral; no forward fill or backfill.",
                    "- Breadth: trailing 63-trading-day observed ticker-days divided by possible ticker-days.",
                    "- Agreement: one minus the trailing 21-trading-day mean cross-ticker dispersion.",
                    "- Confidence: Breadth x Agreement, bounded in [0, 1].",
                    "- Trading overlay: sentiment is lagged at least one trading day before use.",
                    "- Tilt strength: frozen 0.10 primary specification; no parameter was tuned using OOS returns.",
                ]
            )
        )
