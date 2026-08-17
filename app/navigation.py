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


def render_navigation() -> str:
    initialise_navigation()
    current = st.session_state["view"]
    index = JOURNEY_STAGES.index(current)

    if hasattr(st, "segmented_control"):
        selected = st.segmented_control(
            "Journey",
            JOURNEY_STAGES,
            selection_mode="single",
            default=current,
            key="journey_selector",
            label_visibility="collapsed",
        )
    else:
        selected = st.radio(
            "Journey",
            JOURNEY_STAGES,
            index=index,
            horizontal=True,
            key="journey_selector",
            label_visibility="collapsed",
        )

    if selected and selected != current:
        st.session_state["view"] = selected
        current = selected
    return current

