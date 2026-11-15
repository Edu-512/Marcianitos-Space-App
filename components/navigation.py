"""Responsive navigation bar for Field Shift (native widgets, no page reload).

The nav bar is a row of native ``st.button`` inside equal-width columns.
Clicking a button triggers a normal Streamlit rerun over the websocket -
the browser never navigates or reloads.

The active page uses ``type="primary"``, adapting to light/dark modes automatically.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class PageSpec:
    """Metadata for one app page."""

    key: str  # module name inside ``app_pages/``
    title: str  # display name (nav bar + page heading)
    icon: str  # Material icon rendered in the nav bar and page heading
    help_text: str  # tooltip shown on hover


#: Ordered registry of app pages; order defines the nav bar layout.
PAGES: dict[str, PageSpec] = {
    "home": PageSpec(
        key="home",
        title="Field Pulse",
        icon=":material/dashboard:",
        help_text=(
            "Field pulse: overall risk, moisture, plant vigor, and available water, "
            "with a seasonal vulnerability calendar."
        ),
    ),
    "map_view": PageSpec(
        key="map_view",
        title="Field Map",
        icon=":material/map:",
        help_text=(
            "Geospatial map of all plots with satellite layers and "
            "multi-year history (2021-2026)."
        ),
    ),
    "rotations": PageSpec(
        key="rotations",
        title="Rotation Lab",
        icon=":material/repeat:",
        help_text=(
            "Compare crop rotations, simulate climate scenarios, and "
            "measure alignment with your priorities."
        ),
    ),
    "recommendations": PageSpec(
        key="recommendations",
        title="Action Plan",
        icon=":material/lightbulb:",
        help_text=(
            "Action plan: recommendations with satellite evidence, information "
            "gaps, and local ground verification."
        ),
    ),
}

DEFAULT_PAGE = "home"


def _select_page(key: str) -> None:
    """Widget callback: switch the active page without a browser reload."""
    st.session_state.page_key = key


def render_nav(active_key: str) -> None:
    """Render the responsive nav bar with ``active_key`` highlighted."""
    cols = st.columns(len(PAGES))
    for col, (key, spec) in zip(cols, PAGES.items()):
        with col:
            st.button(
                spec.title,
                key=f"fs_nav_{key}",
                icon=spec.icon,
                type="primary" if key == active_key else "secondary",
                use_container_width=True,
                on_click=_select_page,
                args=(key,),
                help=spec.help_text,
            )
    st.divider()


def run_page(key: str) -> None:
    """Import the page module registered under ``key`` and render it."""
    module = importlib.import_module(f"app_pages.{key}")
    module.run()