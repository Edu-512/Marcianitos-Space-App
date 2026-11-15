"""Action Plan: recommendations with evidence, gaps and local verification."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.uncertainty_chart import impact_with_ci
from utils.model_interface import compute_plot_risk, generate_recommendations


def _translate_category(category: str) -> str:
    """Translate mock Spanish categories to English for the UI."""
    mapping = {
        "Fertilizante": "Fertilizer",
        "Práctica agronómica": "Agronomic Practice",
        "Riego": "Irrigation",
    }
    return mapping.get(category, category)


def run() -> None:
    """Render the diagnosis and per-recommendation impact cards."""
    plot_id = st.session_state.selected_plot_id
    priorities = st.session_state.farmer_priorities

    # Defensive loading for the recommendation model
    try:
        risk = compute_plot_risk(plot_id)
        recommendations = generate_recommendations(plot_id, priorities)
    except Exception as exc:
        st.error("Unable to load the Action Plan right now. Please try again later.")
        with st.expander("Technical diagnostics"):
            st.exception(exc)
        return

    st.caption(
        f"**Field Diagnostics:** Drought Risk {risk.drought_risk:.0%} | "
        f"Heat Stress {risk.heat_stress_risk:.0%} | "
        f"Nutrient Depletion {risk.nutrient_depletion_risk:.0%}\n\n"
        "These recommendations are filtered to respect your active farm priorities and constraints."
    )
    st.divider()

    if not recommendations:
        st.info(
            "No immediate actions required. Your current field conditions and "
            "priorities do not flag any critical interventions."
        )
        return

    for rec in recommendations:
        with st.container(border=True):
            category_en = _translate_category(rec.category)
            
            st.subheader(rec.title)
            st.caption(f"Category: **{category_en}** - {rec.rationale}")

            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Expected Impact",
                f"+{rec.expected_impact_pct:.0f}%",
                delta=f"90% CI: {rec.impact_ci_low:.0f}% to {rec.impact_ci_high:.0f}%",
                delta_color="off",
            )
            c2.metric("Water Change", f"{rec.water_delta_mm:+.0f} mm")
            c3.metric("Estimated Cost", f"${rec.cost_usd_per_ha:.0f} / ha")

            # Progressive disclosure: scientific detail on demand.
            with st.expander("Evidence, Gaps, and Local Verification"):
                st.markdown(f"**Satellite Evidence:**\n{rec.evidence_summary}")
                st.markdown(f"**Information Gaps:**\n{rec.information_gaps}")
                st.markdown(f"**Local Verification Needed:**\n{rec.local_review_notes}")

    # --- Expected impact per recommendation --------------------------------------
    st.subheader("Expected Impact per Recommendation")
    
    impact_df = pd.DataFrame(
        [
            {
                "label": rec.title,
                "impact": rec.expected_impact_pct,
                "ci_low": rec.impact_ci_low,
                "ci_high": rec.impact_ci_high,
            }
            for rec in recommendations
        ]
    )
    
    st.altair_chart(
        impact_with_ci(impact_df),
        use_container_width=True,
    )
