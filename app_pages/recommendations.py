"""Action Plan: recommendations with evidence, gaps and local verification."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.uncertainty_chart import impact_with_ci
from utils.model_interface import compute_plot_risk, generate_recommendations

CATEGORY_ICONS = {
    "Fertilizante": ":material/fertility_agent:",
    "Práctica agronómica": ":material/sprout:",
}


def run() -> None:
    """Render the diagnosis and per-recommendation impact cards."""
    plot_id = st.session_state.selected_plot_id
    priorities = st.session_state.farmer_priorities

    risk = compute_plot_risk(plot_id)
    recommendations = generate_recommendations(plot_id, priorities)

    st.caption(
        f"Diagnóstico del lote: riesgo de sequía {risk.drought_risk:.0%}, "
        f"estrés térmico {risk.heat_stress_risk:.0%}, pérdida de nutrientes {risk.nutrient_depletion_risk:.0%}. "
        "Las recomendaciones respetan tus prioridades y restricciones."
    )

    for rec in recommendations:
        with st.container(border=True):
            icon = CATEGORY_ICONS.get(rec.category, ":material/info:")
            st.markdown(f"**{rec.title}** {icon}")
            st.caption(f"Categoría: **{rec.category}** · {rec.rationale}")

            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Expected Impact",
                f"+{rec.expected_impact_pct:.0f}%",
                delta=f"({rec.impact_ci_low:.0f}% – {rec.impact_ci_high:.0f}%) 90% CI",
            )
            c2.metric("Water Change", f"{rec.water_delta_mm:+.0f} mm")
            c3.metric("Cost", f"${rec.cost_usd_per_ha:.0f}/ha")

            # Progressive disclosure: scientific detail on demand.
            with st.expander("Evidencia, brechas y verificación local"):
                st.markdown(f"**Satellite Evidence:** {rec.evidence_summary}")
                st.markdown(f"**Information Gaps:** {rec.information_gaps}")
                st.markdown(f"**Local Verification Needed:** {rec.local_review_notes}")

    # --- Expected impact per recommendation --------------------------------------
    st.markdown("### Impacto esperado por recomendación")
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
        alt="Expected impact of each recommendation with its 90% confidence interval",
    )
