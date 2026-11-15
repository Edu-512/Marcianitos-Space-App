"""Butler County field map: real plot outlines and indicators over satellite imagery."""

from __future__ import annotations

import base64
import json
import math
import urllib.parse

import pandas as pd
import pydeck as pdk
import streamlit as st

from components.palette import PALETTE
from model import units
from model.loader import ROOT, load_parcels, load_results, pattern_label
from utils.data_sources import load_plots
from utils.model_interface import compute_plot_risk

#: Layers offered in the pills: label -> (table column, how it is drawn).
#: "polygon" colors the plots; "pattern" colors them by crop pattern;
#: a PNG file name draws that soil raster under plot outlines.
#: Only layers with real data behind them. SMAP soil moisture, NDVI and
#: GRACE-FO are not in the delivery; heat is one county-wide NASA POWER value,
#: identical for every plot, so it is not mapped.
LAYER_LABELS = {
    "Overall Risk": ("overall_risk", "polygon"),
    "Drought Risk": ("drought_risk", "polygon"),
    "Erosion Risk (RUSLE)": ("erosion_t_ha", "polygon"),
    "Unplanted in 2019": ("unplanted_2019_pct", "polygon"),
    "Crop Pattern": ("current_crop", "pattern"),
    "Productivity (CSR2)": ("csr2", "capa_productividad.png"),
    "Soil Yield Adjustment": ("soil_adjustment_pct", "capa_ajuste_modelo.png"),
    "Sand Content": ("sand_pct", "capa_arena.png"),
    "Flood-Prone Soils (SSURGO)": ("flood_rating_pct", "capa_riesgo_inundacion.png"),
}

#: Plain-language scale for each layer, shown under the map.
LAYER_NOTES = {
    "Overall Risk": "Combined drought, heat and nutrient index (0 to 1).",
    "Drought Risk": "County weather in dry Augusts times how little water the field's soil holds (0 to 1).",
    "Erosion Risk (RUSLE)": "Yearly soil loss with a corn–soybean rotation, from slope and soil (t/ha). Tolerable limit: 11.2 t/ha.",
    "Unplanted in 2019": "Share of the field satellites saw unplanted after the wet spring of 2019.",
    "Crop Pattern": "Corn–soybean pattern seen by satellite from 2018 to 2025.",
    "Productivity (CSR2)": "Soil map: light blue 30 (poor) to dark blue 100 (best).",
    "Soil Yield Adjustment": "Soil map: red −18% through grey 0% to blue +18% on expected yield.",
    "Sand Content": "Soil map: light blue 10% to dark blue 70% sand.",
    "Flood-Prone Soils (SSURGO)": (
        "Soil map: light blue 0% to dark blue 100% flooding rating at planting. This rating did not "
        "predict which fields went unplanted in 2019; see 'Unplanted in 2019' for what was measured."
    ),
}

#: Years covered by the USDA Cropland Data Layer in the delivery.
YEAR_OPTIONS = list(range(2018, 2026))

# Background imagery (not data). deck.gl's TileLayer cannot draw raster tiles from
# pydeck (it needs a JavaScript renderSubLayers function), so the Esri tiles go in
# as a MapLibre raster style passed as a data: URL, which Streamlit accepts.
_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/{}/MapServer/tile/{{z}}/{{y}}/{{x}}"
BASEMAPS = {
    "Satellite": (_ESRI.format("World_Imagery"), 19),
    "Terrain": (_ESRI.format("World_Terrain_Base"), 13),
}

_MAP_COLOR_STOPS = tuple(
    tuple(int(PALETTE[color][index : index + 2], 16) for index in (1, 3, 5))
    for color in ("vegetation", "peach", "soil_dark")
)
_PATTERN_COLORS = {
    "rotacion estricta": list(_MAP_COLOR_STOPS[0]),
    "rotacion con quiebre": list(_MAP_COLOR_STOPS[1]),
    "maiz dominante": list(_MAP_COLOR_STOPS[2]),
    "irregular": [168, 168, 168],
}


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


