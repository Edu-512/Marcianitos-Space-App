"""Recommendations: saved plan context and honest field-level action guidance."""
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from components.action_plan import ActionContext, action_context, reviewed_count, review_widget_key, unique_actions
from components.action_markup import CSS, action_card, heading, impact_range, plan_context, result_summary
from components.crop_comparison import formatted, finite
from components.navigation import PAGES, run_page
from components.uncertainty_chart import impact_with_ci
from utils.data_sources import load_plots, load_rotation_scenarios
from utils.model_interface import compute_plot_risk, generate_recommendations
from utils.types import PlotRisk, Recommendation


AVATAR=Path(__file__).resolve().parents[1]/"static"/"assistant"/"mr-corn-avatar.webp"


def _navigate(key: str) -> None:
    """Recreate the existing callable page through public Streamlit APIs."""
    spec=PAGES[key]
    page=st.Page(partial(run_page,key),title=spec.title,icon=spec.icon,url_path=spec.url_path,default=key=="map_view")
    st.switch_page(page)


def _review_change(context_key: str, recommendation_id: str, widget_key: str) -> None:
    store=st.session_state.setdefault("recommendation_reviews",{})
    reviewed=set(store.get(context_key,[]))
    if st.session_state.get(widget_key,False):
        reviewed.add(recommendation_id)
    else:
        reviewed.discard(recommendation_id)
    store[context_key]=sorted(reviewed)


def _checklist(ctx: ActionContext, recommendations: list[Recommendation]) -> None:
    if not recommendations:
        return
    store=st.session_state.setdefault("recommendation_reviews",{})
    reviewed=store.get(ctx.review_key,[])
    done=reviewed_count(reviewed,recommendations)
    with st.container(key="action_checklist"):
        st.subheader("Prepare for next season",icon=":material/checklist:")
        st.caption("Mark actions you have reviewed. This does not record completed farm work. Your review list stays in this session for this field, plan and weather.")
        st.progress(done/len(recommendations),text=f"{done} of {len(recommendations)} actions reviewed")
        for rec in recommendations:
            key=review_widget_key(ctx.review_key,rec.id)
            st.checkbox(f"Reviewed: {rec.title}",value=rec.id in reviewed,key=key,
                        on_change=_review_change,args=(ctx.review_key,rec.id,key))


def _action_details(rec: Recommendation) -> None:
    with st.expander("Why, sources & details"):
        st.caption("Scope: general field guidance based on the active plot and farm priorities. The current provider does not filter this action by planting plan or weather scenario.")
        st.write(f"Recommendation ID: {rec.id}")
        st.write(f"Water change: {formatted(rec.water_delta_mm,1)} mm")
        st.caption("Negative water change means a modelled reduction. No application schedule or time horizon is supplied.")
        st.write(f"Modelled impact: {formatted(rec.expected_impact_pct,0,suffix='%')}")
        st.write(impact_range(rec))
        for title,field in [("Provider evidence narrative · simulated","evidence_summary"),("Information gaps","information_gaps"),("Field checks suggested by the provider","local_review_notes")]:
            st.markdown(f"**{title}**")
            st.text(getattr(rec,field) or "Not supplied")
        st.caption("Source: generate_recommendations in the existing deterministic demo model. No recommendation here is an observation made by NASA. Date, analysis period, validated methodology and source resolution have not been supplied for this action.")


def _actions(recommendations: list[Recommendation], failed: bool) -> None:
    st.subheader("Your action plan",icon=":material/assignment:")
    st.write("Review these actions as you prepare for your next season.")
    st.caption("General field actions · based on your plot and priorities. Provider order is preserved; no primary recommendation or priority ranking has been supplied.")
    if failed:
        st.warning("Field actions could not be loaded. No recommendations have been assumed.")
        return
    if not recommendations:
        st.info("No actions were returned for this field and its current priorities. This does not establish that the field has no risks.")
        return
    visible=recommendations[:3]
    if len(recommendations)>3 and st.toggle(f"View all {len(recommendations)} actions",key="action_show_more"):
        visible=recommendations
    grid=st.grid(2,min_column_width=290,gap="medium")
    for index,rec in enumerate(visible):
        with grid.cell(column_span="all" if index==0 else 1):
            st.html(action_card(rec,index))
            _action_details(rec)
    st.caption(f"Showing {len(visible)} of {len(recommendations)} supplied actions.")


def _nutrition() -> None:
    st.subheader("Nutrition for your crops",icon=":material/eco:")
    st.html('<section class="ap-nutrition"><span class="ap-kicker">Fertilization · information pending</span><strong>Nitrogen dose not available</strong><p>No crop-specific nitrogen dose, application stage or unit has been supplied for this plan. A fertilizer action above does not establish an application rate.</p><p>Review soil conditions and the applicable agronomic criteria before deciding on an application.</p></section>')
    with st.expander("Nutrition data and limitations"):
        st.write("Pending: target crop, dose and original unit, application conditions, source, method, assumptions, period and limitations. No universal rotation dose or zero placeholder is used.")


