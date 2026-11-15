"""Presentation adapters for Compare Crops; no model or economic calculations."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from typing import Any

import streamlit as st
from utils.data_sources import load_rotation_scenarios
from utils.model_interface import predict_scenario_outcome
from utils.types import RotationScenario, ScenarioOutcome


@dataclass(frozen=True)
class PlanCard:
    key: str
    title: str
    description: str
    art: str


PLANS = (
    PlanCard("continuous", "Continuous maize", "Keep maize as the main crop over consecutive seasons.", "maize"),
    PlanCard("maize-soy", "Maize & soybean", "Alternate maize and soybean across seasons.", "soy"),
    PlanCard("cover", "Rotation with cover", "Explore maize, soybean and a cover crop; timing follows the supplied plan.", "cover"),
)
# Presentation IDs only: the backend accepts rainfall/temperature parameters,
# not climate IDs. Dry uses the endpoints of the pre-existing What-If controls.
CLIMATES: dict[str, dict[str, Any]] = {
    "normal": {"title":"Reference season", "description":"Reference climate inputs.", "icon":"partly_cloudy_day", "rain":0.0, "heat":0.0},
    "dry": {"title":"Dry & hot", "description":"Less rain and more heat.", "icon":"sunny", "rain":-30.0, "heat":3.5},
    "wet": {"title":"Wet spring", "description":"More rain during planting.", "icon":"rainy", "rain":None, "heat":None},
}


def finite(value: Any) -> float | None:
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):
        return None


def formatted(value: Any, decimals: int=2, suffix: str="") -> str:
    n=finite(value)
    return f"{n:,.{decimals}f}{suffix}" if n is not None else "Not available"


def resolve_plans(scenarios: Sequence[RotationScenario]) -> dict[str, RotationScenario | None]:
    """Map definitions, never substitute beans/sorghum for soybean."""
    def normalize(crop: str) -> str:
        name=crop.casefold().strip()
        return {"corn":"maize","soybeans":"soybean","soy":"soybean"}.get(name,name)
    result: dict[str, RotationScenario | None] = {p.key:None for p in PLANS}
    for scenario in scenarios:
        crops={normalize(c) for c in scenario.crops}
        if crops == {"maize"} and result["continuous"] is None:
            result["continuous"]=scenario
        elif crops == {"maize","soybean"} and result["maize-soy"] is None:
            result["maize-soy"]=scenario
        elif crops == {"maize","soybean","cover crop"} and result["cover"] is None:
            result["cover"]=scenario
    return result


@st.cache_data(ttl=300, max_entries=128)
def outcome_for(plot_id: str, scenario_id: str, rain: float, heat: float) -> ScenarioOutcome | None:
    try:
        outcome=predict_scenario_outcome(plot_id,scenario_id,rainfall_shift_pct=rain,temp_anomaly_c=heat)
        if outcome.plot_id == plot_id and outcome.scenario_id == scenario_id:
            return outcome
    except Exception:
        pass
    return None


def selected_outcomes(plot_id: str, climate: str, plans: dict[str, RotationScenario | None]) -> dict[str, ScenarioOutcome | None]:
    weather=CLIMATES[climate]
    if weather["rain"] is None:
        return {key:None for key in plans}
    return {key:outcome_for(plot_id,plan.id,float(weather["rain"]),float(weather["heat"])) if plan else None for key,plan in plans.items()}


def yield_interval(outcome: ScenarioOutcome | None) -> tuple[float,float,float] | None:
    if outcome is None:
        return None
    lo,mid,hi=(finite(outcome.yield_ci_low),finite(outcome.expected_yield_t_per_ha),finite(outcome.yield_ci_high))
    if lo is None or mid is None or hi is None or not lo <= mid <= hi:
        return None
    return lo,mid,hi


def reconcile_selection(plot_id: str, plans: dict[str, RotationScenario | None]) -> None:
    if st.session_state.get("comparison_plot_id") != plot_id:
        st.session_state.selected_plan_key=None
        st.session_state.selected_plan_id=None
    st.session_state.comparison_plot_id=plot_id
    climate=st.session_state.get("selected_climate_id","normal")
    if climate not in CLIMATES:
        climate="normal"
    st.session_state.selected_climate_id=climate
    key=st.session_state.get("selected_plan_key")
    if key not in plans:
        key=None
    st.session_state.selected_plan_key=key
    plan=plans.get(key) if key else None
    st.session_state.selected_plan_id=plan.id if plan else None


def choose_plan(key: str, plot_id: str) -> None:
    if plot_id != st.session_state.get("selected_plot_id"):
        return
    try:
        plans=resolve_plans(load_rotation_scenarios())
    except Exception:
        return
    if key in plans:
        st.session_state.selected_plan_key=key
        plan=plans[key]
        st.session_state.selected_plan_id=plan.id if plan else None


def choose_climate(key: str) -> None:
    if key in CLIMATES:
        st.session_state.selected_climate_id=key
