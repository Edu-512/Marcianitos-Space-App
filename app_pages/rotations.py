"""Rotation Lab: scenario comparison, climate What-If simulator and tradeoffs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.uncertainty_chart import yield_uncertainty_bands
from utils.data_sources import load_rotation_scenarios
from utils.model_interface import (
    predict_scenario_outcome,
    predict_yield_trajectory,
    score_scenario_priority_fit,
)

#: The pinned monoculture baseline every comparison must include.
BASELINE_ID = "maiz-continuo"


def run() -> None:
    """Render scenario comparison, What-If climate sliders and tradeoff tabs."""
    plot_id = st.session_state.selected_plot_id
    priorities = st.session_state.farmer_priorities

    try:
        scenarios_list = load_rotation_scenarios()
        scenarios = {s.name: s for s in scenarios_list}
        baseline_name = next(n for n, s in scenarios.items() if s.id == BASELINE_ID)
        other_names = [n for n in scenarios if n != baseline_name]
    except Exception as exc:
        st.error("Unable to load crop rotation scenarios at this time.")
        with st.expander("Technical diagnostics"):
            st.exception(exc)
        return

    st.caption(f"📌 **Fixed Baseline:** {baseline_name}")

    selected_others = st.pills(
        "Scenarios to compare",
        other_names,
        selection_mode="multi",
        default=other_names[:3],
    )
    if selected_others is None:
        selected_others = []
    comparison_names = [baseline_name] + list(selected_others)

    # --- What-If climate sliders -------------------------------------------------
    st.subheader("Climate Simulator")
    with st.container(border=True):
        st.caption("Adjust expected seasonal weather to test how each rotation plan performs under stress.")
        w1, w2 = st.columns(2)
        with w1:
            rainfall_shift = int(st.slider("Seasonal Rainfall Shift (%)", -30, 20, 0, step=5))
        with w2:
            temp_anomaly = float(st.slider("Temperature Anomaly (°C)", 0.0, 3.5, 0.0, step=0.1))

    # --- Comparison table (all outcomes computed under the climate shift) -------
    st.subheader("Scenario Outcomes")
    rows = []
    
    try:
        for name in comparison_names:
            outcome = predict_scenario_outcome(
                plot_id, scenarios[name].id, rainfall_shift_pct=rainfall_shift, temp_anomaly_c=temp_anomaly
            )
            fit = score_scenario_priority_fit(outcome, priorities)
            rows.append(
                {
                    "Scenario": name,
                    "Priority Match (%)": f"{fit:.0f}%",
                    "Expected Yield (t/ha)": outcome.expected_yield_t_per_ha,
                    "CI 90% Low": outcome.yield_ci_low,
                    "CI 90% High": outcome.yield_ci_high,
                    "Water Use (mm)": round(outcome.water_use_mm),
                    "Nutrient Loss (%)": round(outcome.nutrient_loss_pct, 1),
                    "Organic Matter Δ (%)": outcome.organic_matter_delta_pct,
                    "Erosion Risk Score": outcome.erosion_risk_score,
                    "Cost (USD/ha)": round(outcome.cost_usd_per_ha),
                }
            )
    except Exception as exc:
        st.error("Simulation failed. The prediction model may be offline.")
        with st.expander("Technical diagnostics"):
            st.exception(exc)
        return

    comparison = pd.DataFrame(rows)
    st.dataframe(comparison, use_container_width=True)

    # --- Tabs: tradeoffs / uncertainty / why & local caveats ----------------------
    st.subheader("Detailed Analysis")
    tradeoffs_tab, uncertainty_tab, caveats_tab = st.tabs(
        ["Tradeoffs", "Yield Uncertainty", "Agronomic Evidence"]
    )

    with tradeoffs_tab:
        st.caption(
            "Higher bars for water use, nutrient loss, erosion, and cost indicate worse outcomes. "
            "Higher bars for pest disruption indicate better resistance."
        )
        chart_df = comparison.set_index("Scenario")
        t1, t2, t3 = st.columns(3)
        with t1:
            st.caption("Water Use (mm)")
            st.bar_chart(chart_df["Water Use (mm)"])
        with t2:
            st.caption("Nutrient Loss (%)")
            st.bar_chart(chart_df["Nutrient Loss (%)"])
        with t3:
            st.caption("Organic Matter Change (%)")
            st.bar_chart(chart_df["Organic Matter Δ (%)"])
            
        t4, t5, t6 = st.columns(3)
        with t4:
            st.caption("Erosion Risk Score")
            st.bar_chart(chart_df["Erosion Risk Score"])
        with t5:
            st.caption("Estimated Cost (USD/ha)")
            st.bar_chart(chart_df["Cost (USD/ha)"])
        with t6:
            st.caption("Pest Disruption Capacity")
            pest = pd.Series(
                [
                    predict_scenario_outcome(
                        plot_id, scenarios[n].id, rainfall_shift_pct=rainfall_shift, temp_anomaly_c=temp_anomaly
                    ).pest_disruption_score
                    for n in comparison_names
                ],
                index=comparison_names,
            )
            st.bar_chart(pest)

    with uncertainty_tab:
        try:
            long_rows = []
            for name in comparison_names:
                trajectory = predict_yield_trajectory(
                    plot_id, scenarios[name].id, rainfall_shift_pct=rainfall_shift, temp_anomaly_c=temp_anomaly
                )
                trajectory["scenario"] = name
                long_rows.append(trajectory[["date", "scenario", "median", "ci_low", "ci_high"]])
                
            st.altair_chart(
                yield_uncertainty_bands(pd.concat(long_rows, ignore_index=True)),
                use_container_width=True,
            )
            st.caption(
                f"Shaded band: 90% confidence interval under adjusted climate "
                f"(Rainfall: {rainfall_shift:+d}%, Temp: +{temp_anomaly:.1f}°C). "
                "Bands narrow as they approach current actual observations."
            )
        except Exception:
            st.info("Yield trajectory prediction is currently unavailable for these parameters.")

    with caveats_tab:
        st.caption("Detailed rationale mapping predictions to field realities.")
        for name in comparison_names:
            outcome = predict_scenario_outcome(
                plot_id, scenarios[name].id, rainfall_shift_pct=rainfall_shift, temp_anomaly_c=temp_anomaly
            )
            with st.container(border=True):
                st.markdown(f"### {name}")
                st.markdown(f"**Agronomic Mechanism:**\n{outcome.agronomic_mechanism}")
                st.markdown(f"**Satellite Evidence:**\n{outcome.evidence_summary}")
                st.markdown(f"**Information Gaps:**\n{outcome.information_gaps}")
                st.markdown(f"**Local Verification Needed:**\n{outcome.local_review_notes}")