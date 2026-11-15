"""Data access layer for plot and satellite data.

All functions return typed objects from :mod:`utils.types`. They currently
generate deterministic mock data so the interface can be developed in parallel
with the model. Replace each body with real NASA sources (POWER, SMAP, MODIS,
GPM, ECOSTRESS, GRACE-FO, SRTM) without changing signatures or return types —
the pages only depend on these functions.
"""

from __future__ import annotations

import math
import zlib
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from utils.types import Plot, RotationScenario, SatelliteSnapshot, SeasonalWindow


def stable_seed(key: str) -> int:
    """Stable per-key seed (unlike ``hash()``, it is not salted per process)."""
    return zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF


def _make_polygon(lat: float, lon: float, area_hectares: float) -> tuple[tuple[float, float], ...]:
    """Deterministic irregular parcel boundary around (lat, lon), scaled by area.

    A square-equivalent side of ``sqrt(area)`` km is jittered at the corners and
    edge midpoints so parcels look like real fields, not perfect rectangles.
    """
    rng = np.random.default_rng(stable_seed(f"polygon:{lat}:{lon}"))
    side_km = math.sqrt(area_hectares)
    half_lat = side_km / 2 / 111.0
    half_lon = side_km / 2 / (111.0 * math.cos(math.radians(lat)))

    def _jitter(scale: float) -> float:
        return float(rng.uniform(-0.35, 0.35)) * scale

    corners = [
        (lat - half_lat + _jitter(half_lat), lon - half_lon + _jitter(half_lon)),
        (lat - half_lat + _jitter(half_lat), lon + half_lon + _jitter(half_lon)),
        (lat + half_lat + _jitter(half_lat), lon + half_lon + _jitter(half_lon)),
        (lat + half_lat + _jitter(half_lat), lon - half_lon + _jitter(half_lon)),
    ]
    verts: list[tuple[float, float]] = []
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        verts.append(corners[i])
        verts.append(((a[0] + b[0]) / 2 + _jitter(half_lat), (a[1] + b[1]) / 2 + _jitter(half_lon)))
    return tuple((round(v[0], 6), round(v[1], 6)) for v in verts)


_PLOT_BASES = (
    ("lote-norte", "Lote Norte", 23.48, -102.62, 12, "Maíz"),
    ("lote-sur", "Lote Sur", 23.31, -102.47, 8, "Sorgo"),
    ("lote-este", "Lote Este", 23.42, -102.35, 15, "Trigo"),
    ("lote-oeste", "Lote Oeste", 23.36, -102.71, 10, "Frijol"),
    ("lote-alto", "Lote Alto", 23.55, -102.49, 6, "Alfalfa"),
    ("lote-bajo", "Lote Bajo", 23.28, -102.58, 9, "Maíz"),
)

_PLOTS = tuple(
    Plot(id=i, name=n, lat=la, lon=lo, area_hectares=a, current_crop=c, polygon=_make_polygon(la, lo, a))
    for (i, n, la, lo, a, c) in _PLOT_BASES
)

_ROTATION_SCENARIOS = (
    RotationScenario(id="maiz-continuo", name="Maíz continuo (sin rotación)", crops=("Maíz", "Maíz", "Maíz")),
    RotationScenario(id="maiz-frijol-sorgo", name="Maíz → Frijol → Sorgo", crops=("Maíz", "Frijol", "Sorgo")),
    RotationScenario(id="sorgo-trigo-cobertura", name="Sorgo → Trigo → Cobertura", crops=("Sorgo", "Trigo", "Cultivo de cobertura")),
    RotationScenario(id="trigo-maiz-alfalfa", name="Trigo → Maíz → Alfalfa", crops=("Trigo", "Maíz", "Alfalfa")),
    RotationScenario(id="sorgo-frijol-cobertura", name="Sorgo → Frijol → Cobertura", crops=("Sorgo", "Frijol", "Cultivo de cobertura")),
)


@st.cache_data(ttl="1h")
def load_plots() -> list[Plot]:
    """All farm plots in the study area."""
    return list(_PLOTS)


@st.cache_data(ttl="1h")
def load_rotation_scenarios() -> list[RotationScenario]:
    """Crop rotation scenarios to compare (includes the monoculture baseline)."""
    return list(_ROTATION_SCENARIOS)


@st.cache_data(ttl="15m")
def load_satellite_snapshot(plot_id: str) -> SatelliteSnapshot:
    """Latest satellite-derived indicators for one plot.

    TODO(model team): replace with real NASA POWER / SMAP / MODIS values.
    """
    rng = np.random.default_rng(stable_seed(f"snapshot:{plot_id}"))
    return SatelliteSnapshot(
        plot_id=plot_id,
        date=date.today().isoformat(),
        precipitation_mm=float(rng.uniform(40, 160)),
        soil_moisture_pct=float(rng.uniform(8, 35)),
        temperature_c=float(rng.uniform(24, 38)),
        ndvi=float(rng.uniform(0.2, 0.75)),
        water_availability_idx=float(rng.uniform(0.1, 0.9)),
    )


