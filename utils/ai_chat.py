"""AI chat backend: LLM with function calling over the crop model tools.

The chat is a thin orchestration layer on top of the existing contracts in
:mod:`utils.data_sources` and :mod:`utils.model_interface`. Each tool below
wraps one of those functions, so when the ML team replaces the mock bodies
with the real pipeline, the chat answers automatically use real predictions —
no changes needed here (as long as signatures stay stable).

Provider: Google AI Studio (Gemini) via the ``google-genai`` SDK. The API key
is read from ``.streamlit/secrets.toml`` (``[google] api_key``), falling back
to the ``GOOGLE_API_KEY`` environment variable. To swap providers, replace only
:func:`run_chat_turn`'s model call — tools and page stay untouched.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Callable, Iterator

import streamlit as st

try:  # Friendly degradation when the SDK is not installed yet.
    from google import genai
    from google.genai import errors, types
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    errors = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

from model import units
from model.loader import load_prices, load_results
from utils.data_sources import load_plots, load_rotation_scenarios
from utils.model_interface import (
    compute_plot_risk,
    generate_recommendations,
    predict_scenario_outcome,
    score_scenario_priority_fit,
)
from utils.types import FarmerPriorities

#: True when the google-genai SDK is available in this environment.
AI_READY: bool = genai is not None

#: Fallback model endpoint when ``[google] model`` is not set in secrets.
DEFAULT_MODEL = "gemini-3.6-flash"

_MAX_TOOL_ROUNDS = 5          # safety cap on LLM -> tool -> LLM loops per question
_MAX_HISTORY_MESSAGES = 20    # only recent turns are sent to the model (context size)

def _crop_prices_usd_per_tonne() -> dict[str, float]:
    """Latest model prices (USDA, USD/bushel) converted to USD per tonne.

    Replaces the old mock table. Read lazily so importing this module does not
    touch the data files.
    """
    prices = load_prices()
    return {
        "Corn": round(units.corn_usd_bu_to_usd_t(prices["corn_usd_per_bu"]), 1),
        "Soybean": round(units.soy_usd_bu_to_usd_t(prices["soy_usd_per_bu"]), 1),
    }


_CROP_ALIASES: dict[str, str] = {
    "corn": "Corn",
    "maize": "Corn",
    "maiz": "Corn",
    "maíz": "Corn",
    "soy": "Soybean",
    "soya": "Soybean",
    "soybean": "Soybean",
    "soybeans": "Soybean",
}


def _num(value: Any, digits: int) -> float | None:
    """Round a number for the model; NaN (not produced) becomes None, never 0."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


@dataclass(frozen=True)
class ChatEvent:
    """One step of a chat turn; the page renders these live."""

    kind: str            # "tool" | "final" | "error"
    label: str = ""      # human-readable step name (kind == "tool")
    payload: Any = None  # tool result dict (tool) / answer text (final|error)


def get_api_key() -> str | None:
    """API key from ``.streamlit/secrets.toml``, falling back to the environment."""
    try:
        key = st.secrets["google"]["api_key"]
    except Exception:  # file missing, section missing or key absent
        key = os.environ.get("GOOGLE_API_KEY", "")
    cleaned = str(key).strip().strip('"').strip("'")
    return cleaned or None


def get_model_name() -> str:
    """Model endpoint from secrets (``[google] model``), defaulting to ``DEFAULT_MODEL``."""
    try:
        model = st.secrets["google"]["model"]
    except Exception:
        model = ""
    cleaned = str(model).strip().strip('"').strip("'")
    return cleaned or DEFAULT_MODEL


def _get_active_priorities() -> FarmerPriorities:
    """Read current farmer priorities from session state with a safe fallback."""
    priorities = st.session_state.get("farmer_priorities")
    if isinstance(priorities, FarmerPriorities):
        return priorities
    return FarmerPriorities()


# --- Tools (thin wrappers over the existing contracts) -----------------------

