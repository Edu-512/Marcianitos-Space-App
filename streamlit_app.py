"""Know Your Farm: native navigation, shared parcel context and existing views."""
import streamlit as st

from components.navigation import (
    PAGES, build_navigation, prepare_plot_selection, render_sidebar,
    render_continuation, render_mobile_navigation, render_mobile_clearance, render_mobile_plot_selector,
)
from components.chat_widget import render_chat
from utils.data_sources import load_plots
from utils.types import FarmerPriorities
from utils import field_model as fm
from components.design_system import styles
from components.branding import APP_NAME, APP_ICON, render_mobile_brand

st.set_page_config(
    page_title=f"{APP_NAME} - Adapting Farms with NASA Data",
    page_icon=str(APP_ICON),
    layout="wide",
    initial_sidebar_state="auto",
)

render_mobile_brand()

st.html(
    """
    <style>
    [data-testid="stMainBlockContainer"] {
      padding: clamp(2rem, 6vh, 4rem) clamp(1.25rem, 4vw, 3.5rem) 2rem;
    }
    @media (max-width: 767px) {
      [data-testid="stMainBlockContainer"] {
        padding: 1.5rem clamp(0.75rem, 4vw, 1rem)
          calc(8rem + env(safe-area-inset-bottom, 0px));
      }
    }
    </style>
    """
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
render_mobile_plot_selector(plots)
styles()
if fm.enabled():
    fm.reconcile()
spec = PAGES[active_key]
if not (fm.enabled() and active_key == "map_view"):
    st.title(spec.heading, icon=spec.icon)
    st.write(spec.description)
    if not fm.enabled():
        st.info("Demo mode: plots, indicators, and results are simulated. They are not real observations from Butler County, Iowa.", icon=":material/info:")
if load_error:
    st.error("We couldn't load the plots. Please try again in a moment.")
    st.stop()
if not plots:
    st.warning("No plots are available. Add a plot to start your analysis.")
    st.stop()
if recovered:
    st.info("Your previous plot is no longer available. We selected the first available profile.")
active_plot = next(p for p in plots if p.id == st.session_state.selected_plot_id)
if not (fm.enabled() and active_key == "map_view"):
    st.caption(f"Active plot: {active_plot.name}")


def apply_priority_preset(water: float, soil: float, profit: float) -> None:
    st.session_state.fs_water_w = water
    st.session_state.fs_soil_w = soil
    st.session_state.fs_profit_w = profit


if not (fm.enabled() and active_key == "map_view"):
    # Existing controls stay available without dominating the main journey.
    with st.expander("My priorities and data guide", expanded=False):
        st.selectbox("Data source",["model","legacy"],format_func=lambda mode:"Research model" if mode=="model" else "Legacy demo",key="data_mode")
        if fm.enabled():
            st.caption("Farm priorities below are planning notes. The research export uses fixed source assumptions; these controls do not recalculate or rank its plans.")
        col_priorities, col_guide = st.columns(2)
        priorities = st.session_state.farmer_priorities
        with col_priorities:
            st.caption("Management strategy")
            with st.popover("My priorities and equipment", width="stretch"):
                st.markdown("**Quick settings**")
                st.caption("Choose a preset or adjust your priorities.")
                p_col1, p_col2, p_col3 = st.columns(3)
                with p_col1:
                    st.button(
                        "Save water",
                        width="stretch",
                        on_click=apply_priority_preset,
                        args=(0.85, 0.50, 0.40),
                        help="Prioritize drought resilience and low water usage.",
                    )
                with p_col2:
                    st.button(
                        "Protect soil",
                        width="stretch",
                        on_click=apply_priority_preset,
                        args=(0.50, 0.90, 0.45),
                        help="Focus on long-term soil recovery and organic matter.",
                    )
                with p_col3:
                    st.button(
                        "Prioritize income",
                        width="stretch",
                        on_click=apply_priority_preset,
                        args=(0.35, 0.45, 0.90),
                        help="Focus on high-margin market crops.",
                    )

                st.divider()
                st.markdown("**Priorities (0 = low, 1 = high)**")
                water_w = st.slider(
                    "Water conservation",
                    0.0,
                    1.0,
                    float(priorities.water_conservation_weight),
                    step=0.05,
                    key="fs_water_w",
                    help="Higher values favor drought-tolerant crops and reduced irrigation.",
                )
                soil_w = st.slider(
                    "Soil health",
                    0.0,
                    1.0,
                    float(priorities.soil_health_weight),
                    step=0.05,
                    key="fs_soil_w",
                    help="Higher values favor cover crops, nitrogen fixation, and low erosion.",
                )
                profit_w = st.slider(
                    "Income",
                    0.0,
                    1.0,
                    float(priorities.profit_market_weight),
                    step=0.05,
                    key="fs_profit_w",
                    help="Higher values prioritize immediate cash return per hectare.",
                )

                st.divider()
                st.markdown("**Equipment and working conditions**")
                forage = st.toggle(
                    "I need livestock forage",
                    bool(priorities.forage_priority),
                    key="fs_forage",
                    help="Only recommend crops that can double as livestock feed or grazing.",
                )
                no_till = st.toggle(
                    "I have no-till equipment",
                    bool(priorities.has_no_till_equipment),
                    key="fs_no_till",
                    help="Enable recommendations that require direct seeding into crop residue.",
                )
                limit_water = st.toggle(
                    "Set an irrigation water limit",
                    priorities.max_water_budget_mm is not None,
                    key="fs_budget_on",
                )
                budget = st.number_input(
                    "Irrigation limit (mm per season)",
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
            st.caption("Learn about the data")
            with st.popover("Satellite data guide", width="stretch"):
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
                f"Income: {int(prio.profit_market_weight * 100)}%",
            ]

            if prio.max_water_budget_mm is not None:
                parts.append(f"Cap: {prio.max_water_budget_mm:.0f} mm/season")
            if prio.forage_priority:
                parts.append("Forage needed")
            if prio.has_no_till_equipment:
                parts.append("No-till equipment")

            summary_text = " | ".join(parts)
            st.info(f"**Active priorities:** {summary_text}")


        render_active_context_summary(st.session_state.farmer_priorities)


try:
    current_page.run()
except Exception as page_exc:
    st.warning(
        "This section is temporarily unavailable. "
        "Your selected plot and priorities have been preserved."
    )
    if st.button("Try again", key="retry_page"):
        st.rerun()
    with st.expander("Troubleshooting details"):
        st.exception(page_exc)

if active_key == "rotations":
    from app_pages.rotations import render_plan_continuation
    render_plan_continuation(pages)
elif not (fm.enabled() and active_key == "map_view"):
    render_continuation(pages, active_key)
render_mobile_clearance()
render_chat()
