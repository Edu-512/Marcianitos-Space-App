"""Rotation Lab: compare the three Butler County plans across measured year types."""

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

#: Year types measured in 2000–2025, as the contract's (rainfall %, temperature °C) inputs.
YEAR_TYPES = {
    "Normal year": (0, 0.0),
    "Dry and hot year": (-20, 2.0),
    "Wet spring": (15, 0.0),
}


def run() -> None:
    """Render the plan comparison, year-type selector and tradeoff tabs."""
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

    st.caption(
        "Three real options for Butler County. Corn and soybean are the crops grown here and the only ones "
        "with yield, price and soil records behind them: fewer options, every number measured or sourced."
    )
    st.caption(f"📌 **Fixed Baseline:** {baseline_name}")

    selected_others = st.pills(
        "Plans to compare",
        other_names,
        selection_mode="multi",
        default=other_names,
    )
    comparison_names = [baseline_name] + list(selected_others or [])

    # --- Year type (replaces the two continuous climate sliders) ---------------
    st.subheader("Type of Year")
    with st.container(border=True):
        st.caption("Pick a kind of season. Each one groups past years (2000–2025) with similar measured weather.")
        year_type = st.segmented_control(
            "Type of year", list(YEAR_TYPES), default="Normal year", key="rot_year_type",
            label_visibility="collapsed",
        ) or "Normal year"
        rainfall_shift, temp_anomaly = YEAR_TYPES[year_type]

    # --- One prediction per plan, reused by every section below ----------------
    try:
        outcomes = {
            name: predict_scenario_outcome(
                plot_id, scenarios[name].id, rainfall_shift_pct=rainfall_shift, temp_anomaly_c=temp_anomaly
            )
            for name in comparison_names
        }
    except Exception as exc:
        st.error("Results for this plot are not available right now.")
        with st.expander("Technical diagnostics"):
            st.exception(exc)
        return

    st.info(next(iter(outcomes.values())).scenario_climate_note, icon=":material/partly_cloudy_day:")

    st.subheader("Plan Outcomes")
    st.caption(
        "Harvest and money always go together. Low–high values are an 80% range: 8 in 10 similar past years "
        "fell inside it. Costs include land rent."
    )
    rows = [
        {
            "Plan": name,
            "Priority Match (%)": f"{score_scenario_priority_fit(o, priorities):.0f}%",
            "Corn Yield (t/ha)": round(o.expected_yield_t_per_ha, 2),
            "Yield Low (t/ha)": round(o.yield_ci_low, 2),
            "Yield High (t/ha)": round(o.yield_ci_high, 2),
            "Margin (USD/ha)": round(o.margin_usd_per_ha),
            "Margin Low (USD/ha)": round(o.margin_ci_low),
            "Margin High (USD/ha)": round(o.margin_ci_high),
            "Revenue (USD/ha)": round(o.revenue_usd_per_ha),
            "Cost (USD/ha)": round(o.cost_usd_per_ha),
            "Nitrogen (kg/ha)": round(o.nitrogen_kg_per_ha),
            "Erosion (% of tolerable limit)": round(o.erosion_risk_score * 100),
            "Chance of Not Planting (%)": round(o.prob_unplanted_pct, 2),
            "Chance of >20% Yield Drop (%)": round(o.prob_big_loss_pct, 1),
        }
        for name, o in outcomes.items()
    ]
    comparison = pd.DataFrame(rows)
    st.dataframe(comparison, hide_index=True, width="stretch")

    # --- Tabs: tradeoffs / uncertainty / why & local caveats ---------------------
    st.subheader("Detailed Analysis")
    tradeoffs_tab, uncertainty_tab, caveats_tab = st.tabs(
        ["Tradeoffs", "Yield Uncertainty", "Agronomic Evidence"]
    )

    with tradeoffs_tab:
        st.caption(
            "Higher bars for margin and yield are better. Higher bars for cost, nitrogen, erosion and "
            "planting risk are worse. Erosion is shown as a share of the tolerable soil loss (100% = at the limit)."
        )
        chart_df = comparison.set_index("Plan")
        charts = [
            "Margin (USD/ha)", "Corn Yield (t/ha)", "Cost (USD/ha)",
            "Nitrogen (kg/ha)", "Erosion (% of tolerable limit)", "Chance of Not Planting (%)",
        ]
        for start in (0, 3):
            for column, metric in zip(st.columns(3), charts[start:start + 3]):
                with column:
                    st.caption(metric)
                    st.bar_chart(chart_df[metric])

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
                width="stretch",
            )
            st.caption(
                f"{year_type}. Shaded band: 80% range of corn yield (t/ha). Only the harvest result (the last "
                "point, October) comes from measured years; the curve before it is an approximation of how "
                "the season builds toward that result."
            )
        except Exception:
            st.info("The yield path is not available for this plot.")

    with caveats_tab:
        st.caption("Why each plan behaves as it does, what backs it and what it cannot tell you.")
        for name, outcome in outcomes.items():
            with st.container(border=True):
                st.markdown(f"### {name}")
                st.markdown(f"**How it works:**\n{outcome.agronomic_mechanism}")
                st.markdown(f"**Weather of this year type:**\n{outcome.scenario_climate_note}")
                st.markdown(f"**Sources:**\n{outcome.evidence_summary}")
                st.markdown(f"**Limits of this information:**\n{outcome.information_gaps}")
                st.markdown(f"**Check in your field:**\n{outcome.local_review_notes}")
