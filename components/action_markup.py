"""Editorial recommendations markup using escaped data and existing local art."""
from pathlib import Path

from components.action_plan import ActionContext, category_name
from components.compare_markup import art, e, interval_bar
from components.crop_comparison import CLIMATES, PLANS, finite, formatted, yield_interval
from utils.types import Recommendation

CSS=Path(__file__).with_name("action_frontend")/"action.css"


def heading(ctx: ActionContext) -> str:
    return f'''<section class="ap-hero"><div><span class="ap-kicker">Your growing season · step 4 of 4</span><p class="ap-lead">Your next step starts here.</p><p>Explore actions to prepare your field, care for your crops and review what matters before planting.</p><span class="ap-tag">{e(ctx.plot.name)} · {ctx.plot.area_hectares:g} ha</span></div>{art('landscape','Decorative agricultural illustration, not an image of this plot')}</section>'''


def plan_context(ctx: ActionContext) -> str:
    spec=next((p for p in PLANS if p.key==ctx.plan_key),None)
    title=spec.title if spec else "Choose a plan to explore"
    weather=CLIMATES[ctx.climate_id]["title"] if ctx.climate_id else "Not selected for this field"
    sequence=' → '.join(e(c) for c in ctx.plan.crops) if ctx.plan else 'Crop sequence not available.'
    return f'''<section class="ap-context"><span class="ap-kicker">Your plan to explore</span><h3>{e(title)}</h3><div class="ap-tags"><span class="ap-tag">{e(ctx.plot.name)}</span><span class="ap-tag">{ctx.plot.area_hectares:g} ha</span><span class="ap-tag">{e(weather)}</span></div><p>{e(spec.description if spec else 'Compare the planting options to choose which plan you want to explore.')}</p><small>{sequence}</small><p>{"This is your exploration choice. No plan has been ranked as best for this field." if ctx.plan_key else "You can review general field actions while you choose a plan."}</p></section>'''


def result_summary(ctx: ActionContext) -> str:
    out=ctx.outcome
    harvest=out if ctx.plan_key=="continuous" else None
    interval=yield_interval(harvest)
    domain=(interval[0],interval[2]) if interval else (0.0,1.0)
    return f'''<section class="ap-summary" aria-label="Saved plan costs and harvest"><div class="ap-result"><span class="ap-label">Estimated cost · USD/ha</span><strong>{e(formatted(getattr(out,'cost_usd_per_ha',None),0))}</strong><small>Cost is not income or profit. Cost range and time horizon are not supplied.</small></div><div class="ap-result"><span class="ap-label">{'Maize harvest' if ctx.plan_key=='continuous' else 'Harvest estimate'} · t/ha</span><strong>{e(formatted(getattr(harvest,'expected_yield_t_per_ha',None)))}</strong>{interval_bar(harvest,domain)}<small>{'Saved demo result; duration not supplied.' if ctx.plan_key=='continuous' else 'Per-crop results and comparison method not supplied.'}</small></div></section>'''


def impact_range(rec: Recommendation) -> str:
    low,mid,high=(finite(rec.impact_ci_low),finite(rec.expected_impact_pct),finite(rec.impact_ci_high))
    if low is None or mid is None or high is None or not low<=mid<=high:
        return "Impact range not available."
    return f"Supplied impact range: {low:g}%–{high:g}%. Statistical coverage has not been validated."


def action_card(rec: Recommendation, index: int) -> str:
    category=category_name(rec.category)
    picture="cover" if category=="Fertilizer" else "wet" if rec.water_delta_mm else "maize"
    return f'''<article class="ap-action"><div class="ap-action-heading">{art(picture,'Illustrative crop or water symbol, not a field measurement')}<div><span class="ap-category">ACTION {index+1:02d} · {e(category)}</span><h3>Consider: {e(rec.title)}</h3></div></div><p><b>Why this action appears</b><br>{e(rec.rationale or 'No explanation supplied.')}</p><div class="ap-impact"><span>Modelled impact</span><strong>{e(formatted(rec.expected_impact_pct,0,suffix='%'))}</strong><small>{e(impact_range(rec))}</small><small>The impact measure and time horizon are not specified. This is a demo estimate, not a guaranteed benefit.</small></div><p>Estimated action cost: <b>{e(formatted(rec.cost_usd_per_ha,0))} USD/ha</b></p></article>'''
