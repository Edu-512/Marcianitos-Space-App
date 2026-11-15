"""Data access layer for plot and satellite data.

All functions return typed objects from :mod:`utils.types`. Plots come from the
Butler County, Iowa model delivery (``model/``): real field shapes derived from
the USDA Cropland Data Layer, with SSURGO soil and NASA POWER weather behind the
model results. Signatures are unchanged — the pages only depend on these
functions.

The delivery has no plot-level satellite snapshot, monthly history, seasonal
windows or yearly map composites. Those functions return explicit "not
available" values (NaN / empty) instead of invented numbers.
"""

from __future__ import annotations

import zlib

import pandas as pd
import streamlit as st

from model.loader import load_demo_profiles, load_parcels, pattern_label
from model.units import acres_to_ha
from utils.types import Plot, RotationScenario, SatelliteSnapshot, SeasonalWindow

_NAN = float("nan")


def stable_seed(key: str) -> int:
    """Stable per-key seed (unlike ``hash()``, it is not salted per process)."""
    return zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF


# Only corn and soybean: the crops grown in Butler County and the only ones the
# model has data for. ``maiz-continuo`` stays as the pinned baseline id.
_ROTATION_SCENARIOS = (
    RotationScenario(id="maiz-continuo", name="Continuous Corn (No Rotation)",
                     crops=("Corn", "Corn", "Corn")),
    RotationScenario(id="maiz-soya", name="Corn → Soybean",
                     crops=("Corn", "Soybean")),
    RotationScenario(id="maiz-soya-cobertura", name="Corn → Soybean + Cover Crop",
                     crops=("Corn", "Soybean", "Cover Crop")),
)


def _ring_area_and_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    """Shoelace area (signed, degrees²) and centroid (lon, lat) of one ring."""
    area2 = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area2) < 1e-18:  # degenerate ring: fall back to the vertex mean
        n = len(ring) or 1
        return 0.0, sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n
    return area2 / 2, cx / (3 * area2), cy / (3 * area2)


def _main_outer_ring(geometry: dict) -> list[list[float]]:
    """Outer ring of a Polygon, or of the largest part of a MultiPolygon.

    ``Plot.polygon`` holds a single ring; 25 of the 167 plots are MultiPolygons.
    Their smaller parts stay in the GeoJSON for the map to draw.
    """
    if geometry["type"] == "Polygon":
        return geometry["coordinates"][0]
    parts = [poly[0] for poly in geometry["coordinates"]]
    return max(parts, key=lambda ring: abs(_ring_area_and_centroid(ring)[0]))


def _plot_from_feature(plot_id: str, feature: dict, profile: str | None) -> Plot:
    props = feature["properties"]
    ring = _main_outer_ring(feature["geometry"])
    _, lon, lat = _ring_area_and_centroid([list(p[:2]) for p in ring])
    name = f"{profile} · Field {plot_id}" if profile else f"Field {plot_id}"
    return Plot(
        id=plot_id,
        name=name,
        lat=lat,
        lon=lon,
        area_hectares=acres_to_ha(props["acres"]),
        current_crop=pattern_label(props["patron"]),
        polygon=tuple((float(p[1]), float(p[0])) for p in ring),
    )


@st.cache_data(ttl="1h")
def load_plots() -> list[Plot]:
    """All 167 Butler County plots: the five showcase plots first, then by id."""
    parcels = load_parcels()
    profiles = load_demo_profiles()
    showcase = [pid for pid in profiles if pid in parcels]
    rest = sorted((pid for pid in parcels if pid not in profiles), key=int)
    return [_plot_from_feature(pid, parcels[pid], profiles.get(pid)) for pid in showcase + rest]


@st.cache_data(ttl="1h")
def load_rotation_scenarios() -> list[RotationScenario]:
    """Crop rotation scenarios to compare (includes the monoculture baseline)."""
    return list(_ROTATION_SCENARIOS)


@st.cache_data(ttl="15m")
def load_satellite_snapshot(plot_id: str) -> SatelliteSnapshot:
    """Latest satellite-derived indicators for one plot.

    The model delivery has no plot-level snapshot: every value is NaN (shown as
    "Not available") and the date is empty. NASA POWER weather is county-level
    and lives in the scenario climate blocks instead.
    """
    return SatelliteSnapshot(
        plot_id=plot_id,
        date="",
        precipitation_mm=_NAN,
        soil_moisture_pct=_NAN,
        temperature_c=_NAN,
        ndvi=_NAN,
        water_availability_idx=_NAN,
    )


@st.cache_data(ttl="15m")
def load_plot_history(plot_id: str, months: int = 12) -> pd.DataFrame:
    """Monthly satellite history for one plot. Not in the delivery: empty frame.

    Columns: date, precipitation_mm, soil_moisture_pct, temperature_c, ndvi.
    """
    return pd.DataFrame(columns=["date", "precipitation_mm", "soil_moisture_pct", "temperature_c", "ndvi"])


@st.cache_data(ttl="15m")
def load_seasonal_windows(plot_id: str) -> list[SeasonalWindow]:
    """Bare-soil and climate-hazard windows. Not in the delivery: empty list."""
    return []


@st.cache_data(ttl="15m")
def load_historical_map_snapshot(plot_id: str, year: int) -> dict[str, float]:
    """Annual indicators for the map's year scrubber. Not in the delivery: NaN.

    Keys: overall_risk, soil_moisture_pct, temperature_c, ndvi, water_trend_idx, erosion_risk.
    The map is rebuilt on real soil layers in a later stage.
    """
    return {key: _NAN for key in (
        "overall_risk", "soil_moisture_pct", "temperature_c", "ndvi", "water_trend_idx", "erosion_risk",
    )}
