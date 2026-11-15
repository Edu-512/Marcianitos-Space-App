"""Field Shift — adapting farms with NASA data.

Entry point for the multipage app: responsive navigation, a persistent farmer
context bar (plot + priorities + satellite guide), shared state and page
routing. Page content lives in ``app_pages/``; business logic and data access
live in ``utils/`` (see README.md for the contract with the model team).
"""

import streamlit as st

from components.navigation import DEFAULT_PAGE, PAGES, render_nav, run_page
from utils.data_sources import load_plots
from utils.types import FarmerPriorities

st.set_page_config(
    page_title="Field Shift — Adapting farms with NASA data",
    page_icon=":material/agriculture:",
    layout="wide",
)

# --- Shared state (single source of truth, initialized once per session) ----
if "page_key" not in st.session_state:
    st.session_state.page_key = DEFAULT_PAGE
if "farmer_priorities" not in st.session_state:
    st.session_state.farmer_priorities = FarmerPriorities()
if "local_ground_notes" not in st.session_state:
    st.session_state.local_ground_notes = {}

plots = load_plots()
plot_ids = [p.id for p in plots]
if "selected_plot_id" not in st.session_state:
    st.session_state.selected_plot_id = plot_ids[0]

render_nav(st.session_state.page_key)

# --- Persistent context bar ---------------------------------------------------
col_plot, col_priorities, col_guide = st.columns([5.2, 2.4, 2.4])

plot_labels = {f"{p.name} ({p.area_hectares:.0f} ha · {p.current_crop})": p.id for p in plots}
labels = list(plot_labels)
current_idx = 0
for i, (lbl, pid) in enumerate(plot_labels.items()):
    if pid == st.session_state.selected_plot_id:
        current_idx = i
        break
with col_plot:
    selected_label = st.selectbox("Selected plot", labels, index=current_idx, key="fs_plot_select")
st.session_state.selected_plot_id = plot_labels[selected_label]

priorities = st.session_state.farmer_priorities
with col_priorities:
    with st.popover("⚙ My Priorities"):
        water_w = st.slider(
            "Water Conservation", 0.0, 1.0, float(priorities.water_conservation_weight), step=0.05, key="fs_water_w"
        )
        soil_w = st.slider(
            "Soil Health", 0.0, 1.0, float(priorities.soil_health_weight), step=0.05, key="fs_soil_w"
        )
        profit_w = st.slider(
            "Market Profit", 0.0, 1.0, float(priorities.profit_market_weight), step=0.05, key="fs_profit_w"
        )
        forage = st.toggle("Forage value needed", bool(priorities.forage_priority), key="fs_forage")
        no_till = st.toggle("No-till equipment available", bool(priorities.has_no_till_equipment), key="fs_no_till")
        limit_water = st.toggle(
            "Max water budget (mm)", priorities.max_water_budget_mm is not None, key="fs_budget_on"
        )
        budget = st.number_input(
            "Budget cap (mm/season)",
            min_value=50.0,
            value=float(priorities.max_water_budget_mm or 250.0),
            step=10.0,
            disabled=not limit_water,
            key="fs_budget_mm",
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
    with st.popover("? Satellite Guide"):
        st.markdown(
            """
**NDVI (MODIS/Landsat)** — cuánta vegetación verde hay sobre el suelo; cae con
estrés hídrico, calor o falta de nutrientes.

**Humedad del suelo (SMAP)** — agua disponible para las raíces en la capa
superior (~1 km² por píxel).

**Evapotranspiración (POWER/ECOSTRESS)** — cuánta agua pierde el campo entre
suelo y plantas; sube con calor y viento.

¿Por qué no reemplazan una sonda de suelo? El píxel satelital promedia todo el
lote: detecta *dónde mirar*, pero la decisión fina (dosis, fecha) se confirma
con mediciones locales. Por eso cada recomendación pide verificación en campo.
            """
        )

spec = PAGES[st.session_state.page_key]
st.title(spec.title, icon=spec.icon)

run_page(st.session_state.page_key)
