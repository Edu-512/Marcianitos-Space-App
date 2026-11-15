"""Presentation components for My Field; no inferred soil or crop records."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any
import math

import streamlit as st

SOIL_FIELDS = (
    ("water_storage", "water_drop", "Water storage", "Helps explain how long water may remain available to roots."),
    ("drainage", "water", "Drainage", "Helps assess whether water may collect after rain."),
    ("texture", "layers", "Soil texture", "The mix of sand, silt and clay affects how soil holds water."),
    ("organic_matter", "eco", "Organic matter", "Helps explain soil structure and nutrient cycling."),
)


def number(value: Any, decimals: int = 2, unit: str = "") -> str:
    """Format supplied numbers; missing/invalid values are never zero."""
    try:
        n = float(value)
        return f"{n:.{decimals}f}{unit}" if math.isfinite(n) else "Not available"
    except (TypeError, ValueError):
        return "Not available"


def soil_cards(properties: Mapping[str, Mapping[str, str]] | None = None) -> None:
    grid = st.grid(2, min_column_width=240)
    for key, icon, label, why in SOIL_FIELDS:
        supplied = (properties or {}).get(key)
        with grid.cell():
            with st.container(border=True, height="stretch"):
                st.markdown(f":material/{icon}: **{label}**")
                st.write(supplied.get("description", "Not available for this plot yet.") if supplied else "Not available for this plot yet.")
                st.caption(why)
                if supplied:
                    st.caption(f"Source: {supplied.get('source', 'Not supplied')} · {supplied.get('nature', 'Nature not supplied')}")


def crop_history(records: Sequence[Mapping[str, Any]] = (), *, source: str | None = None,
                 rotation: str | None = None) -> None:
    """Display at most eight supplied years; None=unknown, empty crop=no crop."""
    if not records:
        st.info("No yearly crop records are available for this plot yet.", icon=":material/history:")
        st.caption("A current crop does not establish a rotation pattern. Monthly indicator history is not crop history.")
        return
    ordered = sorted(records, key=lambda r: int(r["year"]))[-8:]
    grid = st.grid(4, min_column_width=145)
    crops: list[str] = []
    for record in ordered:
        crop = record.get("crop")
        label = "No information" if crop is None else ("No crop recorded" if crop == "" else str(crop))
        if crop:
            crops.append(str(crop))
        with grid.cell():
            with st.container(border=True):
                st.markdown(f":material/calendar_today: **{record['year']}**")
                st.write(label)
                st.caption(str(record.get("nature", "Nature not supplied")))
    st.caption(" · ".join(f"{crop}: {count} year(s)" for crop, count in Counter(crops).items()))
    st.caption(f"Source: {source or 'Not supplied'} · Period: {ordered[0]['year']}–{ordered[-1]['year']}")
    st.write(f"Recorded rotation pattern: {rotation or 'Not available; no pattern inferred.'}")


def planting_event(event: Mapping[str, Any] | None = None) -> None:
    if not event:
        st.caption("Historical planting difficulties: no plot-level event records are available yet.")
        return
    st.markdown(f"**Historical planting event · {event['year']}**")
    st.write(event.get("explanation", "Explanation not supplied."))
    st.write(f"Affected area: {event.get('area', 'Not available')} · Unplanted share: {event.get('unplanted_share', 'Not available')}")
    st.caption(f"Source: {event.get('source', 'Not supplied')} · {event.get('nature', 'Nature not supplied')}")
    st.caption(f"Limitations: {event.get('limitations', 'Not supplied')}. This is a historical record, not a future probability.")
