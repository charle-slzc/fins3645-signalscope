"""SignalScope Streamlit entrypoint.

Run locally:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.components import (  # noqa: E402
    install_design_system,
    render_active_stage,
    render_artifact_error,
)
from app.data import ArtifactValidationError, load_startup_artifacts_cached  # noqa: E402
from app.navigation import render_navigation  # noqa: E402


def main() -> None:
    st.set_page_config(
        page_title="SignalScope",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    install_design_system()

    try:
        artifacts = load_startup_artifacts_cached(str(PROJECT_ROOT))
    except ArtifactValidationError as exc:
        render_artifact_error(exc)
        st.stop()

    stage = render_navigation()
    render_active_stage(stage, artifacts)


if __name__ == "__main__":
    main()
