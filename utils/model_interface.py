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

from utils.data_sources import load_rotation_scenarios, load_satellite_snapshot, stable_seed
from utils.types import FarmerPriorities, PlotRisk, Recommendation, ScenarioOutcome


# Mock stand-in for model features: agronomic traits per crop name.
_CROP_TRAITS = {
    "Maize": {"legume": False, "deep_root": False, "cover": False},
    "Beans": {"legume": True, "deep_root": False, "cover": False},
    "Sorghum": {"legume": False, "deep_root": True, "cover": False},
    "Wheat": {"legume": False, "deep_root": True, "cover": False},
    "Alfalfa": {"legume": True, "deep_root": True, "cover": False},
    "Cover Crop": {"legume": False, "deep_root": False, "cover": True},
}


def _scenario_traits(crops: tuple[str, ...]) -> dict:
    """Derive rotation-level agronomic traits from the crop sequence."""
    unique = set(crops)
    diversity = len(unique) / max(len(crops), 1)
    has_legume = any(_CROP_TRAITS.get(c, {}).get("legume") for c in crops)
    has_deep_root = any(_CROP_TRAITS.get(c, {}).get("deep_root") for c in crops)
    has_cover = any(_CROP_TRAITS.get(c, {}).get("cover") for c in crops)
    monoculture = len(unique) == 1
    resilience = min(
        1.0,
        0.45 * diversity + (0.2 if has_legume else 0.0) + (0.15 if has_deep_root else 0.0) + (0.2 if has_cover else 0.0),
    )
    return {
        "diversity": diversity,
        "has_legume": has_legume,
        "has_deep_root": has_deep_root,
        "has_cover": has_cover,
        "monoculture": monoculture,
        "resilience": resilience,
    }


def _climate_stress(rainfall_shift_pct: float, temp_anomaly_c: float) -> tuple[float, float]:
    """Combine a rainfall shift (-30..+20 %) and heat anomaly (0..3.5 °C) into 0..1 indices."""
    drought = min(max(-rainfall_shift_pct, 0.0), 30.0) / 30.0
    heat = min(max(temp_anomaly_c, 0.0), 3.5) / 3.5
    return drought, min(1.0, 0.6 * drought + 0.4 * heat)


def _mechanism_text(traits: dict) -> str:
    parts = []
    if traits["has_legume"]:
        parts.append("Beans and alfalfa fix nitrogen from the air through root bacteria, reducing nitrogen fertilizer needs for the next crop.")
    if traits["has_deep_root"]:
        parts.append("Sorghum and wheat develop deep roots that improve water infiltration and reach residual moisture during drought.")
    if traits["has_cover"]:
        parts.append("A cover crop keeps soil covered year-round, reducing erosion and helping retain moisture.")
    if traits["monoculture"]:
        parts.append(
            "Continuous maize removes the same nutrients each cycle and leaves soil exposed between plantings; "
            "yields can drop sharply under drought or heat."
        )
    return " ".join(parts)


