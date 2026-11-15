"""Recommendation presentation state; no predictions or agronomic rules."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from components.crop_comparison import CLIMATES, resolve_plans
from utils.types import Plot, Recommendation, RotationScenario, ScenarioOutcome


@dataclass(frozen=True)
class ActionContext:
    plot: Plot
    plan: RotationScenario | None = None
    plan_key: str | None = None
    climate_id: str | None = None
    outcome: ScenarioOutcome | None = None
    notice: str | None = None

    @property
    def review_key(self) -> str:
        payload=[self.plot.id,self.plan.id if self.plan else self.plan_key,self.climate_id]
        return hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:24]


def action_context(state: Mapping[str, Any], plot: Plot, scenarios: Sequence[RotationScenario]) -> ActionContext:
    """Validate the Feature 04 handoff against the current canonical state."""
    saved=state.get("comparison_context")
    if not isinstance(saved,Mapping):
        return ActionContext(plot,notice="No planting plan has been selected yet. Compare your options to explore a plan's results.")
    if saved.get("plot_id") != plot.id:
        return ActionContext(plot,notice="Your plot has changed. Choose a plan for this plot before using plan results.")
    key=saved.get("plan_key")
    climate=saved.get("climate_id")
    if (not isinstance(key,str) or key not in resolve_plans(scenarios) or not isinstance(climate,str) or climate not in CLIMATES
        or state.get("selected_plan_key") != key or state.get("selected_climate_id") != climate):
        return ActionContext(plot,notice="The plan context is incomplete or has changed. Return to Compare Crops to confirm it.")
    plan=resolve_plans(scenarios)[key]
    if plan is None:
        return ActionContext(plot,plan_key=key,climate_id=climate,notice="This plan's model definition is not available yet. General field actions remain available below.")
    if saved.get("plan_id") != plan.id or state.get("selected_plan_id") != plan.id:
        return ActionContext(plot,notice="This plan is no longer available for the saved context. Please confirm your choice in Compare Crops.")
    expected={"rainfall_shift_pct":CLIMATES[climate]["rain"],"temp_anomaly_c":CLIMATES[climate]["heat"]}
    if saved.get("climate_inputs") != expected:
        return ActionContext(plot,plan=plan,plan_key=key,climate_id=climate,notice="The saved climate inputs do not match this scenario. Return to Compare Crops to refresh the results.")
    outcome=saved.get("outcome")
    if (not isinstance(outcome,ScenarioOutcome) or outcome.plot_id != plot.id or outcome.scenario_id != plan.id
        or expected["rainfall_shift_pct"] is None):
        return ActionContext(plot,plan=plan,plan_key=key,climate_id=climate,notice="No saved outcome is available for this plan and weather. This page does not run another prediction.")
    return ActionContext(plot,plan,key,climate,outcome)


def unique_actions(records: Any) -> list[Recommendation]:
    """Preserve provider order and stable identities, without inventing a ranking."""
    result: list[Recommendation]=[]
    seen: set[str]=set()
    if not isinstance(records,(list,tuple)):
        return result
    for rec in records:
        if isinstance(rec,Recommendation) and isinstance(rec.id,str) and rec.id and rec.id not in seen:
            result.append(rec);seen.add(rec.id)
    return result


def reviewed_count(stored: Sequence[str], recommendations: Sequence[Recommendation]) -> int:
    return len(set(stored) & {r.id for r in recommendations})


def review_widget_key(context_key: str, rec_id: str) -> str:
    return f"review_{context_key}_{hashlib.sha256(rec_id.encode()).hexdigest()[:16]}"


def category_name(category: str) -> str:
    return {"Fertilizante":"Fertilizer","Pr\u00e1ctica agron\u00f3mica":"Agronomic Practice","Riego":"Irrigation"}.get(category,category)
