"""Geospatial field & stress map with multi-year satellite history."""

from __future__ import annotations

import pandas as pd
import pydeck as pdk
import streamlit as st

from utils.data_sources import load_historical_map_snapshot, load_plots

#: Satellite layers offered in the pills (label -> snapshot key).
LAYER_LABELS = {
    "Overall Risk": "overall_risk",
    "Soil Moisture (SMAP)": "soil_moisture_pct",
    "Heat Stress (ECOSTRESS)": "temperature_c",
    "Vegetation Health (NDVI)": "ndvi",
    "Water Trend (GRACE-FO)": "water_trend_idx",
    "Erosion Risk (SRTM)": "erosion_risk",
}

YEAR_OPTIONS = [2021, 2022, 2023, 2024, 2025, 2026]


def _magnitude_rgb(value: float, lo: float, hi: float) -> list[int]:
    """Green -> red color scale by relative magnitude (chart data colors)."""
    span = float(hi - lo) or 1.0
    t = (float(value) - float(lo)) / span
    return [int(74 + (239 - 74) * t), int(222 + (68 - 222) * t), int(128 + (68 - 128) * t)]


def run() -> None:
    """Render the interactive polygon map and the per-plot indicator table."""
    plot_id = st.session_state.selected_plot_id
    plots = load_plots()

    c_year, c_layer = st.columns([3.0, 5.6])
    with c_year:
        year = int(st.select_slider("Historical Year", options=YEAR_OPTIONS, value=2026, key="map_year"))
    with c_layer:
        layer_label = st.pills("Layer to visualize", list(LAYER_LABELS), default="Overall Risk")
        if layer_label is None:
            layer_label = "Overall Risk"
    column = LAYER_LABELS[layer_label]

    # One row per plot for the selected year, with all six indicators.
    rows = []
    for p in plots:
        snap = load_historical_map_snapshot(p.id, year)
        rows.append(
            {
                "id": p.id,
                "name": p.name,
                "area_hectares": p.area_hectares,
                "current_crop": p.current_crop,
                **{key: snap[key] for key in LAYER_LABELS.values()},
            }
        )
    df = pd.DataFrame(rows)

    # Precompute everything pydeck needs as plain columns (no lambdas at render).
    lo, hi = float(df[column].min()), float(df[column].max())
    df["rgb"] = [ _magnitude_rgb(v, lo, hi) for v in df[column] ]
    df["polygon_geo"] = [[[lon, lat] for (lat, lon) in p.polygon] for p in plots]
    df["border_width"] = [3 if p.id == plot_id else 1 for p in plots]
    df["elevation"] = [1.0 if p.id == plot_id else 0.4 for p in plots]
    df["tooltip_text"] = [
        f"{p.name} · {year}\n{p.area_hectares:.0f} ha · {p.current_crop}\n"
        f"{layer_label}: {row[column]:.2f}"
        for p, row in zip(plots, rows)
    ]

    deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(latitude=23.40, longitude=-102.52, zoom=10),
        layers=[
            pdk.Layer(
                "PolygonLayer",
                data=df,
                get_polygon="polygon_geo",
                get_fill_color="rgb",
                get_border_width="border_width",
                get_elevation="elevation",
                pickable=True,
                tooltip={"text": "{tooltip_text}"},
            )
        ],
    )

    selected_name = df.loc[df["id"] == plot_id, "name"].iloc[0]
    st.pydeck_chart(deck, height=520, alt=f"Map of farm plots colored by {layer_label.lower()}")
    st.caption(
        f"Escala de color: bajo (verde) a alto (rojo) para {layer_label.lower()}. "
        f"Lote seleccionado (borde grueso): {selected_name}."
    )

    # --- Multi-plot comparison table for the selected year ----------------------
    st.markdown(f"### Comparación de lotes ({year})")
    table = df[["id", "name", "area_hectares", "current_crop", *LAYER_LABELS.values()]].set_index("id")
    st.dataframe(table, alt="Table of plots with their satellite indicators for the selected year")
