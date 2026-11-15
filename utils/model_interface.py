"""Contract between the UI and the predictive model.

Backed by the Butler County, Iowa crop-rotation model (``model/``): a
deterministic pipeline whose output (``model/datos_ui/resultado_todas.json``)
holds 167 plots × 3 year types × 3 plans. Nothing is trained or simulated here:
these functions read that output, convert US units to the metric contract
(``model/units.py``) and fill :mod:`utils.types`. Signatures are unchanged.

Golden rule: a contract field the model does not produce keeps its default
(or NaN when it has none) and is declared in ``information_gaps``.
"""

from __future__ import annotations

import math

from typing import Any

import numpy as np
import pandas as pd

from model import units
from model.loader import confidence_label, load_metadata, load_results, plan_name, scenario_label
from utils.data_sources import load_rotation_scenarios
from utils.types import FarmerPriorities, PlotRisk, Recommendation, ScenarioOutcome

_NAN = float("nan")

#: App scenario id -> model plan id.
_PLAN_IDS = {
    "maiz-continuo": "maiz_continuo",
    "maiz-soya": "maiz_soya",
    "maiz-soya-cobertura": "maiz_soya_cobertura",
}

#: Tolerable soil loss (SSURGO T factor), 5 short tons/acre/year.
EROSION_LIMIT_T_PER_ACRE = 5.0

#: Agronomic traits per crop, used only for the plain-language mechanism text.
_CROP_TRAITS = {
    "Corn": {"legume": False, "cover": False},
    "Soybean": {"legume": True, "cover": False},
    "Cover Crop": {"legume": False, "cover": True},
}

_RAINFED_GAP = (
    "Butler County farms are rain-fed: there is no irrigation demand, so water use is shown as 0 mm."
)
_NOT_ESTIMATED_GAP = (
    "Nutrient loss, organic-matter change, pest-cycle disruption and forage value are not estimated for these plans."
)


# --- Lookups -------------------------------------------------------------------


def _scenario_key(rainfall_shift_pct: float, temp_anomaly_c: float) -> str:
    """Map the contract's two climate numbers to the nearest measured year type."""
    if rainfall_shift_pct <= -15 or temp_anomaly_c >= 1.5:
        return "seco_caluroso"
    if rainfall_shift_pct >= 10:
        return "humedo_primavera"
    return "normal"


def _record(plot_id: str) -> dict[str, Any]:
    record = load_results().get(str(plot_id))
    if record is None:
        raise KeyError(f"No model results for plot {plot_id!r}.")
    return record


def _plan(record: dict[str, Any], scenario_key: str, plan_id: str) -> dict[str, Any]:
    for plan in record["escenarios"][scenario_key]["planes"]:
        if plan["id"] == plan_id:
            return plan
    raise KeyError(f"Plan {plan_id!r} not found for plot {record['parcela']['id']}.")


def _ordinal(value: float) -> str:
    n = int(round(value))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _climate_note(scenario_key: str, scenario: dict[str, Any]) -> str:
    c = scenario["clima"]
    years = ", ".join(str(y) for y in scenario["anios_historicos"])
    return (
        f"{scenario_label(scenario_key)}: based on {scenario['n_anios']} measured years with similar weather ({years}). "
        f"August root-zone soil moisture around the {_ordinal(c['humedad_raices_agosto_percentil'])} percentile of 2000–2025; "
        f"{c['dias_arriba_35c']:.1f} days above 35 °C; May–June rainfall around the "
        f"{_ordinal(c['lluvia_mayo_junio_percentil'])} percentile; July average {c['temperatura_julio_c']:.1f} °C."
    )


def _mechanism_text(crops: tuple[str, ...]) -> str:
    has_legume = any(_CROP_TRAITS.get(c, {}).get("legume") for c in crops)
    has_cover = any(_CROP_TRAITS.get(c, {}).get("cover") for c in crops)
    parts = []
    if has_legume:
        parts.append("Soybeans fix nitrogen from the air through root bacteria, so corn after soybeans needs less nitrogen fertilizer.")
    if has_cover:
        parts.append("A cover crop keeps the soil covered between cash crops, cutting erosion.")
    if len(set(crops)) == 1:
        parts.append(
            "Continuous corn removes the same nutrients every year, needs more nitrogen and keeps corn pests "
            "and residue on the field; yields tend to fall more in bad years."
        )
    return " ".join(parts)