def tool_get_plot_status(plot_id: str) -> dict:
    """Current state of a plot: soil (SSURGO) + aggregated risks."""
    plots = {p.id: p for p in load_plots()}
    if plot_id not in plots:
        return {"error": f"Unknown plot: {plot_id}. Valid plot IDs include: {sorted(plots, key=int)[:10]}"}
    plot = plots[plot_id]
    risk = compute_plot_risk(plot_id)
    soil = load_results()[plot_id]["parcela"]["suelo"]
    return {
        "plot": {
            "id": plot.id,
            "name": plot.name,
            "area_ha": round(plot.area_hectares, 1),
            "crop_pattern_2018_2025": plot.current_crop,
        },
        "soil_ssurgo": {
            "productivity_index_csr2_5_100": soil["productividad_csr2"],
            "sand_pct": soil["arena_pct"],
            "available_water_cm": soil["agua_disponible_cm"],
            "slope_pct": soil["pendiente_pct"],
            "organic_matter_pct": soil["materia_organica_pct"],
            "planting_flood_risk_pct": soil["riesgo_inundacion_siembra_pct"],
        },
        "plot_level_satellite_snapshot": "not available",
        "drought_risk_0_1": _num(risk.drought_risk, 2),
        "heat_risk_0_1": _num(risk.heat_stress_risk, 2),
        "nutrient_risk_0_1": _num(risk.nutrient_depletion_risk, 2),
        "overall_risk_0_1": _num(risk.overall_risk, 2),
        "risk_note": "Heat comes from one NASA POWER point for the whole county; drought combines that county weather with how much water this plot's soil holds; nutrient risk comes from organic matter.",
    }


def tool_list_rotation_scenarios() -> list[dict]:
    """All rotation scenarios available for evaluation."""
    return [
        {"id": s.id, "name": s.name, "crops": list(s.crops)}
        for s in load_rotation_scenarios()
    ]


def tool_predict_scenario_outcome(
    plot_id: str,
    scenario_id: str,
    rainfall_shift_pct: float = 0.0,
    temp_anomaly_c: float = 0.0,
) -> dict:
    """Expected outcome of a rotation on a plot, including farmer priority fit score."""
    plots = {p.id for p in load_plots()}
    if plot_id not in plots:
        return {"error": f"Unknown plot: {plot_id}. Valid plot IDs include: {sorted(plots, key=int)[:10]}"}

    valid_scenarios = {s.id for s in load_rotation_scenarios()}
    if scenario_id not in valid_scenarios:
        return {
            "error": (
                f"Unknown scenario: '{scenario_id}'. "
                f"Valid scenario IDs: {sorted(valid_scenarios)}"
            )
        }

    clamped_rain = max(-30.0, min(20.0, float(rainfall_shift_pct)))
    clamped_temp = max(0.0, min(3.5, float(temp_anomaly_c)))

    outcome = predict_scenario_outcome(plot_id, scenario_id, clamped_rain, clamped_temp)
    priorities = _get_active_priorities()
    priority_fit = score_scenario_priority_fit(outcome, priorities)

    return {
        "scenario": scenario_id,
        "plot": plot_id,
        "priority_fit_score_0_100": priority_fit,
        "year_type_weather": outcome.scenario_climate_note,
        "corn_yield_t_ha": _num(outcome.expected_yield_t_per_ha, 2),
        "corn_yield_range80_t_ha": [_num(outcome.yield_ci_low, 2), _num(outcome.yield_ci_high, 2)],
        "revenue_usd_ha": _num(outcome.revenue_usd_per_ha, 0),
        "cost_usd_ha_including_land_rent": _num(outcome.cost_usd_per_ha, 0),
        "margin_usd_ha": _num(outcome.margin_usd_per_ha, 0),
        "margin_range80_usd_ha": [_num(outcome.margin_ci_low, 0), _num(outcome.margin_ci_high, 0)],
        "nitrogen_kg_ha": _num(outcome.nitrogen_kg_per_ha, 0),
        "erosion_share_of_tolerable_limit": _num(outcome.erosion_risk_score, 2),
        "chance_not_planting_pct": _num(outcome.prob_unplanted_pct, 2),
        "chance_yield_drop_over_20pct": _num(outcome.prob_big_loss_pct, 1),
        "agronomic_mechanism": outcome.agronomic_mechanism,
        "sources": outcome.evidence_summary,
        "information_gaps": outcome.information_gaps,
    }