def predict_scenario_outcome(
    plot_id: str,
    scenario_id: str,
    rainfall_shift_pct: float = 0.0,
    temp_anomaly_c: float = 0.0,
) -> ScenarioOutcome:
    """Expected outcome of a rotation on a plot under a climate "What-If" shift.

    Drought/heat stress penalizes continuous monocultures more sharply than
    diversified regenerative rotations; uncertainty widens with the stress.

    TODO(model team): replace with the trained model's prediction.
    """
    rng = np.random.default_rng(stable_seed(f"outcome:{plot_id}:{scenario_id}"))
    base_yield = float(rng.uniform(3.0, 6.0))
    half_ci = float(rng.uniform(0.3, 1.2))
    water_base = float(rng.uniform(200, 500))
    nutrient_loss_base = float(rng.uniform(5, 25))
    cost_base = float(rng.uniform(150, 400))

    scenario = next((s for s in load_rotation_scenarios() if s.id == scenario_id), None)
    traits = _scenario_traits(scenario.crops if scenario else ("Maize", "Maize", "Maize"))
    drought, stress = _climate_stress(rainfall_shift_pct, temp_anomaly_c)

    # Yield: monocultures lose more under stress; CI widens with the stress.
    penalty = stress * (1.0 - traits["resilience"]) * 0.35
    yield_ = base_yield * (1.0 - penalty)
    half_ci_eff = half_ci * (1.0 + 0.9 * stress)

    # Water: demand rises under drought; cover/deep roots cut effective demand.
    water_save = 0.10 * traits["has_cover"] + 0.05 * traits["has_deep_root"]
    water_use = water_base * (1.0 + 0.8 * drought) * (1.0 - water_save)

    nutrient_loss = nutrient_loss_base * (1.0 - 0.25 * traits["has_legume"] - 0.10 * traits["diversity"])
    cost = cost_base + (20 if traits["has_cover"] else 0) + (15 if traits["has_legume"] else 0)

    erosion = float(
        np.clip(
            0.32 + (0.18 if traits["monoculture"] else 0.0) - 0.18 * traits["has_cover"] - 0.08 * traits["has_legume"] + rng.uniform(-0.04, 0.04),
            0.05,
            0.95,
        )
    )
    om_delta = round(
        2.2 * traits["diversity"] + (1.6 if traits["has_legume"] else 0.0) + (1.2 if traits["has_cover"] else 0.0) - (1.4 if traits["monoculture"] else 0.0),
        1,
    )
    pest_disruption = float(np.clip(0.30 + 0.40 * traits["diversity"] + (0.15 if traits["has_legume"] else 0.0) + rng.uniform(-0.04, 0.04), 0.05, 0.95))
    forage_value = float(
        np.clip(
            (0.85 if "Alfalfa" in scenario.crops else 0.55 if ("Sorgo" in scenario.crops or "Frijol" in scenario.crops) else 0.25) + rng.uniform(0, 0.05),
            0.05,
            0.95,
        )
    )

    return ScenarioOutcome(
        scenario_id=scenario_id,
        plot_id=plot_id,
        expected_yield_t_per_ha=round(yield_, 2),
        yield_ci_low=round(max(yield_ - half_ci_eff, 0.5), 2),
        yield_ci_high=round(yield_ + half_ci_eff, 2),
        water_use_mm=round(water_use, 1),
        nutrient_loss_pct=round(nutrient_loss, 1),
        cost_usd_per_ha=round(cost, 0),
        erosion_risk_score=round(erosion, 2),
        organic_matter_delta_pct=om_delta,
        pest_disruption_score=round(pest_disruption, 2),
        forage_value_score=round(forage_value, 2),
        agronomic_mechanism=_mechanism_text(traits),
        evidence_summary=(
            f"SMAP (soil moisture) and MODIS/NDVI (vegetation vigor) for {plot_id}, with seasonal rainfall from NASA POWER. "
            f"Evaluated with a {rainfall_shift_pct:+.0f}% rainfall shift and a +{temp_anomaly_c:.1f}°C temperature anomaly."
        ),
        information_gaps=(
            "Satellite pixels (~1 km²) average the entire field; in-situ soil probes and plot-level soil texture are not yet available. "
            "Uncertainty increases with simulated climate stress."
        ),
        local_review_notes=(
            "Verify in the field before making a decision: check moisture at 20 cm, visible crusting or erosion, and crop health."
        ),
    )


def predict_yield_trajectory(
    plot_id: str,
    scenario_id: str,
    months: int = 12,
    rainfall_shift_pct: float = 0.0,
    temp_anomaly_c: float = 0.0,
) -> pd.DataFrame:
    """Monthly expected yield trajectory for a scenario under a climate shift, with 90% CI.

    Columns: date (ISO string), median, ci_low, ci_high.

    TODO(model team): replace with the model's seasonal forecast.
    """
    outcome = predict_scenario_outcome(plot_id, scenario_id, rainfall_shift_pct=rainfall_shift_pct, temp_anomaly_c=temp_anomaly_c)
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


def score_scenario_priority_fit(outcome: ScenarioOutcome, priorities: FarmerPriorities) -> int:
    """Score 0-100: how well an outcome matches the farmer's stated priorities.

    Weighted blend of water conservation, soil health and market profit, plus
    forage value when relevant and a hard cap when the seasonal water budget
    is exceeded. Pure function (no randomness) so scores are stable per run.
    """
    w_water = max(priorities.water_conservation_weight, 0.0)
    w_soil = max(priorities.soil_health_weight, 0.0)
    w_profit = max(priorities.profit_market_weight, 0.0)
    total_w = w_water + w_soil + w_profit
    if total_w <= 0:
        return 50

    # Water conservation: less seasonal irrigation demand is better (200-500 mm band).
    water_score = float(np.clip(1.0 - (outcome.water_use_mm - 200.0) / 300.0, 0.0, 1.0))

    # Soil health: organic matter gain, low erosion and nutrient loss.
    om_score = float(np.clip(outcome.organic_matter_delta_pct / 5.0, 0.0, 1.0))
    soil_score = (om_score + (1.0 - outcome.erosion_risk_score) + float(np.clip(1.0 - outcome.nutrient_loss_pct / 30.0, 0.0, 1.0))) / 3.0

    # Market profit: yield per dollar of cost.
    efficiency = outcome.expected_yield_t_per_ha / max(outcome.cost_usd_per_ha, 1.0)
    profit_score = float(np.clip((efficiency - 0.008) / (0.032 - 0.008), 0.0, 1.0))

    score = (w_water * water_score + w_soil * soil_score + w_profit * profit_score) / total_w * 100.0

    if priorities.forage_priority:
        score += (outcome.forage_value_score - 0.5) * 20.0
    # No-till equipment available makes residue-cover rotations easier to adopt.
    if priorities.has_no_till_equipment and outcome.organic_matter_delta_pct > 1.0:
        score += 4.0
    # Hard constraint: seasonal water budget cap.
    if priorities.max_water_budget_mm is not None and outcome.water_use_mm > priorities.max_water_budget_mm:
        score = min(score, 35.0)

    return int(round(float(np.clip(score, 0.0, 100.0))))


