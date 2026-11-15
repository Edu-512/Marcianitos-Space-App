"""Responsive navigation bar for Field Shift (native widgets, no page reload).

The nav bar is a row of native ``st.button`` pills inside equal-width columns:

- Clicking a pill triggers a normal Streamlit rerun over the websocket —
  the browser never navigates or reloads.
- The active page uses ``type="primary"``, so its color comes straight from
  the theme in ``.streamlit/config.toml`` and adapts to light/dark modes
  automatically (no hardcoded colors here).

The injected CSS only handles shape and placement: pill rounding, even
distribution and sticky-top (desktop) / fixed-bottom (mobile) positioning.
It intentionally uses no color values, because Streamlit does not expose its
theme as CSS custom properties to regular app content — native widgets are
the reliable way to stay theme-adaptive.
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
            "Pulso del campo: riesgo general, humedad, vigor vegetal y agua "
            "disponible, con el calendario de vulnerabilidades estacionales."
        ),
    ),
    "map_view": PageSpec(
        key="map_view",
        title="Field Map",
        icon=":material/map:",
        help_text=(
            "Mapa geoespacial de todos los lotes con capas satelitales y "
            "histórico multi-año (2021-2026)."
        ),
    ),
    "rotations": PageSpec(
        key="rotations",
        title="Rotation Lab",
        icon=":material/repeat:",
        help_text=(
            "Compara rotaciones de cultivos, simula escenarios climáticos y "
            "mide el ajuste a tus prioridades."
        ),
    ),
    "recommendations": PageSpec(
        key="recommendations",
        title="Action Plan",
        icon=":material/lightbulb:",
        help_text=(
            "Plan de acción: recomendaciones con evidencia satelital, brechas "
            "de información y verificación local."
        ),
    ),
}

DEFAULT_PAGE = "home"


def _select_page(key: str) -> None:
    """Widget callback: switch the active page without a browser reload."""
    st.session_state.page_key = key


#: Shape and placement only — no colors, so both themes render correctly.
_NAV_CSS = """\
/* The nav row is the only horizontal block containing buttons in this app. */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stButton"]) {
  position: sticky;
  top: 0;
  z-index: 50;
  gap: 0.625rem;
  padding: 0.625rem 1.25rem;
}

/* Pill shape for the nav buttons (the only buttons in the app). */
[data-testid="stButton"] > button {
  border-radius: 999px;
}

@media (max-width: 767px) {
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stButton"]) {
    position: fixed;
    top: auto;
    bottom: 0;
    left: 0;
    right: 0;
    justify-content: space-around;
    padding: 0.5rem 0.75rem calc(0.5rem + env(safe-area-inset-bottom, 0px));
  }

  [data-testid="stButton"] > button {
    font-size: 0.78rem;
    white-space: normal;
    min-height: 2.4rem;
  }

  /* Keep page content clear of the fixed bottom bar. */
  [data-testid="stMain"] {
    padding-bottom: calc(6.5rem + env(safe-area-inset-bottom, 0px)) !important;
  }
}
"""


def render_nav(active_key: str) -> None:
    """Render the responsive nav bar with ``active_key`` highlighted."""
    st.markdown(f"<style>{_NAV_CSS}</style>", unsafe_allow_html=True)
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


def run_page(key: str) -> None:
    """Import the page module registered under ``key`` and render it."""
    module = importlib.import_module(f"app_pages.{key}")
    module.run()
