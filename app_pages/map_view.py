"""Interactive geospatial map of all plots with satellite variables."""

import pandas as pd
import pydeck as pdk
import streamlit as st

from utils.data_sources import load_plots, load_satellite_snapshot
from utils.model_interface import compute_plot_risk

plot_id = st.session_state.selected_plot_id
plots = load_plots()

# One row per plot with the variables available for coloring.
rows = []
for p in plots:
    snap = load_satellite_snapshot(p.id)
    risk = compute_plot_risk(p.id)
    rows.append(
        {
            "id": p.id,
            "name": p.name,
            "lon": p.lon,
            "lat": p.lat,
            "area_hectares": p.area_hectares,
            "current_crop": p.current_crop,
            "overall_risk": risk.overall_risk,
            "soil_moisture_pct": snap.soil_moisture_pct,
            "ndvi": snap.ndvi,
            "temperature_c": snap.temperature_c,
        }
    )
df = pd.DataFrame(rows)

VARIABLES = {
    "Overall risk": "overall_risk",
    "Soil moisture": "soil_moisture_pct",
    "NDVI": "ndvi",
    "Temperature": "temperature_c",
}
variable_label = st.pills("Variable to visualize", list(VARIABLES), default="Overall risk")
if variable_label is None:
    variable_label = "Overall risk"
column = VARIABLES[variable_label]

# Precompute color (green -> red by magnitude) and radius so the pydeck
# layer only needs plain column accessors.
lo, hi = df[column].min(), df[column].max()
span = float(hi - lo) or 1.0


def _magnitude_rgb(value: float) -> list[int]:
    t = (float(value) - float(lo)) / span
    return [int(74 + (239 - 74) * t), int(222 + (68 - 222) * t), int(128 + (68 - 128) * t)]


df["rgb"] = df[column].map(_magnitude_rgb)
df["radius"] = 6 + df["area_hectares"]

deck = pdk.Deck(
    map_style=None,
    initial_view_state=pdk.ViewState(latitude=23.40, longitude=-102.52, zoom=10),
    layers=[
        pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position="[lon, lat]",
            get_color="rgb",
            get_radius="radius",
            pickable=True,
        )
    ],
)

st.pydeck_chart(deck, height=520, alt=f"Map of farm plots colored by {variable_label.lower()}")
st.caption(f"Color scale: low (green) to high (red) values of {variable_label.lower()}. Selected plot: {df.loc[df['id'] == plot_id, 'name'].iloc[0]}.")

st.markdown("### Plots in the study area")
table = df.drop(columns=["rgb", "radius"]).set_index("id")
st.dataframe(table, alt="Table of plots with their satellite indicators")
