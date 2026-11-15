"""Read the model's output once and expose it indexed by plot id.

The model (``modelo/gen.py``) is a deterministic pipeline that writes
``datos_ui/resultado_todas.json``. The app never runs it: it only reads that
JSON plus the plot geometry in ``datos_ui/parcelas_todas.geojson``.

The model's texts are in Spanish. They are translated to English *here*, in the
loading layer, so everything the user sees is English while the JSON stays
untouched. Ids (plots, plans, scenarios) stay as they are.

``st.cache_resource`` is used instead of ``st.cache_data`` on purpose: the JSON
is ~1.5 MB and is read on every prediction. ``cache_data`` would deep-copy it on
each call; ``cache_resource`` shares one read-only object per process.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "datos_ui" / "resultado_todas.json"
PARCELS_PATH = ROOT / "datos_ui" / "parcelas_todas.geojson"
DEMO_PATH = ROOT / "datos_ui" / "parcelas_demo.csv"
PRICES_PATH = ROOT / "modelo" / "precios_iowa.csv"

# --- Spanish -> English (UI-facing texts only) ---------------------------------

PLAN_NAMES = {
    "maiz_continuo": "Continuous Corn (No Rotation)",
    "maiz_soya": "Corn → Soybean",
    "maiz_soya_cobertura": "Corn → Soybean + Cover Crop",
}

SCENARIO_LABELS = {
    "normal": "Normal year",
    "seco_caluroso": "Dry and hot year",
    "humedo_primavera": "Wet spring",
}

PATTERN_LABELS = {
    "rotacion estricta": "Corn–soybean rotation",
    "rotacion con quiebre": "Corn–soybean rotation with breaks",
    "maiz dominante": "Mostly corn",
    "soya dominante": "Mostly soybean",
    "irregular": "Irregular pattern",
}

PROFILE_LABELS = {
    "Buen suelo, rotacion clasica": "Good soil, classic rotation",
    "Suelo arenoso, poca agua": "Sandy soil, low water",
    "Maiz dominante, buen suelo": "Mostly corn, good soil",
    "Propensa a no poder sembrarse": "Prone to prevented planting",
    "Pendiente fuerte, erosion": "Steep slope, erosion",
}

CONFIDENCE_LABELS = {"alta": "high", "media": "medium", "baja": "low"}

SOURCE_LABELS = {
    "rendimiento_y_precios": "Yields and prices: USDA NASS QuickStats, 2000–2025",
    "suelo": "Soil: USDA NRCS SSURGO, Butler County IA023 v33 (2026-09-08)",
    "rotacion": "Crop rotation: USDA NASS Cropland Data Layer, 2018–2025",
    "clima": "Weather: NASA POWER (MERRA-2) daily data, 2000–2025, Butler County",
    "penalizacion_rotacion": "Continuous-corn yield penalty: Iowa State University Extension (published literature, not measured by us)",
    "costos": "Costs: ISU Estimated Costs of Crop Production in Iowa 2026 (include land rent)",
    "nitrogeno": "Nitrogen: ISU Corn Nitrogen Rate Calculator",
    "costo_cobertura": "Cover-crop cost: ISU CARD study of cereal rye cover crops in Iowa (37 USD/acre, without cost-share or grazing)",
    "riesgo_no_sembrar": "Risk of not planting: satellite-measured share of each field left unplanted in 2019 (USDA Cropland Data Layer)",
}

WARNING_LABELS = {
    "La penalizacion del maiz continuo viene de la literatura, no de nuestros datos.":
        "The yield penalty for continuous corn comes from Iowa State University literature, not from our own data.",
    "Los rangos p10-p90 estan calibrados: un rango de 80% cubrio el 80% de los casos historicos.":
        "The low–high ranges (10th–90th percentile) are calibrated: an 80% range covered 80% of historical cases.",
    "Los costos incluyen renta de la tierra; un agricultor dueño tiene margenes mayores.":
        "Costs include land rent; a farmer who owns the land has higher margins.",
    "Los escenarios se definen por el clima medido, no por el rendimiento.":
        "Year types are defined by measured weather, not by yield.",
    "El ajuste por suelo usa solo variables disponibles en todo EE.UU. y esta validado en un solo condado.":
        "The soil adjustment uses only variables available across the U.S. and has been validated in a single county.",
    "El cultivo de cobertura cuesta 37 USD/acre y no sube el rendimiento: se paga por reducir erosion. Con apoyo gubernamental o pastoreo el costo baja.":
        "A cover crop costs 37 USD/acre and does not raise yield: you pay for it to cut erosion. Government cost-share or grazing lowers the cost.",
    "El riesgo de no poder sembrar viene de un solo ano observado (2019). La proneidad a inundacion de SSURGO no predijo lo que realmente paso.":
        "The risk of not being able to plant comes from a single observed year (2019). The SSURGO flooding rating did not predict what actually happened.",
}


def _translate(table: dict[str, str], text: str) -> str:
    # Unknown text is kept rather than dropped, so a new model warning is never lost.
    return table.get(text, text)


# --- Cached readers ----------------------------------------------------------


@st.cache_resource(show_spinner=False)
def load_results() -> dict[str, dict[str, Any]]:
    """Model results per plot, keyed by plot id as ``str`` (``Plot.id`` is a str)."""
    doc = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    return {str(item["parcela"]["id"]): item for item in doc["parcelas"]}


@st.cache_resource(show_spinner=False)
def load_parcels() -> dict[str, dict[str, Any]]:
    """GeoJSON features per plot, keyed by plot id as ``str``."""
    doc = json.loads(PARCELS_PATH.read_text(encoding="utf-8"))
    return {str(f["properties"]["id"]): f for f in doc["features"]}


@st.cache_resource(show_spinner=False)
def load_metadata() -> dict[str, Any]:
    """Zone, currency, translated sources and translated warnings."""
    doc = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    return {
        "version": doc.get("version", ""),
        "zone": doc.get("zona", ""),
        "currency": doc.get("moneda", "USD"),
        "sources": {k: SOURCE_LABELS.get(k, v) for k, v in doc.get("fuentes", {}).items()},
        "warnings": [_translate(WARNING_LABELS, w) for w in doc.get("advertencias", [])],
    }


@st.cache_resource(show_spinner=False)
def load_demo_profiles() -> dict[str, str]:
    """The five showcase plots, in delivery order: id -> English profile name."""
    with DEMO_PATH.open(encoding="utf-8") as fh:
        return {str(int(row["id"])): _translate(PROFILE_LABELS, row["perfil"]) for row in csv.DictReader(fh)}


@st.cache_resource(show_spinner=False)
def load_prices() -> dict[str, float]:
    """Latest-year crop prices from the model's price table (USD per bushel)."""
    with PRICES_PATH.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    latest = max(rows, key=lambda r: int(r["anio"]))
    return {
        "year": int(latest["anio"]),
        "corn_usd_per_bu": float(latest["precio_maiz"]),
        "soy_usd_per_bu": float(latest["precio_soya"]),
    }


def plan_name(plan_id: str) -> str:
    return PLAN_NAMES.get(plan_id, plan_id)


def scenario_label(scenario_key: str) -> str:
    return SCENARIO_LABELS.get(scenario_key, scenario_key)


def pattern_label(pattern: str) -> str:
    return _translate(PATTERN_LABELS, pattern)


def confidence_label(confidence: str) -> str:
    return _translate(CONFIDENCE_LABELS, confidence)
