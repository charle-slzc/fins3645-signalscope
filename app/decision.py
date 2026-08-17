"""Decision-page look-through allocation helpers and renderer."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import html
import math

import numpy as np
import pandas as pd
import streamlit as st

from app import charts
from app.data import StartupArtifacts, load_lazy_artifact_cached
from app.funds import (
    FundKey,
    available_funds,
    canonical_family,
    display_family,
    effective_holdings,
    format_percent,
    latest_exposure,
    latest_weights,
    validate_fund_key,
)
from app.navigation import set_view


MAX_DECISION_SLEEVES = 4
TOTAL_TOLERANCE = 1e-6
WEIGHT_SUM_TOLERANCE = 1e-8
POSITIVE_WEIGHT_TOLERANCE = 1e-10
DEFAULT_STARTING_FUND = FundKey("Combined", "Equal Weight")
DECISION_FUNDS_KEY = "decision_funds"
DECISION_ALLOCATIONS_KEY = "decision_allocations"


@dataclass(frozen=True)
class AllocationSleeve:
    family: str
    method: str
    allocation_pct: float

    @property
    def key(self) -> FundKey:
        return FundKey(self.family, self.method)

    @property
    def label(self) -> str:
        return self.key.label

    @property
    def capital_weight(self) -> float:
        return self.allocation_pct / 100.0


@dataclass(frozen=True)
class AllocationValidation:
    sleeves: tuple[AllocationSleeve, ...]
    total_pct: float
    valid: bool
    messages: tuple[str, ...]

    @property
    def remaining_pct(self) -> float:
        return max(0.0, 100.0 - self.total_pct)

    @property
    def overallocated_pct(self) -> float:
        return max(0.0, self.total_pct - 100.0)


@dataclass(frozen=True)
class SnapshotInfo:
    selected_dates: dict[str, str]
    aligned: bool

    @property
    def display_date(self) -> str:
        dates = sorted(set(self.selected_dates.values()))
        if len(dates) == 1:
            return dates[0]
        return ", ".join(dates)


@dataclass(frozen=True)
class StructuralSummary:
    sleeve_count: int
    asset_class_count: int
    underlying_count: int
    effective_underlying_holdings: float
    largest_asset: str
    largest_weight: float
    top5_share: float
    equity_exposure: float
    crypto_exposure: float
    snapshot_date: str


@dataclass(frozen=True)
class PairwiseOverlap:
    fund_a: str
    fund_b: str
    overlap: float


@dataclass(frozen=True)
class HoldingsDisplay:
    visible: pd.DataFrame
    remainder_count: int
    remainder_weight: float
    mode: str


def fund_option_labels(metrics: pd.DataFrame) -> list[str]:
    return [key.label for key in available_funds(metrics)]


def key_from_label(metrics: pd.DataFrame, label: str) -> FundKey:
    if " / " not in label:
        raise ValueError(f"Invalid fund label: {label}")
    family_label, method = label.split(" / ", 1)
    return validate_fund_key(metrics, canonical_family(family_label), method)


def label_for_key(key: FundKey) -> str:
    return key.label


def starting_fund_from_session(metrics: pd.DataFrame) -> FundKey:
    family = st.session_state.get("selected_fund_family")
    method = st.session_state.get("selected_fund_method")
    if family and method:
        try:
            return validate_fund_key(metrics, str(family), str(method))
        except (KeyError, ValueError):
            pass
    try:
        return validate_fund_key(metrics, DEFAULT_STARTING_FUND.family, DEFAULT_STARTING_FUND.method)
    except KeyError:
        funds = available_funds(metrics)
        if not funds:
            raise KeyError("No funds available for Decision allocation.")
        return funds[0]


def initialise_decision_state(metrics: pd.DataFrame) -> None:
    if DECISION_FUNDS_KEY in st.session_state and DECISION_ALLOCATIONS_KEY in st.session_state:
        return
    starting = starting_fund_from_session(metrics)
    st.session_state[DECISION_FUNDS_KEY] = [starting.label]
    st.session_state[DECISION_ALLOCATIONS_KEY] = [100.0]


def _coerce_parallel_state(metrics: pd.DataFrame) -> None:
    options = fund_option_labels(metrics)
    funds = list(st.session_state.get(DECISION_FUNDS_KEY, []))
    allocations = list(st.session_state.get(DECISION_ALLOCATIONS_KEY, []))
    if not funds:
        funds = [starting_fund_from_session(metrics).label]
    if len(allocations) < len(funds):
        allocations.extend([0.0] * (len(funds) - len(allocations)))
    funds = funds[:MAX_DECISION_SLEEVES]
    allocations = allocations[: len(funds)]
    funds = [fund if fund in options else options[0] for fund in funds]
    st.session_state[DECISION_FUNDS_KEY] = funds
    st.session_state[DECISION_ALLOCATIONS_KEY] = [float(value) for value in allocations]


def validate_allocation(
    metrics: pd.DataFrame,
    selected_labels: list[str],
    allocation_pcts: list[float],
) -> AllocationValidation:
    messages: list[str] = []
    sleeves: list[AllocationSleeve] = []
    if len(selected_labels) != len(allocation_pcts):
        messages.append("Fund sleeves and allocation values are out of sync.")
        return AllocationValidation(tuple(), 0.0, False, tuple(messages))
    if not selected_labels:
        messages.append("Select at least one fund sleeve.")
        return AllocationValidation(tuple(), 0.0, False, tuple(messages))
    if len(selected_labels) > MAX_DECISION_SLEEVES:
        messages.append(f"Select no more than {MAX_DECISION_SLEEVES} fund sleeves.")
    if len(set(selected_labels)) != len(selected_labels):
        messages.append("Each selected fund sleeve must be unique.")

    for label, allocation in zip(selected_labels, allocation_pcts):
        try:
            key = key_from_label(metrics, label)
        except (KeyError, ValueError) as exc:
            messages.append(str(exc))
            continue
        if not math.isfinite(float(allocation)):
            messages.append(f"{label} allocation must be finite.")
            continue
        if float(allocation) < 0:
            messages.append(f"{label} allocation cannot be negative.")
        if float(allocation) > 100:
            messages.append(f"{label} allocation cannot exceed 100%.")
        sleeves.append(
            AllocationSleeve(
                family=key.family,
                method=key.method,
                allocation_pct=float(allocation),
            )
        )

    total = float(sum(sleeve.allocation_pct for sleeve in sleeves))
    if total < 100.0 - TOTAL_TOLERANCE:
        messages.append(f"Allocation totals {total:.1f}%; assign the remaining {100.0 - total:.1f}%.")
    elif total > 100.0 + TOTAL_TOLERANCE:
        messages.append(f"Allocation totals {total:.1f}%; reduce by {total - 100.0:.1f}%.")
    valid = not messages and abs(total - 100.0) <= TOTAL_TOLERANCE
    return AllocationValidation(tuple(sleeves), total, valid, tuple(messages))


def latest_snapshot_info(fund_weights: pd.DataFrame, sleeves: tuple[AllocationSleeve, ...]) -> SnapshotInfo:
    dates: dict[str, str] = {}
    for sleeve in sleeves:
        latest = latest_weights(fund_weights, sleeve.key)
        weight_sum = float(latest["weight"].sum())
        if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(f"Latest saved weights for {sleeve.label} sum to {weight_sum:.8f}.")
        dates[sleeve.label] = pd.to_datetime(latest["date"].iloc[0]).date().isoformat()
    return SnapshotInfo(selected_dates=dates, aligned=len(set(dates.values())) <= 1)


def lookthrough_components(
    fund_weights: pd.DataFrame,
    sleeves: tuple[AllocationSleeve, ...],
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for sleeve in sleeves:
        latest = latest_weights(fund_weights, sleeve.key)
        weight_sum = float(latest["weight"].sum())
        if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(f"Latest saved weights for {sleeve.label} sum to {weight_sum:.8f}.")
        component = latest[["date", "asset", "asset_class", "weight"]].copy()
        component["fund_label"] = sleeve.label
        component["fund_family"] = sleeve.family
        component["method"] = sleeve.method
        component["capital_weight"] = sleeve.capital_weight
        component["sleeve_weight"] = component["weight"]
        component["lookthrough_weight"] = component["capital_weight"] * component["sleeve_weight"]
        rows.append(component)
    if not rows:
        raise ValueError("No selected sleeves for look-through calculation.")
    return pd.concat(rows, ignore_index=True)


def aggregate_lookthrough_holdings(components: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        components.groupby(["asset", "asset_class"], as_index=False)["lookthrough_weight"].sum()
        .sort_values(["lookthrough_weight", "asset"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return grouped[grouped["lookthrough_weight"] > POSITIVE_WEIGHT_TOLERANCE].reset_index(drop=True)


def aggregate_asset_classes(holdings: pd.DataFrame) -> pd.DataFrame:
    exposure = (
        holdings.groupby("asset_class", as_index=False)["lookthrough_weight"].sum()
        .sort_values("asset_class")
        .reset_index(drop=True)
    )
    exposure["asset_class_label"] = exposure["asset_class"].str.title()
    return exposure


def format_percent_one(value: float) -> str:
    return format_percent(value, 1)


def method_exposure(sleeves: tuple[AllocationSleeve, ...]) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "method": [sleeve.method for sleeve in sleeves],
            "capital_weight": [sleeve.capital_weight for sleeve in sleeves],
        }
    )
    return frame.groupby("method", as_index=False)["capital_weight"].sum().sort_values("method")


def is_broad_lookthrough(holdings: pd.DataFrame) -> bool:
    if holdings.empty:
        return False
    effective = effective_holdings(holdings.rename(columns={"lookthrough_weight": "weight"}))
    effective_share = effective / len(holdings)
    top_weight = float(holdings["lookthrough_weight"].max())
    return effective_share >= 0.75 and top_weight <= 0.12


def holdings_display(holdings: pd.DataFrame, top_n: int = 8) -> HoldingsDisplay:
    visible = holdings.head(top_n).copy()
    remainder = holdings.iloc[top_n:]
    return HoldingsDisplay(
        visible=visible,
        remainder_count=int(len(remainder)),
        remainder_weight=float(remainder["lookthrough_weight"].sum()) if not remainder.empty else 0.0,
        mode="broad" if is_broad_lookthrough(holdings) else "focused",
    )


def structural_summary(
    sleeves: tuple[AllocationSleeve, ...],
    holdings: pd.DataFrame,
    asset_classes: pd.DataFrame,
    snapshot: SnapshotInfo,
) -> StructuralSummary:
    if holdings.empty:
        raise ValueError("Look-through holdings are empty.")
    largest = holdings.iloc[0]
    exposure_lookup = asset_classes.set_index("asset_class")["lookthrough_weight"].to_dict()
    return StructuralSummary(
        sleeve_count=len(sleeves),
        asset_class_count=int(asset_classes["asset_class"].nunique()),
        underlying_count=int(len(holdings)),
        effective_underlying_holdings=effective_holdings(
            holdings.rename(columns={"lookthrough_weight": "weight"})
        ),
        largest_asset=str(largest["asset"]),
        largest_weight=float(largest["lookthrough_weight"]),
        top5_share=float(holdings.head(5)["lookthrough_weight"].sum()),
        equity_exposure=float(exposure_lookup.get("equity", 0.0)),
        crypto_exposure=float(exposure_lookup.get("crypto", 0.0)),
        snapshot_date=snapshot.display_date,
    )


def pairwise_overlaps(
    fund_weights: pd.DataFrame,
    sleeves: tuple[AllocationSleeve, ...],
) -> list[PairwiseOverlap]:
    overlaps: list[PairwiseOverlap] = []
    for left, right in combinations(sleeves, 2):
        left_weights = latest_weights(fund_weights, left.key).set_index("asset")["weight"]
        right_weights = latest_weights(fund_weights, right.key).set_index("asset")["weight"]
        assets = left_weights.index.union(right_weights.index)
        value = float(np.minimum(left_weights.reindex(assets, fill_value=0.0), right_weights.reindex(assets, fill_value=0.0)).sum())
        overlaps.append(PairwiseOverlap(left.label, right.label, value))
    return overlaps


def sleeve_frame(sleeves: tuple[AllocationSleeve, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fund_label": [sleeve.label for sleeve in sleeves],
            "family_label": [display_family(sleeve.family) for sleeve in sleeves],
            "method": [sleeve.method for sleeve in sleeves],
            "capital_weight": [sleeve.capital_weight for sleeve in sleeves],
        }
    )


def overlap_frame(overlaps: list[PairwiseOverlap]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pair": [f"{item.fund_a} | {item.fund_b}" for item in overlaps],
            "fund_a": [item.fund_a for item in overlaps],
            "fund_b": [item.fund_b for item in overlaps],
            "overlap": [item.overlap for item in overlaps],
        }
    ).sort_values("overlap", ascending=False)


def decision_narrative(summary: StructuralSummary, overlaps: list[PairwiseOverlap]) -> str:
    verb = "resolves" if summary.sleeve_count == 1 else "resolve"
    sentence = (
        f"Your {summary.sleeve_count} fund sleeve"
        f"{'' if summary.sleeve_count == 1 else 's'} {verb} to "
        f"{format_percent(summary.equity_exposure)} equity and "
        f"{format_percent(summary.crypto_exposure)} crypto at the latest saved snapshot. "
        f"The largest underlying position is {summary.largest_asset} at "
        f"{format_percent(summary.largest_weight)}, with "
        f"{summary.effective_underlying_holdings:.1f} effective underlying holdings."
    )
    if overlaps:
        strongest = max(overlaps, key=lambda item: item.overlap)
        sentence += (
            f" The most overlapping selected pair shares "
            f"{format_percent(strongest.overlap, 0)} of its latest saved fund-weight profiles."
        )
    return sentence


def _safe_width(value: float) -> float:
    if value <= 0:
        return 0.0
    return max(4.0, min(100.0, value * 100.0))


def sleeve_strip_html(sleeves: tuple[AllocationSleeve, ...]) -> str:
    segments = []
    for index, sleeve in enumerate(sleeves):
        segments.append(
            f"""
