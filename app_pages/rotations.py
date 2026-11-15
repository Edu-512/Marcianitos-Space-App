"""Compare Crops: visual plan exploration using existing model outputs only."""
from __future__ import annotations

from typing import Any
import pandas as pd
import streamlit as st

from components.crop_comparison import (
    CLIMATES, PLANS, choose_climate, choose_plan, finite, formatted, outcome_for,
    reconcile_selection, resolve_plans, selected_outcomes, yield_interval,
)
from components.compare_markup import CSS, art, e, hero, plan_markup
from components.uncertainty_chart import yield_uncertainty_bands
from utils.data_sources import load_plots, load_rotation_scenarios
from utils.model_interface import predict_yield_trajectory, score_scenario_priority_fit
from utils.types import RotationScenario, ScenarioOutcome


_EXTRA_CSS = """
.st-key-weather_mobile { display:none; }
@media(max-width:767px) {
 .st-key-weather_cards { display:none; }
 .st-key-weather_mobile { display:block;max-width:calc(100% - 4.75rem); }
}
"""


def _mobile_climate() -> None:
    choose_climate(st.session_state.get("compare_weather_mobile", "normal"))


def _weather() -> None:
    climate=st.session_state.selected_climate_id
    st.subheader("What might next season look like?")
    st.caption("Explore possible conditions. This is not a weather forecast.")
    with st.container(key="weather_cards"):
        grid=st.grid(3,min_column_width=220)
        for key,weather in CLIMATES.items():
            with grid.cell():
                with st.container(key=f"climate_{key}"):
                    st.html(f'<div class="rc-weather">{art(key,"Illustrative weather condition")}<h3>{e(weather["title"])}</h3><p>{e(weather["description"])}</p></div>')
                    active=climate==key
                    st.button("Selected" if active else "Explore this weather",icon=":material/check_circle:" if active else f':material/{weather["icon"]}:',
                              key=f"weather_{key}",width="stretch",type="primary" if active else "secondary",on_click=choose_climate,args=(key,))
    st.session_state.compare_weather_mobile=climate
    with st.container(key="weather_mobile"):
        st.segmented_control("Weather scenario",list(CLIMATES),format_func=lambda k:{"normal":"Normal","dry":"Dry & hot","wet":"Wet spring"}[k],
                             key="compare_weather_mobile",selection_mode="single",required=True,on_change=_mobile_climate,width="stretch",wrap=True)
    st.caption(f'Active: {CLIMATES[climate]["title"]} · {CLIMATES[climate]["description"]}')
    if climate=="wet":
        st.info("Wet-spring outcomes are not available. The existing model does not describe planting-season rainfall, drainage or unplanted area. No results are inferred from a seasonal rainfall slider.")
    elif climate=="dry":
        st.caption("Illustrative stress test: −30% seasonal rainfall, +3.5°C. These are the existing simulator's endpoints, not a locally validated scenario.")


def _plan_details(scenario: RotationScenario | None, outcome: ScenarioOutcome | None) -> None:
    with st.expander("Plan details and sources"):
        st.write(f"Model plan ID: {scenario.id if scenario else 'Not supplied'}")
        if scenario:
            st.write(f"Model name: {scenario.name}")
        st.caption("Source: existing deterministic demo model. No observed NASA values or confirmed field outcomes are shown. Prices, income, net return, cost intervals, nitrogen dose and calendar horizon are not supplied.")
        if outcome:
            values={
                "Estimated cost (USD/ha)":outcome.cost_usd_per_ha,
                "Scenario yield (t/ha)":outcome.expected_yield_t_per_ha,
                "Yield lower bound (t/ha)":outcome.yield_ci_low,
                "Yield upper bound (t/ha)":outcome.yield_ci_high,
                "Irrigation demand (mm)":outcome.water_use_mm,
                "Nutrient loss (%)":outcome.nutrient_loss_pct,
                "Organic matter change (%)":outcome.organic_matter_delta_pct,
                "Erosion risk index (0–1)":outcome.erosion_risk_score,
                "Pest disruption index (0–1)":outcome.pest_disruption_score,
                "Forage value index (0–1)":outcome.forage_value_score,
            }
            for label,value in values.items():
                st.write(f"{label}: {formatted(value)}")
            for title,field in [("Model explanation (simulated)","agronomic_mechanism"),("Provider evidence narrative (simulated)","evidence_summary"),("Information gaps","information_gaps"),("Local checks suggested by the provider","local_review_notes")]:
                st.markdown(f"**{title}**")
                st.text(getattr(outcome,field) or "Not supplied")
        else:
            st.write("No outcome is available for this plan and weather combination.")


def _overview(outcomes: dict[str,ScenarioOutcome | None]) -> None:
    rows=[]
    for plan in PLANS:
        out=outcomes[plan.key]
        rows.append(f'<div class="rc-overview-row"><b>{e(plan.title)}</b><span>Cost: {e(formatted(getattr(out,"cost_usd_per_ha",None),0))} USD/ha · Harvest: {e(formatted(getattr(out,"expected_yield_t_per_ha",None) if plan.key == "continuous" else None))} t/ha</span></div>')
    st.html('<div class="rc-overview" aria-label="Compact comparison of supplied costs and yields">'+''.join(rows)+'</div>')
    st.caption("Only supplied values appear. Mixed-crop harvests need per-crop units and a confirmed comparison method.")


