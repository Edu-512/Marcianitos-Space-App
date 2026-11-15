"""Research model screens: display exported results without recomputing them."""
from functools import partial
from html import escape as e
import hashlib
from typing import Any
import pandas as pd
import streamlit as st
from utils import field_model as fm
from components.design_system import section


def navigate(key: str) -> None:
    from components.navigation import PAGES,run_page
    spec=PAGES[key]
    st.switch_page(st.Page(partial(run_page,key),title=spec.title,icon=spec.icon,url_path=spec.url_path,default=key=='map_view'))


def climate_changed() -> None:
    fm.select_climate(st.session_state.research_climate)


def climate_control() -> str:
    st.session_state.research_climate=st.session_state.selected_climate_id
    st.segmented_control('Type of year',list(fm.CLIMATES),format_func=lambda key:fm.CLIMATES[key],key='research_climate',
                         required=True,on_change=climate_changed,width='stretch',wrap=True)
    st.caption('Historical climate groups, not a weather forecast. All three cards use the same selected group.')
    return st.session_state.selected_climate_id


def card(out: dict[str,Any]) -> str:
    margin=out['economia']['margen_usd_acre'];crop=out['rendimiento_maiz_bu_acre'];soil=out['suelo']
    return f'''<article class="fs-card"><h3>{e(fm.PLANS[out['id']])}</h3><span class="fs-label">Estimated margin · USD/acre</span><strong class="fs-value">{fm.n(margin['p50'],0)}</strong><small>p10–p90: {fm.n(margin['p10'],0)} to {fm.n(margin['p90'],0)} USD/acre</small><span class="fs-label">Maize yield · bu/acre</span><strong class="fs-value">{fm.n(crop['p50'])}</strong><small>p10–p90: {fm.n(crop['p10'])} to {fm.n(crop['p90'])} bu/acre</small><div class="fs-soil"><p>Soil loss: <b>{fm.n(soil['erosion_ton_acre_anio'])} ton/acre/year</b></p><small>{'Above the model tolerance' if soil['arriba_del_limite'] else 'Not above the model tolerance'} · numeric tolerance not supplied in the export.</small><small>Costs include land rent. Rotation economics average the maize and soybean phases; the yield above is maize only.</small></div></article>'''


def sources() -> None:
    with st.expander('Model sources, uncertainty & limitations'):
        st.write('Source: the model team’s version '+fm.catalog()['version']+' export. This interface reads the supplied JSON without changing estimates.')
        st.write('p10, p50 and p90 are the supplied historical/model quantiles. Historical calibration does not guarantee a field-level outcome or future coverage.')
        st.write('Historical period: 2000–2025. Budget assumptions: Iowa 2026, including land rent. Soil/rotation effects combine source data and literature assumptions.')
        st.write('Nitrogen values apply to the maize phase in the model, not to soybean or an entire rotation as a universal dose. Confirm agronomic applicability.')
        st.write('The planting-risk probabilities are model estimates. They are not measured probabilities for a verified property boundary.')
        st.write('The cover plan includes the source assumption of 37 USD/acre for establishment. Planting risk is scaled from the field fraction observed unplanted in 2019; one observed year does not establish a future probability.')
        for key,value in fm.catalog()['fuentes'].items():st.text(f'{key}: {value}')
        st.caption('Continuous-maize penalties are literature assumptions; soil adjustment was calibrated in one county. Cover-crop timing, current crop, field-level annual history and verified ownership boundaries are not supplied.')