<div class="ss-decision-segment ss-decision-cat-{index % 4}" style="width: {_safe_width(sleeve.capital_weight):.3f}%;">
  <span>{html.escape(sleeve.label)}</span>
  <strong>{format_percent_one(sleeve.capital_weight)}</strong>
</div>
"""
        )
    return f'<div class="ss-decision-strip">{"".join(segments)}</div>'


def asset_class_strip_html(asset_classes: pd.DataFrame) -> str:
    ordered = asset_classes.copy()
    ordered["order"] = ordered["asset_class"].map({"equity": 0, "crypto": 1}).fillna(2)
    segments = []
    for row in ordered.sort_values(["order", "asset_class"]).itertuples(index=False):
        css_class = "ss-asset-equity" if row.asset_class == "equity" else "ss-asset-crypto"
        segments.append(
            f"""
<div class="ss-decision-segment {css_class}" style="width: {_safe_width(float(row.lookthrough_weight)):.3f}%;">
  <span>{html.escape(str(row.asset_class_label))}</span>
  <strong>{format_percent_one(float(row.lookthrough_weight))}</strong>
</div>
"""
        )
    return f'<div class="ss-decision-strip">{"".join(segments)}</div>'


def format_snapshot_date(date_text: str) -> str:
    date = pd.Timestamp(date_text)
    return f"{date.day} {date.strftime('%b %Y')}"


def _allocated_status(validation: AllocationValidation) -> str:
    if validation.overallocated_pct > 0:
        return f"Allocated: {validation.total_pct:.1f}% | Overallocated: {validation.overallocated_pct:.1f}%"
    return f"Allocated: {validation.total_pct:.1f}% | Remaining: {validation.remaining_pct:.1f}%"


def _normalise_decision_allocations() -> None:
    allocations = [float(value) for value in st.session_state.get(DECISION_ALLOCATIONS_KEY, [])]
    total = sum(allocations)
    if total <= 0:
        return
    st.session_state[DECISION_ALLOCATIONS_KEY] = [value / total * 100.0 for value in allocations]


def _available_label_options(all_options: list[str], current: str, selected: list[str]) -> list[str]:
    excluded = set(selected)
    excluded.discard(current)
    return [option for option in all_options if option not in excluded]


def render_allocation_builder(metrics: pd.DataFrame) -> AllocationValidation:
    initialise_decision_state(metrics)
    _coerce_parallel_state(metrics)
    options = fund_option_labels(metrics)
    funds_state = list(st.session_state[DECISION_FUNDS_KEY])
    allocations_state = list(st.session_state[DECISION_ALLOCATIONS_KEY])

    st.markdown('<p class="ss-section-label">Allocation builder</p>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ss-disclosure">User-defined structural allocation. Custom mixes are structural look-throughs of saved fund weights, not new historical backtests.</div>',
        unsafe_allow_html=True,
    )

    for index, (label, allocation) in enumerate(zip(funds_state, allocations_state)):
        row_cols = st.columns([1.45, 0.65, 0.42])
        with row_cols[0]:
            label_options = _available_label_options(options, label, funds_state)
            if label not in label_options:
                label_options = [label, *label_options]
            selected = st.selectbox(
                f"Sleeve {index + 1}",
                label_options,
                index=label_options.index(label),
                key=f"decision_sleeve_{index}",
            )
            funds_state[index] = selected
        with row_cols[1]:
            value = st.number_input(
                "Allocation %",
                min_value=0.0,
                max_value=100.0,
                value=float(allocation),
                step=5.0,
                format="%.1f",
                key=f"decision_allocation_{index}",
            )
            allocations_state[index] = float(value)
        with row_cols[2]:
            st.write("")
            if len(funds_state) > 1 and st.button(f"Remove sleeve {index + 1}", key=f"remove_decision_sleeve_{index}"):
                funds_state.pop(index)
                allocations_state.pop(index)
                st.session_state[DECISION_FUNDS_KEY] = funds_state
                st.session_state[DECISION_ALLOCATIONS_KEY] = allocations_state
                st.rerun()

    st.session_state[DECISION_FUNDS_KEY] = funds_state
    st.session_state[DECISION_ALLOCATIONS_KEY] = allocations_state
    validation = validate_allocation(metrics, funds_state, allocations_state)

    action_cols = st.columns([1.0, 1.0, 3.0])
    with action_cols[0]:
        if len(funds_state) < MAX_DECISION_SLEEVES and st.button("Add fund sleeve", width="stretch"):
            unused = [option for option in options if option not in funds_state]
            if unused:
                funds_state.append(unused[0])
                allocations_state.append(0.0)
                st.session_state[DECISION_FUNDS_KEY] = funds_state
                st.session_state[DECISION_ALLOCATIONS_KEY] = allocations_state
                st.rerun()
    with action_cols[1]:
        if validation.valid:
            st.caption("Allocation already totals 100.0%.")
        elif abs(validation.total_pct - 100.0) > TOTAL_TOLERANCE:
            if st.button("Normalise to 100%", width="stretch"):
                _normalise_decision_allocations()
                st.rerun()

    st.markdown(
        f'<div class="ss-decision-status">{"Valid total" if validation.valid else "Allocation not active"}<br><strong>{html.escape(_allocated_status(validation))}</strong></div>',
        unsafe_allow_html=True,
    )
    if validation.messages:
        for message in validation.messages:
            st.markdown(f'<div class="ss-warning">{html.escape(message)}</div>', unsafe_allow_html=True)
    return validation


def _render_structural_summary(summary: StructuralSummary) -> None:
    st.markdown(
        f"""
