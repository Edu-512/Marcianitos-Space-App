"""Read-only integration of the team's exported model; no scientific calculations."""
from __future__ import annotations
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
MODEL_FILE=ROOT/'model/datos_ui/resultado_todas.json'
PARCELS_FILE=ROOT/'model/datos_ui/parcelas_todas.geojson'
DELIVERY_REVISION='9c2fa4e58ee448e02cd78c8008e24cca6da82cbd'
CLIMATES={'normal':'Normal year','seco_caluroso':'Dry & hot year','humedo_primavera':'Wet spring'}
PLANS={'maiz_continuo':'Continuous maize','maiz_soya':'Maize & soybean','maiz_soya_cobertura':'Rotation with cover'}
PROFILE_NAMES={806:'Good soil · classic rotation',467:'Sandy soil · less stored water',1452:'Maize-dominant profile',1737:'Planting-access profile',1413:'Sloping soil · erosion profile'}
PATTERNS={'rotacion estricta':'Strict rotation','rotacion con quiebre':'Rotation with breaks','maiz dominante':'Maize dominant','irregular':'Irregular pattern','soya dominante':'Soybean dominant'}


def enabled() -> bool:
    return st.session_state.get('data_mode','model')=='model'


def catalog() -> dict[str,Any]:
    return _read_catalog(str(MODEL_FILE),MODEL_FILE.stat().st_mtime_ns)


@st.cache_resource(max_entries=2, show_spinner=False)
def _read_catalog(filename: str, revision: int) -> dict[str,Any]:
    # Shared source objects are read-only by convention; never mutate them.
    data=json.loads(Path(filename).read_text(encoding='utf-8'))
    ids=set()
    for item in data['parcelas']:
        pid=str(item['parcela']['id'])
        if pid in ids:raise ValueError('Duplicate model profile ID')
        ids.add(pid)
        if set(item['escenarios'])!=set(CLIMATES):raise ValueError('Incomplete climate catalog')
        for climate in item['escenarios'].values():
            if {p['id'] for p in climate['planes']}!=set(PLANS):raise ValueError('Incomplete plan catalog')
    return data


def records() -> dict[str,dict[str,Any]]:
    return _index_catalog(str(MODEL_FILE),MODEL_FILE.stat().st_mtime_ns)


@st.cache_resource(max_entries=2, show_spinner=False)
def _index_catalog(filename: str, revision: int) -> dict[str,dict[str,Any]]:
    return {str(row['parcela']['id']):row for row in _read_catalog(filename,revision)['parcelas']}


def profile(pid: str) -> dict[str,Any]:
    try:return records()[str(pid)]
    except KeyError:raise ValueError('Unknown model profile') from None


def label(pid: str) -> str:
    raw=profile(pid)['parcela']
    return PROFILE_NAMES.get(int(raw['id']),f"Field {raw['id']}")


def result(pid: str, climate_id: str, plan_id: str) -> dict[str,Any]:
    if climate_id not in CLIMATES or plan_id not in PLANS:raise ValueError('Unknown model scenario or plan')
    return deepcopy(next(p for p in profile(pid)['escenarios'][climate_id]['planes'] if p['id']==plan_id))


def parcels() -> dict[str,dict[str,Any]]:
    data=_read_parcels(str(PARCELS_FILE),PARCELS_FILE.stat().st_mtime_ns)
    if set(data)!=set(records()):raise ValueError('Parcel geometry and model IDs do not match')
    return data


@st.cache_resource(max_entries=2, show_spinner=False)
def _read_parcels(filename: str, revision: int) -> dict[str,dict[str,Any]]:
    doc=json.loads(Path(filename).read_text(encoding='utf-8'))
    found={}
    for feature in doc['features']:
        pid=str(feature['properties']['id'])
        if pid in found:raise ValueError('Duplicate parcel geometry ID')
        geom=feature['geometry']
        if geom['type'] not in ('Polygon','MultiPolygon'):raise ValueError('Unsupported parcel geometry')
        polygons=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
        if not polygons:raise ValueError('Empty parcel geometry')
        for polygon in polygons:
            if not polygon:raise ValueError('Empty parcel polygon')
            for ring in polygon:
                if len(ring)<4 or ring[0]!=ring[-1]:raise ValueError('Parcel ring is not closed')
                for lon,lat in ring:
                    if not (math.isfinite(lon) and math.isfinite(lat) and -180<=lon<=180 and -90<=lat<=90):
                        raise ValueError('Invalid geographic parcel coordinate')
        found[pid]=feature
    return found


def plot_position(pid: str) -> tuple[float,float]:
    """Bounds center for the legacy Plot contract only; map draws full geometry."""
    geom=parcels()[pid]['geometry']
    polygons=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
    points=[p for polygon in polygons for p in polygon[0]]
    return ((min(p[1] for p in points)+max(p[1] for p in points))/2,
            (min(p[0] for p in points)+max(p[0] for p in points))/2)


def map_features() -> dict[str,Any]:
    features=[]
    for pid,source in parcels().items():
        features.append({'type':'Feature','id':pid,'properties':{'plot_id':pid,'name':label(pid),'geometry_nature':'cdl_derived'},
                         'geometry':deepcopy(source['geometry'])})
    return {'type':'FeatureCollection','features':features}


def reconcile() -> None:
    if st.session_state.get('selected_climate_id') not in CLIMATES:st.session_state.selected_climate_id='normal'
    ctx=st.session_state.get('comparison_context',{})
    if ctx and ctx.get('model_revision')!=DELIVERY_REVISION:
        st.session_state.selected_plan_id=None
        st.session_state.comparison_context={}
        ctx={}
    if ctx.get('plot_id')!=st.session_state.get('selected_plot_id') or st.session_state.get('selected_plan_id') not in PLANS:
        st.session_state.selected_plan_id=None
    if ctx.get('plot_id')!=st.session_state.get('selected_plot_id'):st.session_state.comparison_context={}


def select_plan(plan_id: str) -> None:
    if plan_id not in PLANS:return
    pid=st.session_state.selected_plot_id;climate=st.session_state.selected_climate_id
    out=result(pid,climate,plan_id)
    st.session_state.selected_plan_id=plan_id
    st.session_state.comparison_context={'plot_id':pid,'climate_id':climate,'plan_id':plan_id,'outcome':out,'data_nature':'research_model','model_version':catalog()['version'],'model_revision':DELIVERY_REVISION}


def select_climate(climate_id: str) -> None:
    if climate_id not in CLIMATES:return
    st.session_state.selected_climate_id=climate_id
    chosen=st.session_state.get('selected_plan_id')
    if chosen in PLANS:select_plan(chosen)


def n(value: Any, decimals: int=1) -> str:
    try:
        num=float(value)
        return f'{num:,.{decimals}f}' if math.isfinite(num) else 'Not available'
    except (ValueError,TypeError):return 'Not available'


def context_result() -> dict[str,Any] | None:
    ctx=st.session_state.get('comparison_context',{})
    if (ctx.get('data_nature')=='research_model' and ctx.get('model_revision')==DELIVERY_REVISION and ctx.get('plot_id')==st.session_state.get('selected_plot_id')
        and ctx.get('climate_id')==st.session_state.get('selected_climate_id') and ctx.get('plan_id')==st.session_state.get('selected_plan_id')):
        try:
            expected=result(ctx['plot_id'],ctx['climate_id'],ctx['plan_id'])
            return expected if ctx.get('outcome')==expected else None
        except (ValueError,KeyError):pass
    return None
