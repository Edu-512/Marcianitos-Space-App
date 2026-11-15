"""Small shared visual primitives; warm surfaces with teal and gold accents."""
from html import escape
import streamlit as st


def styles() -> None:
    dark=st.context.theme.type=='dark'
    teal='#71d4c7' if dark else '#146c65';gold='#f0c46b' if dark else '#805500'
    st.html('''<style>
:root { --fs-accent:TEAL;--fs-gold:GOLD; }
.fs-section { display:flex;align-items:center;gap:12px;font-size:24px!important;margin:32px 0 18px!important;padding-top:22px;border-top:2px solid color-mix(in srgb,var(--fs-accent) 30%,transparent); }
.fs-section span { color:var(--fs-accent);font-size:28px; }
.fs-context { display:flex;flex-wrap:wrap;gap:8px;margin:12px 0; }
.fs-pill { border:1px solid color-mix(in srgb,var(--fs-accent) 35%,transparent);background:color-mix(in srgb,var(--fs-accent) 7%,transparent);padding:6px 12px;border-radius:100px;font-size:14px; }
.fs-card { border:1px solid color-mix(in srgb,currentColor 18%,transparent);border-radius:18px;padding:22px;background:color-mix(in srgb,currentColor 3%,transparent);height:100%;overflow-wrap:anywhere; }
.fs-card h3 { font-size:21px;margin:12px 0; }.fs-card p { font-size:15px;line-height:1.6;margin:10px 0; }
.fs-card .fs-label { display:block;color:var(--fs-accent);font-size:14px;font-weight:650;margin-top:14px; }
.fs-card strong.fs-value { display:block;font-size:30px;line-height:1.35;font-variant-numeric:tabular-nums; }
.fs-card small { display:block;font-size:14px;line-height:1.6;margin:6px 0; }
.fs-card .fs-soil { border-top:1px solid color-mix(in srgb,currentColor 15%,transparent);margin-top:16px;padding-top:12px; }
.fs-model-note { padding:14px 18px;border-left:4px solid var(--fs-gold);background:color-mix(in srgb,var(--fs-gold) 7%,transparent);border-radius:8px;font-size:14px;line-height:1.65; }
.st-key-model_content button { min-height:44px; }
@media(max-width:767px) { .fs-section { font-size:22px!important; }.fs-card {padding:18px;} .st-key-model_content button {max-width:calc(100% - 4.75rem);} }
</style>'''.replace('TEAL',teal).replace('GOLD',gold))


def section(title: str, symbol: str='◈') -> None:
    st.html(f'<h2 class="fs-section"><span aria-hidden="true">{escape(symbol)}</span>{escape(title)}</h2>')