<div class="ss-structure-summary">
  <div>
    <span>Fund sleeves</span>
    <strong>{summary.sleeve_count}</strong>
  </div>
  <div>
    <span>Underlying securities</span>
    <strong>{summary.underlying_count}</strong>
  </div>
  <div>
    <span>Effective holdings</span>
    <strong>{summary.effective_underlying_holdings:.1f}</strong>
  </div>
  <div>
    <span>Largest position</span>
    <strong>{html.escape(summary.largest_asset)} {format_percent(summary.largest_weight)}</strong>
  </div>
  <div>
    <span>Top-5 share</span>
    <strong>{format_percent(summary.top5_share)}</strong>
  </div>
  <div>
    <span>Equity / Crypto split</span>
    <strong>{format_percent(summary.equity_exposure)} / {format_percent(summary.crypto_exposure)}</strong>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_overlap(overlaps: list[PairwiseOverlap]) -> None:
    if not overlaps:
        return
    st.markdown('<p class="ss-section-label">Holdings overlap</p>', unsafe_allow_html=True)
    strongest = max(overlaps, key=lambda item: item.overlap)
    weakest = min(overlaps, key=lambda item: item.overlap)
    if len(overlaps) == 1:
        st.markdown(
            f"""
<div class="ss-overlap-insight">
  <strong>2 fund sleeves, but {format_percent(strongest.overlap)} of their latest weight profiles overlap.</strong>
  This is structural latest-holdings overlap, not correlation or a forecast.
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
<div class="ss-overlap-insight">
  <strong>Most overlapping pair:</strong> {html.escape(strongest.fund_a)} and {html.escape(strongest.fund_b)}
  share {format_percent(strongest.overlap, 0)} of their latest saved fund-weight profiles.<br>
  <strong>Least overlapping pair:</strong> {html.escape(weakest.fund_a)} and {html.escape(weakest.fund_b)}
  share {format_percent(weakest.overlap, 0)}.
</div>
""",
            unsafe_allow_html=True,
        )
    with st.expander("Pairwise overlap detail", expanded=False):
        st.vega_lite_chart(overlap_frame(overlaps), charts.decision_overlap_spec(), width="stretch")
        st.caption(
            "Overlap is the share of two latest saved fund-weight profiles held in common. It is not return correlation, risk correlation, or a forecast."
        )


