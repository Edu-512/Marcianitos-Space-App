"""Local demonstration geography and persistent CCv2 map; no model changes."""
from __future__ import annotations

from collections.abc import Callable
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data" / "geography"
FRONTEND = Path(__file__).with_name("map_frontend")


@st.cache_data
def load_geography() -> dict[str, Any]:
    return json.loads((DATA / "butler-demo.geojson").read_text(encoding="utf-8"))


def positions(geometry: dict[str, Any]) -> list[list[float]]:
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    return [point for polygon in polygons for ring in polygon for point in ring]


def bounds(collection: dict[str, Any]) -> list[list[float]]:
    points = [point for feature in collection["features"] for point in positions(feature["geometry"])]
    if not points:
        return [[-92.85, 42.69], [-92.73, 42.77]]
    return [[min(p[0] for p in points), min(p[1] for p in points)],
            [max(p[0] for p in points), max(p[1] for p in points)]]


def map_features(frame: pd.DataFrame, selected_id: str) -> dict[str, Any]:
    """Join only explicitly simulated geometry by its existing demo identifier."""
    collection = load_geography()
    rows = {row["id"]: row for row in frame.to_dict("records")}
    features = []
    for feature in collection["features"]:
        props = feature["properties"]
        row = rows.get(props["demo_plot_id"])
        if row is None:
            continue
        color = "#" + "".join(f"{int(channel):02x}" for channel in row["rgb"])
        features.append({**feature, "properties": {**props, "name": row["name"], "color": color,
                        "selected": row["id"] == selected_id}})
    return {"type": "FeatureCollection", "features": features}


def valid_camera(value: Any) -> dict[str, Any] | None:
    try:
        center = value["center"]
        numbers = [float(center[0]), float(center[1]), float(value["zoom"])]
        if len(center) != 2 or not all(math.isfinite(n) for n in numbers):
            return None
        lon, lat, zoom = numbers
        if not (-180 <= lon <= 180 and -85 <= lat <= 85 and 0 <= zoom <= 22):
            return None
        return {"center": [lon, lat], "zoom": zoom}
    except (TypeError, ValueError, KeyError, IndexError):
        return None


def selection_id(value: Any, valid_ids: tuple[str, ...]) -> str | None:
    if not isinstance(value, dict):
        return None
    selected = value.get("plot_id")
    known = {f["properties"]["demo_plot_id"]: f["properties"]["reference_id"] for f in load_geography()["features"]}
    if selected in valid_ids and known.get(selected) == value.get("reference_id"):
        return str(selected)
    return None


_COMPONENT = st.components.v2.component(
    "field_shift_parcel_map",
    html='<section class="parcel-map" aria-label="Mapa de parcelas simuladas en Butler County"><div class="map-canvas"></div><div class="map-tools"><button class="fit" type="button">Ver parcelas</button><button class="county" type="button">Ver condado</button></div><p class="map-status" role="status"></p><p class="map-selection"></p></section>',
    css=(FRONTEND / "vendor" / "maplibre-gl.css").read_text(encoding="utf-8") + "\n" + (FRONTEND / "map.css").read_text(encoding="utf-8-sig"),
    js=(FRONTEND / "vendor" / "maplibre-gl.js").read_text(encoding="utf-8") + "\n" + (FRONTEND / "map.js").read_text(encoding="utf-8-sig"),
)


def render_map(collection: dict[str, Any], basemap: str, interactive: bool, camera: Any,
               *, key: str, on_select: Callable[[], None], on_camera: Callable[[], None]) -> None:
    _COMPONENT(key=key, data={"collection": collection, "bounds": bounds(collection),
               "basemap": basemap, "interactive": interactive, "camera": valid_camera(camera)},
               height=460, width="stretch", on_selected_change=on_select, on_camera_change=on_camera)
