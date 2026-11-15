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

from utils.data_sources import load_plots, load_rotation_scenarios, load_satellite_snapshot
from utils.model_interface import (
    compute_plot_risk,
    generate_recommendations,
    predict_scenario_outcome,
    score_scenario_priority_fit,
)
from utils.types import FarmerPriorities
from utils import field_model as fm

#: True when the google-genai SDK is available in this environment.
AI_READY: bool = genai is not None

#: Fallback model endpoint when ``[google] model`` is not set in secrets.
DEFAULT_MODEL = "gemini-3.5-flash-lite"

_MAX_TOOL_ROUNDS = 5          # safety cap on LLM -> tool -> LLM loops per question
_MAX_HISTORY_MESSAGES = 20    # only recent turns are sent to the model (context size)

# TODO(data team): replace with a real market price source (SADER / PRODEPA / USDA).
_MOCK_CROP_PRICES_USD_PER_TONNE: dict[str, float] = {
    "Maize": 145.0,
    "Beans": 980.0,
    "Sorghum": 160.0,
    "Wheat": 210.0,
    "Alfalfa": 320.0,
}

_CROP_ALIASES: dict[str, str] = {
    "corn": "Maize",
    "maize": "Maize",
    "maiz": "Maize",
    "maíz": "Maize",
    "bean": "Beans",
    "beans": "Beans",
    "frijol": "Beans",
    "sorghum": "Sorghum",
    "sorgo": "Sorghum",
    "wheat": "Wheat",
    "trigo": "Wheat",
    "alfalfa": "Alfalfa",
}


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
    if fm.enabled():
        try:return {"profile":fm.profile(plot_id)["parcela"],"profile_name":fm.label(plot_id),"nature":"derived research model inputs","geometry":"USDA CDL satellite-derived geometry; not verified ownership boundaries","sources":fm.catalog()["fuentes"]}
        except ValueError:return {"error":"Unknown model profile"}

    """Current state of a plot: satellite indicators + aggregated risks."""
    plots = {p.id: p for p in load_plots()}
    if plot_id not in plots:
        return {"error": f"Unknown plot: {plot_id}. Valid plot IDs: {sorted(plots)}"}
    plot = plots[plot_id]
    snap = load_satellite_snapshot(plot_id)
    risk = compute_plot_risk(plot_id)
    return {
        "plot": {
            "id": plot.id,
            "name": plot.name,
            "area_ha": plot.area_hectares,
            "current_crop": plot.current_crop,
        },
        "satellite_data_date": snap.date,
        "ndvi": round(snap.ndvi, 3),
        "soil_moisture_pct": round(snap.soil_moisture_pct, 1),
        "temperature_c": round(snap.temperature_c, 1),
        "precipitation_mm": round(snap.precipitation_mm, 1),
        "water_availability_index": round(snap.water_availability_idx, 2),
        "drought_risk_0_1": round(risk.drought_risk, 2),
        "heat_risk_0_1": round(risk.heat_stress_risk, 2),
        "nutrient_risk_0_1": round(risk.nutrient_depletion_risk, 2),
        "overall_risk_0_1": round(risk.overall_risk, 2),
    }


def tool_list_rotation_scenarios() -> list[dict]:
    if fm.enabled():
        return [{"id":pid,"name":name,"climates":fm.CLIMATES,"units":"bu/acre, USD/acre, ton/acre/year, lb/acre"} for pid,name in fm.PLANS.items()]

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
    climate_id: str | None = None,
) -> dict:
    """Expected outcome of a rotation on a plot, including farmer priority fit score."""
    if fm.enabled():
        climate=climate_id or st.session_state.get("selected_climate_id","normal")
        if rainfall_shift_pct or temp_anomaly_c:
            return {"error":"Research model supports named historical climates, not arbitrary rainfall/temperature sliders.","climates":fm.CLIMATES}
        try:return {"plot_id":plot_id,"climate_id":climate,"outcome":fm.result(plot_id,climate,scenario_id),"nature":"derived model estimate","sources":fm.catalog()["fuentes"]}
        except (ValueError,KeyError):return {"error":"Unknown model profile, plan or climate","plans":fm.PLANS,"climates":fm.CLIMATES}

    plots = {p.id for p in load_plots()}
    if plot_id not in plots:
        return {"error": f"Unknown plot: {plot_id}. Valid plot IDs: {sorted(plots)}"}

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
        "rainfall_shift_pct": clamped_rain,
        "temperature_anomaly_c": clamped_temp,
        "expected_yield_t_ha": round(outcome.expected_yield_t_per_ha, 2),
        "yield_ci90": [round(outcome.yield_ci_low, 2), round(outcome.yield_ci_high, 2)],
        "irrigation_water_mm": round(outcome.water_use_mm, 1),
        "nutrient_loss_pct": round(outcome.nutrient_loss_pct, 1),
        "cost_usd_ha": round(outcome.cost_usd_per_ha, 0),
        "erosion_risk_0_1": round(outcome.erosion_risk_score, 2),
        "organic_matter_delta_pct": round(outcome.organic_matter_delta_pct, 1),
        "agronomic_mechanism": outcome.agronomic_mechanism,
        "satellite_evidence": outcome.evidence_summary,
        "information_gaps": outcome.information_gaps,
    }


