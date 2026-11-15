"""Responsive navigation bar for Field Shift (native widgets, no page reload).

The nav bar is a row of native ``st.button`` pills inside a keyed container:

- Clicking a pill triggers a normal Streamlit rerun over the websocket —
  the browser never navigates or reloads.
- The active page uses ``type="primary"``, so its color comes straight from
  the theme in ``.streamlit/config.toml`` and adapts to light/dark modes
  automatically (no hardcoded colors here).

The injected CSS only handles shape and placement: pill rounding, even
distribution and fixed-top (desktop) / fixed-bottom (mobile) positioning.
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


# Scoped to this container: other page buttons keep their native styling.
_NAV_CSS = """
.st-key-fs_navigation {
  position: fixed;
  top: 4rem;
  left: 1rem;
  right: 1rem;
  transform: none;
  z-index: 100;
  width: auto !important;
  max-width: none;
  box-sizing: border-box;
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: center;
  align-self: center;
  padding: 0.5rem;
  border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
  border-radius: 1.75rem;
  background: linear-gradient(135deg,
    color-mix(in srgb, currentColor 9%, transparent),
    color-mix(in srgb, currentColor 4%, transparent));
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 10px 32px rgb(0 0 0 / 10%),
              inset 0 1px 0 color-mix(in srgb, currentColor 8%, transparent);
  gap: 0.5rem;
  overflow: visible;
}
.st-key-fs_navigation > div {
  flex: 1 1 0 !important;
  min-width: 0 !important;
}
/* Center compact buttons inside four equal tracks, including their wrappers. */
.st-key-fs_navigation .stButton,
.st-key-fs_navigation .stButton > div {
  display: flex;
  justify-content: center;
  width: 100%;
  min-width: 0;
}
.st-key-fs_navigation button {
  position: relative;
  width: min(100%, 9rem);
  margin-inline: auto;
  min-height: 5.25rem;
  padding: 0.5rem 0.35rem;
  border: none !important;
  box-shadow: none;
  border-radius: 1.25rem;
  flex-direction: column;
  gap: 0.3rem;
  transition: background-color 180ms ease, color 180ms ease,
              box-shadow 180ms ease, transform 180ms ease;
}
/* The native label has its own flex row inside the button. */
.st-key-fs_navigation button > div,
.st-key-fs_navigation button > div > span[data-has-shortcut] {
  display: flex !important;
  flex-direction: column !important;
  align-items: center;
  justify-content: center;
  gap: 0.875rem;
  width: 100%;
  min-width: 0;
}
.st-key-fs_navigation button [data-testid="stMarkdownContainer"] {
  text-align: center;
}
.st-key-fs_navigation button[data-testid="stBaseButton-secondary"],
.st-key-fs_navigation button[data-testid="stBaseButton-secondary"]:hover,
.st-key-fs_navigation button[data-testid="stBaseButton-secondary"]:active {
  background: transparent !important;
  color: inherit !important;
}
.st-key-fs_navigation button[data-testid="stBaseButton-primary"]:hover,
.st-key-fs_navigation button[data-testid="stBaseButton-primary"]:active {
  filter: none;
}
.st-key-fs_navigation button [data-testid="stIconMaterial"] {
  font-size: 2.125rem !important;
  width: 2.125rem;
  height: 2.125rem;
  line-height: 1;
  margin: 0;
  border-radius: 0.65rem;
  transition: transform 180ms ease, box-shadow 180ms ease;
}
.st-key-fs_navigation button:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}
.st-key-fs_navigation button p {
  white-space: normal;
  overflow-wrap: anywhere;
  font-size: 0.875rem;
  line-height: 1.2;
}
/* A dedicated spacer keeps the final content above the mobile dock. */
.st-key-fs_navigation_clearance { display: none; }
/* Native st.space below reserves actual layout height, even on first load. */
.st-key-fs_navigation button[data-testid="stBaseButton-primary"] {
  color: inherit !important;
  background: linear-gradient(145deg,
    color-mix(in srgb, currentColor 18%, transparent),
    color-mix(in srgb, currentColor 9%, transparent)) !important;
  box-shadow: 0 4px 12px rgb(0 0 0 / 7%),
              inset 0 -3px 0 color-mix(in srgb, currentColor 35%, transparent);
  animation: fs-nav-select 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
}
.st-key-fs_navigation button[data-testid="stBaseButton-primary"] [data-testid="stIconMaterial"] {
  font-variation-settings: "FILL" 1;
  transform: scale(1.06);
  box-shadow: none;
}
.st-key-fs_navigation button[data-testid="stBaseButton-primary"] p {
  font-weight: 600;
}
@keyframes fs-nav-select {
  from { opacity: 0.65; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}
/* Pointer feedback adds depth without coloring inactive destinations. */
@media (hover: hover) and (pointer: fine) {
  .st-key-fs_navigation button:hover {
    transform: translateY(-2px);
  }
  .st-key-fs_navigation button:hover [data-testid="stIconMaterial"] {
    transform: translateY(-1px) scale(1.08);
  }
}
.st-key-fs_navigation button:active {
  transform: scale(0.97);
}
@media (max-width: 767px) {
  .st-key-fs_navigation {
    position: fixed;
    top: auto;
    bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
    left: max(0.5rem, env(safe-area-inset-left, 0px));
    right: max(0.5rem, env(safe-area-inset-right, 0px));
    width: auto;
    transform: none;
    padding: 0.4rem;
    gap: 0.25rem;
    border-radius: 1.5rem;
  }
  .st-key-fs_navigation button {
    min-height: 4.75rem;
    padding: 0.4rem 0.2rem;
    border-radius: 1.1rem;
    flex-direction: column;
    gap: 0.25rem;
  }
  .st-key-fs_navigation button p {
    font-size: clamp(0.625rem, 2.7vw, 0.8rem);
    line-height: 1.2;
  }
  .st-key-fs_navigation_top_clearance { display: none; }
  .st-key-fs_navigation_clearance {
    display: block;
    height: calc(7rem + env(safe-area-inset-bottom, 0px));
  }
}
@media (prefers-reduced-motion: reduce) {
  .st-key-fs_navigation button,
  .st-key-fs_navigation button [data-testid="stIconMaterial"] {
    transform: none !important;
    transition: none !important;
    animation: none !important;
  }
}
"""


def render_nav(active_key: str) -> None:
    """Render a top desktop bar or a floating bottom mobile dock."""
    st.html(f"<style>{_NAV_CSS}</style>")
    with st.container(key="fs_navigation", horizontal=True, wrap=False):
        for key, spec in PAGES.items():
            st.button(
                spec.title,
                key=f"fs_nav_{key}",
                icon=spec.icon,
                type="primary" if key == active_key else "secondary",
                width="stretch",
                on_click=_select_page,
                args=(key,),
                wrap=True,
            )
    with st.container(key="fs_navigation_top_clearance"):
        st.space(80)


def render_nav_clearance() -> None:
    """Reserve mobile scroll space after the page, outside the fixed dock."""
    with st.container(key="fs_navigation_clearance"):
        st.space(112)


def run_page(key: str) -> None:
    """Import the page module registered under ``key`` and render it."""
    module = importlib.import_module(f"app_pages.{key}")
    module.run()