def tool_get_action_recommendations(plot_id: str) -> list[dict] | dict:
    """Decision-support recommendations aligned with the farmer's active priorities."""
    plots = {p.id for p in load_plots()}
    if plot_id not in plots:
        return {"error": f"Unknown plot: {plot_id}. Valid plot IDs include: {sorted(plots, key=int)[:10]}"}

    priorities = _get_active_priorities()
    recs = generate_recommendations(plot_id, priorities)
    return [
        {
            "action": r.title,
            "category": r.category,
            "rationale": r.rationale,
            "expected_impact_pct": _num(r.expected_impact_pct, 0),
            "impact_range_pct": [_num(r.impact_ci_low, 0), _num(r.impact_ci_high, 0)],
            "cost_usd_ha": _num(r.cost_usd_per_ha, 0),
            "sources": r.evidence_summary,
            "information_gaps": r.information_gaps,
            "local_verification": r.local_review_notes,
        }
        for r in recs
    ]


def tool_get_crop_price(crop: str) -> dict:
    """Crop price used by the plan results (USDA, latest year), in USD per tonne."""
    prices = _crop_prices_usd_per_tonne()
    canonical = _CROP_ALIASES.get(crop.strip().lower(), crop.strip().capitalize())
    if canonical not in prices:
        return {"error": f"No price is available for '{crop}'. Available crops: {sorted(prices)}"}
    return {
        "crop": canonical,
        "price_usd_per_tonne": prices[canonical],
        "year": load_prices()["year"],
        "source": "USDA NASS QuickStats (Iowa price), the price used in the plan results",
    }


_TOOL_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "get_plot_status": tool_get_plot_status,
    "list_rotation_scenarios": tool_list_rotation_scenarios,
    "predict_scenario_outcome": tool_predict_scenario_outcome,
    "get_action_recommendations": tool_get_action_recommendations,
    "get_crop_price": tool_get_crop_price,
}

_TOOL_LABELS: dict[str, str] = {
    "get_plot_status": "Checking plot conditions",
    "list_rotation_scenarios": "Listing available crop rotations",
    "predict_scenario_outcome": "Simulating a crop rotation",
    "get_action_recommendations": "Checking the action plan and recommendations",
    "get_crop_price": "Checking market prices",
}

#: JSON schemas for the Gemini function declarations (OpenAPI subset).
#: Tools without parameters omit ``parameters_json_schema`` because Gemini
#: rejects ``{"type": "object", "properties": {}}`` with 400 INVALID_ARGUMENT.
_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_plot_status",
        "description": (
            "Current plot conditions: soil properties (SSURGO: productivity, sand, available water, slope, "
            "organic matter, planting flood risk) and aggregate 0–1 risks (drought, heat, nutrients). Use for "
            "questions such as 'How is my plot doing?' or 'What is my soil like?'"
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": (
                        "Plot ID, such as '806'. If the user does not specify one, "
                        "use the selected plot from the instructions."
                    ),
                },
            },
            "required": ["plot_id"],
        },
    },
    {
        "name": "list_rotation_scenarios",
        "description": (
            "List all crop rotation scenarios available for evaluation, with their IDs and "
            "crop sequences by season."
        ),
    },
    {
        "name": "predict_scenario_outcome",
        "description": (
            "Result of a crop rotation on a plot in one type of year: farmer-priority fit score (0–100), "
            "corn yield and margin with 80% ranges, revenue, cost (including land rent), nitrogen, erosion and "
            "planting risk. The two climate numbers select a measured year type: rainfall_shift_pct <= -15 or "
            "temp_anomaly_c >= 1.5 -> dry and hot year (use -20 and 2.0); rainfall_shift_pct >= 10 -> wet "
            "spring (use 15 and 0); otherwise a normal year (use 0 and 0)."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "Plot ID, such as '806'.",
                },
                "scenario_id": {
                    "type": "string",
                    "description": "Rotation scenario ID (retrieve IDs with list_rotation_scenarios).",
                },
                "rainfall_shift_pct": {
                    "type": "number",
                    "description": "Seasonal rainfall change in percent: -20 = dry and hot, 15 = wet spring, 0 = normal.",
                },
                "temp_anomaly_c": {
                    "type": "number",
                    "description": "Temperature anomaly in °C: 2.0 = dry and hot, 0 = normal or wet spring.",
                },
            },
            "required": ["plot_id", "scenario_id"],
        },
    },
    {
        "name": "get_action_recommendations",
        "description": (
            "Get recommended actions for a plot from its real results in a normal year (planting risk, "
            "erosion above the tolerable limit, plans that lose money). Use when asked what actions to take "
            "or how to reduce risks."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "Plot ID, such as '806'.",
                },
            },
            "required": ["plot_id"],
        },
    },
    {
        "name": "get_crop_price",
        "description": (
            "Crop price in USD per tonne used in the plan results (USDA, latest year). Only corn and "
            "soybean. Use for questions such as 'What is the price of corn?'"
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "crop": {
                    "type": "string",
                    "description": "Crop name: 'Corn' or 'Soybean'.",
                },
            },
            "required": ["crop"],
        },
    },
]