def _evidence_text(plan_id: str) -> str:
    sources = load_metadata()["sources"]
    keys = ["rendimiento_y_precios", "suelo", "rotacion", "clima", "costos", "nitrogeno"]
    if plan_id == "maiz_continuo":
        keys.append("penalizacion_rotacion")
    return " · ".join(sources[k] for k in keys if k in sources)


def _gaps_text(plan_id: str, confidence: str) -> str:
    warnings = list(load_metadata()["warnings"])
    if plan_id == "maiz_continuo":
        # The literature-based penalty is the main limit of this plan: lead with it.
        warnings.sort(key=lambda w: "continuous corn" not in w)
    gaps = [*warnings, _RAINFED_GAP,
            "Yield shown is corn yield; soybean-year yield is included in revenue but not reported separately.",
            _NOT_ESTIMATED_GAP]
    if plan_id == "maiz_soya_cobertura":
        gaps.append(
            "The cost includes 37 USD/acre to establish the cover crop (ISU CARD). Iowa cost-share programs "
            "or grazing the cover crop can lower that cost; this is not modeled."
        )
    gaps.append(f"Confidence for this plan: {confidence_label(confidence)}.")
    return " ".join(gaps)


# --- Contract functions ----------------------------------------------------------


def predict_scenario_outcome(
    plot_id: str,
    scenario_id: str,
    rainfall_shift_pct: float = 0.0,
    temp_anomaly_c: float = 0.0,
) -> ScenarioOutcome:
    """Model result for a rotation on a plot in the year type nearest the climate shift.

    The two climate numbers select one of three measured year types (see
    :func:`_scenario_key`). Ranges are the model's 10th–90th percentiles.
    """
    if scenario_id not in _PLAN_IDS:
        raise KeyError(f"Unknown rotation scenario {scenario_id!r}.")
    plan_id = _PLAN_IDS[scenario_id]
    key = _scenario_key(rainfall_shift_pct, temp_anomaly_c)
    record = _record(plot_id)
    plan = _plan(record, key, plan_id)
    scenario = next((s for s in load_rotation_scenarios() if s.id == scenario_id), None)

    yield_bu = plan["rendimiento_maiz_bu_acre"]
    econ = plan["economia"]
    erosion_t_acre = float(plan["suelo"]["erosion_ton_acre_anio"])

    return ScenarioOutcome(
        scenario_id=scenario_id,
        plot_id=str(plot_id),
        expected_yield_t_per_ha=units.corn_bu_acre_to_t_ha(yield_bu["p50"]),
        yield_ci_low=units.corn_bu_acre_to_t_ha(yield_bu["p10"]),
        yield_ci_high=units.corn_bu_acre_to_t_ha(yield_bu["p90"]),
        water_use_mm=0.0,  # rain-fed: no irrigation demand (declared in information_gaps)
        nutrient_loss_pct=_NAN,  # not produced by the model; no default exists
        cost_usd_per_ha=units.usd_acre_to_usd_ha(econ["costo_usd_acre"]),
        erosion_risk_score=min(erosion_t_acre / EROSION_LIMIT_T_PER_ACRE, 1.0),
        # organic_matter_delta_pct, pest_disruption_score, forage_value_score:
        # not produced -> contract defaults, declared in information_gaps.
        agronomic_mechanism=_mechanism_text(scenario.crops if scenario else ()),
        evidence_summary=_evidence_text(plan_id),
        information_gaps=_gaps_text(plan_id, plan.get("confianza", "")),
        local_review_notes=(
            "Before deciding, compare these costs with your real rent and input prices, check how the field "
            "drains after heavy spring rain, and look for erosion on slopes."
        ),
        revenue_usd_per_ha=units.usd_acre_to_usd_ha(econ["ingreso_usd_acre"]["p50"]),
        margin_usd_per_ha=units.usd_acre_to_usd_ha(econ["margen_usd_acre"]["p50"]),
        margin_ci_low=units.usd_acre_to_usd_ha(econ["margen_usd_acre"]["p10"]),
        margin_ci_high=units.usd_acre_to_usd_ha(econ["margen_usd_acre"]["p90"]),
        nitrogen_kg_per_ha=units.lb_acre_to_kg_ha(plan["fertilizante"]["nitrogeno_lb_acre"]),
        prob_unplanted_pct=float(plan["riesgo"]["prob_no_poder_sembrar_pct"]),
        prob_big_loss_pct=float(plan["riesgo"]["prob_caida_mayor_20_pct"]),
        scenario_climate_note=_climate_note(key, record["escenarios"][key]),
        erosion_t_per_ha=units.short_tons_acre_to_t_ha(erosion_t_acre),
    )