@st.cache_data(ttl="15m")
def load_plot_history(plot_id: str, months: int = 12) -> pd.DataFrame:
    """Monthly satellite history for one plot (last ``months`` months).

    Columns: date, precipitation_mm, soil_moisture_pct, temperature_c, ndvi.

    TODO(model team): replace with real time series from NASA sources.
    """
    base = load_satellite_snapshot(plot_id)
    rng = np.random.default_rng(stable_seed(f"history:{plot_id}"))

    end = date.today()
    year, month = end.year, end.month
    dates: list[str] = []
    for i in range(months - 1, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        dates.append(date(y, m, 1).isoformat())

    return pd.DataFrame(
        {
            "date": dates,
            "precipitation_mm": np.round(np.clip(base.precipitation_mm / months + rng.normal(0, 8, months), 0, None), 1),
            "soil_moisture_pct": np.round(np.clip(base.soil_moisture_pct + rng.normal(0, 3, months), 2, None), 1),
            "temperature_c": np.round(np.clip(base.temperature_c + rng.normal(0, 2.5, months), 0, None), 1),
            "ndvi": np.round(np.clip(base.ndvi + rng.normal(0, 0.05, months), 0, 1), 3),
        }
    )


@st.cache_data(ttl="15m")
def load_seasonal_windows(plot_id: str) -> list[SeasonalWindow]:
    """Deterministic bare-soil and climate-hazard windows across the year.

    TODO(model team): replace with real hazard modeling (POWER, GPM, SMAP).
    """
    rng = np.random.default_rng(stable_seed(f"windows:{plot_id}"))

    def _month(n: int) -> str:
        return f"{((n - 1) % 12) + 1:02d}"

    bare_start = 3 + int(rng.integers(0, 2))  # Mar/Apr post-harvest fallow
    bare_len = 2 + int(rng.integers(0, 2))  # 2-3 months uncovered
    heat_severity = ["Moderate", "High"][int(rng.integers(0, 2))]
    frost_severity = "Low" if rng.random() < 0.7 else "Moderate"

    return [
        SeasonalWindow(
            start_month=_month(bare_start),
            end_month=_month(bare_start + bare_len - 1),
            window_type="Bare Soil (Erosion Risk)",
            severity=["Low", "Moderate", "High"][int(rng.integers(0, 3))],
            plain_explanation=(
                "Tras la cosecha el suelo queda sin cobertura; cada lluvia fuerte arranca "
                "la capa fértil. Sembrar un cultivo de cobertura cierra esta ventana."
            ),
        ),
        SeasonalWindow(
            start_month="06",
            end_month="08",
            window_type="Peak Heat Stress",
            severity=heat_severity,
            plain_explanation=(
                "El calor pico coincide con la etapa más sensible del cultivo; los suelos "
                "secos multiplican el estrés y reducen el rinde."
            ),
        ),
        SeasonalWindow(
            start_month="12",
            end_month="01",
            window_type="Frost Risk",
            severity=frost_severity,
            plain_explanation=(
                "Heladas ligeras en la temporada fría; afectan siembras tardías y rebrotes. "
                "En esta zona el riesgo es bajo pero no nulo."
            ),
        ),
    ]


@st.cache_data(ttl="15m")
def load_historical_map_snapshot(plot_id: str, year: int) -> dict[str, float]:
    """Annual satellite indicators for one plot (multi-year scrubbing, 2021-2026).

    Keys: overall_risk, soil_moisture_pct, temperature_c, ndvi, water_trend_idx, erosion_risk.

    TODO(model team): replace with real yearly composites (SMAP, MODIS, GRACE-FO, SRTM).
    """
    rng = np.random.default_rng(stable_seed(f"histmap:{plot_id}:{year}"))
    drift = year - 2021  # slow multi-year trend so scrubbing shows visible change
    return {
        "overall_risk": round(float(np.clip(0.35 + 0.04 * drift + rng.uniform(-0.1, 0.1), 0.05, 0.95)), 2),
        "soil_moisture_pct": round(float(np.clip(22 - 0.8 * drift + rng.uniform(-3, 3), 6, 40)), 1),
        "temperature_c": round(float(np.clip(30 + 0.15 * drift + rng.uniform(-1.5, 1.5), 20, 42)), 1),
        "ndvi": round(float(np.clip(0.5 - 0.02 * drift + rng.uniform(-0.08, 0.08), 0.1, 0.9)), 2),
        "water_trend_idx": round(float(np.clip(0.6 - 0.05 * drift + rng.uniform(-0.08, 0.08), 0.05, 0.95)), 2),
        "erosion_risk": round(float(np.clip(0.3 + 0.03 * drift + rng.uniform(-0.1, 0.1), 0.05, 0.95)), 2),
    }