def _risks(plot_id: str, ctx: ActionContext) -> None:
    st.subheader("Before you decide",icon=":material/visibility:")
    st.write("Actual field conditions can differ from the weather scenario. Harvest and action impacts can vary; check current field conditions before acting.")
    risk: PlotRisk | None = None
    try:
        risk=compute_plot_risk(plot_id)
        if getattr(risk,"plot_id",None) != plot_id:
            risk=None
    except Exception:
        risk=None
    with st.expander("Field risk indices and limitations"):
        st.caption("General simulated field indices on a 0–1 scale. These are not future probabilities or assessments for the selected plan and weather.")
        for label,field in [("Drought index","drought_risk"),("Heat stress index","heat_stress_risk"),("Nutrient depletion index","nutrient_depletion_risk"),("Overall index","overall_risk")]:
            st.write(f"{label}: {formatted(getattr(risk,field,None))}")
        st.caption("Source: existing demo compute_plot_risk function. Excess moisture, planting difficulty, historical events and financial uncertainty are not supplied for this context.")
        if ctx.outcome:
            st.write(f"Saved plan erosion index: {formatted(ctx.outcome.erosion_risk_score)} / 1")
            st.caption("No tolerable soil-loss limit or physical erosion unit is supplied. The demo index does not guarantee an erosion outcome.")
    with st.expander("Result sources and assumptions"):
        st.write("The plan summary reuses the exact saved outcome from Compare Crops. Recommendations are supplied separately by the existing field-and-priorities provider.")
        st.write(f"Active field ID: {plot_id}")
        st.write(f"Plan ID: {ctx.plan.id if ctx.plan else 'Not available'}")
        st.write(f"Weather ID: {ctx.climate_id or 'Not available'}")
        if ctx.outcome:
            st.write(f"Saved lower yield bound: {formatted(ctx.outcome.yield_ci_low)} t/ha")
            st.write(f"Saved upper yield bound: {formatted(ctx.outcome.yield_ci_high)} t/ha")
        st.caption("Nature: simulated. No observed field results, literature parameters or validated probabilities are claimed. Income, net return, economic interval, analysis date/horizon and per-crop mixed-rotation yields are not supplied. Climate and estimation uncertainty cannot be separated by the current contract.")


def _impact_details(recommendations: list[Recommendation]) -> None:
    box=st.expander("Compare supplied action impact ranges",on_change="rerun",key="action_impact_ranges")
    if not box.open:
        return
    with box:
        rows=[]
        for rec in recommendations:
            lo,mid,hi=(finite(rec.impact_ci_low),finite(rec.expected_impact_pct),finite(rec.impact_ci_high))
            if lo is not None and mid is not None and hi is not None and lo<=mid<=hi:
                rows.append({"label":rec.title,"impact":mid,"ci_low":lo,"ci_high":hi})
        if rows:
            st.altair_chart(impact_with_ci(pd.DataFrame(rows)),width="stretch",alt="Supplied simulated action impacts and ranges on one percent scale")
            st.caption("Supplied demo bounds; interval type and statistical coverage are not validated. The impact target and horizon are unspecified, so these bars do not establish which action is best.")
        else:
            st.info("No valid impact ranges are available to draw.")


def _help() -> None:
    st.subheader("Questions about your plan?",icon=":material/chat:")
    with st.container(horizontal=True,vertical_alignment="center"):
        st.image(str(AVATAR),width=72,alt="Mr Corn, the friendly corn farming assistant")
        st.write("**Mr Corn** · Your farming companion")
    st.write("Open the floating corn icon to chat. Mr Corn receives your active field and farm priorities. Mention the plan and weather you are exploring in your question; they are not passed automatically.")


def run() -> None:
    try:
        plots=load_plots()
    except Exception:
        plots=[]
    plot=next((p for p in plots if p.id==st.session_state.get("selected_plot_id")),None)
    if plot is None:
        st.info("Choose an available plot to review field actions.")
        st.button("Explore plots",key="action_explore_plot",on_click=_navigate,args=("map_view",))
        return
    try:
        scenarios=load_rotation_scenarios()
    except Exception:
        scenarios=[]
    ctx=action_context({key:st.session_state.get(key) for key in ("comparison_context","selected_plan_key","selected_plan_id","selected_climate_id")},plot,scenarios)
    failed=False
    try:
        recommendations=unique_actions(generate_recommendations(plot.id,st.session_state.farmer_priorities))
    except Exception:
        recommendations=[];failed=True
    with st.container(key="recommend_screen"):
        st.html('<style>'+CSS.read_text(encoding="utf-8-sig")+'</style>')
        st.html(heading(ctx))
        st.html(plan_context(ctx))
        if ctx.notice:
            st.info(ctx.notice)
        st.button("Change my planting plan" if ctx.plan else "Compare my planting options",key="change_action_plan",
                  icon=":material/compare_arrows:",width="stretch",on_click=_navigate,args=("rotations",))
        st.subheader("What could you get?")
        st.caption("Plan results saved in Compare Crops. The field actions below have a different scope.")
        st.html(result_summary(ctx))
        _actions(recommendations,failed)
        _checklist(ctx,recommendations)
        _nutrition()
        _risks(plot.id,ctx)
        _impact_details(recommendations)
        _help()
        st.subheader("Want to explore another option?")
        st.write("Use Compare Again below to revisit planting plans. Your current plot and weather remain available when you return.")
        st.button("Explore another plot",key="action_explore_plot",icon=":material/map:",on_click=_navigate,args=("map_view",))
    # The shell keeps its existing primary Compare Again action and mobile clearance.
