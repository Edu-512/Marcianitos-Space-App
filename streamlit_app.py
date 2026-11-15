"""Field Shift: native navigation, shared parcel context and existing views."""
import streamlit as st

from components.navigation import (
    PAGES, build_navigation, prepare_plot_selection, render_sidebar,
    render_continuation, render_mobile_navigation, render_mobile_clearance,
)
from components.chat_widget import render_chat
from utils.data_sources import load_plots
from utils.types import FarmerPriorities

st.set_page_config(
    page_title="Field Shift - Adapting Farms with NASA Data",
    layout="wide",
    initial_sidebar_state="auto",
)

if "farmer_priorities" not in st.session_state:
    st.session_state.farmer_priorities = FarmerPriorities()
if "local_ground_notes" not in st.session_state:
    st.session_state.local_ground_notes = {}

pages, current_page = build_navigation()
active_key = next(key for key, spec in PAGES.items() if spec.title == current_page.title)
st.session_state.page_key = active_key

load_error = False
try:
    plots = load_plots()
except Exception:
    plots = []
    load_error = True

recovered = prepare_plot_selection(plots)
render_sidebar(pages, active_key, plots)
render_mobile_navigation(pages, active_key)
spec = PAGES[active_key]
st.title(spec.heading, icon=spec.icon)
st.write(spec.description)
st.info(
    "Modo demostración: las parcelas, indicadores y resultados son simulados. "
    "No son observaciones reales de Butler County, Iowa.",
    icon=":material/info:",
)
if load_error:
    st.error("No pudimos cargar las parcelas. Intenta de nuevo en un momento.")
    st.stop()
if not plots:
    st.warning("No hay parcelas disponibles. Cuando se agreguen, podrás comenzar el análisis.")
    st.stop()
if recovered:
    st.info("La parcela anterior ya no está disponible. Seleccionamos la primera parcela de demostración.")
active_plot = next(p for p in plots if p.id == st.session_state.selected_plot_id)
st.caption(f"Parcela activa: {active_plot.name}")


def apply_priority_preset(water: float, soil: float, profit: float) -> None:
    st.session_state.fs_water_w = water
    st.session_state.fs_soil_w = soil
    st.session_state.fs_profit_w = profit