def predict_yield_trajectory(
    plot_id: str,
    scenario_id: str,
    months: int = 12,
    rainfall_shift_pct: float = 0.0,
    temp_anomaly_c: float = 0.0,
) -> pd.DataFrame:
    """Approximate in-season corn yield path ending at the model's annual result.

    Columns: date (ISO string), median, ci_low, ci_high.

    The model produces an annual result, not a monthly curve. This keeps the
    previous ramp shape but anchors its last point exactly to the real p50 and
    p10–p90 range; earlier months are an approximation (wider range, lower
    median). Months end at the 2026 harvest (October) — no ``date.today()``.
    """
    outcome = predict_scenario_outcome(plot_id, scenario_id, rainfall_shift_pct=rainfall_shift_pct, temp_anomaly_c=temp_anomaly_c)
    end = pd.Period("2026-10", freq="M")
    dates = [(end - i).to_timestamp().date().isoformat() for i in range(months - 1, -1, -1)]

    t = np.linspace(0.0, 1.0, months)
    widen = 1.4 - 0.4 * t  # 1.4× the real range early in the season, exactly 1× at harvest
    median = outcome.expected_yield_t_per_ha * (0.85 + 0.15 * t)
    low = median - (outcome.expected_yield_t_per_ha - outcome.yield_ci_low) * widen
    high = median + (outcome.yield_ci_high - outcome.expected_yield_t_per_ha) * widen

    return pd.DataFrame(
        {
            "date": dates,
            "median": np.round(median, 2),
            "ci_low": np.round(np.clip(low, 0.0, None), 2),
            "ci_high": np.round(high, 2),
        }
    )


def compute_plot_risk(plot_id: str) -> PlotRisk:
    """Risk indices (0..1) from measured weather and the plot's soil.

    The function has no year-type argument, so weather uses all 26 measured
    years: each year type's indicators are weighted by how many years it holds.
    NASA POWER is a single county point, so drought and heat are the same for
    every plot. Drought risk therefore combines that county exposure with the
    plot's own vulnerability (water the soil holds, SSURGO 0-150 cm): a sandy
    13.7 cm soil gets about twice the risk of a 23.6 cm soil under the same
    weather. Heat has no plot-level modifier and stays county-wide. Nutrient
    depletion comes from the plot's SSURGO organic matter.
    """
    record = _record(plot_id)
    scenarios = record["escenarios"].values()
    years = sum(s["n_anios"] for s in scenarios)
    august_pct = sum(s["clima"]["humedad_raices_agosto_percentil"] * s["n_anios"] for s in scenarios) / years
    hot_days = sum(s["clima"]["dias_arriba_35c"] * s["n_anios"] for s in scenarios) / years
    organic_matter = float(record["parcela"]["suelo"]["materia_organica_pct"])
    available_water_cm = float(record["parcela"]["suelo"]["agua_disponible_cm"])

    exposure = 1.0 - august_pct / 100.0
    vulnerability = float(np.clip((24.0 - available_water_cm) / 12.0, 0.3, 1.0))
    drought_risk = float(np.clip(exposure * vulnerability * 1.6, 0, 1))
    heat_stress_risk = float(np.clip(hot_days / 10.0, 0, 1))
    nutrient_depletion_risk = float(np.clip(1.0 - organic_matter / 6.0, 0, 1))
    overall_risk = 0.4 * drought_risk + 0.35 * heat_stress_risk + 0.25 * nutrient_depletion_risk
    return PlotRisk(
        plot_id=str(plot_id),
        drought_risk=drought_risk,
        heat_stress_risk=heat_stress_risk,
        nutrient_depletion_risk=nutrient_depletion_risk,
        overall_risk=float(np.clip(overall_risk, 0, 1)),
    )


