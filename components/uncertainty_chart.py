"""Reusable charts that make model uncertainty visible."""

from __future__ import annotations

import altair as alt
import pandas as pd


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