def generate_recommendations(plot_id: str, priorities: FarmerPriorities | None = None) -> list[Recommendation]:
    """Decision-support recommendations driven by the detected anomalies.

    Respects farmer constraints (water budget cap, forage priority) and adds a
    transparency block to every recommendation.

    TODO(model team): replace with the model's recommendation engine.
    """
    risk = compute_plot_risk(plot_id)
    recs: list[Recommendation] = []

    if risk.drought_risk > 0.45:
        recs.append(
            Recommendation(
                id=f"{plot_id}-riego",
                title="Regulated Deficit Drip Irrigation",
                category="Agronomic Practice",
                rationale="Water deficit detected: soil moisture is below the optimal threshold.",
                expected_impact_pct=12,
                impact_ci_low=6,
                impact_ci_high=19,
                water_delta_mm=-35,
                cost_usd_per_ha=85,
                evidence_summary="SMAP indicates volumetric moisture below the optimal threshold, and NASA POWER confirms a seasonal rainfall deficit.",
                information_gaps="A SMAP pixel (~1 km²) averages the field and does not measure vertical variation in the soil profile.",
                local_review_notes="Measure moisture at 20 cm with a probe or tensiometer before adjusting irrigation.",
            )
        )

    if risk.heat_stress_risk > 0.45:
        recs.append(
            Recommendation(
                id=f"{plot_id}-calor",
                title="Adjust Planting Dates and Choose a Heat-Tolerant Variety",
                category="Agronomic Practice",
                rationale="High heat stress during a critical crop growth window.",
                expected_impact_pct=8,
                impact_ci_low=3,
                impact_ci_high=14,
                water_delta_mm=0,
                cost_usd_per_ha=25,
                evidence_summary="ECOSTRESS/MODIS indicate high surface temperatures during a critical window (NASA POWER).",
                information_gaps="Satellite temperature measures the surface, not air temperature at crop-canopy height.",
                local_review_notes="Record daily highs with a shaded thermometer and check for wilting around midday.",
            )
        )

    if risk.nutrient_depletion_risk > 0.4:
        recs.append(
            Recommendation(
                id=f"{plot_id}-npk",
                title="Controlled-Release NPK Fertilizer",
                category="Fertilizer",
                rationale="Low NDVI may indicate nutrient loss and reduced vegetation vigor.",
                expected_impact_pct=10,
                impact_ci_low=4,
                impact_ci_high=17,
                water_delta_mm=0,
                cost_usd_per_ha=60,
                evidence_summary="Low NDVI (MODIS) may indicate nitrogen deficiency; the 12-month trend confirms the decline.",
                information_gaps="NDVI cannot identify whether nitrogen, phosphorus, or potassium is limiting, or indicate organic matter levels.",
                local_review_notes="Collect a 0–20 cm soil sample for laboratory analysis before applying fertilizer.",
            )
        )

    if not recs:
        recs.append(
            Recommendation(
                id=f"{plot_id}-monitoreo",
                title="Maintain Current Practices and Monitor Monthly",
                category="Agronomic Practice",
                rationale="No critical anomalies were detected in the satellite indicators.",
                expected_impact_pct=2,
                impact_ci_low=0,
                impact_ci_high=5,
                water_delta_mm=0,
                cost_usd_per_ha=10,
                evidence_summary="SMAP, MODIS, and POWER indicators have remained within normal ranges over the past 12 months.",
                information_gaps="There are no in-situ probes; each pixel averages microzones across the field.",
                local_review_notes="Walk the field monthly and record local observations (rainfall, moisture, pests).",
            )
        )

    if priorities is not None:
        # Hard constraint: skip water-adding recommendations beyond the budget.
        if priorities.max_water_budget_mm is not None:
            recs = [r for r in recs if r.water_delta_mm <= 0 or r.water_delta_mm <= priorities.max_water_budget_mm]
        # Forage value needed: add a forage/cover-crop option.
        if priorities.forage_priority and not any("forraje" in r.id for r in recs):
            recs.append(
                Recommendation(
                    id=f"{plot_id}-forraje",
                    title="Add Alfalfa or a Forage Cover Crop",
                    category="Agronomic Practice",
                    rationale="Stated priority: forage value for livestock in addition to grain.",
                    expected_impact_pct=6,
                    impact_ci_low=2,
                    impact_ci_high=11,
                    water_delta_mm=-10,
                    cost_usd_per_ha=45,
                    evidence_summary="Seasonal NDVI (MODIS) and SMAP soil moisture support planting forage during the identified window.",
                    information_gaps="Livestock demand and local forage prices are not available.",
                    local_review_notes="Confirm pasture availability and market conditions before planting.",
                )
            )

    return recs
