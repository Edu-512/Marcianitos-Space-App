"""Navigation acceptance tests without model changes or paid API calls."""
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class MainNavigationTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"), default_timeout=20)

    def test_initial_screen_sidebar_order_and_data_notice(self):
        at = self.app().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["page_key"], "map_view")
        self.assertEqual(at.main.title[0].value, "Explore Plots")
        self.assertEqual([link.label for link in at.sidebar.get("page_link")], [
            "Explore Plots", "My Field", "Compare Crops", "Recommendations",
        ])
        self.assertTrue(any("USDA and NASA" in message.value for message in at.info))
        self.assertTrue(any("Butler County" in message.value for message in at.info))

    def test_full_journey_preserves_selected_plot_and_headings(self):
        at = self.app().run()
        at.selectbox(key="fs_plot_select").select("467").run()
        for source, target, heading in [
            ("map_view", "home", "Know Your Field"),
            ("home", "rotations", "Compare Your Options"),
            ("rotations", "recommendations", "Your Next Steps"),
            ("recommendations", "rotations", "Compare Your Options"),
        ]:
            at.button(key=f"continue_{source}").click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state["page_key"], target)
            self.assertEqual(at.session_state["selected_plot_id"], "467")
            self.assertEqual(at.selectbox(key="fs_plot_select").value, "467")
            self.assertEqual(at.main.title[0].value, heading)

    def test_mobile_dock_navigates_freely_without_losing_the_plot(self):
        at = self.app().run()
        at.selectbox(key="fs_plot_select").select("1452").run()
        self.assertEqual([b.label for b in at.button if b.key and b.key.startswith("mobile_nav_")], [
            "Explore Plots", "My Field", "Compare Crops", "Recommendations",
        ])
        for target in ("recommendations", "home", "rotations", "map_view"):
            at.button(key=f"mobile_nav_{target}").click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state["page_key"], target)
            self.assertEqual(at.session_state["selected_plot_id"], "1452")
            self.assertEqual(at.selectbox(key="fs_plot_select").value, "1452")

    def test_external_plot_selection_reconciles_sidebar(self):
        at = self.app().run()
        # Same public state contract that a map selection would update.
        at.session_state["selected_plot_id"] = "1452"
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.selectbox(key="fs_plot_select").value, "1452")
        at.button(key="continue_map_view").click().run()
        self.assertEqual(at.session_state["selected_plot_id"], "1452")

    def test_invalid_plot_id_recovers_safely(self):
        at = self.app()
        at.session_state["selected_plot_id"] = "does-not-exist"
        at.session_state["fs_plot_select"] = "does-not-exist"
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["selected_plot_id"], "806")
        self.assertEqual(at.selectbox(key="fs_plot_select").value, "806")
        self.assertTrue(any("previous" in item.value for item in at.info))

    def test_empty_plots_show_message_and_do_not_run_analysis(self):
        with patch("utils.data_sources.load_plots", return_value=[]):
            at = self.app().run()
        self.assertFalse(at.exception)
        self.assertIsNone(at.session_state["selected_plot_id"])
        self.assertEqual(len(at.sidebar.selectbox), 0)
        self.assertEqual(len(at.sidebar.get("page_link")), 4)
        self.assertTrue(at.warning)
        self.assertFalse(at.metric)

    def test_failed_plot_loading_is_handled(self):
        with patch("utils.data_sources.load_plots", side_effect=RuntimeError("unavailable")):
            at = self.app().run()
        self.assertFalse(at.exception)
        self.assertTrue(at.error)
        self.assertIsNone(at.session_state["selected_plot_id"])

    def test_removed_plot_is_replaced_by_available_plot(self):
        from utils.data_sources import load_plots
        plots = load_plots()
        at = self.app().run()
        at.selectbox(key="fs_plot_select").select("467").run()
        with patch("utils.data_sources.load_plots", return_value=[plots[0]]):
            at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["selected_plot_id"], plots[0].id)


if __name__ == "__main__":
    unittest.main()
