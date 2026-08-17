"""Stateful journey navigation for SignalScope."""

from __future__ import annotations

import streamlit as st


JOURNEY_STAGES = ("Fund", "Risk", "Signal", "Evidence", "Decision", "Challenge")
DEFAULT_STAGE = "Fund"


def initialise_navigation() -> None:
    if st.session_state.get("view") not in JOURNEY_STAGES:
        st.session_state["view"] = DEFAULT_STAGE


def set_view(stage: str) -> None:
    if stage not in JOURNEY_STAGES:
        raise ValueError(f"Unknown journey stage: {stage}")
    st.session_state["view"] = stage
    st.session_state["_pending_view_sync"] = stage


def render_navigation() -> str:
    initialise_navigation()
    pending = st.session_state.pop("_pending_view_sync", None)
    if pending in JOURNEY_STAGES:
        st.session_state["view"] = pending
        st.session_state["journey_selector"] = pending

    current = st.session_state["view"]
    index = JOURNEY_STAGES.index(current)

    if hasattr(st, "segmented_control"):
        segmented_kwargs = {}
        if "journey_selector" not in st.session_state:
            segmented_kwargs["default"] = current
        selected = st.segmented_control(
            "Journey",
            JOURNEY_STAGES,
            selection_mode="single",
            key="journey_selector",
            label_visibility="collapsed",
            **segmented_kwargs,
        )
    else:
        radio_kwargs = {}
        if "journey_selector" not in st.session_state:
            radio_kwargs["index"] = index
        selected = st.radio(
            "Journey",
            JOURNEY_STAGES,
            horizontal=True,
            key="journey_selector",
            label_visibility="collapsed",
            **radio_kwargs,
        )

    if selected and selected != current:
        st.session_state["view"] = selected
        current = selected
    return current