def _interpret(outcomes: dict[str,ScenarioOutcome | None]) -> None:
    st.subheader("What do these results tell us?")
    available=[(p,outcomes[p.key]) for p in PLANS if outcomes[p.key] is not None]
    climate=st.session_state.selected_climate_id
    if available:
        plan,out=available[0]
        messages=[f"◉ Cost is not profit. {plan.title} has a simulated cost of {formatted(getattr(out,'cost_usd_per_ha',None),0)} USD/ha; income and net return are not available.",
                  "↔ No complete three-plan comparison yet. Soybean plan definitions and per-crop outcomes are pending; there is no basis to name a winner.",
                  f"☀ Active condition: {CLIMATES[climate]['title']}. The harvest range is supplied by the demo model and is not a validated guarantee."]
    else:
        messages=["◉ No economic conclusions can be drawn without outcomes for the active plans and weather.","↔ Keep exploring the plan definitions. Missing values are not zero.","☂ Wet-spring planting impacts require a model response for that condition." if climate=="wet" else "☀ Weather choices are scenarios to explore, not forecasts."]
    st.html('<section class="rc-explain">'+''.join(f'<p>{e(message)}</p>' for message in messages)+'</section>')


def _advanced(plot_id: str, scenarios: list[RotationScenario]) -> None:
    box=st.expander("More demo plans & original simulator",on_change="rerun",key="compare_advanced")
    if not box.open:
        return
    with box:
        st.caption("The original plans and simulator remain available here. Beans, sorghum and wheat plans are not soybean plans. These exploratory results do not select the three plans above.")
        baseline=next((s for s in scenarios if s.id=="maiz-continuo"),None)
        choices={s.id:s for s in scenarios if not baseline or s.id!=baseline.id}
        ids=st.multiselect("Additional demo plans",list(choices),default=list(choices)[:3],format_func=lambda sid:choices[sid].name,key="compare_extra_ids")
        rain=st.slider("Seasonal rainfall shift (%)",-30,20,0,step=5,key="compare_rain")
        heat=st.slider("Temperature anomaly (°C)",0.0,3.5,0.0,step=0.1,key="compare_heat")
        selected=([baseline] if baseline else [])+[choices[sid] for sid in ids]
        records=[];valid=[]
        for scenario in selected:
            out=outcome_for(plot_id,scenario.id,float(rain),heat)
            if not out:
                st.caption(f"{scenario.name}: results unavailable.")
                continue
            valid.append((scenario,out))
            try:
                fit=score_scenario_priority_fit(out,st.session_state.farmer_priorities)
            except Exception:
                fit=None
            records.append({"Plan":scenario.name,"Priority match (model score /100)":fit,"Scenario yield (t/ha)":out.expected_yield_t_per_ha,
                            "Range low (t/ha)":out.yield_ci_low,"Range high (t/ha)":out.yield_ci_high,"Water use (mm)":out.water_use_mm,
                            "Nutrient loss (%)":out.nutrient_loss_pct,"Organic matter change (%)":out.organic_matter_delta_pct,
                            "Erosion index (0–1)":out.erosion_risk_score,"Cost (USD/ha)":out.cost_usd_per_ha,"Pest disruption index (0–1)":out.pest_disruption_score})
        if records:
            df=pd.DataFrame(records)
            st.dataframe(df,hide_index=True,width="stretch",alt="Original demo plan outputs under the custom rainfall and temperature inputs")
            st.caption("Scenario-level harvest estimates do not establish comparable per-crop yields. No economic ranking is made.")
            with st.expander("Original tradeoff charts"):
                for column in ["Water use (mm)","Nutrient loss (%)","Organic matter change (%)","Erosion index (0–1)","Cost (USD/ha)","Pest disruption index (0–1)"]:
                    st.bar_chart(df,x="Plan",y=column,horizontal=True,height=180,width="stretch",alt=f"Simulated {column.lower()} for original demo plans")
            with st.expander("Original yield trajectories"):
                rows=[]
                for scenario,_out in valid:
                    try:
                        trajectory=predict_yield_trajectory(plot_id,scenario.id,rainfall_shift_pct=rain,temp_anomaly_c=heat).copy()
                        trajectory["scenario"]=scenario.name
                        rows.append(trajectory[["date","scenario","median","ci_low","ci_high"]])
                    except Exception:
                        st.caption(f"{scenario.name}: trajectory not available.")
                if rows:
                    st.altair_chart(yield_uncertainty_bands(pd.concat(rows,ignore_index=True)),width="stretch",alt="Simulated scenario yield trajectories and supplied ranges")
                    st.caption("Demo bounds: interval type and coverage are not validated. These curves are not observed crop histories.")
            for scenario,out in valid:
                st.markdown(f"**{scenario.name}**")
                _plan_details(scenario,out)


