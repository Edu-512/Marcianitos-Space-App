"""Typed data contracts shared by the UI and the model layer.

These dataclasses are the interface between the Streamlit frontend (developed
by the UI team) and the predictive backend (developed by the ML team). Change
a field only with agreement from both teams, since every page and every model
function depends on them.
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
    category: str  # "Fertilizante" | "Práctica agronómica"
    rationale: str  # which detected anomaly drives this recommendation
    expected_impact_pct: float  # expected yield / health improvement (%)
    impact_ci_low: float
    impact_ci_high: float
    water_delta_mm: float  # extra irrigation needed; negative = savings
    cost_usd_per_ha: float
