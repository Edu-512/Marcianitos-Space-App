"""Compare crop rotation scenarios and reveal their tradeoffs."""

import pandas as pd
import streamlit as st

from components.uncertainty_chart import yield_uncertainty_bands
from utils.data_sources import load_rotation_scenarios
from utils.model_interface import predict_scenario_outcome, predict_yield_trajectory

plot_id = st.session_state.selected_plot_id
scenarios = {s.name: s for s in load_rotation_scenarios()}

selected_names = st.pills(
    "Scenarios to compare",
    list(scenarios),
    selection_mode="multi",
    default=[list(scenarios)[0], list(scenarios)[-1]],
)

if not selected_names:
    st.info("Select at least one scenario to compare.")
    st.stop()

# Comparison table: one row per selected scenario.
rows = []
for name in selected_names:
    outcome = predict_scenario_outcome(plot_id, scenarios[name].id)
    rows.append(
        {
            "Scenario": name,
            "Expected yield (t/ha)": outcome.expected_yield_t_per_ha,
            "CI 90% low": outcome.yield_ci_low,
            "CI 90% high": outcome.yield_ci_high,
            "Water use (mm)": round(outcome.water_use_mm),
            "Nutrient loss (%)": round(outcome.nutrient_loss_pct, 1),
            "Cost (USD/ha)": round(outcome.cost_usd_per_ha),
        }
    )
comparison = pd.DataFrame(rows)
st.dataframe(comparison, alt="Comparison of rotation scenarios for the selected plot")

# Tabs with on_change="rerun" so each tab renders only its own content.
tradeoffs_tab, uncertainty_tab = st.tabs(["Tradeoffs", "Uncertainty"], on_change="rerun")

if tradeoffs_tab.open:
    with tradeoffs_tab:
        t1, t2, t3 = st.columns(3)
        chart_df = comparison.set_index("Scenario")
        with t1:
            st.bar_chart(chart_df["Water use (mm)"])
        with t2:
            st.bar_chart(chart_df["Nutrient loss (%)"])
        with t3:
            st.bar_chart(chart_df["Cost (USD/ha)"])
        st.caption("Higher bars mean more water, nutrient loss or cost. Compare against expected yield to weigh the tradeoffs.")

if uncertainty_tab.open:
    with uncertainty_tab:
        long_rows = []
        for name in selected_names:
            trajectory = predict_yield_trajectory(plot_id, scenarios[name].id)
            trajectory["scenario"] = name
            long_rows.append(trajectory[["date", "scenario", "median", "ci_low", "ci_high"]])
        st.altair_chart(
            yield_uncertainty_bands(pd.concat(long_rows, ignore_index=True)),
            alt="Expected monthly yield per scenario with 90% confidence bands",
        )
        st.caption("Shaded area: 90% confidence interval. Bands narrow as the forecast horizon gets closer.")
