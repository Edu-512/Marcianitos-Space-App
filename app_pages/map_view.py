"""Explore existing demo parcels with accessible, synchronized selection."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.parcel_map import (
    INDICATORS, NO_DATA_COLOR, build_rows, color_rows, crop_categories,
)
from components.geographic_map import load_geography, map_features, render_map, selection_id, valid_camera
from components.palette import PALETTE
from utils.data_sources import load_historical_map_snapshot, load_plots
from utils.types import Plot

MAP_KEY = "explore_parcel_map"
PICKER_KEY = "explore_plot_select"
YEAR_OPTIONS = [2021, 2022, 2023, 2024, 2025, 2026]

# Local layout only; navigation and Don Surco are not modified. Reserve their
# floating corner beside controls and the existing continuation button.
_LOCAL_CSS = """
.st-key-explore_mobile_selector { display: none; }
.explore-legend { display:flex; flex-wrap:wrap; gap:.6rem 1.2rem; padding:0; margin:.5rem 0 1rem; list-style:none; }
.explore-legend li { display:flex; align-items:center; gap:.45rem; font-size:.9rem; }
.explore-legend .swatch { width:1rem; height:1rem; flex:none; border:1px solid #7a6b60; border-radius:.25rem; }
@media (max-width:767px) {
  .st-key-explore_mobile_selector { display:block; }
  .st-key-explore_mobile_selector, .st-key-explore_controls,
  .st-key-continue_map_view { max-width:calc(100% - 5.25rem); }
}
"""


def _on_picker(valid_ids: tuple[str, ...]) -> None:
    selected = st.session_state.get(PICKER_KEY)
    if selected in valid_ids:
        st.session_state.selected_plot_id = selected


def _on_map_select(valid_ids: tuple[str, ...]) -> None:
    state = st.session_state.get(MAP_KEY, {})
    selected = selection_id(state.get("selected"), valid_ids)
    if selected is not None:
        st.session_state.selected_plot_id = selected


def _on_camera() -> None:
    camera = valid_camera(st.session_state.get(MAP_KEY, {}).get("camera"))
    if camera is not None:
        st.session_state.explore_camera = camera


def _legend(items: list[tuple[str, str]]) -> None:
    markup = ''.join(f'<li><span class="swatch" style="background:{color}" aria-hidden="true"></span><span>{escape(label)}</span></li>' for label, color in items)
    st.html(f'<ul class="explore-legend" aria-label="Leyenda del mapa">{markup}</ul>')


def _selected_panel(plot: Plot) -> None:
    with st.container(border=True):
        st.subheader("Parcela seleccionada", icon=":material/check_circle:")
        st.markdown("**Nombre de la parcela**")
        st.write(plot.name)
        area, crop = st.columns(2)
        area.metric("Superficie simulada", f"{plot.area_hectares:g} ha")
        with crop:
            st.markdown("**Cultivo simulado**")
            st.write(plot.current_crop or "Información no disponible")
        st.caption(f"Identificador: {plot.id}")
        st.caption("Historial de rotación: información no disponible. El cultivo registrado no permite inferir una rotación.")
        st.caption("Geometría e indicadores de demostración: no representan un campo verificado ni límites legales.")
        with st.expander("Ubicación y detalles del mapa"):
            feature = next((f for f in load_geography()["features"] if f["properties"]["demo_plot_id"] == plot.id), None)
            if feature:
                st.write(f"Referencia visual simulada: {feature['properties']['reference_id']}.")
                st.write("Butler County, Iowa · WGS84 (EPSG:4326). Coordenadas GeoJSON: longitud, latitud.")
                st.write("La forma local es esquemática, a escala de la superficie de demostración; no procede de USDA CSB.")
            else:
                st.write("Sin geometría de referencia local para esta parcela. Sigue disponible en la lista.")
            st.write("Las coordenadas originales del escenario del modelo no se modificaron ni se utilizan en este mapa.")


def _comparison(frame: pd.DataFrame, year: int) -> None:
    with st.expander(f"Comparar indicadores simulados · {year}"):
        st.caption("Se conservan las seis variables de la vista anterior. Son valores de demostración por parcela, no imágenes satelitales.")
        columns = {"name":"Parcela", "area_hectares":"Superficie (ha)", "crop":"Cultivo registrado"}
        columns.update({column:f"{label} ({unit})" for label, (column, unit) in INDICATORS.items()})
        table = frame[["id", *columns]].rename(columns=columns).set_index("id")
        st.dataframe(table, width="stretch", alt=f"Comparación de las seis variables simuladas por parcela en {year}")


def run() -> None:
    """Keep the global heading, notices, CTA and navigation from Feature 01."""
    plots = load_plots()
    if not plots:
        st.info("No hay parcelas disponibles. Vuelve cuando se hayan agregado terrenos.")
        return
    valid_ids = tuple(p.id for p in plots)
    if st.session_state.get("selected_plot_id") not in valid_ids:
        st.session_state.selected_plot_id = valid_ids[0]
        st.rerun()  # Reconcile the sidebar before its selector is mounted again.
    plot_id = st.session_state.selected_plot_id
    names = {p.id:p.name for p in plots}
    st.html(f"<style>{_LOCAL_CSS}</style>")
    if st.session_state.get(PICKER_KEY) != plot_id:
        st.session_state[PICKER_KEY] = plot_id
    with st.container(key="explore_mobile_selector"):
        st.selectbox("Elegir parcela", list(names), format_func=lambda pid:names[pid],
                     key=PICKER_KEY, on_change=_on_picker, args=(valid_ids,))
    st.caption("Selecciona un terreno en el mapa o usa la lista de parcelas. La marca ✓ y el borde grueso indican tu selección.")
    with st.container(key="explore_controls"):
        basemap = st.segmented_control("Mapa base", ["Mapa normal", "Satelital", "Sin fondo"],
                                       default="Mapa normal", selection_mode="single", required=True, key="explore_basemap")
        mode = st.selectbox("Mostrar en el mapa", ["Cultivos", "Parcelas", *INDICATORS], key="explore_layer")
        interactive = st.toggle("Mover y acercar el mapa", value=False, key="explore_interact",
                                help="Actívalo para arrastrar o acercar el mapa. Desactívalo para desplazar la página cómodamente.")
        with st.expander("Año de los indicadores y detalles de las capas"):
            year = int(st.select_slider("Año de los indicadores simulados", options=YEAR_OPTIONS, value=2026, key="map_year"))
            st.caption("El año cambia los indicadores simulados. El cultivo registrado es el actual; no hay historial de cultivos por año.")
            st.caption("Vegetación corresponde al indicador NDVI; humedad a SMAP; temperatura a ECOSTRESS; agua a GRACE-FO y erosión a SRTM. Las fuentes reales aún no están integradas.")
    st.caption("Toca una parcela para seleccionarla. Para mover la vista, activa el control; acerca con doble clic o con dos dedos.")
    frame = build_rows(plots, year, load_historical_map_snapshot)
    categories = crop_categories(plots)
    colored = color_rows(frame, mode, categories)
    st.warning("Límites simulados en Butler County: aún no hay campos oficiales de Iowa integrados. Cultivos e indicadores también son simulados; no describen el terreno de la fotografía.")
    collection = map_features(colored, plot_id)
    if collection["features"]:
        render_map(collection, str(basemap), interactive, st.session_state.get("explore_camera"),
                   key=MAP_KEY, on_select=lambda: _on_map_select(valid_ids), on_camera=_on_camera)
        st.caption("Fondo: USGS The National Map / USDA. La imagen aérea es una referencia externa, no una capa NDVI ni una observación del año elegido. Requiere Internet; «Sin fondo» conserva las geometrías locales.")
    else:
        st.warning("No hay geometrías locales disponibles. Puedes elegir una parcela desde la lista.")
    st.markdown("**Leyenda del mapa**")
    if mode == "Cultivos":
        _legend([(f"{crop} · {sum((p.current_crop or 'Sin cultivo registrado') == crop for p in plots)} parcela(s)", color) for crop, color in categories.items()])
    elif mode == "Parcelas":
        _legend([("Parcelas disponibles", PALETTE["soil"])])
    else:
        column, unit = INDICATORS[mode]
        values = pd.to_numeric(frame[column], errors="coerce").replace([float("inf"), float("-inf")], float("nan"))
        finite = values.dropna()
        if finite.nunique() == 1:
            _legend([(f"Valor disponible · {finite.iloc[0]:g} {unit}", PALETTE["peach"])])
        elif not finite.empty:
            _legend([(f"Menor valor · {finite.min():g} {unit}", PALETTE["vegetation"]),
                     ("Valor intermedio", PALETTE["peach"]),
                     (f"Mayor valor · {finite.max():g} {unit}", PALETTE["soil_dark"])])
        if values.isna().any():
            _legend([("Sin indicador disponible", NO_DATA_COLOR)])
        st.caption(f"Representación simulada de {mode.lower()} por parcela en {year}. La escala es relativa a las parcelas disponibles; un valor mayor no siempre significa una condición mejor.")
    st.caption("✓ Nombre con marca y contorno dorado grueso: parcela seleccionada. Los rellenos representan escenarios simulados, no cultivos verificados.")
    if len(collection["features"]) < len(plots):
        st.info("Algunas parcelas no tienen geometría local disponible. Siguen disponibles en los selectores y en el panel.")
    selected = next(p for p in plots if p.id == plot_id)
    _selected_panel(selected)
    _comparison(frame, year)
