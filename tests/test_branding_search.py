"""Regression coverage for searchable field selection and shared mobile branding."""
from pathlib import Path
from unittest import TestCase
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

class BrandingSearchTests(TestCase):
    def test_search_filters_by_id_without_changing_selection_while_typing(self):
        at=AppTest.from_file(str(ROOT/"streamlit_app.py"),default_timeout=30).run()
        initial=at.session_state["selected_plot_id"]
        at.text_input(key="fs_plot_select_search").input("502").run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["selected_plot_id"],initial)
        self.assertTrue(any("Field 502" in option for option in at.selectbox(key="fs_plot_select").options))
        at.selectbox(key="fs_plot_select").select("502").run()
        self.assertEqual(at.session_state["selected_plot_id"],"502")
        self.assertEqual(at.selectbox(key="fs_mobile_plot_select").value,"502")
        at.text_input(key="fs_plot_select_search").input("no-such-field").run()
        self.assertEqual(at.session_state["selected_plot_id"],"502")
        self.assertTrue(any("No matching fields" in item.value for item in at.caption))

    def test_mobile_search_and_brand_persist_through_navigation(self):
        at=AppTest.from_file(str(ROOT/"streamlit_app.py"),default_timeout=30).run()
        at.text_input(key="fs_mobile_plot_select_search").input("Field 25").run()
        at.selectbox(key="fs_mobile_plot_select").select("25").run()
        for page in ["home","rotations","recommendations","map_view"]:
            at.button(key="mobile_nav_"+page).click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state["selected_plot_id"],"25")
            self.assertTrue(any(node.key=="kyf_mobile_brand" for node in at.get("flex_container")))
