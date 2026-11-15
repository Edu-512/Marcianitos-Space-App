"""Field Shift — adapting farms with NASA data.

Entry point for the multipage app: responsive navigation, a persistent farmer
context bar (plot + priorities + satellite guide), text-based active-priority 
summary, and resilient page routing ready for model integration.
"""

import streamlit as st

from components.navigation import (
    DEFAULT_PAGE,
    PAGES,
    render_nav,
    render_nav_clearance,
    run_page,
)
from components.chat_widget import render_chat
from utils.data_sources import load_plots
from utils.types import FarmerPriorities

st.set_page_config(
    page_title="Field Shift - Adapting Farms with NASA Data",
    layout="wide",
)

# --- Shared state (single source of truth, initialized once per session) ----
if "page_key" not in st.session_state:
    st.session_state.page_key = DEFAULT_PAGE
if "farmer_priorities" not in st.session_state:
    st.session_state.farmer_priorities = FarmerPriorities()
if "local_ground_notes" not in st.session_state:
    st.session_state.local_ground_notes = {}

# Defensive data loading in case backend/data source is temporarily unavailable
try:
    plots = load_plots()
except Exception as exc:
    st.error(
        "**Unable to load farm plots right now.** Please check your connection or contact support."
    )
    with st.expander("Technical details (for model/engineering team)"):
        st.exception(exc)
    st.stop()

if not plots:
    st.warning("No farm plots found in your profile. Please add a plot to begin.")
    st.stop()

plot_ids = [p.id for p in plots]
if (
    "selected_plot_id" not in st.session_state
    or st.session_state.selected_plot_id not in plot_ids
):
    st.session_state.selected_plot_id = plot_ids[0]


# --- Helper callback for quick farmer-friendly priority presets -------------
def apply_priority_preset(water: float, soil: float, profit: float) -> None:
    st.session_state.fs_water_w = water
    st.session_state.fs_soil_w = soil
    st.session_state.fs_profit_w = profit


# --- Navigation --------------------------------------------------------------
render_nav(st.session_state.page_key)

# --- Persistent Context Bar (Aligned & Digestible) ---------------------------
col_plot, col_priorities, col_guide = st.columns([5.2, 2.4, 2.4])

plot_labels = {
    f"{p.name} ({p.area_hectares:.0f} ha - {p.current_crop})": p.id for p in plots
}
labels = list(plot_labels)
current_idx = 0
for i, (lbl, pid) in enumerate(plot_labels.items()):
    if pid == st.session_state.selected_plot_id:
        current_idx = i
        break

with col_plot:
    st.caption("Active Field Plot")
    selected_label = st.selectbox(
        "Selected plot",
        labels,
        index=current_idx,
        key="fs_plot_select",
        label_visibility="collapsed",
    )
st.session_state.selected_plot_id = plot_labels[selected_label]

priorities = st.session_state.farmer_priorities
with col_priorities:
    st.caption("Farm Strategy")
    with st.popover("My Priorities and Equipment", width="stretch"):
        st.markdown("**Quick Strategy Presets**")
        st.caption("Click a preset or fine-tune the sliders below.")
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            st.button(
                "Save Water",
                width="stretch",
                on_click=apply_priority_preset,
                args=(0.85, 0.50, 0.40),
                help="Prioritize drought resilience and low water usage.",
            )
        with p_col2:
            st.button(
                "Soil First",
                width="stretch",
                on_click=apply_priority_preset,
                args=(0.50, 0.90, 0.45),
                help="Focus on long-term soil recovery and organic matter.",
            )
        with p_col3:
            st.button(
                "Max Return",
                width="stretch",
                on_click=apply_priority_preset,
                args=(0.35, 0.45, 0.90),
                help="Focus on high-margin market crops.",
            )

        st.divider()
        st.markdown("**Goal Weights (0 = Low, 1 = Critical)**")
        water_w = st.slider(
            "Water Conservation",
            0.0,
            1.0,
            float(priorities.water_conservation_weight),
            step=0.05,
            key="fs_water_w",
            help="Higher values favor drought-tolerant crops and reduced irrigation.",
        )
        soil_w = st.slider(
            "Soil Health",
            0.0,
            1.0,
            float(priorities.soil_health_weight),
            step=0.05,
            key="fs_soil_w",
            help="Higher values favor cover crops, nitrogen fixation, and low erosion.",
        )
        profit_w = st.slider(
            "Market Profit",
            0.0,
            1.0,
            float(priorities.profit_market_weight),
            step=0.05,
            key="fs_profit_w",
            help="Higher values prioritize immediate cash return per hectare.",
        )

        st.divider()
        st.markdown("**Farm Operations and Constraints**")
        forage = st.toggle(
            "Livestock forage needed",
            bool(priorities.forage_priority),
            key="fs_forage",
            help="Only recommend crops that can double as livestock feed or grazing.",
        )
        no_till = st.toggle(
            "No-till equipment available",
            bool(priorities.has_no_till_equipment),
            key="fs_no_till",
            help="Enable recommendations that require direct seeding into crop residue.",
        )
        limit_water = st.toggle(
            "Enforce seasonal water cap (mm)",
            priorities.max_water_budget_mm is not None,
            key="fs_budget_on",
        )
        budget = st.number_input(
            "Max water budget (mm/season)",
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
    st.caption("Field Reference")
    with st.popover("Satellite Guide", width="stretch"):
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
        f"Water: {int(prio.water_conservation_weight * 100)}%",
        f"Soil: {int(prio.soil_health_weight * 100)}%",
        f"Profit: {int(prio.profit_market_weight * 100)}%",
    ]
    
    if prio.max_water_budget_mm is not None:
        parts.append(f"Cap: {prio.max_water_budget_mm:.0f} mm/season")
    if prio.forage_priority:
        parts.append("Forage Required")
    if prio.has_no_till_equipment:
        parts.append("No-Till Ready")

    summary_text = " | ".join(parts)
    st.info(f"**Active Strategy:** {summary_text}")


render_active_context_summary(st.session_state.farmer_priorities)

# --- Page Header & Model-Resilient Page Execution ----------------------------
spec = PAGES[st.session_state.page_key]
st.title(spec.title)

try:
    run_page(st.session_state.page_key)
except Exception as page_exc:
    st.warning(
        "### Model or Satellite Service Temporarily Unavailable\n"
        "We are currently updating the recommendation engine for this section. "
        "Your plot selection and farm priorities are safely saved."
    )
    col_retry, col_fallback = st.columns([1, 4])
    with col_retry:
        if st.button("Retry Loading Page", width="stretch"):
            st.rerun()
    with st.expander("Technical diagnostics (for the model integration team)"):
        st.exception(page_exc)

render_nav_clearance()

render_chat()