def _build_tool() -> Any:
    """The single Gemini Tool bundling all function declarations."""
    declarations = []
    for schema in _TOOL_SCHEMAS:
        decl_kwargs: dict[str, Any] = {
            "name": schema["name"],
            "description": schema["description"],
        }
        params = schema.get("parameters_json_schema")
        if params and params.get("properties"):
            decl_kwargs["parameters_json_schema"] = params
        declarations.append(types.FunctionDeclaration(**decl_kwargs))
    return types.Tool(function_declarations=declarations)


def _format_priorities_summary(priorities: FarmerPriorities) -> str:
    budget_text = (
        f"{priorities.max_water_budget_mm:.0f} mm/season"
        if priorities.max_water_budget_mm is not None
        else "no limit"
    )
    return (
        f"planting reliability={priorities.water_conservation_weight:.2f}, "
        f"soil health={priorities.soil_health_weight:.2f}, "
        f"profitability={priorities.profit_market_weight:.2f}, "
        f"forage value={'yes' if priorities.forage_priority else 'no'}, "
        f"no-till equipment={'yes' if priorities.has_no_till_equipment else 'no'}, "
        f"irrigation cap={budget_text}"
    )


def _system_prompt(plot_id: str) -> str:
    plot = next((p for p in load_plots() if p.id == plot_id), None)
    context = (
        f"{plot.name} ({plot_id}), {plot.area_hectares:.0f} ha, Butler County, Iowa, crop pattern 2018–2025: {plot.current_crop}"
        if plot
        else f"Unknown ID: {plot_id}"
    )
    priorities_text = _format_priorities_summary(_get_active_priorities())

    return f"""You are "Mr Corn", the agronomy assistant in the Field Shift app (NASA Space Apps 2026).
The user is a farmer and has selected this plot: {context}.
The farmer's current priorities are: {priorities_text}.

Strict rules:
1. Always respond in English, using clear, plain language; explain technical terms.
2. NEVER invent figures, prices, or measurements: every number must come from your tools. If a tool does not return the information you need, say so honestly.
3. Briefly cite the data sources returned by the tools (USDA, NASA POWER, SSURGO) when they support a claim. Always give harvest and money together.
4. Explain uncertainty, including the 80% ranges (8 in 10 similar past years fell inside them), in plain language.
5. When asked to recommend rotations based on the farmer's priorities, list scenarios with list_rotation_scenarios, evaluate the most relevant ones with predict_scenario_outcome, and compare their "priority_fit_score_0_100".
6. When asked what actions to take, call get_action_recommendations and remind the user to verify conditions in the field. Butler County farms are rain-fed: never recommend irrigation.
7. For hypothetical questions (a dry and hot year, a wet spring), use predict_scenario_outcome with the matching year type and explain the agronomic mechanism returned by the tool. Only corn and soybean plans exist.
8. Prices are the USDA prices used in the results; costs include land rent, so a farmer who owns the land earns more.
9. If a question is outside the scope of your tools, say so and suggest what information is missing.
10. Be concise: answer in 3 to 10 lines and use bullets when they improve readability."""