# Existing controls stay available without dominating the main journey.
with st.expander("Mis prioridades y guía de datos", expanded=False):
    col_priorities, col_guide = st.columns(2)
    priorities = st.session_state.farmer_priorities
    with col_priorities:
        st.caption("Estrategia de manejo")
        with st.popover("Mis prioridades y equipo", width="stretch"):
            st.markdown("**Ajustes rápidos**")
            st.caption("Elige un ajuste o modifica las prioridades.")
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                st.button(
                    "Ahorrar agua",
                    width="stretch",
                    on_click=apply_priority_preset,
                    args=(0.85, 0.50, 0.40),
                    help="Prioritize drought resilience and low water usage.",
                )
            with p_col2:
                st.button(
                    "Cuidar el suelo",
                    width="stretch",
                    on_click=apply_priority_preset,
                    args=(0.50, 0.90, 0.45),
                    help="Focus on long-term soil recovery and organic matter.",
                )
            with p_col3:
                st.button(
                    "Priorizar ingresos",
                    width="stretch",
                    on_click=apply_priority_preset,
                    args=(0.35, 0.45, 0.90),
                    help="Focus on high-margin market crops.",
                )

            st.divider()
            st.markdown("**Prioridades (0 = baja, 1 = alta)**")
            water_w = st.slider(
                "Ahorro de agua",
                0.0,
                1.0,
                float(priorities.water_conservation_weight),
                step=0.05,
                key="fs_water_w",
                help="Higher values favor drought-tolerant crops and reduced irrigation.",
            )
            soil_w = st.slider(
                "Cuidado del suelo",
                0.0,
                1.0,
                float(priorities.soil_health_weight),
                step=0.05,
                key="fs_soil_w",
                help="Higher values favor cover crops, nitrogen fixation, and low erosion.",
            )
            profit_w = st.slider(
                "Ingresos",
                0.0,
                1.0,
                float(priorities.profit_market_weight),
                step=0.05,
                key="fs_profit_w",
                help="Higher values prioritize immediate cash return per hectare.",
            )

            st.divider()
            st.markdown("**Equipo y condiciones de trabajo**")
            forage = st.toggle(
                "Necesito forraje para ganado",
                bool(priorities.forage_priority),
                key="fs_forage",
                help="Only recommend crops that can double as livestock feed or grazing.",
            )
            no_till = st.toggle(
                "Tengo equipo para siembra directa",
                bool(priorities.has_no_till_equipment),
                key="fs_no_till",
                help="Enable recommendations that require direct seeding into crop residue.",
            )
            limit_water = st.toggle(
                "Limitar el agua de riego",
                priorities.max_water_budget_mm is not None,
                key="fs_budget_on",
            )
            budget = st.number_input(
                "Límite de riego (mm por temporada)",
                min_value=50.0,
                value=float(priorities.max_water_budget_mm or 250.0),
                step=10.0,
                disabled=not limit_water,
                key="fs_budget_mm",
                help="1 mm of water equals 10 cubic meters (10,000 liters) per hectare.",
            )

    # Rebuild the frozen dataclass so every page reads one consistent object.
    st.session_state.farmer_priorities = FarmerPriorities(
        water_conservation_weight=float(water_w),
        soil_health_weight=float(soil_w),
        profit_market_weight=float(profit_w),
        forage_priority=bool(forage),
        has_no_till_equipment=bool(no_till),
        max_water_budget_mm=float(budget) if limit_water else None,
    )

    with col_guide:
        st.caption("Aprende sobre los datos")
        with st.popover("Guía de datos satelitales", width="stretch"):
            st.markdown(
                """
    ### Understanding Your NASA Data

    * **Crop Vigor - NDVI (MODIS / Landsat)**
      Measures how green and dense your crop canopy is. A sudden drop usually warns of water stress, heat damage, or nutrient deficiency.

    * **Root-Zone Moisture (SMAP)**
      Estimates how much water is available in the top soil layer (approx. 1 square km area average). Great for spotting regional dry-down trends.

    * **Crop Water Loss - Evapotranspiration (POWER / ECOSTRESS)**
      Shows how fast your field is losing water through soil evaporation and plant transpiration. Spikes during hot, windy days.

    ---
    **Why walk the field before acting?**
    Satellites view your farm in large grid squares (pixels) and average the whole area. They tell you **where to look**, but final decisions (exact fertilizer rate or irrigation timing) should always be confirmed with a shovel or soil probe on the ground.
                """
            )


    # --- Active Context Summary Bar (Native Streamlit implementation) -------------
    def render_active_context_summary(prio: FarmerPriorities) -> None:
        parts = [
            f"Agua: {int(prio.water_conservation_weight * 100)}%",
            f"Suelo: {int(prio.soil_health_weight * 100)}%",
            f"Ingresos: {int(prio.profit_market_weight * 100)}%",
        ]
    
        if prio.max_water_budget_mm is not None:
            parts.append(f"Cap: {prio.max_water_budget_mm:.0f} mm/season")
        if prio.forage_priority:
            parts.append("Necesita forraje")
        if prio.has_no_till_equipment:
            parts.append("Equipo de siembra directa")

        summary_text = " | ".join(parts)
        st.info(f"**Prioridades activas:** {summary_text}")


    render_active_context_summary(st.session_state.farmer_priorities)


try:
    current_page.run()
except Exception as page_exc:
    st.warning(
        "Esta sección no está disponible por el momento. "
        "Tu parcela seleccionada y tus prioridades se conservan."
    )
    if st.button("Volver a intentar", key="retry_page"):
        st.rerun()
    with st.expander("Detalles del problema"):
        st.exception(page_exc)

render_continuation(pages, active_key)
render_mobile_clearance()
render_chat()
