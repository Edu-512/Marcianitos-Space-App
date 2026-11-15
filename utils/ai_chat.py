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

#: True when the google-genai SDK is available in this environment.
AI_READY: bool = genai is not None

#: Fallback model endpoint when ``[google] model`` is not set in secrets.
DEFAULT_MODEL = "gemini-3.6-flash"

_MAX_TOOL_ROUNDS = 5          # safety cap on LLM -> tool -> LLM loops per question
_MAX_HISTORY_MESSAGES = 20    # only recent turns are sent to the model (context size)

# TODO(data team): replace with a real market price source (SADER / PRODEPA / USDA).
_MOCK_CROP_PRICES_USD_PER_TONNE: dict[str, float] = {
    "Maíz": 145.0,
    "Frijol": 980.0,
    "Sorgo": 160.0,
    "Trigo": 210.0,
    "Alfalfa": 320.0,
}

_CROP_ALIASES: dict[str, str] = {
    "maiz": "Maíz",
    "maíz": "Maíz",
    "frijol": "Frijol",
    "sorgo": "Sorgo",
    "trigo": "Trigo",
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
    """Current state of a plot: satellite indicators + aggregated risks."""
    plots = {p.id: p for p in load_plots()}
    if plot_id not in plots:
        return {"error": f"Parcela desconocida: {plot_id}. IDs válidos: {sorted(plots)}"}
    plot = plots[plot_id]
    snap = load_satellite_snapshot(plot_id)
    risk = compute_plot_risk(plot_id)
    return {
        "parcela": {
            "id": plot.id,
            "nombre": plot.name,
            "area_ha": plot.area_hectares,
            "cultivo_actual": plot.current_crop,
        },
        "fecha_dato_satelital": snap.date,
        "ndvi": round(snap.ndvi, 3),
        "humedad_suelo_pct": round(snap.soil_moisture_pct, 1),
        "temperatura_c": round(snap.temperature_c, 1),
        "precipitacion_mm": round(snap.precipitation_mm, 1),
        "indice_disponibilidad_agua": round(snap.water_availability_idx, 2),
        "riesgo_sequia_0_1": round(risk.drought_risk, 2),
        "riesgo_calor_0_1": round(risk.heat_stress_risk, 2),
        "riesgo_nutrientes_0_1": round(risk.nutrient_depletion_risk, 2),
        "riesgo_general_0_1": round(risk.overall_risk, 2),
    }


def tool_list_rotation_scenarios() -> list[dict]:
    """All rotation scenarios available for evaluation."""
    return [
        {"id": s.id, "nombre": s.name, "cultivos": list(s.crops)}
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
        return {"error": f"Parcela desconocida: {plot_id}. IDs válidos: {sorted(plots)}"}

    valid_scenarios = {s.id for s in load_rotation_scenarios()}
    if scenario_id not in valid_scenarios:
        return {
            "error": (
                f"Escenario desconocido: '{scenario_id}'. "
                f"IDs válidos: {sorted(valid_scenarios)}"
            )
        }

    clamped_rain = max(-30.0, min(20.0, float(rainfall_shift_pct)))
    clamped_temp = max(0.0, min(3.5, float(temp_anomaly_c)))

    outcome = predict_scenario_outcome(plot_id, scenario_id, clamped_rain, clamped_temp)
    priorities = _get_active_priorities()
    priority_fit = score_scenario_priority_fit(outcome, priorities)

    return {
        "escenario": scenario_id,
        "parcela": plot_id,
        "ajuste_a_prioridades_0_100": priority_fit,
        "cambio_lluvia_pct": clamped_rain,
        "anomalia_calor_c": clamped_temp,
        "rendimiento_esperado_t_ha": round(outcome.expected_yield_t_per_ha, 2),
        "ci90_rendimiento": [round(outcome.yield_ci_low, 2), round(outcome.yield_ci_high, 2)],
        "agua_irrigacion_mm": round(outcome.water_use_mm, 1),
        "perdida_nutrientes_pct": round(outcome.nutrient_loss_pct, 1),
        "costo_usd_ha": round(outcome.cost_usd_per_ha, 0),
        "riesgo_erosion_0_1": round(outcome.erosion_risk_score, 2),
        "delta_materia_organica_pct": round(outcome.organic_matter_delta_pct, 1),
        "mecanismo_agronomico": outcome.agronomic_mechanism,
        "evidencia_satelital": outcome.evidence_summary,
        "brechas_informacion": outcome.information_gaps,
    }


def tool_get_action_recommendations(plot_id: str) -> list[dict] | dict:
    """Decision-support recommendations aligned with the farmer's active priorities."""
    plots = {p.id for p in load_plots()}
    if plot_id not in plots:
        return {"error": f"Parcela desconocida: {plot_id}. IDs válidos: {sorted(plots)}"}

    priorities = _get_active_priorities()
    recs = generate_recommendations(plot_id, priorities)
    return [
        {
            "accion": r.title,
            "categoria": r.category,
            "motivo": r.rationale,
            "impacto_esperado_pct": r.expected_impact_pct,
            "ci90_impacto_pct": [r.impact_ci_low, r.impact_ci_high],
            "cambio_agua_mm": r.water_delta_mm,
            "costo_usd_ha": r.cost_usd_per_ha,
            "evidencia_satelital": r.evidence_summary,
            "verificacion_local": r.local_review_notes,
        }
        for r in recs
    ]


def tool_get_crop_price(crop: str) -> dict:
    """Current market price of a crop (mock table — TODO: real source)."""
    canonical = _CROP_ALIASES.get(crop.strip().lower(), crop.strip().capitalize())
    if canonical not in _MOCK_CROP_PRICES_USD_PER_TONNE:
        return {
            "error": (
                f"Sin precio para '{crop}'. Cultivos disponibles: "
                f"{sorted(_MOCK_CROP_PRICES_USD_PER_TONNE)}"
            )
        }
    return {
        "cultivo": canonical,
        "precio_usd_por_tonelada": _MOCK_CROP_PRICES_USD_PER_TONNE[canonical],
        "fuente": "tabla simulada (demo)",
    }


_TOOL_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "get_plot_status": tool_get_plot_status,
    "list_rotation_scenarios": tool_list_rotation_scenarios,
    "predict_scenario_outcome": tool_predict_scenario_outcome,
    "get_action_recommendations": tool_get_action_recommendations,
    "get_crop_price": tool_get_crop_price,
}

_TOOL_LABELS: dict[str, str] = {
    "get_plot_status": "Consultando estado del lote",
    "list_rotation_scenarios": "Listando rotaciones disponibles",
    "predict_scenario_outcome": "Simulando escenario de rotación",
    "get_action_recommendations": "Consultando plan de acción y recomendaciones",
    "get_crop_price": "Consultando precio de mercado",
}

#: JSON schemas for the Gemini function declarations (OpenAPI subset).
#: Tools without parameters omit ``parameters_json_schema`` because Gemini
#: rejects ``{"type": "object", "properties": {}}`` with 400 INVALID_ARGUMENT.
_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_plot_status",
        "description": (
            "Estado actual de una parcela: indicadores satelitales (NDVI, humedad del suelo, "
            "temperatura, precipitación) y riesgos agregados de 0 a 1 (sequía, calor, nutrientes). "
            "Úsalo para preguntas como '¿cómo se encuentra mi parcela?' o '¿mi cultivo está bien?'"
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": (
                        "ID de la parcela, por ejemplo 'lote-norte'. Si el usuario no especifica, "
                        "usa la parcela seleccionada indicada en las instrucciones."
                    ),
                },
            },
            "required": ["plot_id"],
        },
    },
    {
        "name": "list_rotation_scenarios",
        "description": (
            "Lista todas las rotaciones de cultivos disponibles para evaluar, con su ID y la "
            "secuencia de cultivos por temporada."
        ),
    },
    {
        "name": "predict_scenario_outcome",
        "description": (
            "Resultado esperado de una rotación en una parcela: puntaje de ajuste a las prioridades "
            "del agricultor (0 a 100), rendimiento con intervalo de confianza 90%, agua, nutrientes, "
            "costo y mecanismo agronómico. Soporta escenarios What-If: rainfall_shift_pct es el cambio "
            "porcentual de lluvia estacional (-30 a +20; positivo = más lluvia, ej. +20 para lluvias "
            "intensas prolongadas) y temp_anomaly_c la anomalía de temperatura en °C (0 a 3.5)."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "ID de la parcela, por ejemplo 'lote-norte'.",
                },
                "scenario_id": {
                    "type": "string",
                    "description": "ID del escenario de rotación (obtén los IDs con list_rotation_scenarios).",
                },
                "rainfall_shift_pct": {
                    "type": "number",
                    "description": "Cambio porcentual de lluvia estacional, -30 a +20. 0 = sin cambio.",
                },
                "temp_anomaly_c": {
                    "type": "number",
                    "description": "Anomalía de temperatura en °C, 0 a 3.5. 0 = sin cambio.",
                },
            },
            "required": ["plot_id", "scenario_id"],
        },
    },
    {
        "name": "get_action_recommendations",
        "description": (
            "Obtiene las recomendaciones agronómicas y de fertilizantes para una parcela, "
            "filtradas según las prioridades y presupuesto hídrico del agricultor. "
            "Úsalo cuando pregunten qué acciones tomar, qué fertilizante aplicar o cómo reducir riesgos."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "plot_id": {
                    "type": "string",
                    "description": "ID de la parcela, por ejemplo 'lote-norte'.",
                },
            },
            "required": ["plot_id"],
        },
    },
    {
        "name": "get_crop_price",
        "description": (
            "Precio de mercado actual de un cultivo en USD por tonelada (tabla simulada para la demo). "
            "Úsalo para preguntas como '¿a qué precio está el maíz?'"
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "crop": {
                    "type": "string",
                    "description": "Nombre del cultivo, por ejemplo 'Maíz', 'Frijol', 'Sorgo', 'Trigo' o 'Alfalfa'.",
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
        f"{priorities.max_water_budget_mm:.0f} mm/temporada"
        if priorities.max_water_budget_mm is not None
        else "sin límite"
    )
    return (
        f"ahorro de agua={priorities.water_conservation_weight:.2f}, "
        f"salud de suelo={priorities.soil_health_weight:.2f}, "
        f"rentabilidad={priorities.profit_market_weight:.2f}, "
        f"valor forrajero={'sí' if priorities.forage_priority else 'no'}, "
        f"siembra directa (no-till)={'sí' if priorities.has_no_till_equipment else 'no'}, "
        f"tope de riego={budget_text}"
    )


def _system_prompt(plot_id: str) -> str:
    plot = next((p for p in load_plots() if p.id == plot_id), None)
    context = (
        f"{plot.name} ({plot_id}), {plot.area_hectares:.0f} ha, cultivo actual: {plot.current_crop}"
        if plot
        else f"ID desconocido: {plot_id}"
    )
    priorities_text = _format_priorities_summary(_get_active_priorities())

    return f"""Eres "Don Surco", el asistente agronómico de la app Field Shift (NASA Space Apps 2026).
El usuario es un granjero y tiene seleccionada la parcela: {context}.
Prioridades actuales del agricultor: {priorities_text}.

Reglas estrictas:
1. Responde siempre en español, con lenguaje claro y sencillo; explica cualquier término técnico.
2. NUNCA inventes cifras, precios o mediciones: todo número debe salir de tus herramientas. Si una herramienta no devuelve el dato que necesitas, dilo con honestidad.
3. Cita brevemente la evidencia satelital relevante (NDVI, humedad del suelo, etc.) cuando respalde una afirmación.
4. Cuando los resultados incluyan incertidumbre (intervalos de confianza), menciónala en lenguaje llano.
5. Cuando te pidan recomendar rotaciones según sus prioridades, lista los escenarios con list_rotation_scenarios, evalúa los más relevantes con predict_scenario_outcome y compara su campo "ajuste_a_prioridades_0_100".
6. Cuando te pregunten qué acciones tomar o qué fertilizante usar, consulta get_action_recommendations y recuerda mencionar la verificación en campo.
7. Para preguntas hipotéticas ("¿y si lloviera más?", "¿si hace más calor?"), usa predict_scenario_outcome (máximo +20% de lluvia o +3.5 °C) y explica el mecanismo agronómico que devuelve la herramienta.
8. Los precios provienen de una tabla simulada para la demo; indícalo brevemente cuando cites un precio.
9. Si la pregunta está fuera del alcance de tus herramientas, dilo y sugiere qué dato faltaría.
10. Sé conciso: entre 3 y 10 líneas por respuesta; usa viñetas cuando ayuden a leer."""


def _build_generate_config(plot_id: str, model_name: str) -> Any:
    """Build GenerateContentConfig tuned for fast tool-calling orchestration."""
    config_kwargs: dict[str, Any] = {
        "system_instruction": _system_prompt(plot_id),
        "temperature": 0.3,
        "tools": [_build_tool()],
    }
    if "2.5" in model_name and hasattr(types, "ThinkingConfig"):
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
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
            payload="El paquete `google-genai` no está instalado. Ejecuta `pip install google-genai` y reinicia la app.",
        )
        return

    api_key = get_api_key()
    if not api_key:
        yield ChatEvent(
            "error",
            payload=(
                "Falta la API key de Google AI Studio. Agrégala en `.streamlit/secrets.toml` bajo "
                "`[google] api_key` (o en la variable de entorno `GOOGLE_API_KEY`) y reinicia la app."
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
                    payload=f"Error de API ({code} - {status}): {detail}",
                )
            else:
                yield ChatEvent(
                    "error",
                    payload=f"No pude contactar al modelo ({exc.__class__.__name__}): {exc}",
                )
            return

        candidate = response.candidates[0] if response.candidates else None
        parts = (candidate.content.parts or []) if candidate and candidate.content else []
        function_calls = [p for p in parts if p.function_call]
        text = "".join(p.text for p in parts if p.text).strip()

        if not function_calls:
            yield ChatEvent("final", payload=text or "No obtuve una respuesta del modelo. Inténtalo de nuevo.")
            return

        # Execute each requested tool locally, then feed the results back to the model.
        if candidate is None or candidate.content is None:
            yield ChatEvent("error", payload="El modelo no devolvi? contenido v?lido. Intenta de nuevo.")
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
                result = fn(**args) if fn else {"error": f"Herramienta desconocida: {name}"}
            except Exception as exc:  # let the model handle tool failures gracefully
                result = {"error": str(exc)}
            yield ChatEvent("tool", label=_TOOL_LABELS.get(name, name), payload=result)
            responses.append(types.Part.from_function_response(name=name, response={"result": result}))
        contents.append(types.Content(role="user", parts=responses))

    yield ChatEvent(
        "error",
        payload="La consulta requirió demasiados pasos; intenta una pregunta más específica.",
    )