def compare() -> None:
    pid=st.session_state.selected_plot_id;raw=fm.profile(pid)['parcela']
    with st.container(key='model_content'):
        st.html(f'<div class="fs-context"><span class="fs-pill">{e(fm.label(pid))}</span><span class="fs-pill">{fm.n(raw["acres"],0)} acres</span><span class="fs-pill">Research model · 9 outcomes per profile</span></div>')
        climate=climate_control()
        section('Three planting plans','↻')
        grid=st.grid(3,min_column_width=285,gap='medium')
        for plan in fm.PLANS:
            out=fm.result(pid,climate,plan)
            with grid.cell():
                st.html(card(out))
                chosen=st.session_state.get('selected_plan_id')==plan
                st.button('Selected for exploration' if chosen else 'Explore this plan',key='model_select_'+plan,
                          icon=':material/check_circle:' if chosen else ':material/arrow_forward:',type='primary' if chosen else 'secondary',
                          width='stretch',on_click=fm.select_plan,args=(plan,))
                with st.expander('Plan inputs & complete output'):
                    st.write(f"Gross income (p50): {fm.n(out['economia']['ingreso_usd_acre']['p50'],0)} USD/acre")
                    st.write(f"Cost: {fm.n(out['economia']['costo_usd_acre'],0)} USD/acre")
                    st.write(f"Nitrogen input for maize: {fm.n(out['fertilizante']['nitrogeno_lb_acre'],0)} lb/acre")
                    income=out['economia']['ingreso_usd_acre']
                    st.write(f"Gross income range (p10 to p90): {fm.n(income['p10'],0)} to {fm.n(income['p90'],0)} USD/acre")
                    st.write(f"Historical/model frequency of a yield drop greater than 20%: {fm.n(out['riesgo']['prob_caida_mayor_20_pct'])}%")
                    st.write(f"Estimated share unable to be planted: {fm.n(out['riesgo']['prob_no_poder_sembrar_pct'],2)}%")
                    confidence={'alta':'High','media':'Medium','baja':'Low'}.get(str(out.get('confianza')),'Not supplied')
                    st.write(f"Source confidence label: {confidence}. This is not a probability or guarantee.")
        section('Read the tradeoffs','◈')
        st.write(f'You are exploring {fm.CLIMATES[climate].lower()}. Compare the lower margin bound alongside soil loss before choosing; neither a higher median nor a confidence label guarantees the result.')
        scenario=fm.profile(pid)['escenarios'][climate]
        st.caption(f"Historical years in this group: {scenario['n_anios']} · "+', '.join(map(str,scenario['anios_historicos'])))
        sources()


def continue_to_recommendations(pages: dict[str,Any]) -> None:
    ready=fm.context_result() is not None
    st.caption('Choose a plan to carry its exported results into your action review.')
    if st.button('View recommendations for this plan',key='continue_rotations',type='primary',width='stretch',disabled=not ready):
        st.switch_page(pages['recommendations'])


def home() -> None:
    pid=st.session_state.selected_plot_id;raw=fm.profile(pid)['parcela'];soil=raw['suelo']
    with st.container(key='model_content'):
        st.subheader(fm.label(pid))
        st.write(f"Model profile {pid} · {fm.n(raw['acres'],0)} acres · historical pattern: {fm.PATTERNS.get(raw['rotacion_actual'],'Source pattern available in details')}")
        st.caption('Field position and outline are derived from USDA CDL crop patterns. They are not verified ownership or cadastral boundaries.')
        section('What is your soil like?','◈')
        grid=st.grid(2,min_column_width=230)
        for label,key,unit,explanation in [
            ('Stored water','agua_disponible_cm','cm','Available-water input across the source soil profile; not today’s measured moisture.'),
            ('Sand content','arena_pct','%','Soil texture input used by the existing model.'),
            ('Slope','pendiente_pct','%','Slope input used for the exported soil adjustment and erosion estimate.'),
            ('Organic matter','materia_organica_pct','%','Source soil input; no field-specific sampling date is supplied.')]:
            with grid.cell():
                st.html(f'<article class="fs-card"><span class="fs-label">{label}</span><strong class="fs-value">{fm.n(soil[key])} {unit}</strong><p>{explanation}</p></article>')
        section('Crop history','↻')
        st.write('Historical pattern: '+fm.PATTERNS.get(raw['rotacion_actual'],raw['rotacion_actual']))
        st.caption('CDL pattern period: 2018–2025. The export does not include yearly crops or a verified current crop; no annual timeline is inferred.')
        section('Conditions to review','◉')
        st.write(f"Source soil adjustment: {fm.n(raw['ajuste_por_suelo_pct'])}%. This is the model team’s supplied adjustment, not a new frontend calculation.")
        st.write(f"Soil inundation input during planting: {fm.n(soil['riesgo_inundacion_siembra_pct'])}%. This source variable is not a future planting-failure forecast.")
        sources()
        section('Your field notes','✎')
        from app_pages.home import _ground_log
        _ground_log(pid)


