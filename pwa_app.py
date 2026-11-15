"""PWA server entrypoint: streamlit run pwa_app.py."""

from pathlib import Path

import streamlit as st

from utils.pwa import pwa_routes

app = st.App(Path(__file__).with_name("streamlit_app.py"), routes=pwa_routes())
