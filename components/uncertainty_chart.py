"""Reusable charts that make model uncertainty visible."""

from __future__ import annotations

import altair as alt
import pandas as pd

from utils.types import SeasonalWindow


def yield_uncertainty_bands(df: pd.DataFrame, height: int = 300) -> alt.v6.LayerChart:
    """Expected yield over time with a confidence band per scenario.

    Expected columns: date (ISO string), scenario, median, ci_low, ci_high.
    """
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])

    # Long format for the area-between pattern: one row per bound.
    band_df = data.melt(
        id_vars=["scenario", "date"],
        value_vars=["ci_low", "ci_high"],
        var_name="bound",
        value_name="value",
    )

    # Mark properties (opacity, interpolate, point, strokeWidth) must live in
    # the MarkDef, not as Chart constructor kwargs: Altair 6.x rejects them at
    # spec-validation time.
    band = alt.Chart(band_df, mark="area").encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("value:Q", scale=alt.Scale(zero=False)),
        color=alt.Color("scenario:N", legend=alt.Legend(title="Escenario")),
    )
    band.mark = alt.MarkDef(type="area", opacity=0.25, interpolate="monotone")

    median = alt.Chart(data, mark="line").encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("median:Q", scale=alt.Scale(zero=False)),
        color=alt.Color("scenario:N"),
    )
    median.mark = alt.MarkDef(type="line", point=True, strokeWidth=2)

    return alt.layer(band, median).properties(height=height)


def impact_with_ci(df: pd.DataFrame, height: int = 300) -> alt.v6.LayerChart:
    """Horizontal bars of expected impact with CI whiskers.

    Expected columns: label, impact, ci_low, ci_high.
    """
    data = df.copy()
    data["label"] = data["label"].astype("category")

    bar = alt.Chart(data, mark="bar", height=18).encode(
        x=alt.X("impact:Q", title="Impacto esperado (%)"),
        y=alt.Y("label:N", sort="-x", title=None),
    )
    bar.mark = alt.MarkDef(type="bar", opacity=0.75)

    whiskers = alt.Chart(data, mark="rule").encode(
        x=alt.X("ci_low:Q"),
        x2=alt.X2("ci_high:Q"),
        y=alt.Y("label:N", sort="-x"),
    )
    whiskers.mark = alt.MarkDef(type="rule", strokeWidth=2, orient="horizontal")

    return alt.layer(bar, whiskers).properties(height=max(height, 40 * len(data)))


#: Calendar order for the seasonal timeline (Spanish month abbreviations).
_MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

#: Severity -> data color (chart data colors are theme-independent by design).
_SEVERITY_COLORS = {"Low": "#6B8E23", "Moderate": "#6A452C", "High": "#3D2217"}


def _window_months(start_month: str, end_month: str) -> list[int]:
    """Month numbers (1..12) covered by a window, handling Dec -> Jan wraparound."""
    start, end = int(start_month), int(end_month)
    if end >= start:
        return list(range(start, end + 1))
    return list(range(start, 13)) + list(range(1, end + 1))


def seasonal_vulnerability_timeline(windows: list[SeasonalWindow], height: int = 180) -> alt.v6.LayerChart:
    """Horizontal 12-month timeline of bare-soil and climate-hazard windows.

    One row per window type; each covered month is a bar colored by severity,
    with rich tooltips carrying the plain-language explanation.
    """
    rows: list[dict] = []
    for w in windows:
        span = f"{_MONTHS_ES[int(w.start_month) - 1]}–{_MONTHS_ES[int(w.end_month) - 1]}"
        for m in _window_months(w.start_month, w.end_month):
            rows.append(
                {
                    "month": _MONTHS_ES[m - 1],
                    "window_type": w.window_type,
                    "severity": w.severity,
                    "span": span,
                    "explanation": w.plain_explanation,
                }
            )

    if not rows:
        return alt.layer().properties(height=height)

    df = pd.DataFrame(rows)

    chart = alt.Chart(df, mark="bar").encode(
        x=alt.X("month:N", sort=_MONTHS_ES, title=None),
        y=alt.Y("window_type:N", title=None),
        color=alt.Color(
            "severity:N",
            scale=alt.Scale(domain=list(_SEVERITY_COLORS), range=list(_SEVERITY_COLORS.values())),
            legend=alt.Legend(title="Severidad"),
        ),
        tooltip=[
            alt.Tooltip("window_type:N", title="Ventana"),
            alt.Tooltip("severity:N", title="Severidad"),
            alt.Tooltip("span:N", title="Periodo"),
            alt.Tooltip("explanation:N", title=None),
        ],
    )
    chart.mark = alt.MarkDef(type="bar", opacity=0.85)

    return alt.layer(chart).properties(height=max(height, 40 * len(windows)))