def recommendations() -> None:
    pid=st.session_state.selected_plot_id;out=fm.context_result()
    with st.container(key='model_content'):
        st.write(f'Active profile: {fm.label(pid)}')
        if out is None:
            st.info('Choose a planting plan for this profile to review its model results. No plan is selected automatically.')
            st.button('Compare my planting options',key='change_action_plan',on_click=navigate,args=('rotations',))
            sources();return
        climate=st.session_state.selected_climate_id;plan=out['id']
        st.html(f'<div class="fs-context"><span class="fs-pill">{e(fm.PLANS[plan])}</span><span class="fs-pill">{e(fm.CLIMATES[climate])}</span></div>')
        st.button('Change my planting plan',key='change_action_plan',on_click=navigate,args=('rotations',))
        st.html(card(out))
        section('Your action review','✓')
        st.caption('Review prompts assembled from supplied model fields. They are not additional agronomic predictions or an optimized recommendation algorithm.')
        actions=[('budget','Review the scenario budget',f"Median margin: {fm.n(out['economia']['margen_usd_acre']['p50'],0)} USD/acre. Costs include land rent; review the p10 bound before using this budget."),
                 ('soil','Review soil protection',f"Estimated loss: {fm.n(out['suelo']['erosion_ton_acre_anio'])} ton/acre/year. "+('The export flags it above tolerance.' if out['suelo']['arriba_del_limite'] else 'The export does not flag it above tolerance; this is not a guarantee.')),
                 ('nitrogen','Check the maize nitrogen assumption',f"Model input: {fm.n(out['fertilizante']['nitrogeno_lb_acre'],0)} lb/acre, for maize in this plan. Application stage, timing and field testing remain to be confirmed."),
                 ('risk','Review the risk assumptions',f"Historical/model frequency of a yield drop greater than 20%: {fm.n(out['riesgo']['prob_caida_mayor_20_pct'])}%. Model planting-failure estimate: {fm.n(out['riesgo']['prob_no_poder_sembrar_pct'],2)}%. These do not guarantee a future field outcome.")]
        for _,title,text in actions:
            st.markdown('**'+title+'**');st.write(text)
        section('Prepare for next season','✓')
        context=hashlib.sha256(f'{fm.DELIVERY_REVISION}:{pid}:{climate}:{plan}'.encode()).hexdigest()[:20]
        stored=st.session_state.setdefault('model_reviews',{}).setdefault(context,[])
        def reviewed(action_id: str, widget_key: str) -> None:
            values=set(st.session_state.model_reviews[context])
            if st.session_state[widget_key]:values.add(action_id)
            else:values.discard(action_id)
            st.session_state.model_reviews[context]=sorted(values)
        st.progress(len(set(stored)&{x[0] for x in actions})/len(actions),text=f'{len(set(stored)&{x[0] for x in actions})} of {len(actions)} reviewed')
        st.caption('Reviewed means read and checked, not agricultural work completed. Progress stays in this session and context.')
        for aid,title,_ in actions:
            key=f'model_review_{context}_{aid}'
            st.checkbox('Reviewed: '+title,value=aid in stored,key=key,on_change=reviewed,args=(aid,key))
        sources()
        from app_pages.recommendations import _help
        _help()
        st.button('Explore another plot',key='action_explore_plot',on_click=navigate,args=('map_view',))


def map_view() -> None:
    from components.field_map import render
    render()
    with st.expander('View model comparison table',on_change='rerun',key='model_map_table') as details:
        if details.open:
            rows=[];climate=st.session_state.selected_climate_id
            for pid in fm.records():
                for plan in fm.PLANS:
                    out=fm.result(pid,climate,plan)
                    rows.append({'Profile':fm.label(pid),'ID':pid,'Area (acres)':fm.profile(pid)['parcela']['acres'],'Plan':fm.PLANS[plan],
                                 'Margin p50 (USD/acre)':out['economia']['margen_usd_acre']['p50'],'Margin p10':out['economia']['margen_usd_acre']['p10'],
                                 'Margin p90':out['economia']['margen_usd_acre']['p90'],'Maize p50 (bu/acre)':out['rendimiento_maiz_bu_acre']['p50'],
                                 'Soil loss (ton/acre/year)':out['suelo']['erosion_ton_acre_anio']})
            st.dataframe(pd.DataFrame(rows),width='stretch',hide_index=True,alt='Exported model comparison for all satellite-derived fields under the selected climate')
    with st.expander('Legacy satellite-indicator demo table'):
        st.caption('These indicators are simulated and separate from the research model. They are not observations of the model profiles.')
        from utils.data_sources import _load_legacy_plots,load_historical_map_snapshot
        rows=[{'Demo plot':p.name,**load_historical_map_snapshot(p.id,2026)} for p in _load_legacy_plots()]
        st.dataframe(pd.DataFrame(rows),width='stretch',hide_index=True,alt='Separate legacy simulated satellite indicators')
