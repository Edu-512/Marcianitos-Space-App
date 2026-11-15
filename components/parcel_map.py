"""Presentation-only parcel map helpers; no agricultural calculations."""
from __future__ import annotations

from collections.abc import Callable, Mapping
import math
from typing import Any

import pandas as pd
import pydeck as pdk

from components.palette import PALETTE
from utils.types import Plot

INDICATORS = {
    "Riesgo general": ("overall_risk", "índice"),
    "Humedad del suelo": ("soil_moisture_pct", "%"),
    "Temperatura": ("temperature_c", "°C"),
    "Vegetación": ("ndvi", "índice"),
    "Disponibilidad de agua": ("water_trend_idx", "índice"),
    "Riesgo de erosión": ("erosion_risk", "índice"),
}
LAYER_IDS = ("parcelas", "centros", "seleccion-contorno", "seleccion-borde")
CROP_COLORS = [PALETTE["soil_dark"], PALETTE["vegetation"], PALETTE["peach"], PALETTE["soil"], PALETTE["vegetation_bright"], "#8373a8"]
NO_DATA_COLOR = "#92918a"


def rgb(color: str) -> list[int]:
    return [int(color[i:i + 2], 16) for i in (1, 3, 5)]


def valid_position(lat: Any, lon: Any) -> bool:
    try:
        return math.isfinite(float(lat)) and math.isfinite(float(lon)) and -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
    except (TypeError, ValueError):
        return False


def crop_categories(plots: list[Plot]) -> dict[str, str]:
    crops = sorted({p.current_crop or "Sin cultivo registrado" for p in plots})
    return {crop: CROP_COLORS[i % len(CROP_COLORS)] for i, crop in enumerate(crops)}


def build_rows(plots: list[Plot], year: int, loader: Callable[[str, int], dict[str, float]]) -> pd.DataFrame:
    rows = []
    for plot in plots:
        try:
            snapshot = loader(plot.id, year)
        except Exception:
            snapshot = {}
        if not isinstance(snapshot, Mapping):
            snapshot = {}
        # Geometry is used as supplied; an absent/invalid boundary becomes a point,
        # never a guessed polygon or a fabricated legal property boundary.
        polygon = plot.polygon
        polygon_ok = len(polygon) >= 3 and all(valid_position(lat, lon) for lat, lon in polygon)
        rows.append({
            "id": plot.id, "name": plot.name, "lat": plot.lat, "lon": plot.lon,
            "area_hectares": plot.area_hectares,
            "crop": plot.current_crop or "Sin cultivo registrado",
            "polygon_geo": [[lon, lat] for lat, lon in polygon] if polygon_ok else [],
            "mappable": valid_position(plot.lat, plot.lon),
            **{column: snapshot.get(column, float("nan")) for column, _ in INDICATORS.values()},
        })
    return pd.DataFrame(rows)


def color_rows(frame: pd.DataFrame, mode: str, categories: dict[str, str]) -> pd.DataFrame:
    result = frame.copy()
    if mode == "Cultivos":
        result["rgb"] = result["crop"].map(lambda crop: rgb(categories[crop]))
    elif mode == "Parcelas":
        result["rgb"] = [rgb(PALETTE["soil"])] * len(result)
    else:
        column, _ = INDICATORS[mode]
        values = pd.to_numeric(result[column], errors="coerce").replace([float("inf"), float("-inf")], float("nan"))
        lo, hi = values.min(), values.max()
        stops = [rgb(PALETTE[c]) for c in ("vegetation", "peach", "soil_dark")]
        def shade(value: float) -> list[int]:
            if not math.isfinite(value):
                return rgb(NO_DATA_COLOR)
            t = (value - lo) / (hi - lo) if hi > lo else 0.5
            scaled = min(1.0, max(0.0, t)) * 2
            index = min(int(scaled), 1)
            return [round(stops[index][c] * (1 - (scaled - index)) + stops[index + 1][c] * (scaled - index)) for c in range(3)]
        result["rgb"] = values.map(shade)
    return result


