"""Field Pulse: plain-language KPIs, seasonal calendar and local ground log."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.uncertainty_chart import seasonal_vulnerability_timeline
from utils.data_sources import load_plot_history, load_satellite_snapshot, load_seasonal_windows
from utils.model_interface import compute_plot_risk
from utils.types import SeasonalWindow

_MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _risk_caption(value: float) -> str:
    if value >= 0.6:
        return "Riesgo alto: prioriza acciones esta semana."
    if value >= 0.4:
        return "Riesgo moderado: vigila y prepara ajustes."
    return "Riesgo bajo: condiciones estables en el lote."


def _moisture_caption(value: float) -> str:
    if value < 15:
        return "Suelo seco: poca agua disponible para las raíces."
    if value <= 25:
        return "Humedad en rango normal para la temporada."
    return "Buen nivel de humedad para las raíces."


def _ndvi_caption(value: float) -> str:
    if value < 0.3:
        return "Vigor vegetal bajo: el cultivo está sufriendo estrés."
    if value <= 0.6:
        return "Vigor moderado: vegetación estable."
    return "Buen vigor: la planta está verde y activa."


def _water_caption(value: float) -> str:
    if value < 0.3:
        return "Agua escasa en la zona: planifica el riego con cuidado."
    if value <= 0.6:
        return "Disponibilidad de agua moderada."
    return "Buena disponibilidad de agua para la temporada."


def _window_span(window: SeasonalWindow) -> str:
    start = _MONTHS_ES[int(window.start_month) - 1]
    end = _MONTHS_ES[int(window.end_month) - 1]
    return f"{start}–{end}"


def _save_observation(plot_id: str) -> None:
    """Append the current ground-observation widgets to the session log."""
    entry = {
        "fecha": st.session_state[f"obs_date_{plot_id}"].isoformat(),
        "lluvia_mm": float(st.session_state[f"obs_rain_{plot_id}"]),
        "humedad_sonda_pct": float(st.session_state[f"obs_soil_{plot_id}"]),
        "notas": st.session_state.get(f"obs_notes_{plot_id}", ""),
    }
    st.session_state.local_ground_notes.setdefault(plot_id, []).append(entry)


def run() -> None:
    """Render KPIs, the seasonal calendar and the local observation log."""
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
    st.markdown("### Señales de riesgo")
    b1, b2, b3 = st.columns(3)
    b1.metric("Drought Risk", f"{risk.drought_risk:.0%}")
    b2.metric("Heat Stress", f"{risk.heat_stress_risk:.0%}")
    b3.metric("Nutrient Depletion", f"{risk.nutrient_depletion_risk:.0%}")

    signals = {
        "Déficit de humedad en el suelo (SMAP bajo)": risk.drought_risk,
        "Estrés por calor (temperatura alta, ECOSTRESS/POWER)": risk.heat_stress_risk,
        "Pérdida de nutrientes y vigor bajo (NDVI bajo)": risk.nutrient_depletion_risk,
    }
    dominant = max(signals, key=signals.get)
    if risk.overall_risk >= 0.6:
        st.warning(f"Señal dominante: **{dominant}**. Actúa antes de la próxima ventana crítica.")
    elif risk.overall_risk >= 0.4:
        st.info(f"Señal dominante: **{dominant}**. Prepara ajustes y revisa el plan de acción.")
    else:
        st.success("Sin señales críticas: mantén las prácticas actuales y sigue monitoreando.")

    # --- 3. Seasonal vulnerability & bare-soil timeline -------------------------
    st.markdown("### Calendario estacional de vulnerabilidades")
    windows = load_seasonal_windows(plot_id)
    st.altair_chart(
        seasonal_vulnerability_timeline(windows),
        alt="Timeline of bare-soil and climate-hazard windows across the year",
    )
    for w in windows:
        st.markdown(f"- **{w.window_type}** ({_window_span(w)}, severidad {w.severity}): {w.plain_explanation}")

    # --- 4. 12-month dual satellite history -------------------------------------
    st.markdown("### Historial satelital de 12 meses")
    history = load_plot_history(plot_id)
    h1, h2 = st.columns(2)
    with h1:
        st.line_chart(history, x="date", y=["precipitation_mm", "soil_moisture_pct"])
    with h2:
        st.line_chart(history, x="date", y=["temperature_c", "ndvi"])

    # --- 5. Local ground observation log (human-in-the-loop) --------------------
    with st.expander("Log Local Ground Observation"):
        st.caption(
            "Registra lo que ves en el campo: la sonda local confirma o corrige "
            "lo que el píxel satelital promedia."
        )
        g1, g2, g3 = st.columns([1.4, 1.4, 1.6])
        with g1:
            obs_date = st.date_input("Fecha", key=f"obs_date_{plot_id}")
        with g2:
            obs_rain = st.number_input(
                "Lluvia registrada (mm)", min_value=0.0, value=0.0, step=0.5, key=f"obs_rain_{plot_id}"
            )
        with g3:
            obs_soil = st.number_input(
                "Humedad con sonda (%)", min_value=0.0, value=20.0, step=0.5, key=f"obs_soil_{plot_id}"
            )
        obs_notes = st.text_area("Notas de campo (plagas, costra, color de hoja…)", key=f"obs_notes_{plot_id}")

        if st.button("Guardar observación", key=f"obs_save_{plot_id}"):
            _save_observation(plot_id)

        entries: list[dict] = st.session_state.local_ground_notes.get(plot_id, [])
        if entries:
            st.dataframe(pd.DataFrame(entries), hide_index=True, alt="Local ground observations for this plot")
        else:
            st.caption("Aún no hay observaciones locales para este lote.")

    st.caption(
        "Datos simulados para el desarrollo de la interfaz; se reemplazarán con fuentes reales de NASA (POWER, SMAP, MODIS)."
    )
