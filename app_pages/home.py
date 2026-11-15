"""Field Pulse: plain-language KPIs, seasonal calendar, and local ground log."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.uncertainty_chart import seasonal_vulnerability_timeline
from utils.data_sources import load_plot_history, load_satellite_snapshot, load_seasonal_windows
from utils.model_interface import compute_plot_risk
from utils.types import SeasonalWindow

_MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _risk_caption(value: float) -> str:
    if value >= 0.6:
        return "High Risk: Prioritize actions this week."
    if value >= 0.4:
        return "Moderate Risk: Monitor and prepare adjustments."
    return "Low Risk: Stable field conditions."


def _moisture_caption(value: float) -> str:
    if value < 15:
        return "Dry Soil: Low available water for roots."
    if value <= 25:
        return "Moisture in normal range for the season."
    return "Good moisture level for roots."


def _ndvi_caption(value: float) -> str:
    if value < 0.3:
        return "Low Vigor: The crop is experiencing stress."
    if value <= 0.6:
        return "Moderate Vigor: Stable vegetation."
    return "Good Vigor: Plant is green and active."


def _water_caption(value: float) -> str:
    if value < 0.3:
        return "Scarce local water: Plan irrigation carefully."
    if value <= 0.6:
        return "Moderate water availability."
    return "Good water availability for the season."


def _window_span(window: SeasonalWindow) -> str:
    start = _MONTHS_EN[int(window.start_month) - 1]
    end = _MONTHS_EN[int(window.end_month) - 1]
    return f"{start}-{end}"


def _save_observation(plot_id: str) -> None:
    """Append the current ground-observation widgets to the session log."""
    entry = {
        "Date": st.session_state[f"obs_date_{plot_id}"].isoformat(),
        "Rain (mm)": float(st.session_state[f"obs_rain_{plot_id}"]),
        "Probe Moisture (%)": float(st.session_state[f"obs_soil_{plot_id}"]),
        "Notes": st.session_state.get(f"obs_notes_{plot_id}", ""),
    }
    st.session_state.local_ground_notes.setdefault(plot_id, []).append(entry)
    st.toast("Field observation saved successfully.", icon="check")


def run() -> None:
    """Render KPIs, the seasonal calendar, and the local observation log."""
    plot_id = st.session_state.selected_plot_id
    snap = load_satellite_snapshot(plot_id)
    risk = compute_plot_risk(plot_id)

    # --- 1. Top KPI cards with plain-English status captions -------------------
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Overall Risk", f"{risk.overall_risk:.0%}", border=True, height="stretch")
    k1.caption(_risk_caption(risk.overall_risk))
    k2.metric("Soil Moisture", f"{snap.soil_moisture_pct:.1f}%", border=True, height="stretch")
    k2.caption(_moisture_caption(snap.soil_moisture_pct))
    k3.metric("Vegetation Vigor (NDVI)", f"{snap.ndvi:.2f}", border=True, height="stretch")
    k3.caption(_ndvi_caption(snap.ndvi))
    k4.metric("Water Availability", f"{snap.water_availability_idx:.0%}", border=True, height="stretch")
    k4.caption(_water_caption(snap.water_availability_idx))

    # --- 2. Risk breakdown + plain-language diagnostic callout -----------------
    st.subheader("Risk Signals")
    b1, b2, b3 = st.columns(3)
    b1.metric("Drought Risk", f"{risk.drought_risk:.0%}")
    b2.metric("Heat Stress", f"{risk.heat_stress_risk:.0%}")
    b3.metric("Nutrient Depletion", f"{risk.nutrient_depletion_risk:.0%}")

    signals = {
        "Soil moisture deficit (Low SMAP)": risk.drought_risk,
        "Heat stress (High Temp, ECOSTRESS/POWER)": risk.heat_stress_risk,
        "Nutrient loss and low vigor (Low NDVI)": risk.nutrient_depletion_risk,
    }
    dominant = max(signals, key=signals.get)
    
    if risk.overall_risk >= 0.6:
        st.warning(f"Dominant Signal: **{dominant}**. Act before the next critical window.")
    elif risk.overall_risk >= 0.4:
        st.info(f"Dominant Signal: **{dominant}**. Prepare adjustments and review your Action Plan.")
    else:
        st.success("No critical signals: Maintain current practices and keep monitoring.")

    # --- 3. Seasonal vulnerability & bare-soil timeline -------------------------
    st.subheader("Seasonal Vulnerability Calendar")
    windows = load_seasonal_windows(plot_id)
    st.altair_chart(
        seasonal_vulnerability_timeline(windows),
        use_container_width=True,
    )
    for w in windows:
        st.markdown(f"- **{w.window_type}** ({_window_span(w)}, Severity {w.severity}): {w.plain_explanation}")

    # --- 4. 12-month dual satellite history -------------------------------------
    st.subheader("12-Month Satellite History")
    history = load_plot_history(plot_id)
    h1, h2 = st.columns(2)
    with h1:
        st.caption("Precipitation & Soil Moisture")
        st.line_chart(history, x="date", y=["precipitation_mm", "soil_moisture_pct"])
    with h2:
        st.caption("Temperature & Vegetation (NDVI)")
        st.line_chart(history, x="date", y=["temperature_c", "ndvi"])

    # --- 5. Local ground observation log (human-in-the-loop) --------------------
    st.subheader("Local Ground Log")
    with st.expander("Add New Field Observation", expanded=False):
        st.caption(
            "Log what you see in the field: Local probing confirms or corrects "
            "what the satellite pixel averages."
        )
        g1, g2, g3 = st.columns([1.4, 1.4, 1.6])
        with g1:
            st.date_input("Date", key=f"obs_date_{plot_id}")
        with g2:
            st.number_input(
                "Recorded Rain (mm)", min_value=0.0, value=0.0, step=0.5, key=f"obs_rain_{plot_id}"
            )
        with g3:
            st.number_input(
                "Probe Moisture (%)", min_value=0.0, value=20.0, step=0.5, key=f"obs_soil_{plot_id}"
            )
        st.text_area("Field Notes (pests, crusting, leaf color...)", key=f"obs_notes_{plot_id}")

        if st.button("Save Observation", key=f"obs_save_{plot_id}", type="primary"):
            _save_observation(plot_id)

    entries: list[dict] = st.session_state.local_ground_notes.get(plot_id, [])
    if entries:
        # Create a dataframe and reverse it so the newest entries are at the top
        df = pd.DataFrame(entries).iloc[::-1]
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.caption("No local observations recorded for this plot yet.")

    st.divider()
    st.caption(
        "Simulated data for interface development; will be replaced with real NASA sources (POWER, SMAP, MODIS)."
    )