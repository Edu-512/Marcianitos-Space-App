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
    "Maíz": {"legume": False, "deep_root": False, "cover": False},
    "Frijol": {"legume": True, "deep_root": False, "cover": False},
    "Sorgo": {"legume": False, "deep_root": True, "cover": False},
    "Trigo": {"legume": False, "deep_root": True, "cover": False},
    "Alfalfa": {"legume": True, "deep_root": True, "cover": False},
    "Cultivo de cobertura": {"legume": False, "deep_root": False, "cover": True},
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
        parts.append("El frijol/alfalfa fija nitrógeno del aire con bacterias en sus raíces, abaratando el fertilizante N del siguiente cultivo.")
    if traits["has_deep_root"]:
        parts.append("El sorgo/trigo desarrolla raíces profundas que infiltran agua y acceden a humedad residual durante la sequía.")
    if traits["has_cover"]:
        parts.append("El cultivo de cobertura mantiene el suelo cubierto todo el año: menos erosión y más humedad retenida.")
    if traits["monoculture"]:
        parts.append(
            "El maíz continuo extrae los mismos nutrientes cada ciclo y deja el suelo expuesto entre siembras; "
            "bajo sequía o calor su rendimiento cae con fuerza."
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
    traits = _scenario_traits(scenario.crops if scenario else ("Maíz", "Maíz", "Maíz"))
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
            f"SMAP (humedad del suelo) y MODIS/NDVI (vigor) para {plot_id}, con lluvia estacional de NASA POWER. "
            f"Evaluado con {rainfall_shift_pct:+.0f}% de cambio de lluvia y +{temp_anomaly_c:.1f}°C de anomalía térmica."
        ),
        information_gaps=(
            "Los píxeles satelitales (~1 km²) promedian todo el lote; aún no hay sondas de suelo in-situ ni "
            "textura por parcela. La incertidumbre crece con el estrés climático simulado."
        ),
        local_review_notes=(
            "Verificar en campo antes de decidir: humedad a 20 cm, costra/erosión visible y estado sanitario del cultivo."
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
                title="Riego por goteo con déficit regulado",
                category="Práctica agronómica",
                rationale="Déficit hídrico detectado: humedad del suelo por debajo del umbral óptimo.",
                expected_impact_pct=12,
                impact_ci_low=6,
                impact_ci_high=19,
                water_delta_mm=-35,
                cost_usd_per_ha=85,
                evidence_summary="SMAP muestra humedad volumétrica por debajo del umbral óptimo y NASA POWER confirma déficit de lluvia estacional.",
                information_gaps="El píxel SMAP (~1 km²) promedia el lote; no mide la estratificación vertical del perfil del suelo.",
                local_review_notes="Medir humedad a 20 cm con sonda o tensiómetro antes de calibrar el riego.",
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
                evidence_summary="ECOSTRESS/MODIS indican temperatura superficial alta en la ventana crítica (NASA POWER).",
                information_gaps="La temperatura satelital es de superficie, no del aire a altura de planta.",
                local_review_notes="Registrar máximas diarias con termómetro de sombra y revisar marchitez al mediodía.",
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
                evidence_summary="NDVI (MODIS) bajo sugiere deficiencia de nitrógeno; la tendencia de 12 meses confirma el descenso.",
                information_gaps="El NDVI no distingue entre N, P o K limitantes ni el estado de la materia orgánica.",
                local_review_notes="Tomar muestra de suelo (0-20 cm) para análisis de laboratorio antes de aplicar.",
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
                evidence_summary="SMAP, MODIS y POWER dentro de rangos normales en los últimos 12 meses.",
                information_gaps="Ausencia de sondas in-situ; la resolución del píxel promedia microzonas del lote.",
                local_review_notes="Recorrer el lote mensualmente y anotar observaciones locales (lluvia, humedad, plagas).",
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
                    title="Incorporar alfalfa o cultivo de cobertura forrajero",
                    category="Práctica agronómica",
                    rationale="Prioridad declarada: valor forrajero para el ganado además del grano.",
                    expected_impact_pct=6,
                    impact_ci_low=2,
                    impact_ci_high=11,
                    water_delta_mm=-10,
                    cost_usd_per_ha=45,
                    evidence_summary="El NDVI estacional (MODIS) y la humedad SMAP soportan un forrajero en la ventana identificada.",
                    information_gaps="No hay datos de demanda ganadera ni precios locales de forraje.",
                    local_review_notes="Confirmar disponibilidad de pastura y mercado antes de sembrar.",
                )
            )

    return recs
