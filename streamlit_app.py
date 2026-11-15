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
    "Plots, soils and results come from USDA and NASA records for Butler County, Iowa. "
    "They show likely ranges, not guarantees: check your own field before deciding.",
    icon=":material/info:",
)
if load_error:
    st.error("We couldn't load the plots. Please try again in a moment.")
    st.stop()
if not plots:
    st.warning("No plots are available. Add a plot to start your analysis.")
    st.stop()
if recovered:
    st.info("Your previous plot is no longer available. We selected the first demo plot.")
active_plot = next(p for p in plots if p.id == st.session_state.selected_plot_id)
st.caption(f"Active plot: {active_plot.name}")


def apply_priority_preset(water: float, soil: float, profit: float) -> None:
    st.session_state.fs_water_w = water
    st.session_state.fs_soil_w = soil
    st.session_state.fs_profit_w = profit


# Existing controls stay available without dominating the main journey.
with st.expander("My priorities and data guide", expanded=False):
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
                    "Plant on time",
                    width="stretch",
                    on_click=apply_priority_preset,
                    args=(0.85, 0.50, 0.40),
                    help="Prioritize plans with a lower risk of not being able to plant in a wet spring.",
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
                    help="Focus on the plans that leave the most money per hectare.",
                )

            st.divider()
            st.markdown("**Priorities (0 = low, 1 = high)**")
            water_w = st.slider(
                "Planting reliability",
                0.0,
                1.0,
                float(priorities.water_conservation_weight),
                step=0.05,
                key="fs_water_w",
                help="Higher values favor plans with a lower chance of not being able to plant after a wet spring.",
            )
            soil_w = st.slider(
                "Soil health",
                0.0,
                1.0,
                float(priorities.soil_health_weight),
                step=0.05,
                key="fs_soil_w",
                help="Higher values favor plans with less soil erosion.",
            )
            profit_w = st.slider(
                "Income",
                0.0,
                1.0,
                float(priorities.profit_market_weight),
                step=0.05,
                key="fs_profit_w",
                help="Higher values favor plans with a higher margin per hectare.",
            )

            st.divider()
            st.markdown("**Equipment and working conditions**")
            forage = st.toggle(
                "I need livestock forage",
                bool(priorities.forage_priority),
                key="fs_forage",
                help="Forage value is not estimated for the corn and soybean plans yet, so this does not change results.",
            )
            no_till = st.toggle(
                "I have no-till equipment",
                bool(priorities.has_no_till_equipment),
                key="fs_no_till",
                help="Enable recommendations that require direct seeding into crop residue.",
            )
            # Butler County is rain-fed: there is no irrigation demand to cap, so
            # the control stays visible but disabled and the cap is never set.
            st.toggle(
                "Set an irrigation water limit",
                False,
                key="fs_budget_on",
                disabled=True,
                help="Butler County farms are rain-fed, so there is no irrigation demand to limit.",
            )
            st.caption("Not available: Butler County farms are rain-fed (no irrigation).")
            limit_water, budget = False, None

    # Rebuild the frozen dataclass so every page reads one consistent object.
    st.session_state.farmer_priorities = FarmerPriorities(
        water_conservation_weight=float(water_w),
        soil_health_weight=float(soil_w),
        profit_market_weight=float(profit_w),
        forage_priority=bool(forage),
        has_no_till_equipment=bool(no_till),
        max_water_budget_mm=float(budget) if limit_water and budget is not None else None,
    )

    with col_guide:
        st.caption("Learn about the data")
        with st.popover("Satellite data guide", width="stretch"):
            st.markdown(
                """
    ### Where These Numbers Come From

    * **Weather - NASA POWER (2000–2025)**
      Daily temperature, rainfall and root-zone soil wetness for one point at the center of Butler County. Past years are grouped into normal, dry-and-hot and wet-spring seasons.

    * **Yields and prices - USDA NASS QuickStats (2000–2025)**
      County corn and soybean yields across Iowa show how much harvests swing in each kind of year.

    * **Soil - USDA NRCS SSURGO**
      Sand, water the soil can hold, slope and organic matter under each field.

    * **Fields - USDA Cropland Data Layer (2018–2025)**
      Satellite crop maps give each field's outline and its corn–soybean pattern.

    * **Costs and nitrogen - Iowa State University Extension**
      Production costs (including land rent) and nitrogen rates.

    ---
    **Why walk the field before acting?**
    Weather comes from one point for the whole county and satellite maps average large squares. They tell you **where to look**, but final decisions should always be confirmed on the ground.
                """
            )


    # --- Active Context Summary Bar (Native Streamlit implementation) -------------
    def render_active_context_summary(prio: FarmerPriorities) -> None:
        parts = [
            f"Planting: {int(prio.water_conservation_weight * 100)}%",
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

render_continuation(pages, active_key)
render_mobile_clearance()
render_chat()
