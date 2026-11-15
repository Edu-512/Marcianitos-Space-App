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

    scenarios = {s.name: s for s in load_rotation_scenarios()}
    baseline_name = next(n for n, s in scenarios.items() if s.id == BASELINE_ID)
    other_names = [n for n in scenarios if n != baseline_name]

    st.markdown(f"📌 **Baseline fija:** {baseline_name}")

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
    with st.container(border=True):
        w1, w2 = st.columns(2)
        with w1:
            rainfall_shift = int(st.slider("Seasonal Rainfall Shift (%)", -30, 20, 0, step=5))
        with w2:
            temp_anomaly = float(st.slider("Temperature Anomaly (°C)", 0.0, 3.5, 0.0, step=0.1))

    # --- Comparison table (all outcomes computed under the climate shift) -------
    rows = []
    for name in comparison_names:
        outcome = predict_scenario_outcome(
            plot_id, scenarios[name].id, rainfall_shift_pct=rainfall_shift, temp_anomaly_c=temp_anomaly
        )
        fit = score_scenario_priority_fit(outcome, priorities)
        rows.append(
            {
                "Scenario": name,
                "Priority Match (%)": fit,
                "Expected yield (t/ha)": outcome.expected_yield_t_per_ha,
                "CI 90% low": outcome.yield_ci_low,
                "CI 90% high": outcome.yield_ci_high,
                "Water use (mm)": round(outcome.water_use_mm),
                "Nutrient loss (%)": round(outcome.nutrient_loss_pct, 1),
                "Organic matter Δ (%)": outcome.organic_matter_delta_pct,
                "Erosion risk": outcome.erosion_risk_score,
                "Cost (USD/ha)": round(outcome.cost_usd_per_ha),
            }
        )
    comparison = pd.DataFrame(rows)
    st.dataframe(comparison, alt="Comparison of rotation scenarios for the selected plot")

    # --- Tabs: tradeoffs / uncertainty / why & local caveats ----------------------
    tradeoffs_tab, uncertainty_tab, caveats_tab = st.tabs(
        ["Tradeoffs", "Uncertainty", "Why & Local Caveats"], on_change="rerun"
    )

    if tradeoffs_tab.open:
        with tradeoffs_tab:
            chart_df = comparison.set_index("Scenario")
            t1, t2, t3 = st.columns(3)
            with t1:
                st.bar_chart(chart_df["Water use (mm)"])
            with t2:
                st.bar_chart(chart_df["Nutrient loss (%)"])
            with t3:
                st.bar_chart(chart_df["Organic matter Δ (%)"])
            t4, t5, t6 = st.columns(3)
            with t4:
                st.bar_chart(chart_df["Erosion risk"])
            with t5:
                st.bar_chart(chart_df["Cost (USD/ha)"])
            with t6:
                # Pest disruption is "higher is better" — show it as-is.
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
            st.caption(
                "Barras altas de agua, pérdida de nutrientes, erosión o costo = peor; "
                "barrera alta de interrupción de plagas = mejor. Compara contra el rinde esperado."
            )

    if uncertainty_tab.open:
        with uncertainty_tab:
            long_rows = []
            for name in comparison_names:
                trajectory = predict_yield_trajectory(
                    plot_id, scenarios[name].id, rainfall_shift_pct=rainfall_shift, temp_anomaly_c=temp_anomaly
                )
                trajectory["scenario"] = name
                long_rows.append(trajectory[["date", "scenario", "median", "ci_low", "ci_high"]])
            st.altair_chart(
                yield_uncertainty_bands(pd.concat(long_rows, ignore_index=True)),
                alt="Expected monthly yield per scenario with 90% confidence bands under the climate shift",
            )
            st.caption(
                f"Banda sombreada: intervalo de confianza del 90% con lluvia {rainfall_shift:+d}% y "
                f"anomalía térmica +{temp_anomaly:.1f}°C. Las bandas se estrechan cerca de la fecha actual."
            )

    if caveats_tab.open:
        with caveats_tab:
            for name in comparison_names:
                outcome = predict_scenario_outcome(
                    plot_id, scenarios[name].id, rainfall_shift_pct=rainfall_shift, temp_anomaly_c=temp_anomaly
                )
                with st.container(border=True):
                    st.markdown(f"**{name}**")
                    st.markdown(f"**Mecanismo agronómico:** {outcome.agronomic_mechanism}")
                    st.markdown(f"**Evidencia satelital:** {outcome.evidence_summary}")
                    st.markdown(f"**Brechas de información:** {outcome.information_gaps}")
                    st.markdown(f"**Verificación local necesaria:** {outcome.local_review_notes}")
