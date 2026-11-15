"""Local CCv2 Leaflet viewer with in-map model cards and canonical state callbacks."""
from pathlib import Path
import math
import streamlit as st
from utils import field_model as fm

FRONT=Path(__file__).with_name('field_map_frontend')
KEY='research_field_map'
_COMPONENT=st.components.v2.component('research_field_map',html=(FRONT/'map.html').read_text(encoding='utf-8-sig'),
    css=(FRONT/'vendor/leaflet.css').read_text()+'\n'+(FRONT/'map.css').read_text(encoding='utf-8-sig'),
    js=(FRONT/'vendor/leaflet.js').read_text(encoding='utf-8')+'\n'+(FRONT/'map.js').read_text(encoding='utf-8-sig'))


def _action() -> None:
    event=st.session_state.get(KEY,{}).get('action')
    if not isinstance(event,dict):return
    if not isinstance(event.get('plot_id'),str) or not isinstance(event.get('climate_id'),str):return
    if event['plot_id'] not in fm.records() or event['climate_id'] not in fm.CLIMATES:return
    changed=st.session_state.get('selected_plot_id')!=event['plot_id']
    st.session_state.selected_plot_id=event['plot_id']
    if changed:st.session_state.selected_plan_id=None;st.session_state.comparison_context={}
    fm.select_climate(event['climate_id'])
    if isinstance(event.get('plan_id'),str) and event['plan_id'] in fm.PLANS:fm.select_plan(event['plan_id'])
    if event.get('action') in ['compare','home']:
        from components.model_views import navigate
        navigate('rotations' if event['action']=='compare' else 'home')


def _camera() -> None:
    value=st.session_state.get(KEY,{}).get('camera')
    try:
        lat,lon=value['center'];zoom=value['zoom']
        if all(math.isfinite(float(x)) for x in [lat,lon,zoom]) and -85<lat<85 and -180<=lon<=180 and 0<=zoom<=22:
            st.session_state.research_map_camera={'center':[lat,lon],'zoom':zoom}
    except (TypeError,ValueError,KeyError):pass


def render() -> None:
    _COMPONENT(key=KEY,data={'geometry':fm.map_features(),'profiles':fm.records(),'names':{pid:fm.label(pid) for pid in fm.records()},
                           'selected':st.session_state.selected_plot_id,'climate':st.session_state.selected_climate_id,
                           'plan':st.session_state.get('selected_plan_id'),'plans':fm.PLANS,'climates':fm.CLIMATES,
                           'camera':st.session_state.get('research_map_camera')},height='content',width='stretch',on_action_change=_action,on_camera_change=_camera)