def run() -> None:
    from utils import field_model as fm
    if fm.enabled():
        from components import model_views
        model_views.compare()
        return

    try:
        plots=load_plots()
        scenarios=load_rotation_scenarios()
    except Exception:
        st.warning("The plan catalog could not be loaded. Please try again later.")
        st.session_state.comparison_ready=False
        return
    plot=next((p for p in plots if p.id==st.session_state.get("selected_plot_id")),None)
    if plot is None:
        st.info("Choose a valid plot in the main navigation before comparing plans.")
        st.session_state.comparison_ready=False
        return
    plans=resolve_plans(scenarios)
    reconcile_selection(plot.id,plans)
    with st.container(key="compare_screen"):
        st.html('<style>'+CSS.read_text(encoding="utf-8-sig")+_EXTRA_CSS+'</style>')
        st.html(hero(plot))
        _weather()
        selected_key=st.session_state.get("selected_plan_key")
        active_weather=st.session_state.selected_climate_id
        selected_style=f".st-key-climate_{active_weather} {{ border:2px solid currentColor; }}"
        if selected_key in {p.key for p in PLANS}:
            selected_style+=f".st-key-plan_{selected_key} {{ border:2px solid currentColor; }}"
        st.html("<style>"+selected_style+"</style>")
        outcomes=selected_outcomes(plot.id,st.session_state.selected_climate_id,plans)
        st.subheader("Your three planting options")
        st.caption("Choose a plan to explore, not a model recommendation. Illustrations are decorative; they do not show this plot.")
        _overview(outcomes)
        intervals=[interval for plan_key,out in outcomes.items() if plan_key == "continuous" and (interval:=yield_interval(out)) is not None]
        domain=(min(x[0] for x in intervals),max(x[2] for x in intervals)) if intervals else (0.0,1.0)
        cards=st.grid(3,min_column_width=285,gap="medium")
        for plan in PLANS:
            with cards.cell():
                with st.container(key=f"plan_{plan.key}"):
                    chosen=st.session_state.selected_plan_key==plan.key
                    st.html(plan_markup(plan,plans[plan.key],outcomes[plan.key],chosen,domain))
                    st.button("Selected for exploration" if chosen else "Explore this plan",key=f"select_{plan.key}",
                              icon=":material/check_circle:" if chosen else ":material/arrow_forward:",type="primary" if chosen else "secondary",
                              width="stretch",on_click=choose_plan,args=(plan.key,plot.id))
                    _plan_details(plans[plan.key],outcomes[plan.key])
        with st.expander("Why do results have a range?"):
            st.write("Actual harvests may differ from an estimate because field conditions and model knowledge vary. The bounds here come directly from the demo model; their statistical coverage has not been validated.")
            st.write("Weather scenarios change model inputs. The harvest interval expresses model uncertainty; this interface cannot separate its climate and estimation components.")
        _interpret(outcomes)
        _advanced(plot.id,scenarios)
    key=st.session_state.selected_plan_key
    st.session_state.comparison_ready=bool(key and plans.get(key) and outcomes.get(key))
    st.session_state.comparison_context={"plot_id":plot.id,"climate_id":st.session_state.selected_climate_id,
                                         "plan_key":key,"plan_id":st.session_state.selected_plan_id,
                                         "plot_name":plot.name,"climate_inputs":{
                                             "rainfall_shift_pct":CLIMATES[st.session_state.selected_climate_id]["rain"],
                                             "temp_anomaly_c":CLIMATES[st.session_state.selected_climate_id]["heat"]},"data_nature":"simulated",
                                         "outcome":outcomes.get(key)}


def render_plan_continuation(pages: dict[str,Any]) -> None:
    from utils import field_model as fm
    if fm.enabled():
        from components.model_views import continue_to_recommendations
        continue_to_recommendations(pages)
        return

    """Called by the shared shell only for this screen; other navigation is intact."""
    key=st.session_state.get("selected_plan_key")
    name=next((p.title for p in PLANS if p.key==key),"No plan selected")
    climate=st.session_state.get("selected_climate_id","normal")
    context=st.session_state.get("comparison_context",{})
    ready=bool(st.session_state.get("comparison_ready") and context.get("plot_id")==st.session_state.get("selected_plot_id")
               and context.get("climate_id")==climate and context.get("plan_id")==st.session_state.get("selected_plan_id"))
    with st.container(key="compare_continue"):
        st.subheader("Your plan to explore")
        st.write(f"{name} · {CLIMATES.get(climate,CLIMATES['normal'])['title']}")
        st.caption(f"Plot: {context.get('plot_name',st.session_state.get('selected_plot_id','Not selected'))}")
        st.write("Next, review recommendations based on your field and priorities. These recommendations do not yet change with the selected plan or weather scenario.")
        if not ready:
            st.caption("Select a plan with available model outcomes to continue. Pending definitions or wet-spring results cannot be passed off as supported plans.")
        if st.button("View recommendations for this plan",icon=":material/arrow_forward:",key="continue_rotations",type="primary",width="stretch",disabled=not ready):
            st.switch_page(pages["recommendations"])
