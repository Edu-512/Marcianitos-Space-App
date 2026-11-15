"""Safe editorial markup for plan cards. All data strings are escaped."""
from __future__ import annotations
from html import escape
from pathlib import Path
from typing import Any

from components.crop_comparison import PlanCard, finite, formatted, yield_interval
from utils.types import Plot, RotationScenario, ScenarioOutcome

ASSETS=Path(__file__).resolve().parents[1]/"static"/"compare"
CSS=Path(__file__).with_name("compare_frontend")/"compare.css"


def e(value: Any) -> str:
    return escape(str(value),quote=True)


def art(name: str, label: str) -> str:
    # Asset names come only from internal constants, never external content.
    if name not in {"maize","soy","cover","normal","dry","wet","landscape"}:
        return ""
    return (ASSETS/f"{name}.svg").read_text().replace('<svg ',f'<svg role="img" aria-label="{e(label)}" ')


def hero(plot: Plot) -> str:
    return f'''<section class="rc-hero"><div><span class="rc-kicker">Field planning · step 3 of 4</span>
<p class="rc-lead">What will you grow next season?</p><p>Explore the harvest, costs and soil tradeoffs of different planting plans.</p>
<div class="rc-context"><span class="rc-chip">{e(plot.name)}</span><span class="rc-chip">{plot.area_hectares:g} ha</span><span class="rc-chip">Registered crop: {e(plot.current_crop or 'Not available')}</span></div></div>
{art('landscape','Decorative farm illustration, not a photograph of this plot')}</section>'''


def interval_bar(outcome: ScenarioOutcome | None, domain: tuple[float,float]) -> str:
    values=yield_interval(outcome)
    if values is None:
        return '<small>Range not available.</small>'
    lo,mid,hi=values;start,end=domain;span=end-start
    if span<=0:
        return f'<small>Supplied range: {lo:g}–{hi:g} t/ha</small>'
    left=(lo-start)/span*100;width=(hi-lo)/span*100;point=(mid-start)/span*100
    return f'''<div class="rc-track" role="img" aria-label="Supplied simulated yield range {lo:g} to {hi:g}, estimate {mid:g} tonnes per hectare"><span class="rc-range" style="left:{left:.3f}%;width:{width:.3f}%"></span><span class="rc-mid" style="left:{point:.3f}%"></span></div><div class="rc-limits"><span>{lo:g} t/ha</span><span>{hi:g} t/ha</span></div><small>Supplied demo bounds · statistical coverage not validated.</small>'''


def plan_markup(spec: PlanCard, scenario: RotationScenario | None, outcome: ScenarioOutcome | None,
                selected: bool, domain: tuple[float,float]) -> str:
    status='✓ Selected for exploration' if selected else ('Available demo plan' if scenario else 'Awaiting model definition')
    sequence=' → '.join(e(crop) for crop in scenario.crops) if scenario else 'Exact crop sequence and timing pending.'
    cost=formatted(getattr(outcome,'cost_usd_per_ha',None),0)
    harvest=outcome if spec.key == "continuous" else None
    yield_=formatted(getattr(harvest,'expected_yield_t_per_ha',None))
    erosion=finite(getattr(outcome,'erosion_risk_score',None))
    erosion_html='<small>No erosion result or tolerable limit supplied.</small>'
    if erosion is not None:
        if 0<=erosion<=1:
            erosion_html=f'<div class="rc-track" role="img" aria-label="Simulated erosion index {erosion:g} on a zero to one scale"><span class="rc-range" style="left:0;width:{erosion*100:.2f}%"></span></div>'
        else:
            erosion_html='<small>Value outside the documented 0–1 scale; no bar drawn.</small>'
        erosion_html+=f'<small>{erosion:g} / 1 · demo index, not soil loss in tonnes. No tolerable limit supplied.</small>'
    description='Definition available; outcomes depend on the selected climate.' if scenario else 'The model team has not supplied this plan. No substitute crop or invented results are used.'
    notes=(f'<p><b>Resource to consider</b><br>Model irrigation demand: {e(formatted(outcome.water_use_mm,1))} mm. This is a simulated requirement, not measured water availability.</p><p><b>Modelled soil change</b><br>Organic matter change: {e(formatted(outcome.organic_matter_delta_pct,1))}%. The time horizon has not been supplied.</p>' if outcome else f'<p><b>What this plan explores</b><br>{e(spec.description)}</p><p><b>What to consider</b><br>{e(description)}</p>')
    return f'''<article class="rc-plan">{art(spec.art,'Illustrative crops, not an image of the active plot')}
<div class="rc-plan-head"><div class="rc-status">{status}</div><h3>{e(spec.title)}</h3><p class="rc-desc">{e(spec.description)}</p></div>
<div class="rc-sequence"><b>Crop sequence</b><br>{sequence}<br><small>{'Source order, one entry per season; calendar timing not supplied.' if scenario else 'Cover crop placement will follow the model definition.'}</small></div>
<div class="rc-result"><span class="rc-label">Estimated cost · USD/ha</span><strong>{cost}</strong><small>Not income or profit. Time horizon and cost range not supplied.</small></div>
<div class="rc-result"><span class="rc-label">{'Maize yield' if spec.key=='continuous' else 'Harvest estimate'} · t/ha</span><strong>{yield_}</strong>{interval_bar(harvest,domain)}<small>{'Model scenario estimate; duration not supplied.' if spec.key=='continuous' else 'Per-crop yields and comparison method pending.'}</small></div>
<div class="rc-result"><span class="rc-label">Soil erosion</span>{erosion_html}</div>
<div class="rc-notes">{notes}</div></article>'''
