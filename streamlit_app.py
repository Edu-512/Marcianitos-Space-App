"""Field Shift — adapting farms with NASA data.

Entry point for the multipage app: shared state, sidebar controls and
navigation. Page content lives in ``app_pages/``; business logic and data
access live in ``utils/`` (see README.md for the contract with the model team).
"""

import streamlit as st

from utils.data_sources import load_plots

st.set_page_config(
    page_title="Field Shift — Adapting farms with NASA data",
    page_icon=":material/agriculture:",
    layout="wide",
)

# --- Shared state (single source of truth, initialized once per session) ---
if "plots" not in st.session_state:
    st.session_state.plots = load_plots()
if "selected_plot_id" not in st.session_state:
    st.session_state.selected_plot_id = st.session_state.plots[0].id

with st.sidebar:
    plot_names = {p.id: p.name for p in st.session_state.plots}
    selected_name = st.selectbox(
        "Selected plot",
        list(plot_names.values()),
        index=list(plot_names).index(st.session_state.selected_plot_id),
        key="selected_plot_name",
    )
    st.session_state.selected_plot_id = next(
        pid for pid, name in plot_names.items() if name == selected_name
    )

page = st.navigation(
    [
        st.Page(
            "app_pages/home.py",
            title="Overview",
            icon=":material/dashboard:",
            help=(
                "Key indicators for the selected plot: overall risk, soil "
                "moisture, vegetation health and the 12-month satellite history."
            ),
        ),
        st.Page(
            "app_pages/map_view.py",
            title="Map",
            icon=":material/map:",
            help=(
                "Interactive map of all plots with satellite layers. Choose "
                "which variable to visualize and inspect each parcel."
            ),
        ),
        st.Page(
            "app_pages/rotations.py",
            title="Rotations",
            icon=":material/repeat:",
            help=(
                "Compare crop rotation scenarios side by side: expected yield, "
                "water use, nutrient loss and cost, with uncertainty bands."
            ),
        ),
        st.Page(
            "app_pages/recommendations.py",
            title="Recommendations",
            icon=":material/lightbulb:",
            help=(
                "Fertilizer and agronomic practice recommendations driven by the "
                "detected anomalies, with expected impact and uncertainty."
            ),
        ),
    ]
)

# Titles are handled here; pages must not call st.title again.
st.title(page.title, icon=page.icon)
page.run()
