"""Inline CCv2 assistant, mounted once on every page and streamed via a fragment."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from utils import ai_chat, field_model as fm
from utils.chat_state import ChatSession
from utils.data_sources import load_plots

FRONTEND = Path(__file__).with_name("chat_frontend")
KEY = "don_surco_widget"
SESSIONS = "don_surco_conversations"

_COMPONENT = st.components.v2.component(
    "field_shift_don_surco",
    html=(FRONTEND / "chat.html").read_text(encoding="utf-8-sig"),
    css=(FRONTEND / "chat.css").read_text(encoding="utf-8-sig"),
    js=(FRONTEND / "chat.js").read_text(encoding="utf-8-sig"),
)

def _context() -> str:
    if st.session_state.get("data_mode")=="legacy":
        return repr(st.session_state.farmer_priorities)
    return repr((st.session_state.farmer_priorities,st.session_state.get("data_mode","model"),st.session_state.get("selected_plan_id"),st.session_state.get("selected_climate_id")))


def _sessions() -> dict[str, ChatSession]:
    if SESSIONS not in st.session_state:
        st.session_state[SESSIONS] = {}
    return st.session_state[SESSIONS]


def _session(plot_id: str) -> ChatSession:
    return _sessions().setdefault(plot_id, ChatSession())


def _available() -> bool:
    return ai_chat.AI_READY and bool(ai_chat.get_api_key())


def _submit() -> None:
    payload = st.session_state.get(KEY, {}).get("submit")
    plot_id = st.session_state.selected_plot_id
    if not isinstance(payload, dict) or payload.get("plot_id") != plot_id or not _available():
        return
    _session(plot_id).begin(str(payload.get("text", "")), str(payload.get("id", "")), _context())


def _clear() -> None:
    plot_id = st.session_state.selected_plot_id
    payload = st.session_state.get(KEY, {}).get("clear")
    if isinstance(payload, dict) and payload.get("plot_id") == plot_id and not _session(plot_id).busy:
        _session(plot_id).messages.clear()
        _session(plot_id).request_id = ""


def _noop() -> None:
    pass


def render_chat() -> None:
    """Preserve conversations by plot across navigation; no idle polling."""
    plot_id = st.session_state.selected_plot_id
    context = _context()
    for old_plot, conversation in _sessions().items():
        if conversation.busy and (old_plot != plot_id or conversation.context != context):
            conversation.cancel()
    conversation = _session(plot_id)
    plot = next((p for p in load_plots() if p.id == plot_id), None)
    enabled = _available()

    @st.fragment(run_every=0.3 if conversation.busy else None)
    def panel() -> None:
        if conversation.starting:
            conversation.starting = False
            st.rerun()  # Enable the timer after a fragment-local submit callback.
        was_busy = conversation.busy
        _COMPONENT(
            key=KEY,
            data={
                "avatar": "./app/static/assistant/mr-corn-watermarked.webp?v=1",
                "model_context": (f"{plot.name if plot else plot_id} | {fm.CLIMATES.get(str(st.session_state.get('selected_climate_id')),'Normal year')} | {fm.PLANS.get(str(st.session_state.get('selected_plan_id')),'Choose a plan')}" if fm.enabled() else None),
                "plot_id": plot_id,
                "plot_name": plot.name if plot else plot_id,
                "messages": conversation.messages,
                "busy": conversation.busy,
                "enabled": enabled,
                "open": st.session_state.get(KEY, {}).get("open", False),
            },
            height=0,
            on_submit_change=_submit,
            on_clear_change=_clear,
            on_open_change=_noop,
        )
        # Send the visible panel before potentially slow network/model work.
        # Otherwise Streamlit treats the previous component as stale and dims
        # the entire overlay until advance() returns.
        if conversation.busy:
            if conversation.iterator is None:
                conversation.iterator = ai_chat.run_chat_turn(conversation.history(), plot_id)
            conversation.advance()
        if was_busy and not conversation.busy:
            st.rerun()  # Disable polling after the terminal event.

    panel()