def score_scenario_priority_fit(outcome: ScenarioOutcome, priorities: FarmerPriorities) -> int:
    """Score 0-100: how well an outcome matches the farmer's stated priorities.

    Adjusted for the Butler County model (rain-fed, margin-based):
    - "Water" block: with no irrigation (``water_use_mm == 0``) the old water
      score would be constant. It now uses the risk of not being able to plant
      in a wet spring, inverted (0 % -> 1.0, 5 % or more -> 0.0): managing
      excess water is the water question in this county.
    - Soil block: erosion only, as ``limit / (limit + erosion)`` (1.0 with no
      loss, 0.5 at the tolerable limit). It never caps, so on steep fields a
      cover crop that cuts 14 t to 5.6 t still scores better than the plain
      rotation. Organic-matter change and nutrient loss are not produced by
      the model, so they do not enter the score.
    - Profit block: the p50 margin per hectare, scaled over -500..+100 USD/ha,
      the span of the rotation and cover-crop results. Continuous corn in a
      dry year falls below it and scores 0.
      With the 37 USD/acre cover-crop cost, a high soil weight picks the cover
      crop on every plot and a high income weight picks the plain rotation.
    - Forage: the model has no forage value, so the forage toggle no longer
      changes the score.
    Pure function (no randomness) so scores are stable per run.
    """
    w_water = max(priorities.water_conservation_weight, 0.0)
    w_soil = max(priorities.soil_health_weight, 0.0)
    w_profit = max(priorities.profit_market_weight, 0.0)
    total_w = w_water + w_soil + w_profit
    if total_w <= 0:
        return 50

    water_score = float(np.clip(1.0 - outcome.prob_unplanted_pct / 5.0, 0.0, 1.0))
    if math.isnan(outcome.erosion_t_per_ha):
        soil_score = float(np.clip(1.0 - outcome.erosion_risk_score, 0.0, 1.0))
    else:
        limit_t_ha = units.short_tons_acre_to_t_ha(EROSION_LIMIT_T_PER_ACRE)
        soil_score = limit_t_ha / (limit_t_ha + max(outcome.erosion_t_per_ha, 0.0))
    profit_score = float(np.clip((outcome.margin_usd_per_ha + 500.0) / 600.0, 0.0, 1.0))

    score = (w_water * water_score + w_soil * soil_score + w_profit * profit_score) / total_w * 100.0

    # No-till equipment makes residue-cover rotations easier to adopt (inert
    # while organic_matter_delta_pct is not produced; kept for a future model).
    if priorities.has_no_till_equipment and outcome.organic_matter_delta_pct > 1.0:
        score += 4.0
    # Hard constraint: seasonal irrigation cap (never binds while rain-fed).
    if priorities.max_water_budget_mm is not None and outcome.water_use_mm > priorities.max_water_budget_mm:
        score = min(score, 35.0)

    return int(round(float(np.clip(score, 0.0, 100.0))))


