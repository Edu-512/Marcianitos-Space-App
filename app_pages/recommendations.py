"""Decision support: recommendations with expected impact and uncertainty."""

import pandas as pd
import streamlit as st

from components.uncertainty_chart import impact_with_ci
from utils.model_interface import compute_plot_risk, generate_recommendations

plot_id = st.session_state.selected_plot_id
risk = compute_plot_risk(plot_id)
recommendations = generate_recommendations(plot_id)

st.caption(
    f"Diagnosis for this plot: drought risk {risk.drought_risk:.0%}, "
    f"heat stress {risk.heat_stress_risk:.0%}, nutrient depletion {risk.nutrient_depletion_risk:.0%}."
)

CATEGORY_ICONS = {
    "Fertilizante": ":material/fertility_agent:",
    "Práctica agronómica": ":material/sprout:",
}

for rec in recommendations:
    with st.container(border=True):
        icon = CATEGORY_ICONS.get(rec.category, ":material/info:")
        st.markdown(f"**{rec.title}** {icon}")
        st.caption(rec.rationale)
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Expected impact",
            f"+{rec.expected_impact_pct:.0f}%",
            delta=f"({rec.impact_ci_low:.0f}% – {rec.impact_ci_high:.0f}%)",
        )
        c2.metric("Water change", f"{rec.water_delta_mm:+.0f} mm")
        c3.metric("Cost", f"${rec.cost_usd_per_ha:.0f}/ha")

st.markdown("### Expected impact per recommendation")
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
