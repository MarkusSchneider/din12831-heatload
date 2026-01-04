"""Tab für Debug-Informationen."""

import streamlit as st


def render_debug_tab() -> None:
    """Rendert den kompletten Debug-Tab."""
    st.header("Debug-Informationen")
    st.json(st.session_state.building.model_dump())
