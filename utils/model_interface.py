"""Contract between the UI and the predictive model.

The ML team owns this module. Each function currently returns a deterministic
mock result so the interface can be built in parallel; replace each body with
the real pipeline without changing signatures or return types (see
:mod:`utils.types`). If loading the trained model is expensive, cache it with
``@st.cache_resource`` and keep these functions as thin wrappers around it.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from utils.data_sources import load_satellite_snapshot, stable_seed
from utils.types import PlotRisk, Recommendation, ScenarioOutcome


def predict_scenario_outcome(plot_id: str, scenario_id: str) -> ScenarioOutcome:
    """Expected outcome of a rotation scenario on a plot, with 90% CI.

    TODO(model team): replace with the trained model's prediction.
    """
    rng = np.random.default_rng(stable_seed(f"outcome:{plot_id}:{scenario_id}"))
    base_yield = float(rng.uniform(3.0, 6.0))
    half_ci = float(rng.uniform(0.3, 1.2))
    return ScenarioOutcome(
        scenario_id=scenario_id,
        plot_id=plot_id,
        expected_yield_t_per_ha=round(base_yield, 2),
        yield_ci_low=round(max(base_yield - half_ci, 0.5), 2),
        yield_ci_high=round(base_yield + half_ci, 2),
        water_use_mm=float(rng.uniform(200, 500)),
        nutrient_loss_pct=float(rng.uniform(5, 25)),
        cost_usd_per_ha=float(rng.uniform(150, 400)),
    )


def predict_yield_trajectory(
    plot_id: str,
    scenario_id: str,
    months: int = 12,
) -> pd.DataFrame:
    """Monthly expected yield trajectory for a scenario, with 90% CI.

    Columns: date (ISO string), median, ci_low, ci_high.

    TODO(model team): replace with the model's seasonal forecast.
    """
    outcome = predict_scenario_outcome(plot_id, scenario_id)
    rng = np.random.default_rng(stable_seed(f"trajectory:{plot_id}:{scenario_id}"))

    end = date.today()
    year, month = end.year, end.month
    dates: list[str] = []
    for i in range(months - 1, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        dates.append(date(y, m, 1).isoformat())

    # Mock: yield ramps up through the season and the CI narrows as the
    # forecast horizon gets closer.
    t = np.linspace(0.0, 1.0, months)
    median = outcome.expected_yield_t_per_ha * (0.85 + 0.15 * t) + rng.normal(0, 0.05, months)
    half_ci = (outcome.yield_ci_high - outcome.yield_ci_low) / 2 * (1.4 - 0.6 * t)

    return pd.DataFrame(
        {
            "date": dates,
            "median": np.round(np.clip(median, 0.5, None), 2),
            "ci_low": np.round(np.clip(median - half_ci, 0.5, None), 2),
            "ci_high": np.round(np.clip(median + half_ci, 0.5, None), 2),
        }
    )


def compute_plot_risk(plot_id: str) -> PlotRisk:
    """Translate satellite indicators into plain-language risk levels (0..1).

    TODO(model team): replace with the model's risk quantification.
    """
    snap = load_satellite_snapshot(plot_id)
    drought_risk = float(np.clip((25 - snap.soil_moisture_pct) / 25, 0, 1))
    heat_stress_risk = float(np.clip((snap.temperature_c - 27) / 11, 0, 1))
    nutrient_depletion_risk = float(np.clip(0.6 - snap.ndvi, 0, 1))
    overall_risk = 0.4 * drought_risk + 0.35 * heat_stress_risk + 0.25 * nutrient_depletion_risk
    return PlotRisk(
        plot_id=plot_id,
        drought_risk=drought_risk,
        heat_stress_risk=heat_stress_risk,
        nutrient_depletion_risk=nutrient_depletion_risk,
        overall_risk=float(np.clip(overall_risk, 0, 1)),
    )


def generate_recommendations(plot_id: str) -> list[Recommendation]:
    """Decision-support recommendations driven by the detected anomalies.

    TODO(model team): replace with the model's recommendation engine.
    """
    risk = compute_plot_risk(plot_id)
    recs: list[Recommendation] = []

    if risk.drought_risk > 0.45:
        recs.append(
            Recommendation(
                id=f"{plot_id}-riego",
                title="Riego por goteo con déficit regulado",
                category="Práctica agronómica",
                rationale="Déficit hídrico detectado: humedad del suelo por debajo del umbral óptimo.",
                expected_impact_pct=12,
                impact_ci_low=6,
                impact_ci_high=19,
                water_delta_mm=-35,
                cost_usd_per_ha=85,
            )
        )

    if risk.heat_stress_risk > 0.45:
        recs.append(
            Recommendation(
                id=f"{plot_id}-calor",
                title="Ajuste de fecha de siembra y variedad tolerante al calor",
                category="Práctica agronómica",
                rationale="Estrés térmico elevado en la ventana crítica del cultivo.",
                expected_impact_pct=8,
                impact_ci_low=3,
                impact_ci_high=14,
                water_delta_mm=0,
                cost_usd_per_ha=25,
            )
        )

    if risk.nutrient_depletion_risk > 0.4:
        recs.append(
            Recommendation(
                id=f"{plot_id}-npk",
                title="Fertilizante NPK de liberación controlada",
                category="Fertilizante",
                rationale="NDVI bajo sugiere pérdida de nutrientes y vigor vegetal reducido.",
                expected_impact_pct=10,
                impact_ci_low=4,
                impact_ci_high=17,
                water_delta_mm=0,
                cost_usd_per_ha=60,
            )
        )

    if not recs:
        recs.append(
            Recommendation(
                id=f"{plot_id}-monitoreo",
                title="Mantener prácticas actuales y monitorear mensualmente",
                category="Práctica agronómica",
                rationale="Sin anomalías críticas detectadas en las variables satelitales.",
                expected_impact_pct=2,
                impact_ci_low=0,
                impact_ci_high=5,
                water_delta_mm=0,
                cost_usd_per_ha=10,
            )
        )

    return recs
