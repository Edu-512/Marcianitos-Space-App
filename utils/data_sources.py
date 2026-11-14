"""Data access layer for plot and satellite data.

All functions return typed objects from :mod:`utils.types`. They currently
generate deterministic mock data so the interface can be developed in parallel
with the model. Replace each body with real NASA sources (POWER, SMAP, MODIS,
GPM) without changing signatures or return types — the pages only depend on
these functions.
"""

from __future__ import annotations

import zlib
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from utils.types import Plot, RotationScenario, SatelliteSnapshot


def stable_seed(key: str) -> int:
    """Stable per-key seed (unlike ``hash()``, it is not salted per process)."""
    return zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF


_PLOTS = (
    Plot(id="lote-norte", name="Lote Norte", lat=23.48, lon=-102.62, area_hectares=12, current_crop="Maíz"),
    Plot(id="lote-sur", name="Lote Sur", lat=23.31, lon=-102.47, area_hectares=8, current_crop="Sorgo"),
    Plot(id="lote-este", name="Lote Este", lat=23.42, lon=-102.35, area_hectares=15, current_crop="Trigo"),
    Plot(id="lote-oeste", name="Lote Oeste", lat=23.36, lon=-102.71, area_hectares=10, current_crop="Frijol"),
    Plot(id="lote-alto", name="Lote Alto", lat=23.55, lon=-102.49, area_hectares=6, current_crop="Alfalfa"),
    Plot(id="lote-bajo", name="Lote Bajo", lat=23.28, lon=-102.58, area_hectares=9, current_crop="Maíz"),
)

_ROTATION_SCENARIOS = (
    RotationScenario(id="maiz-frijol-sorgo", name="Maíz → Frijol → Sorgo", crops=("Maíz", "Frijol", "Sorgo")),
    RotationScenario(id="sorgo-trigo-cobertura", name="Sorgo → Trigo → Cobertura", crops=("Sorgo", "Trigo", "Cultivo de cobertura")),
    RotationScenario(id="trigo-maiz-alfalfa", name="Trigo → Maíz → Alfalfa", crops=("Trigo", "Maíz", "Alfalfa")),
    RotationScenario(id="maiz-continuo", name="Maíz continuo (sin rotación)", crops=("Maíz", "Maíz", "Maíz")),
)


@st.cache_data(ttl="1h")
def load_plots() -> list[Plot]:
    """All farm plots in the study area."""
    return list(_PLOTS)


@st.cache_data(ttl="1h")
def load_rotation_scenarios() -> list[RotationScenario]:
    """Crop rotation scenarios to compare."""
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