def _basemap_style(name: str) -> str:
    url, max_zoom = BASEMAPS[name]
    style = {
        "version": 8,
        "sources": {"esri": {"type": "raster", "tiles": [url], "tileSize": 256, "maxzoom": max_zoom,
                             "attribution": "Tiles © Esri"}},
        "layers": [{"id": "esri", "type": "raster", "source": "esri"}],
    }
    return "data:application/json;charset=utf-8," + urllib.parse.quote(json.dumps(style))


@st.cache_resource(show_spinner=False)
def _soil_png(file_name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((ROOT / "datos_ui" / file_name).read_bytes()).decode()


@st.cache_resource(show_spinner=False)
def _soil_bounds() -> list[float]:
    b = json.loads((ROOT / "datos_ui" / "suelo_bounds.json").read_text(encoding="utf-8"))
    return [b["oeste"], b["sur"], b["este"], b["norte"]]


@st.cache_data(show_spinner=False)
def _plot_rows() -> pd.DataFrame:
    """One row per plot with every layer's real value (same in every year)."""
    parcels, results = load_parcels(), load_results()
    rows = []
    for p in load_plots():
        props = parcels[p.id]["properties"]
        record = results[p.id]
        rotation = next(pl for pl in record["escenarios"]["normal"]["planes"] if pl["id"] == "maiz_soya")
        risk = compute_plot_risk(p.id)
        rows.append({
            "id": p.id,
            "name": p.name,
            "area_hectares": p.area_hectares,
            "current_crop": p.current_crop,
            "pattern_key": props["patron"],
            "overall_risk": risk.overall_risk,
            "drought_risk": risk.drought_risk,
            "erosion_t_ha": units.short_tons_acre_to_t_ha(rotation["suelo"]["erosion_ton_acre_anio"]),
            "unplanted_2019_pct": float(props["pct_sin_sembrar19"]),
            "csr2": float(props["csr2"]),
            "soil_adjustment_pct": float(record["parcela"]["ajuste_por_suelo_pct"]),
            "sand_pct": float(props["arena"]),
            "flood_rating_pct": float(props["inund"]),
        })
    return pd.DataFrame(rows)


def _parts(plot_id: str) -> list:
    """Every part of the plot's (Multi)Polygon, as rings in [lon, lat]."""
    geom = load_parcels()[plot_id]["geometry"]
    return [geom["coordinates"]] if geom["type"] == "Polygon" else list(geom["coordinates"])


def _fmt(value: float, pattern: str) -> str:
    return "Not available" if isinstance(value, float) and math.isnan(value) else pattern.format(value)


def run() -> None:
    """Render the interactive polygon map and the per-plot indicator table."""
    plot_id = st.session_state.selected_plot_id
    df = _plot_rows()

    if df.empty:
        st.warning("No plots available to display on the map.")
        return

    c_year, c_layer = st.columns([3.0, 5.6])
    with c_year:
        year = int(st.select_slider("Historical Year", options=YEAR_OPTIONS, value=YEAR_OPTIONS[-1], key="map_year"))
    with c_layer:
        layer_label = st.pills("Layer to visualize", list(LAYER_LABELS), default="Overall Risk")
        if layer_label is None:
            layer_label = "Overall Risk"

    column, mode = LAYER_LABELS[layer_label]
    soil_png = mode if mode.endswith(".png") else None

    basemap = st.segmented_control("Background", list(BASEMAPS), default="Satellite", key="map_basemap") or "Satellite"

    # Colors: value scale for polygon layers, categories for crop pattern,
    # plain outlines when a soil map is drawn underneath.
    if mode == "polygon":
        lo, hi = float(df[column].min()), float(df[column].max())
        df["rgb"] = [_magnitude_rgb(v, lo, hi) for v in df[column]]
        fill_alpha = 170
    elif mode == "pattern":
        df["rgb"] = [_PATTERN_COLORS.get(k, [168, 168, 168]) for k in df["pattern_key"]]
        fill_alpha = 170
    else:
        df["rgb"] = [[255, 255, 255]] * len(df)
        fill_alpha = 0

    value_fmt = {
        "overall_risk": "{:.2f}", "drought_risk": "{:.2f}", "erosion_t_ha": "{:.1f} t/ha",
        "unplanted_2019_pct": "{:.1f}%", "csr2": "{:.0f}", "soil_adjustment_pct": "{:+.1f}%",
        "sand_pct": "{:.0f}%", "flood_rating_pct": "{:.0f}%",
    }
    rows, selected_rows = [], []
    for rec in df.to_dict("records"):
        shown = rec[column] if mode == "pattern" else _fmt(rec[column], value_fmt[column])
        tooltip = (
            f"{rec['name']} - {year}\n{rec['area_hectares']:.0f} ha - {rec['current_crop']}\n"
            f"{layer_label}: {shown}"
        )
        for rings in _parts(rec["id"]):
            row = {"id": rec["id"], "polygon_geo": rings, "rgb": [*rec["rgb"], fill_alpha],
                   "line_rgb": rec["rgb"], "tooltip_text": tooltip}
            rows.append(row)
            if rec["id"] == plot_id:
                selected_rows.append(row)

    layers = []
    if soil_png:
        layers.append(pdk.Layer("BitmapLayer", id="soil", image=pdk.types.String(_soil_png(soil_png)),
                                bounds=_soil_bounds(), opacity=0.75))
    layers.append(pdk.Layer(
        "PolygonLayer", id="plots", data=rows, get_polygon="polygon_geo",
        get_fill_color="rgb", get_line_color="line_rgb", get_line_width=2 if soil_png else 1,
        line_width_units="pixels", stroked=True, filled=True, pickable=True, auto_highlight=True,
    ))
    # Selected plot: white ring underneath, thick line on top.
    layers.append(pdk.Layer(
        "PolygonLayer", id="selected-ring", data=selected_rows, get_polygon="polygon_geo",
        filled=False, stroked=True, get_line_color=[255, 255, 255], get_line_width=8, line_width_units="pixels",
    ))
    layers.append(pdk.Layer(
        "PolygonLayer", id="selected-line", data=selected_rows, get_polygon="polygon_geo",
        filled=False, stroked=True, get_line_color=list(_MAP_COLOR_STOPS[2]), get_line_width=4,
        line_width_units="pixels",
    ))

    deck = pdk.Deck(
        map_style=_basemap_style(basemap),
        initial_view_state=pdk.ViewState(latitude=42.73, longitude=-92.79, zoom=10),
        layers=layers,
        tooltip={"text": "{tooltip_text}"},
    )

    try:
        selected_name = df.loc[df["id"] == plot_id, "name"].iloc[0]
    except IndexError:
        selected_name = "Unknown Plot"

    st.pydeck_chart(deck, height=520)
    if mode == "polygon":
        scale = f"Relative indicator scale: Green (lowest) through Soil colors (highest) for {layer_label.lower()}."
    elif mode == "pattern":
        scale = "Green: corn–soybean rotation · Peach: rotation with breaks · Soil: mostly corn · Grey: irregular."
    else:
        scale = "The soil map is drawn under white field outlines."
    st.caption(
        f"{scale} {LAYER_NOTES[layer_label]} Selected plot (white ring, thick border): {selected_name}. "
        f"These records do not change from year to year: {YEAR_OPTIONS[0]}–{YEAR_OPTIONS[-1]} share the same "
        f"values. Background: Esri {basemap.lower()} imagery."
    )

    # --- Multi-plot comparison table for the selected year ----------------------
    st.subheader(f"Plot Comparison ({year})")

    display_columns = {
        "id": "Plot ID",
        "name": "Field Name",
        "area_hectares": "Area (ha)",
        "current_crop": "Current Crop",
    }
    indicator_names = {col: label for label, (col, mode_) in LAYER_LABELS.items() if mode_ != "pattern"}
    display_columns.update(indicator_names)

    table = df[list(display_columns)].rename(columns=display_columns).set_index("Plot ID")

    format_dict = {
        "Area (ha)": "{:.1f}",
        "Overall Risk": "{:.2f}",
        "Drought Risk": "{:.2f}",
        "Erosion Risk (RUSLE)": "{:.1f} t/ha",
        "Unplanted in 2019": "{:.1f}%",
        "Productivity (CSR2)": "{:.0f}",
        "Soil Yield Adjustment": "{:+.1f}%",
        "Sand Content": "{:.0f}%",
        "Flood-Prone Soils (SSURGO)": "{:.0f}%",
    }

    st.dataframe(table.style.format(format_dict, na_rep="-"), width="stretch")
