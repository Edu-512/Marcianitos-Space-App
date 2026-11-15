"""Native sidebar navigation and shared plot selection for Field Shift."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Callable

import streamlit as st

from utils.types import Plot

@dataclass(frozen=True)
class PageSpec:
    key: str
    title: str
    icon: str
    heading: str
    description: str
    url_path: str
    next_page: str
    next_label: str

# User-facing navigation and headings live here to keep future translation simple.
PAGES = {
    "map_view": PageSpec("map_view", "Explore Plots", ":material/map:",
        "Explore Plots", "Choose the field you want to analyze.",
        "explorar", "home", "Analyze This Plot"),
    "home": PageSpec("home", "My Field", ":material/landscape:",
        "Know Your Field", "Explore your soil characteristics and cropping history.",
        "mi-terreno", "rotations", "Compare My Options"),
    "rotations": PageSpec("rotations", "Compare Crops", ":material/compare_arrows:",
        "Compare Your Options", "Explore different crop plans and their possible outcomes.",
        "comparar", "recommendations", "View Recommendations"),
    "recommendations": PageSpec("recommendations", "Recommendations", ":material/lightbulb:",
        "Your Next Steps", "Review actions to consider for your next growing season.",
        "recomendaciones", "rotations", "Compare Again"),
}
DEFAULT_PAGE = "map_view"


def run_page(key: str) -> None:
    importlib.import_module(f"app_pages.{key}").run()


def _renderer(key: str) -> Callable[[], None]:
    def render() -> None:
        run_page(key)
    return render


def build_navigation() -> tuple[dict[str, Any], Any]:
    pages = {
        key: st.Page(_renderer(key), title=spec.title, icon=spec.icon,
                     url_path=spec.url_path, default=key == DEFAULT_PAGE)
        for key, spec in PAGES.items()
    }
    # Native page links below provide brand-first ordering without custom CSS.
    current = st.navigation(list(pages.values()), position="hidden")
    return pages, current


def prepare_plot_selection(plots: list[Plot]) -> bool:
    """Reconcile a canonical ID, including future selections from the map."""
    ids = [plot.id for plot in plots]
    selected = st.session_state.get("selected_plot_id")
    recovered = selected is not None and selected not in ids
    if selected not in ids:
        st.session_state.selected_plot_id = ids[0] if ids else None
    selected = st.session_state.selected_plot_id
    # This runs before the selector is mounted. Never overwrite another widget
    # after mount, and never use a display name as the parcel identity.
    if st.session_state.get("fs_plot_select") != selected:
        st.session_state.fs_plot_select = selected
    return recovered


def _select_plot(valid_ids: tuple[str, ...]) -> None:
    selected = st.session_state.get("fs_plot_select")
    st.session_state.selected_plot_id = (
        selected if selected in valid_ids else valid_ids[0] if valid_ids else None
    )


def render_sidebar(pages: dict[str, Any], active_key: str, plots: list[Plot]) -> None:
    with st.sidebar:
        st.title("Field Shift")
        st.caption("Adapting Farms with NASA Data")
        st.space("small")
        st.markdown("**Your Journey**")
        for key, spec in PAGES.items():
            st.page_link(pages[key], label=spec.title, icon=spec.icon, help="", width="stretch")
        step = list(PAGES).index(active_key) + 1
        st.caption(f"You are here: {PAGES[active_key].title} · Step {step} of 4")
        st.divider()
        st.markdown("**Selected Plot**")
        if not plots:
            st.info("No plots are available to select.")
        else:
            names = {plot.id: plot.name for plot in plots}
            st.selectbox(
                "Change plot", list(names), format_func=lambda pid: names[pid],
                key="fs_plot_select", on_change=_select_plot,
                args=(tuple(names),),
            )
            plot = next(p for p in plots if p.id == st.session_state.selected_plot_id)
            st.caption(f"{plot.name} · {plot.area_hectares:g} ha · {plot.current_crop}")
        st.divider()
        st.caption("Case study: Butler County, Iowa.")
        st.caption("Prototype with simulated plots and results.")


def render_continuation(pages: dict[str, Any], active_key: str) -> None:
    spec = PAGES[active_key]
    st.space("medium")
    st.caption(f"Next section: {PAGES[spec.next_page].title}")
    if st.button(spec.next_label, key=f"continue_{active_key}", type="primary",
                 icon=":material/arrow_forward:", width="stretch"):
        st.switch_page(pages[spec.next_page])

# Scoped to our keyed containers; sidebar visibility stays under Streamlit's
# native responsive behavior. The plot selector remains accessible in its menu.
_MOBILE_NAV_CSS = """
.st-key-fs_mobile_navigation,
.st-key-fs_mobile_navigation_clearance { display: none !important; }
@media (max-width: 767px) {
  .st-key-fs_mobile_navigation {
    display: grid !important;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    position: fixed;
    left: max(0.5rem, env(safe-area-inset-left, 0px));
    right: max(0.5rem, env(safe-area-inset-right, 0px));
    bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
    width: auto !important;
    box-sizing: border-box;
    padding: 0.4rem;
    gap: 0.25rem;
    z-index: 150;
    border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
    border-radius: 1.5rem;
    background: linear-gradient(135deg,
      color-mix(in srgb, currentColor 9%, transparent),
      color-mix(in srgb, currentColor 4%, transparent));
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    box-shadow: 0 10px 32px rgb(0 0 0 / 10%);
  }
  .st-key-fs_mobile_navigation > div { min-width: 0 !important; }
  .st-key-fs_mobile_navigation .stButton,
  .st-key-fs_mobile_navigation .stButton > div {
    display: flex;
    justify-content: center;
    width: 100%;
    min-width: 0;
  }
  .st-key-fs_mobile_navigation button {
    width: 100%;
    min-height: 5.25rem;
    padding: 0.4rem 0.15rem;
    border: none !important;
    border-radius: 1.1rem;
    color: inherit !important;
    background: transparent !important;
    transition: background-color 180ms ease, box-shadow 180ms ease;
  }
  .st-key-fs_mobile_navigation button > div,
  .st-key-fs_mobile_navigation button > div > span[data-has-shortcut] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center;
    justify-content: center;
    gap: 0.875rem;
    width: 100%;
    min-width: 0;
  }
  .st-key-fs_mobile_navigation button [data-testid="stIconMaterial"] {
    font-size: 1.9rem !important;
    line-height: 1;
    margin: 0;
  }
  .st-key-fs_mobile_navigation button p {
    font-size: clamp(0.64rem, 2.6vw, 0.8rem);
    white-space: normal;
    overflow-wrap: anywhere;
    text-align: center;
    line-height: 1.2;
  }
  .st-key-fs_mobile_navigation button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(145deg,
      color-mix(in srgb, currentColor 18%, transparent),
      color-mix(in srgb, currentColor 9%, transparent)) !important;
    box-shadow: inset 0 -3px 0 color-mix(in srgb, currentColor 35%, transparent);
  }
  .st-key-fs_mobile_navigation button[data-testid="stBaseButton-primary"] p { font-weight: 700; }
  .st-key-fs_mobile_navigation button[data-testid="stBaseButton-primary"] [data-testid="stIconMaterial"] {
    font-variation-settings: "FILL" 1;
  }
  .st-key-fs_mobile_navigation button:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
  .st-key-fs_mobile_navigation_clearance { display: block !important; }
}
@media (prefers-reduced-motion: reduce) {
  .st-key-fs_mobile_navigation button { transition: none !important; }
}
"""


def render_mobile_navigation(pages: dict[str, Any], active_key: str) -> None:
    """A floating bottom dock on phones; no duplicate desktop navigation."""
    st.html(f"<style>{_MOBILE_NAV_CSS}</style>")
    with st.container(key="fs_mobile_navigation", horizontal=True, wrap=False):
        for key, spec in PAGES.items():
            if st.button(
                spec.title, key=f"mobile_nav_{key}", icon=spec.icon,
                type="primary" if key == active_key else "secondary",
                width="stretch", wrap=True,
            ):
                st.switch_page(pages[key])


def render_mobile_clearance() -> None:
    """Let users scroll the final action above the phone navigation dock."""
    with st.container(key="fs_mobile_navigation_clearance"):
        st.space(136)
