"""Overview page: key indicators and risk summary for the selected plot."""

import streamlit as st

from utils.data_sources import load_plot_history, load_satellite_snapshot
from utils.model_interface import compute_plot_risk

plot_id = st.session_state.selected_plot_id
snap = load_satellite_snapshot(plot_id)
risk = compute_plot_risk(plot_id)

# KPI row: fixed grid of equal-width cards -> st.columns is the right tool.
col1, col2, col3, col4 = st.columns(4)
col1.metric("Overall risk", f"{risk.overall_risk:.0%}", border=True, height="stretch")
col2.metric("Soil moisture", f"{snap.soil_moisture_pct:.1f}%", border=True, height="stretch")
col3.metric("NDVI (vegetation)", f"{snap.ndvi:.2f}", border=True, height="stretch")
col4.metric("Water availability", f"{snap.water_availability_idx:.0%}", border=True, height="stretch")

st.markdown("### Risk breakdown")
r1, r2, r3 = st.columns(3)
r1.metric("Drought risk", f"{risk.drought_risk:.0%}")
r2.metric("Heat stress", f"{risk.heat_stress_risk:.0%}")
r3.metric("Nutrient depletion", f"{risk.nutrient_depletion_risk:.0%}")

st.markdown("### 12-month satellite history")
history = load_plot_history(plot_id)
h1, h2 = st.columns(2)
with h1:
    st.line_chart(history, x="date", y=["precipitation_mm", "soil_moisture_pct"])
with h2:
    st.line_chart(history, x="date", y=["temperature_c", "ndvi"])

st.caption("Simulated data for interface development; it will be replaced with real NASA sources (POWER, SMAP, MODIS).")
