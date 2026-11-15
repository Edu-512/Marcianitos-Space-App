"""My Field: understand the active demo plot before comparing crop plans."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

from components.field_overview import crop_history, number, planting_event, soil_cards
from components.uncertainty_chart import seasonal_vulnerability_timeline
from utils.data_sources import load_plots, load_plot_history, load_satellite_snapshot, load_seasonal_windows
from utils.model_interface import compute_plot_risk
from utils.types import Plot, PlotRisk, SatelliteSnapshot

# Page-local clearance for the existing assistant. No shared navigation styles.
_LOCAL_CSS = """
@media(max-width:767px) {
 .st-key-my_field_content, .st-key-continue_home { max-width:calc(100% - 5.25rem); }
}
"""


def _load(loader: Callable[[str], Any], plot_id: str) -> Any:
    try:
        result = loader(plot_id)
        # Reject an accidentally mismatched provider response.
        return result if getattr(result, "plot_id", plot_id) == plot_id else None
    except Exception:
        return None


def _summary(plot: Plot) -> None:
    with st.container(border=True):
        st.markdown(":material/landscape: **Selected plot · Butler County, Iowa**")
        st.subheader(plot.name)
        grid = st.grid(2, min_column_width=200)
        with grid.cell():
            st.metric("Recorded area", f"{plot.area_hectares:.1f} ha")
        with grid.cell():
            st.markdown("**Crop pattern 2018–2025**")
            st.write(plot.current_crop or "Not available")
        st.caption(f"Plot ID: {plot.id} · Center: {plot.lat:.4f}, {plot.lon:.4f}")
        st.write(
            "Field outline: an area of 40 acres or more with the same 2018–2025 crop pattern in the USDA "
            "Cropland Data Layer. It is not a surveyed property line."
        )


def _indicators(snap: SatelliteSnapshot | None) -> None:
    st.markdown("**Satellite snapshot**")
    st.caption(
        f"Snapshot date: {snap.date if snap and snap.date else 'Not available'}. No plot-level satellite snapshot "
        "has been connected yet; county weather from NASA POWER is used in Compare Crops."
    )
    grid = st.grid(2, min_column_width=220)
    for label, field, decimals, unit, explanation in [
        ("Soil moisture", "soil_moisture_pct", 1, "%", "Water content in the soil; it does not describe the soil's water-storage capacity."),
        ("Vegetation vigor (NDVI)", "ndvi", 2, "", "A greenness indicator. It cannot diagnose crop health on its own."),
        ("Temperature", "temperature_c", 1, " °C", "A temperature indicator; the measurement type and resolution are not supplied."),
        ("Water availability", "water_availability_idx", 2, " / 1", "A demo index on a 0–1 scale, not a percentage of irrigation water available."),
    ]:
        with grid.cell():
            with st.container(border=True, height="stretch"):
                st.metric(label, number(getattr(snap, field, None), decimals, unit))
                st.caption(explanation)


def _risks(risk: PlotRisk | None) -> None:
    st.subheader("Things to consider", icon=":material/visibility:")
    st.caption(
        "Indices on a 0–1 scale from measured weather (NASA POWER, 2000–2025) and this plot's soil (SSURGO). "
        "They are not probabilities or confirmed field conditions."
    )
    if risk is None:
        st.info("Risk indicators could not be loaded. No risk level has been assumed.")
    grid = st.grid(2, min_column_width=220)
    for label, field, explanation in [
        ("Overall risk index", "overall_risk", "Weighted blend of the three indices below; no action threshold is applied here."),
        ("Drought index", "drought_risk", "How dry Augusts get in this county (26 measured years), times how little water this field's soil can hold. Sandy, low-water soils score higher."),
        ("Heat stress index", "heat_stress_risk", "From the average number of days above 35 °C (10 days = 1). County-wide: the same for every plot."),
        ("Nutrient depletion index", "nutrient_depletion_risk", "From this plot's soil organic matter (6% or more = 0). Not a substitute for a soil test."),
    ]:
        with grid.cell():
            with st.container(border=True, height="stretch"):
                st.metric(label, number(getattr(risk, field, None), 2, " / 1"))
                st.caption(explanation)
    st.caption("Plot-level erosion, waterlogging and planting-access assessments are not available. No extra risks have been inferred.")


def _technical(plot: Plot, snap: SatelliteSnapshot | None, risk: PlotRisk | None) -> None:
    with st.expander("View technical details and sources", key="my_field_technical"):
        st.write("Plot outlines, soils and plan results come from the Butler County delivery in the model/ folder.")
        rows = []
        for obj, fields, units, source, nature, period in [
            (snap, ["soil_moisture_pct", "ndvi", "temperature_c", "water_availability_idx", "precipitation_mm"],
             ["%", "index", "°C", "0–1 index", "mm"], "Not connected", "Not available", "Not supplied"),
            (risk, ["overall_risk", "drought_risk", "heat_stress_risk"], ["0–1 index"] * 3,
             "NASA POWER (MERRA-2), county point 42.73 N, 92.79 W", "Measured weather", "2000–2025, daily"),
            (risk, ["nutrient_depletion_risk"], ["0–1 index"],
             "USDA NRCS SSURGO IA023 v33", "Soil survey", "Survey of 2026-09-08"),
        ]:
            for field, unit in zip(fields, units):
                rows.append({"Variable": field, "Value": number(getattr(obj, field, None)), "Unit": unit,
                             "Source": source, "Nature": nature, "Period / resolution": period})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Technical variables, units and provenance for the active plot")
        st.caption(f"Plot center: {plot.lat:.5f}, {plot.lon:.5f} (latitude, longitude).")
        st.caption("Weather is a single point for the whole county, so heat does not differ between plots. Drought also uses each field's soil water, so it does.")


def _seasonal_and_history(plot_id: str) -> None:
    calendar = st.expander("Seasonal vulnerability calendar", on_change="rerun", key="my_field_calendar")
    if calendar.open:
        with calendar:
            windows = _load(load_seasonal_windows, plot_id)
            if windows:
                st.caption("Seasonal windows and severity labels come from the data provider; they are not confirmed events in this plot.")
                st.altair_chart(seasonal_vulnerability_timeline(windows), width="stretch", alt="Simulated seasonal windows for the active plot")
                months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                for w in windows:
                    st.write(f"{w.window_type} · {months[int(w.start_month)-1]}–{months[int(w.end_month)-1]} · Provider severity: {w.severity}")
                    st.caption(w.plain_explanation)
            else:
                st.info("No seasonal windows are available for this plot.")
    history_box = st.expander("12-month indicator history", on_change="rerun", key="my_field_history")
    if history_box.open:
        with history_box:
            history = _load(load_plot_history, plot_id)
            if isinstance(history, pd.DataFrame) and not history.empty and "date" in history:
                st.caption("Monthly indicators, not yearly crop records. Each variable keeps its own unit and scale.")
                for field,label,unit in [("precipitation_mm","Precipitation","mm"),("soil_moisture_pct","Soil moisture","%"),("temperature_c","Temperature","°C"),("ndvi","Vegetation vigor (NDVI)","index")]:
                    if field in history:
                        st.line_chart(history, x="date", y=field, x_label="Month", y_label=f"{label} ({unit})", width="stretch", height=180, alt=f"Simulated monthly {label.lower()} for the active plot")
                    else:
                        st.caption(f"{label}: not available.")
            else:
                st.info("No monthly indicator history is available for this plot.")


def _save_observation(plot_id: str) -> None:
    entry = {
        "Date": st.session_state[f"obs_date_{plot_id}"].isoformat(),
        "Rain (mm)": float(st.session_state[f"obs_rain_{plot_id}"]),
        "Probe Moisture (%)": float(st.session_state[f"obs_soil_{plot_id}"]),
        "Notes": st.session_state.get(f"obs_notes_{plot_id}", ""),
    }
    st.session_state.local_ground_notes.setdefault(plot_id, []).append(entry)
    st.toast("Field observation saved for this session.", icon=":material/check:")


def _ground_log(plot_id: str) -> None:
    with st.expander("Local ground log", key="my_field_ground_log"):
        st.caption("Your own notes, not validated measurements or model inputs. Saved only in this session, separately for each plot.")
        g1,g2 = st.columns(2)
        with g1:
            st.date_input("Date", key=f"obs_date_{plot_id}")
            st.number_input("Recorded rain (mm)", min_value=0.0, value=0.0, step=0.5, key=f"obs_rain_{plot_id}")
        with g2:
            st.number_input("Probe moisture (%)", min_value=0.0, max_value=100.0, value=20.0, step=0.5, key=f"obs_soil_{plot_id}")
        st.text_area("Field notes (pests, crusting, leaf color...)", key=f"obs_notes_{plot_id}")
        st.button("Save observation", key=f"obs_save_{plot_id}", on_click=_save_observation, args=(plot_id,))
        entries = st.session_state.local_ground_notes.get(plot_id, [])
        if entries:
            st.dataframe(pd.DataFrame(entries).iloc[::-1], hide_index=True, width="stretch", alt="User-entered observations for the active plot")
        else:
            st.caption("No local observations recorded for this plot yet.")


def run() -> None:
    plots = _load(lambda _: load_plots(), "") or []
    plot_id = st.session_state.get("selected_plot_id")
    plot = next((p for p in plots if p.id == plot_id), None)
    if plot is None:
        st.info("No valid plot is selected. Choose one in Explore Plots using the main navigation.")
        return
    plot_id = plot.id
    st.session_state.setdefault("local_ground_notes", {})
    snap = _load(load_satellite_snapshot, plot_id)
    risk = _load(compute_plot_risk, plot_id)
    st.html(f"<style>{_LOCAL_CSS}</style>")
    with st.container(key="my_field_content"):
        _summary(plot)
        st.subheader("What is your soil like?", icon=":material/layers:")
        st.caption("Soil properties have not been supplied for this plot. They cannot be inferred from moisture or vegetation indicators.")
        soil_cards()
        st.subheader("Crop history", icon=":material/history:")
        crop_history()
        _risks(risk)
        _indicators(snap)
        st.subheader("More about this field", icon=":material/info:")
        planting_event()
        _technical(plot, snap, risk)
        _seasonal_and_history(plot_id)
        _ground_log(plot_id)
    # The shared shell renders the single Compare My Options action and mobile clearance.
