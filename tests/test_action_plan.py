"""Action-plan context and checklist acceptance; no paid APIs or model changes."""
from dataclasses import replace
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from components.action_plan import action_context, reviewed_count, review_widget_key, unique_actions
from components.action_markup import action_card, impact_range
from components.crop_comparison import outcome_for
from utils.data_sources import load_plots, load_rotation_scenarios
from utils.model_interface import generate_recommendations

ROOT=Path(__file__).resolve().parents[1]

class ActionPlanTests(TestCase):
    def app(self,with_plan=False):
        at=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=25).run()
        if with_plan:
            at.button(key='mobile_nav_rotations').click().run()
            at.button(key='select_continuous').click().run()
            at.button(key='continue_rotations').click().run()
        else:
            at.button(key='mobile_nav_recommendations').click().run()
        self.assertFalse(at.exception)
        return at

    def test_direct_entry_and_real_change_plan_navigation(self):
        at=self.app()
        self.assertTrue(any('No planting plan' in x.value for x in at.info))
        with self.assertRaises(KeyError):
            at.session_state['selected_plan_id']
        self.assertTrue(any('General field actions' in x.value for x in at.caption))
        at.button(key='change_action_plan').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['page_key'],'rotations')
        self.assertIsNone(at.session_state['selected_plan_id'])

    def test_saved_outcome_is_reused_without_another_prediction_and_context_survives(self):
        at=self.app(with_plan=True)
        saved=at.session_state['comparison_context']['outcome']
        outcome_for.clear()
        with patch('components.crop_comparison.predict_scenario_outcome',side_effect=AssertionError('must not predict')) as predict:
            at.run()
            self.assertFalse(at.exception)
            predict.assert_not_called()
        self.assertEqual(at.session_state['selected_plan_id'],'maiz-continuo')
        self.assertEqual(at.session_state['comparison_context']['outcome'],saved)
        at.button(key='change_action_plan').click().run()
        at.button(key='weather_dry').click().run()
        at.button(key='continue_rotations').click().run()
        self.assertEqual(at.session_state['comparison_context']['climate_id'],'dry')
        self.assertNotEqual(at.session_state['comparison_context']['outcome'].expected_yield_t_per_ha,saved.expected_yield_t_per_ha)
        at.button(key='continue_recommendations').click().run()
        self.assertEqual(at.session_state['page_key'],'rotations')
        self.assertEqual(at.session_state['selected_climate_id'],'dry')

    def test_checklist_persists_per_context_and_can_be_unchecked(self):
        at=self.app(with_plan=True)
        key=next(x.key for x in at.checkbox if x.key.startswith('review_'))
        at.checkbox(key=key).check().run()
        self.assertTrue(any(len(ids)==1 for ids in at.session_state['recommendation_reviews'].values()))
        at.button(key='change_action_plan').click().run()
        at.button(key='weather_dry').click().run()
        at.button(key='continue_rotations').click().run()
        self.assertFalse(any(x.value for x in at.checkbox if x.key.startswith('review_')))
        at.button(key='change_action_plan').click().run()
        at.button(key='weather_normal').click().run()
        at.button(key='continue_rotations').click().run()
        self.assertTrue(at.checkbox(key=key).value)
        at.button(key='change_action_plan').click().run()
        at.button(key='select_maize-soy').click().run()
        at.button(key='mobile_nav_recommendations').click().run()
        self.assertFalse(any(x.value for x in at.checkbox if x.key.startswith('review_')))
        self.assertTrue(any('model definition is not available' in x.value for x in at.info))
        at.button(key='change_action_plan').click().run()
        at.button(key='select_continuous').click().run()
        at.button(key='continue_rotations').click().run()
        self.assertTrue(at.checkbox(key=key).value)
        at.checkbox(key=key).uncheck().run()
        self.assertTrue(all(not ids for ids in at.session_state['recommendation_reviews'].values()))
        at.checkbox(key=key).check().run()
        at.selectbox(key='fs_plot_select').select('lote-sur').run()
        self.assertFalse(at.exception)
        self.assertFalse(any(x.value for x in at.checkbox if x.key.startswith('review_')))
        self.assertTrue(any('Your plot has changed' in x.value for x in at.info))

    def test_failed_or_empty_recommendations_do_not_invent_actions(self):
        for result in [[],None]:
            with patch('app_pages.recommendations.generate_recommendations',return_value=result):
                at=self.app()
                self.assertEqual(len(at.checkbox),0)
                self.assertFalse(at.exception)
                self.assertTrue(any('No actions were returned' in x.value for x in at.info))
        with patch('app_pages.recommendations.generate_recommendations',side_effect=RuntimeError('offline')):
            at=self.app()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.checkbox),0)
            self.assertTrue(any('could not be loaded' in x.value for x in at.warning))

    def test_stale_mismatched_or_missing_outcome_is_rejected(self):
        at=self.app(with_plan=True)
        state={key:at.session_state[key] for key in ["comparison_context","selected_plan_key","selected_plan_id","selected_climate_id"]}
        plots=load_plots();scenarios=load_rotation_scenarios()
        active=action_context(state,plots[0],scenarios)
        self.assertIsNotNone(active.outcome)
        stale=action_context(state,plots[1],scenarios)
        self.assertIsNone(stale.outcome)
        self.assertIsNone(stale.plan)
        for update in [{'outcome':None},{'outcome':replace(active.outcome,scenario_id='other')},{'climate_inputs':{'rainfall_shift_pct':99,'temp_anomaly_c':0}}]:
            altered={**state,'comparison_context':{**state['comparison_context'],**update}}
            self.assertIsNone(action_context(altered,plots[0],scenarios).outcome)
        altered={**state,'comparison_context':{**state['comparison_context'],'climate_id':[]}}
        self.assertIsNone(action_context(altered,plots[0],scenarios).outcome)

    def test_all_provider_actions_remain_accessible_and_html_is_escaped(self):
        rec=generate_recommendations('lote-norte')[0]
        records=[replace(rec,id=f'action-{i}',title=f'Action {i}') for i in range(5)]
        with patch('app_pages.recommendations.generate_recommendations',return_value=records):
            at=self.app()
            self.assertEqual(len(at.checkbox),5)
            self.assertTrue(any('Showing 3 of 5' in x.value for x in at.caption))
            at.toggle(key='action_show_more').set_value(True).run()
            self.assertTrue(any('Showing 5 of 5' in x.value for x in at.caption))
        bad=replace(rec,title='<script>unsafe</script>',rationale='<img onerror="bad">')
        markup=action_card(bad,0)
        self.assertNotIn('<script>',markup)
        self.assertNotIn('<img',markup)
        self.assertIn('&lt;script&gt;',markup)
        self.assertEqual(unique_actions([rec,rec,None]),[rec])
        self.assertEqual(reviewed_count(['missing',rec.id],[rec]),1)
        self.assertNotEqual(review_widget_key('plot-a',rec.id),review_widget_key('plot-b',rec.id))
        self.assertEqual(impact_range(replace(rec,impact_ci_low=float('nan'))),'Impact range not available.')

    def test_explore_another_plot_uses_existing_navigation(self):
        at=self.app(with_plan=True)
        at.button(key='action_explore_plot').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['page_key'],'map_view')
        self.assertEqual(at.session_state['selected_plot_id'],'lote-norte')
