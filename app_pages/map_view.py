"""Geospatial field and stress map with multi-year satellite history."""

from __future__ import annotations

import pandas as pd
import pydeck as pdk
import streamlit as st

from components.palette import PALETTE
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
_MAP_COLOR_STOPS = tuple(
    tuple(int(PALETTE[color][index : index + 2], 16) for index in (1, 3, 5))
    for color in ("vegetation", "peach", "soil_dark")
)


def _magnitude_rgb(value: float, lo: float, hi: float) -> list[int]:
    """Interpolate the shared palette from vegetation green through peach to soil."""
    span = float(hi - lo) or 1.0
    t = min(1.0, max(0.0, (float(value) - float(lo)) / span))
    scaled = t * (len(_MAP_COLOR_STOPS) - 1)
    start = min(int(scaled), len(_MAP_COLOR_STOPS) - 2)
    fraction = scaled - start
    return [
        round(_MAP_COLOR_STOPS[start][channel] * (1 - fraction) + _MAP_COLOR_STOPS[start + 1][channel] * fraction)
        for channel in range(3)
    ]


def run() -> None:
    """Render the interactive polygon map and the per-plot indicator table."""
    plot_id = st.session_state.selected_plot_id
    plots = load_plots()

    if not plots:
        st.warning("No plots available to display on the map.")
        return

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
        try:
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
        except Exception:
            # Skip plots where snapshot data cannot be loaded to prevent complete map failure
            continue
            
    if not rows:
        st.error(f"Could not load map data for the year {year}.")
        return

    df = pd.DataFrame(rows)

    # Precompute everything pydeck needs as plain columns (no lambdas at render).
    lo, hi = float(df[column].min()), float(df[column].max())
    df["rgb"] = [ _magnitude_rgb(v, lo, hi) for v in df[column] ]
    df["polygon_geo"] = [[[lon, lat] for (lat, lon) in p.polygon] for p in plots if p.id in df["id"].values]
    df["border_width"] = [3 if p.id == plot_id else 1 for p in plots if p.id in df["id"].values]
    df["elevation"] = [1.0 if p.id == plot_id else 0.4 for p in plots if p.id in df["id"].values]
    
    # Safely build tooltip text matching the valid plots
    tooltip_data = []
    for p in plots:
        if p.id in df["id"].values:
            row_data = df.loc[df["id"] == p.id].iloc[0]
            tooltip_data.append(
                f"{p.name} - {year}\n{p.area_hectares:.0f} ha - {p.current_crop}\n"
                f"{layer_label}: {row_data[column]:.2f}"
            )
    df["tooltip_text"] = tooltip_data

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
                auto_highlight=True,
            )
        ],
        tooltip={"text": "{tooltip_text}"},
    )

    try:
        selected_name = df.loc[df["id"] == plot_id, "name"].iloc[0]
    except IndexError:
        selected_name = "Unknown Plot"

    st.pydeck_chart(deck, height=520)
    st.caption(
        f"Relative indicator scale: Green through Soil colors for {layer_label.lower()}; "
        "interpretation depends on the selected layer. "
        f"Selected plot (thick border): {selected_name}."
    )

    # --- Multi-plot comparison table for the selected year ----------------------
    st.subheader(f"Plot Comparison ({year})")
    
    # Rename columns for the display table to be farmer-friendly
    display_columns = {
        "id": "Plot ID",
        "name": "Field Name",
        "area_hectares": "Area (ha)",
        "current_crop": "Current Crop",
    }
    
    # Invert the LAYER_LABELS dictionary to get display names for the indicator columns
    inv_layer_labels = {v: k for k, v in LAYER_LABELS.items()}
    display_columns.update(inv_layer_labels)
    
    table = df.rename(columns=display_columns).set_index("Plot ID")
    
    # Format numeric columns for cleaner display
    format_dict = {
        "Area (ha)": "{:.1f}",
        "Overall Risk": "{:.2f}",
        "Soil Moisture (SMAP)": "{:.1f}%",
        "Heat Stress (ECOSTRESS)": "{:.1f}",
        "Vegetation Health (NDVI)": "{:.2f}",
        "Water Trend (GRACE-FO)": "{:.2f}",
        "Erosion Risk (SRTM)": "{:.2f}",
    }
    
    st.dataframe(
        table.style.format(format_dict, na_rep="-"),
        use_container_width=True
    )