def plot_id_from_selection(state: Any, valid_ids: tuple[str, ...]) -> str | None:
    if not isinstance(state, Mapping):
        return None
    selection = state.get("selection", {})
    if not isinstance(selection, Mapping):
        return None
    objects = selection.get("objects", {})
    if not isinstance(objects, Mapping):
        return None
    for layer in LAYER_IDS:
        items = objects.get(layer, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, Mapping) and item.get("id") in valid_ids:
                return str(item["id"])
    return None


def make_deck(frame: pd.DataFrame, selected_id: str, interactive: bool) -> pdk.Deck:
    # Only rendering fields go to the browser: missing indicator NaNs must not
    # leak into Deck's JSON (JSON.parse rejects NaN).
    visible = frame.loc[frame["mappable"], ["id", "name", "lat", "lon", "crop", "polygon_geo", "rgb", "area_hectares"]].copy()
    visible["selection_label"] = visible.apply(lambda row: ("✓ " if row["id"] == selected_id else "") + row["name"], axis=1)
    visible["tooltip_text"] = visible.apply(lambda row: f"{row['name']}\n{row['area_hectares']:g} ha · {row['crop']}\nParcela de demostración", axis=1)
    visible = visible.drop(columns=["area_hectares"])
    polygons = visible.loc[visible["polygon_geo"].map(bool)]
    points = visible.loc[~visible["polygon_geo"].map(bool)]
    selected = polygons.loc[polygons["id"] == selected_id]
    layers = [
        pdk.Layer("PolygonLayer", polygons, id="parcelas", get_polygon="polygon_geo", get_fill_color="rgb", filled=True, stroked=True,
                  get_line_color=[55, 40, 30], get_line_width=1.5, line_width_units="pixels", pickable=True, auto_highlight=True),
        pdk.Layer("ScatterplotLayer", points, id="centros", get_position="[lon, lat]", get_fill_color="rgb", get_radius=120,
                  radius_min_pixels=8, stroked=True, get_line_color=[55, 40, 30], get_line_width=2, line_width_units="pixels", pickable=True),
        pdk.Layer("PolygonLayer", selected, id="seleccion-contorno", get_polygon="polygon_geo", filled=False, stroked=True,
                  get_line_color=[255, 248, 244], get_line_width=7, line_width_units="pixels", pickable=True),
        pdk.Layer("PolygonLayer", selected, id="seleccion-borde", get_polygon="polygon_geo", filled=False, stroked=True,
                  get_line_color=rgb(PALETTE["soil_dark"]), get_line_width=3, line_width_units="pixels", pickable=True),
        pdk.Layer("ScatterplotLayer", points.loc[points["id"] == selected_id], id="seleccion-punto", get_position="[lon, lat]",
                  get_radius=120, radius_min_pixels=12, filled=False, stroked=True, get_line_width=4,
                  line_width_units="pixels", get_line_color=[255, 248, 244], pickable=False),
        pdk.Layer("TextLayer", visible, id="nombres", get_position="[lon, lat]", get_text="selection_label", get_size=13,
                  get_color=[53, 35, 25], get_pixel_offset=[0, -22], outline_width=3, outline_color=[255, 248, 244], pickable=False),
    ]
    controller = {"dragPan": interactive, "scrollZoom": False, "touchZoom": interactive, "doubleClickZoom": interactive,
                  "keyboard": interactive, "dragRotate": False, "touchRotate": False}
    return pdk.Deck(
        layers=layers, map_style=None,
        views=[pdk.View(type="MapView", controller=controller)],
        initial_view_state=pdk.ViewState(latitude=float(visible["lat"].mean()), longitude=float(visible["lon"].mean()), zoom=9.5),
        tooltip={"text": "{tooltip_text}"},
    )