def tool_get_action_recommendations(plot_id: str) -> list[dict] | dict:
    if fm.enabled():
        plan=st.session_state.get("selected_plan_id")
        if plan not in fm.PLANS:return {"notice":"Select a plan before discussing its budget, erosion, nitrogen and risks.","plans":fm.PLANS}
        try:
            out=fm.result(plot_id,st.session_state.get("selected_climate_id","normal"),plan)
            return {"scope":"Review prompts from supplied model outputs, not additional prescriptions","plan":out,"nitrogen_target":"maize phase only; timing and applicability require agronomic confirmation","sources":fm.catalog()["fuentes"]}
        except ValueError:return {"error":"Unknown model profile"}

    """Decision-support recommendations aligned with the farmer's active priorities."""
    plots = {p.id for p in load_plots()}
    if plot_id not in plots:
        return {"error": f"Unknown plot: {plot_id}. Valid plot IDs: {sorted(plots)}"}

    priorities = _get_active_priorities()
    recs = generate_recommendations(plot_id, priorities)
    return [
        {
            "action": r.title,
            "category": r.category,
            "rationale": r.rationale,
            "expected_impact_pct": r.expected_impact_pct,
            "impact_ci90_pct": [r.impact_ci_low, r.impact_ci_high],
            "water_change_mm": r.water_delta_mm,
            "cost_usd_ha": r.cost_usd_per_ha,
            "satellite_evidence": r.evidence_summary,
            "local_verification": r.local_review_notes,
        }
        for r in recs
    ]


def tool_get_crop_price(crop: str) -> dict:
    if fm.enabled():
        return {"notice":"Standalone current prices are not exposed by the model export. Use the supplied income, cost and margin outputs; do not substitute the legacy simulated price table.","source":fm.catalog()["fuentes"]["rendimiento_y_precios"]}

    """Current market price of a crop (mock table — TODO: real source)."""
    canonical = _CROP_ALIASES.get(crop.strip().lower(), crop.strip().capitalize())
    if canonical not in _MOCK_CROP_PRICES_USD_PER_TONNE:
        return {
            "error": (
                f"No price is available for '{crop}'. Available crops: "
                f"{sorted(_MOCK_CROP_PRICES_USD_PER_TONNE)}"
            )
        }
    return {
        "crop": canonical,
        "price_usd_per_tonne": _MOCK_CROP_PRICES_USD_PER_TONNE[canonical],
        "source": "simulated demo table",
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
            "Current plot conditions: satellite indicators (NDVI, soil moisture, temperature, precipitation) "
            "and aggregate 0–1 risks (drought, heat, nutrients). Use for questions such as "
            "'How is my plot doing?' or 'Is my crop healthy?'"
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": (
                        "Profile ID from active context (research examples: 806, 467); legacy demo uses lote-norte. If the user does not specify one, "
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
            "Expected outcome of a crop rotation on a plot: farmer-priority fit score (0–100), "
            "source quantiles and units. In research mode use climate_id for the three historical groups; no arbitrary weather inputs. In legacy mode only, water, nutrients, cost, and agronomic mechanism. "
            "Supports what-if scenarios: rainfall_shift_pct is the seasonal rainfall change "
            "(-30 to +20; positive means more rain, e.g. +20 for prolonged heavy rainfall), and "
            "temp_anomaly_c is the temperature anomaly in °C (0 to 3.5)."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "Profile ID from active context (research examples: 806, 467); legacy demo uses lote-norte.",
                },
                "scenario_id": {
                    "type": "string",
                    "description": "Rotation scenario ID (retrieve IDs with list_rotation_scenarios).",
                },
                "climate_id": {"type":"string","description":"Research-model climate ID: normal, seco_caluroso or humedo_primavera."},
                "rainfall_shift_pct": {
                    "type": "number",
                    "description": "Seasonal rainfall change in percent, -30 to +20. 0 = no change.",
                },
                "temp_anomaly_c": {
                    "type": "number",
                    "description": "Temperature anomaly in °C, 0 to 3.5. 0 = no change.",
                },
            },
            "required": ["plot_id", "scenario_id"],
        },
    },
    {
        "name": "get_action_recommendations",
        "description": (
            "Get agronomic and fertilizer recommendations for a plot, filtered by the farmer's "
            "priorities and water budget. Use when asked what actions to take, which fertilizer "
            "to apply, or how to reduce risks."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "Profile ID from active context (research examples: 806, 467); legacy demo uses lote-norte.",
                },
            },
            "required": ["plot_id"],
        },
    },
    {
        "name": "get_crop_price",
        "description": (
            "Current crop market price in USD per tonne (simulated demo table). "
            "Use for questions such as 'What is the price of maize?'"
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "crop": {
                    "type": "string",
                    "description": "Crop name, such as 'Maize', 'Beans', 'Sorghum', 'Wheat', or 'Alfalfa'.",
                },
            },
            "required": ["crop"],
        },
    },
]