def _build_generate_config(plot_id: str, model_name: str) -> Any:
    """Build GenerateContentConfig tuned for Gemini 3.x / 2.5 tool-calling orchestration."""
    config_kwargs: dict[str, Any] = {
        "system_instruction": _system_prompt(plot_id),
        "tools": [_build_tool()],
    }
    # Gemini 3.x models use thinking_level (LOW avoids premature tool-chain stops while keeping latency low).
    if ("3." in model_name or "gemini-3" in model_name) and hasattr(types, "ThinkingConfig") and hasattr(types, "ThinkingLevel"):
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.LOW
        )
    elif "2.5" in model_name and hasattr(types, "ThinkingConfig"):
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        config_kwargs["temperature"] = 0.3
    else:
        config_kwargs["temperature"] = 0.3
    return types.GenerateContentConfig(**config_kwargs)


def run_chat_turn(history: list[dict], plot_id: str) -> Iterator[ChatEvent]:
    """Process one user turn and yield :class:`ChatEvent` steps for live rendering.

    ``history`` is the full conversation as ``{"role": "user"|"assistant",
    "content": str}`` dicts, including the new user message at the end. The
    generator yields a ``tool`` event before each local tool execution and a
    final ``final`` (answer) or ``error`` event.
    """
    if not AI_READY:
        yield ChatEvent(
            "error",
            payload="The `google-genai` package is not installed. Run `pip install google-genai` and restart the app.",
        )
        return

    api_key = get_api_key()
    if not api_key:
        yield ChatEvent(
            "error",
            payload=(
                "The Google AI Studio API key is missing. Add it to `.streamlit/secrets.toml` under "
                "`[google] api_key` (or set the `GOOGLE_API_KEY` environment variable), then restart the app."
            ),
        )
        return

    client = genai.Client(api_key=api_key)
    model_name = get_model_name()

    # Gemini roles are "user"/"model"; Streamlit stores "assistant".
    contents = [
        types.Content(
            role="model" if msg["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=msg["content"])],
        )
        for msg in history[-_MAX_HISTORY_MESSAGES:]
    ]

    config = _build_generate_config(plot_id, model_name)

    for _ in range(_MAX_TOOL_ROUNDS):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            if errors is not None and isinstance(exc, errors.APIError):
                detail = getattr(exc, "message", str(exc))
                status = getattr(exc, "status", exc.__class__.__name__)
                code = getattr(exc, "code", "4xx")
                yield ChatEvent(
                    "error",
                    payload=f"API error ({code} - {status}): {detail}",
                )
            else:
                yield ChatEvent(
                    "error",
                    payload=f"Could not contact the model ({exc.__class__.__name__}): {exc}",
                )
            return

        candidate = response.candidates[0] if response.candidates else None
        parts = (candidate.content.parts or []) if candidate and candidate.content else []
        function_calls = [p for p in parts if p.function_call]
        text = "".join(p.text for p in parts if p.text).strip()

        if not function_calls:
            yield ChatEvent("final", payload=text or "The model returned no response. Please try again.")
            return

        # Execute each requested tool locally, then feed the results back to the model.
        if candidate is None or candidate.content is None:
            yield ChatEvent("error", payload="The model returned no valid content. Please try again.")
            return
        contents.append(candidate.content)
        responses = []
        for part in function_calls:
            call = part.function_call
            if call is None:
                continue
            name = call.name or ""
            args = dict(call.args or {})
            fn = _TOOL_FUNCTIONS.get(name)
            try:
                result = fn(**args) if fn else {"error": f"Unknown tool: {name}"}
            except Exception as exc:  # let the model handle tool failures gracefully
                result = {"error": str(exc)}
            yield ChatEvent("tool", label=_TOOL_LABELS.get(name, name), payload=result)
            responses.append(types.Part.from_function_response(name=name, response={"result": result}))
        contents.append(types.Content(role="user", parts=responses))

    yield ChatEvent(
        "error",
        payload="The request required too many steps. Try asking a more specific question.",
    )