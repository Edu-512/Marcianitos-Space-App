"""Shared product identity and artwork."""
from pathlib import Path

APP_NAME = "Know Your Farm"
BRAND_DIR = Path(__file__).resolve().parents[1] / "static" / "brand"
APP_ICON = BRAND_DIR / "know-your-farm-emblem-watermarked.webp"
APP_LOGO = BRAND_DIR / "know-your-farm-emblem-watermarked.webp"


def render_mobile_brand() -> None:
    """Shared fixed brand header, present on all four pages on phones."""
    import streamlit as st
    st.html("""<style>
.st-key-kyf_mobile_brand,.st-key-kyf_mobile_brand_clearance {display:none;}
@media(max-width:767px){
 .st-key-kyf_mobile_brand {display:flex;position:fixed;top:3rem;left:0;right:0;height:68px;z-index:150;justify-content:center;align-items:center;gap:12px;padding:4px 12px;background:var(--st-background-color);border-bottom:1px solid color-mix(in srgb,currentColor 15%,transparent);}
 .st-key-kyf_mobile_brand p {font-size:clamp(20px,5.5vw,24px);font-weight:700;white-space:nowrap;margin:0;}
 .st-key-kyf_mobile_brand_clearance {display:block;}
}
</style>""")
    with st.container(key="kyf_mobile_brand",horizontal=True,horizontal_alignment="center",vertical_alignment="center",gap="small",wrap=False):
        st.image(str(APP_LOGO),width=60,alt="Know Your Farm emblem, AI-generated with Codex")
        st.markdown("**"+APP_NAME+"**",width="content")
    with st.container(key="kyf_mobile_brand_clearance"):
        st.space(112)