def _build_tool() -> Any:
    """Build a ``types.Tool`` from ``_TOOL_SCHEMAS`` for Gemini function calling."""
    if types is None:
        raise RuntimeError("The `google-genai` package is not installed.")
    declarations = [
        types.FunctionDeclaration(**schema)
        for schema in _TOOL_SCHEMAS
    ]
    return types.Tool(function_declarations=declarations)


def _format_priorities_summary(priorities: FarmerPriorities) -> str:
    budget_text = (
        f"{priorities.max_water_budget_mm:.0f} mm/season"
        if priorities.max_water_budget_mm is not None
        else "no limit"
    )
    return (
        f"water conservation={priorities.water_conservation_weight:.2f}, "
        f"soil health={priorities.soil_health_weight:.2f}, "
        f"profitability={priorities.profit_market_weight:.2f}, "
        f"forage value={'yes' if priorities.forage_priority else 'no'}, "
        f"no-till equipment={'yes' if priorities.has_no_till_equipment else 'no'}, "
        f"irrigation cap={budget_text}"
    )


def _system_prompt(plot_id: str) -> str:
    if fm.enabled():
        return (f'You are Mr Corn, the Field Shift farming assistant. Respond in clear English. Active model profile: {plot_id}. '
                f'Active climate: {st.session_state.get("selected_climate_id","normal")}; selected plan: {st.session_state.get("selected_plan_id")}. '
                'Use only tool outputs for every figure. The research model supplies derived estimates from historical data and literature; it does not predict an individual future harvest. '
                'Preserve source units: maize bu/acre, USD/acre, soil loss ton/acre/year and nitrogen lb/acre. Do not sum maize and soybean yields. '
                'p10/p50/p90 are supplied quantiles, not validated guarantees for this profile. Costs include land rent; rotation economics average maize and soybean phases. '
                'Nitrogen applies to maize and requires confirmation, not a universal rotation prescription. Plot locations and outlines come from USDA CDL crop patterns, not verified ownership boundaries. The model includes a 37 USD/acre cover establishment assumption and a planting-risk estimate scaled from the unplanted fraction observed in 2019; neither is a guaranteed field outcome. '
                'Do not use arbitrary weather sliders, legacy simulated prices, invented observations, new forecasts or invented actions. Compare the three named historical climates and three exported plans. '
                'Describe tradeoffs without guaranteeing profit or safety. Quote source and limitations briefly. Keep answers concise.')

    plot = next((p for p in load_plots() if p.id == plot_id), None)
    context = (
        f"{plot.name} ({plot_id}), {plot.area_hectares:.0f} ha, current crop: {plot.current_crop}"
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
3. Briefly cite relevant satellite evidence (NDVI, soil moisture, etc.) when it supports a claim.
4. Explain uncertainty, including confidence intervals, in plain language.
5. When asked to recommend rotations based on the farmer's priorities, list scenarios with list_rotation_scenarios, evaluate the most relevant ones with predict_scenario_outcome, and compare their "priority_fit_score_0_100".
6. When asked what actions to take or which fertilizer to use, call get_action_recommendations and remind the user to verify conditions in the field.
7. For hypothetical questions (for example, more rain or higher temperatures), use predict_scenario_outcome (maximum +20% rainfall or +3.5 °C) and explain the agronomic mechanism returned by the tool.
8. Prices come from a simulated demo table; briefly note this when citing a price.
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