def _render_evidence_policy(project_root: Path | None = None) -> None:
    st.markdown('<p class="ss-section-label">Evidence policy</p>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="ss-disclosure">
Base construction remains primary. SignalScope does not rebuild this custom mix from headline sentiment; news evidence acts only as a tested control layer.
</div>
""",
        unsafe_allow_html=True,
    )
    with st.expander("Methodological boundary", expanded=False):
        st.markdown(
            "The frozen Confidence Lens was tested only as a control on the equity sentiment overlay. "
            "Decision does not apply sentiment attenuation to the user-defined fund mix."
        )
    if st.session_state.get("evidence_case") == "attenuation":
        try:
            root_arg = str(project_root) if project_root else None
            cases = load_lazy_artifact_cached("confidence_lens_attenuation_cases", root_arg)
            row = cases[
                (cases["date"] == "2021-11-01")
                & (cases["sector"] == "RealEstate")
                & (cases["base_method"] == "Minimum Variance")
            ].iloc[0]
            st.caption(
                "Active Evidence case: RealEstate / 1 Nov 2021. "
                f"Raw sector change {float(row['standard_change']) * 100:+.2f}pp; "
                f"evidence-adjusted {float(row['confidence_change']) * 100:+.2f}pp."
            )
        except Exception:
            pass
    if st.button("Inspect evidence", width="stretch"):
        set_view("Evidence")
        st.rerun()


def render_decision_page(artifacts: StartupArtifacts, project_root: Path | None = None) -> None:
    metrics = artifacts.frames["performance_metrics"]
    weights = artifacts.frames["fund_weights"]
    exposure = artifacts.frames["asset_class_exposure"]

    st.markdown(
        """
<p class="ss-kicker">Decision</p>
<h2 class="ss-stage-title">What does this allocation actually become?</h2>
<p class="ss-stage-copy">Combine fund sleeves, then look through the labels to the underlying exposure.</p>
""",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 1.25])
    snapshot: SnapshotInfo | None = None
    holdings: pd.DataFrame | None = None
    asset_classes: pd.DataFrame | None = None
    summary: StructuralSummary | None = None
    overlaps: list[PairwiseOverlap] = []
    with left:
        validation = render_allocation_builder(metrics)
    with right:
        if not validation.valid:
            st.markdown(
                """
<div class="ss-panel">
  <h3>Look-through withheld</h3>
  <p>Set the selected sleeve allocations to exactly 100% to activate the structural snapshot. SignalScope does not silently normalise user allocations.</p>
  <div class="ss-control-bar"></div>
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            try:
                snapshot = latest_snapshot_info(weights, validation.sleeves)
                components = lookthrough_components(weights, validation.sleeves)
                holdings = aggregate_lookthrough_holdings(components)
                asset_classes = aggregate_asset_classes(holdings)
                summary = structural_summary(validation.sleeves, holdings, asset_classes, snapshot)
                overlaps = pairwise_overlaps(weights, validation.sleeves)
            except (KeyError, ValueError) as exc:
                st.markdown(f'<div class="ss-warning">{html.escape(str(exc))}</div>', unsafe_allow_html=True)

            if summary is not None and snapshot is not None:
                st.markdown('<p class="ss-section-label">Structural summary</p>', unsafe_allow_html=True)
                _render_structural_summary(summary)
                st.markdown(
                    f'<div class="ss-decision-narrative">{html.escape(decision_narrative(summary, overlaps))}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    """
<div class="ss-thesis-bridge">
  <strong>FUND COUNT != UNDERLYING DIVERSIFICATION</strong>
  <span>SignalScope looks through each sleeve to the latest saved underlying holdings.</span>
</div>
""",
                    unsafe_allow_html=True,
                )
                if snapshot.aligned:
                    st.caption(f"Latest saved holdings snapshot: {format_snapshot_date(summary.snapshot_date)}")
                else:
                    st.caption(f"Selected sleeves use different saved holdings snapshots: {snapshot.display_date}.")

    if validation.valid and holdings is not None and asset_classes is not None:
        st.markdown('<p class="ss-section-label">Allocation anatomy</p>', unsafe_allow_html=True)
        st.markdown(
            """
<div class="ss-anatomy-flow">
  <div><strong>FUND WRAPPERS</strong><span>capital the user assigns</span></div>
  <i>LOOK THROUGH</i>
  <div><strong>ASSET CLASSES</strong><span>economic sleeve exposure</span></div>
  <i>LOOK THROUGH</i>
  <div><strong>UNDERLYING HOLDINGS</strong><span>actual saved securities</span></div>
</div>
""",
            unsafe_allow_html=True,
        )
        anatomy_left, anatomy_right = st.columns([0.95, 1.05])
        with anatomy_left:
            st.markdown(sleeve_strip_html(validation.sleeves), unsafe_allow_html=True)
            st.caption("Capital allocated to selected fund wrappers.")
            st.markdown(asset_class_strip_html(asset_classes), unsafe_allow_html=True)
            st.caption("Look-through asset-class exposure from saved underlying weights.")
        with anatomy_right:
            display = holdings_display(holdings)
            st.vega_lite_chart(display.visible, charts.decision_holdings_spec(), width="stretch")
            if display.remainder_count:
                st.markdown(
                    f"""
<div class="ss-remainder-note">
  <strong>{display.remainder_count} additional holdings</strong>
  <span>{format_percent_one(display.remainder_weight)} combined. This is a compact remainder, not one security.</span>
</div>
""",
                    unsafe_allow_html=True,
                )
            if display.mode == "broad":
                st.caption("Representative holdings shown first because this is a broad look-through profile.")
            else:
                st.caption("Largest underlying holdings shown first. Duplicate assets across sleeves are combined.")

        _render_overlap(overlaps)

        if len({sleeve.method for sleeve in validation.sleeves}) > 1:
            st.markdown('<p class="ss-section-label">Construction method exposure</p>', unsafe_allow_html=True)
            st.vega_lite_chart(method_exposure(validation.sleeves), charts.decision_method_exposure_spec(), width="stretch")
            st.caption("Method exposure describes wrapper construction, not independent economic diversification.")

        if len(validation.sleeves) > 1:
            starting = starting_fund_from_session(metrics)
            try:
                start_latest = latest_weights(weights, starting)
                start_holdings = aggregate_lookthrough_holdings(
                    lookthrough_components(
                        weights,
                        (AllocationSleeve(starting.family, starting.method, 100.0),),
                    )
                )
                start_classes = latest_exposure(exposure, starting)
                st.markdown('<p class="ss-section-label">Against starting fund context</p>', unsafe_allow_html=True)
                st.caption(
                    f"Starting context {starting.label}: "
                    f"{len(start_holdings)} represented holdings, "
                    f"{effective_holdings(start_latest):.1f} effective holdings, "
                    f"largest {start_holdings.iloc[0]['asset']} {format_percent(float(start_holdings.iloc[0]['lookthrough_weight']))}, "
                    f"{format_percent(float(start_classes.loc[start_classes['asset_class'].eq('equity'), 'exposure'].sum()))} equity / "
                    f"{format_percent(float(start_classes.loc[start_classes['asset_class'].eq('crypto'), 'exposure'].sum()))} crypto."
                )
            except (KeyError, ValueError, IndexError):
                pass

    _render_evidence_policy(project_root)

    nav_cols = st.columns([1.0, 1.0, 1.15, 2.0])
    with nav_cols[0]:
        if st.button("Compare funds", width="stretch", key="decision_to_fund"):
            set_view("Fund")
            st.rerun()
    with nav_cols[1]:
        if st.button("Open fact sheet", width="stretch", key="decision_to_risk"):
            set_view("Risk")
            st.rerun()
    with nav_cols[2]:
        if st.button("Challenge the model", type="primary", width="stretch"):
            set_view("Challenge")
            st.rerun()
