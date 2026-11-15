"""Typed data contracts shared by the UI and the model layer.

These dataclasses are the interface between the Streamlit frontend (developed
by the UI team) and the predictive backend (developed by the ML team). Change
a field only with agreement from both teams, since every page and every model
function depends on them. New fields always ship with defaults so existing
call sites keep working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plot:
    """A farm plot (parcel) with its geospatial identity."""

    id: str
    name: str
    lat: float
    lon: float
    area_hectares: float
    current_crop: str
    # Field boundary as (lat, lon) vertices; empty tuple = no geometry yet.
    polygon: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class FarmerPriorities:
    """Farmer-stated preferences that steer scenario scoring and recommendations."""

    water_conservation_weight: float = 0.5  # 0.0..1.0
    soil_health_weight: float = 0.5  # 0.0..1.0
    profit_market_weight: float = 0.5  # 0.0..1.0
    forage_priority: bool = False  # livestock feed value matters
    has_no_till_equipment: bool = True  # residue-cover rotations are feasible
    max_water_budget_mm: float | None = None  # hard seasonal irrigation cap


@dataclass(frozen=True)
class SeasonalWindow:
    """A flagged period of the year (bare soil or climate hazard) for one plot."""

    start_month: str  # "01".."12"
    end_month: str  # "01".."12"; may wrap around December -> January
    window_type: str  # e.g. "Bare Soil (Erosion Risk)", "Peak Heat Stress", "Frost Risk"
    severity: str  # "Low" | "Moderate" | "High"
    plain_explanation: str


@dataclass(frozen=True)
class SatelliteSnapshot:
    """Latest satellite-derived indicators for one plot (NASA multispectral stack)."""

    plot_id: str
    date: str  # ISO date, e.g. "2026-11-14"
    precipitation_mm: float  # recent seasonal rainfall
    soil_moisture_pct: float  # volumetric water content (%)
    temperature_c: float  # surface / air temperature (°C)
    ndvi: float  # vegetation health index (0..1)
    water_availability_idx: float  # hydrological availability index (0..1)


@dataclass(frozen=True)
class RotationScenario:
    """A crop rotation sequence to evaluate."""

    id: str
    name: str
    crops: tuple[str, ...]  # one entry per season of the cycle


@dataclass(frozen=True)
class ScenarioOutcome:
    """Model output for one rotation scenario on a plot, with uncertainty (90% CI)."""

    scenario_id: str
    plot_id: str
    expected_yield_t_per_ha: float
    yield_ci_low: float
    yield_ci_high: float
    water_use_mm: float  # seasonal irrigation demand
    nutrient_loss_pct: float  # estimated soil nutrient depletion (%)
    cost_usd_per_ha: float
    # --- tradeoff + transparency fields (added with defaults) -----------------
    erosion_risk_score: float = 0.3  # 0..1, lower is better
    organic_matter_delta_pct: float = 0.0  # expected change over the cycle (%)
    pest_disruption_score: float = 0.5  # 0..1, higher is better (pest cycles broken)
    forage_value_score: float = 0.3  # 0..1, feed value of crops/residues
    agronomic_mechanism: str = ""  # plain language: how the crops help soil/water
    evidence_summary: str = ""  # which satellite variables support this result
    information_gaps: str = ""  # what the data cannot tell us yet
    local_review_notes: str = ""  # ground checks a farmer should perform
    # --- economics + risk from the Butler County model (added with defaults) --
    # The model's ranges are 10th-90th percentile (an 80% range), so the
    # yield_ci_* and margin_ci_* fields carry p10/p90 when it is the source.
    revenue_usd_per_ha: float = 0.0
    margin_usd_per_ha: float = 0.0
    margin_ci_low: float = 0.0
    margin_ci_high: float = 0.0
    nitrogen_kg_per_ha: float = 0.0
    prob_unplanted_pct: float = 0.0  # risk of not being able to plant
    prob_big_loss_pct: float = 0.0  # probability of a yield drop larger than 20 %
    scenario_climate_note: str = ""  # the scenario's weather, in plain language
    erosion_t_per_ha: float = float("nan")  # soil loss per year, uncapped (NaN when not produced)


@dataclass(frozen=True)
class PlotRisk:
    """Aggregated risk indicators for a plot, translated from satellite metrics (0..1)."""

    plot_id: str
    drought_risk: float
    heat_stress_risk: float
    nutrient_depletion_risk: float
    overall_risk: float


@dataclass(frozen=True)
class Recommendation:
    """A decision-support recommendation (fertilizer or agronomic practice)."""

    id: str
    title: str
    category: str  # "Fertilizer" | "Agronomic Practice"
    rationale: str  # which detected anomaly drives this recommendation
    expected_impact_pct: float  # expected yield / health improvement (%)
    impact_ci_low: float
    impact_ci_high: float
    water_delta_mm: float  # extra irrigation needed; negative = savings
    cost_usd_per_ha: float
    # --- transparency fields (added with defaults) ----------------------------
    evidence_summary: str = ""  # which satellite variables support this recommendation
    information_gaps: str = ""  # limits of the current data
    local_review_notes: str = ""  # human-in-the-loop ground checks