def generate_recommendations(plot_id: str, priorities: FarmerPriorities | None = None) -> list[Recommendation]:
    """Actions triggered by the plot's real results in a normal year.

    Numbers the model does not quantify (impact, cost of an action) are NaN and
    the page shows them as not estimated. Irrigation advice is gone: the county
    is rain-fed.
    """
    record = _record(plot_id)
    plans = {p["id"]: p for p in record["escenarios"]["normal"]["planes"]}
    sources = load_metadata()["sources"]
    recs: list[Recommendation] = []

    unplanted = max(p["riesgo"]["prob_no_poder_sembrar_pct"] for p in plans.values())
    if unplanted > 5:
        # The wet-spring year type repeats the 2019 event (factor 1.0), so its
        # value is the share of this field measured unplanted in 2019.
        observed_2019 = max(p["riesgo"]["prob_no_poder_sembrar_pct"]
                            for p in record["escenarios"]["humedo_primavera"]["planes"])
        recs.append(Recommendation(
            id=f"{plot_id}-drenaje",
            title="Improve Drainage or Plan an Early Planting Window",
            category="Agronomic Practice",
            rationale=(
                f"In 2019, {observed_2019:.0f}% of this field could not be planted because of a wet spring. "
                f"In a normal year we expect about {unplanted:.0f}% to go unplanted."
            ),
            expected_impact_pct=_NAN, impact_ci_low=_NAN, impact_ci_high=_NAN,
            water_delta_mm=0.0, cost_usd_per_ha=_NAN,
            evidence_summary=" · ".join(sources[k] for k in ("riesgo_no_sembrar", "clima") if k in sources),
            information_gaps=(
                "This comes from a single observed year (2019), scaled for each year type. "
                "The benefit and cost of drainage work are not estimated."
            ),
            local_review_notes="Walk the field after heavy spring rain and mark where water stands.",
        ))

    limit_t_ha = units.short_tons_acre_to_t_ha(EROSION_LIMIT_T_PER_ACRE)
    over = {pid: p for pid, p in plans.items() if pid != "maiz_soya_cobertura" and p["suelo"]["arriba_del_limite"]}
    cover = plans.get("maiz_soya_cobertura")
    if over and cover:
        worst = max(over.values(), key=lambda p: p["suelo"]["erosion_ton_acre_anio"])
        worst_t = worst["suelo"]["erosion_ton_acre_anio"]
        cover_t = cover["suelo"]["erosion_ton_acre_anio"]
        reduction = (1 - cover_t / worst_t) * 100 if worst_t else _NAN
        still_over = " It would still be above the limit." if cover["suelo"]["arriba_del_limite"] else ""
        base = plans.get("maiz_soya")
        extra_cost = (cover["economia"]["costo_usd_acre"] - base["economia"]["costo_usd_acre"]) if base else _NAN
        money = ""
        if base:
            money = (
                f" It costs about {units.usd_acre_to_usd_ha(extra_cost):,.0f} USD/ha more than {plan_name('maiz_soya')}: "
                f"money left goes from {units.usd_acre_to_usd_ha(base['economia']['margen_usd_acre']['p50']):,.0f} "
                f"to {units.usd_acre_to_usd_ha(cover['economia']['margen_usd_acre']['p50']):,.0f} USD/ha in a normal year."
            )
        recs.append(Recommendation(
            id=f"{plot_id}-cobertura",
            title="Add a Cover Crop to the Rotation",
            category="Agronomic Practice",
            rationale=(
                f"Soil loss reaches {units.short_tons_acre_to_t_ha(worst_t):.1f} t/ha per year with "
                f"{plan_name(worst['id'])}, above the tolerable {limit_t_ha:.1f} t/ha. With a cover crop it drops to "
                f"{units.short_tons_acre_to_t_ha(cover_t):.1f} t/ha.{still_over}{money}"
            ),
            expected_impact_pct=reduction, impact_ci_low=_NAN, impact_ci_high=_NAN,
            water_delta_mm=0.0,
            cost_usd_per_ha=units.usd_acre_to_usd_ha(extra_cost) if base else _NAN,
            evidence_summary=" · ".join(
                [sources[k] for k in ("suelo", "costo_cobertura") if k in sources]
                + ["Erosion estimated with RUSLE from slope and soil erodibility."]
            ),
            information_gaps=(
                "Impact is the estimated cut in soil loss, not a yield change. Iowa cost-share programs or "
                "grazing the cover crop can lower its cost; this is not modeled."
            ),
            local_review_notes="Look for rills and gullies on the steepest parts of the field after spring rains.",
        ))

    margins = {pid: p["economia"]["margen_usd_acre"]["p50"] for pid, p in plans.items()}
    best_id = max(margins, key=margins.get)
    if margins[best_id] < 0:
        recs.append(Recommendation(
            id=f"{plot_id}-margen",
            title="No Plan Leaves a Profit This Year: Choose the One That Loses Least",
            category="Agronomic Practice",
            rationale=(
                f"In a normal year every plan loses money on this field once costs (including land rent) are paid. "
                f"{plan_name(best_id)} loses least: about {units.usd_acre_to_usd_ha(margins[best_id]):,.0f} USD/ha."
            ),
            expected_impact_pct=_NAN, impact_ci_low=_NAN, impact_ci_high=_NAN,
            water_delta_mm=0.0, cost_usd_per_ha=_NAN,
            evidence_summary=" · ".join(sources[k] for k in ("rendimiento_y_precios", "costos") if k in sources),
            information_gaps="Costs include land rent; if you own the land, your margins are higher.",
            local_review_notes="Compare with your real rent, input prices and any marketing contracts.",
        ))

    if not recs:
        recs.append(Recommendation(
            id=f"{plot_id}-monitoreo",
            title="Keep Your Current Plan and Review It Each Season",
            category="Agronomic Practice",
            rationale="None of the checked conditions (planting risk, erosion above the limit, losses in every plan) apply to this field.",
            expected_impact_pct=_NAN, impact_ci_low=_NAN, impact_ci_high=_NAN,
            water_delta_mm=0.0, cost_usd_per_ha=_NAN,
            evidence_summary=" · ".join(load_metadata()["sources"].values()),
            information_gaps="Only planting risk, erosion and margin are checked.",
            local_review_notes="Walk the field each season and note drainage, erosion and crop condition.",
        ))

    return recs
