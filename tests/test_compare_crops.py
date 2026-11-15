"""Compare Crops: truthful data mapping, selection and retained navigation."""
from dataclasses import replace
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from components.crop_comparison import PLANS, resolve_plans, outcome_for, selected_outcomes, yield_interval
from components.compare_markup import plan_markup
from utils.data_sources import load_rotation_scenarios
from utils.types import RotationScenario

ROOT=Path(__file__).resolve().parents[1]

class CompareCropsTests(TestCase):
    def setUp(self):
        outcome_for.clear()

    def app(self):
        at=_legacy_app_from_file(str(ROOT/'streamlit_app.py'),default_timeout=25).run()
        at.button(key='mobile_nav_rotations').click().run()
        self.assertFalse(at.exception)
        return at

    def test_catalog_never_substitutes_beans_for_soy_and_supports_future_real_ids(self):
        plans=resolve_plans(load_rotation_scenarios())
        self.assertEqual(plans['continuous'].id,'maiz-continuo')
        self.assertIsNone(plans['maize-soy']);self.assertIsNone(plans['cover'])
        future=[RotationScenario('team-soy','Team supplied',('Corn','Soybeans','Corn')),
                RotationScenario('team-cover','Team supplied',('Maize','Cover Crop','Soybean','Cover Crop'))]
        mapped=resolve_plans(future)
        self.assertEqual(mapped['maize-soy'].id,'team-soy')
        self.assertEqual(mapped['cover'].id,'team-cover')

    def test_select_climate_plan_continue_and_return_preserve_context(self):
        at=self.app()
        self.assertTrue(at.button(key='continue_rotations').disabled)
        self.assertEqual(at.session_state['selected_climate_id'],'normal')
        at.segmented_control(key='compare_weather_mobile').set_value('dry').run()
        self.assertEqual(at.session_state['selected_climate_id'],'dry')
        at.button(key='weather_normal').click().run()
        at.button(key='select_continuous').click().run()
        self.assertEqual(at.session_state['selected_plan_id'],'maiz-continuo')
        at.button(key='weather_dry').click().run()
        self.assertEqual(at.session_state['selected_plan_id'],'maiz-continuo')
        self.assertEqual(at.session_state['selected_climate_id'],'dry')
        self.assertFalse(at.button(key='continue_rotations').disabled)
        at.button(key='continue_rotations').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['page_key'],'recommendations')
        self.assertEqual(at.session_state['comparison_context']['climate_id'],'dry')
        at.button(key='mobile_nav_rotations').click().run()
        self.assertEqual(at.session_state['selected_plan_id'],'maiz-continuo')
        self.assertEqual(at.session_state['selected_climate_id'],'dry')
        at.selectbox(key='fs_plot_select').select('lote-sur').run()
        self.assertIsNone(at.session_state['selected_plan_id'])
        self.assertEqual(at.session_state['selected_plot_id'],'lote-sur')
        self.assertTrue(at.button(key='continue_rotations').disabled)

    def test_pending_plans_are_selectable_without_fabricating_model_ids(self):
        at=self.app()
        for key in ['maize-soy','cover']:
            at.button(key=f'select_{key}').click().run()
            self.assertEqual(at.session_state['selected_plan_key'],key)
            self.assertIsNone(at.session_state['selected_plan_id'])
            self.assertTrue(at.button(key='continue_rotations').disabled)
            self.assertFalse(at.exception)

    def test_wet_spring_is_unavailable_and_not_zero_or_seasonal_rainfall_proxy(self):
        plans=resolve_plans(load_rotation_scenarios())
        with patch('components.crop_comparison.predict_scenario_outcome') as predictor:
            wet=selected_outcomes('lote-sur','wet',plans)
            predictor.assert_not_called()
        self.assertTrue(all(out is None for out in wet.values()))
        at=self.app()
        at.button(key='select_continuous').click().run()
        at.button(key='weather_wet').click().run()
        self.assertTrue(at.button(key='continue_rotations').disabled)
        self.assertEqual(at.session_state['selected_plan_id'],'maiz-continuo')
        self.assertTrue(any('Wet-spring outcomes are not available' in x.value for x in at.info))
        at.button(key='weather_normal').click().run()
        self.assertFalse(at.button(key='continue_rotations').disabled)

    def test_results_change_with_inputs_and_missing_or_mismatched_results_fail_closed(self):
        plans=resolve_plans(load_rotation_scenarios())
        normal=selected_outcomes('lote-norte','normal',plans)['continuous']
        dry=selected_outcomes('lote-norte','dry',plans)['continuous']
        self.assertNotEqual(normal.expected_yield_t_per_ha,dry.expected_yield_t_per_ha)
        self.assertEqual(normal.plot_id,'lote-norte')
        outcome_for.clear()
        with patch('components.crop_comparison.predict_scenario_outcome',return_value=replace(normal,plot_id='other')):
            self.assertIsNone(outcome_for('lote-norte','maiz-continuo',0,0))
        outcome_for.clear()
        with patch('components.crop_comparison.predict_scenario_outcome',side_effect=RuntimeError('offline')):
            at=self.app()
            at.button(key='select_continuous').click().run()
            self.assertTrue(at.button(key='continue_rotations').disabled)
            self.assertFalse(at.exception)

    def test_cards_escape_external_text_and_keep_actual_units_and_bounds(self):
        out=outcome_for('lote-norte','maiz-continuo',0,0)
        scenario=RotationScenario('id','<script>bad</script>',('<script>bad</script>',))
        html=plan_markup(PLANS[0],scenario,out,True,(0,10))
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('USD/ha',html);self.assertIn('t/ha',html)
        self.assertIn('not soil loss in tonnes',html)
        self.assertIn('statistical coverage not validated',html)
        mixed=plan_markup(PLANS[1],scenario,out,True,(0,10))
        self.assertNotIn('Supplied simulated yield range',mixed)
        self.assertIn('Per-crop yields and comparison method pending',mixed)
        self.assertEqual(yield_interval(replace(out,yield_ci_low=99)),None)
        self.assertEqual(yield_interval(replace(out,yield_ci_high=float('nan'))),None)
        for image in (ROOT/'static'/'compare').glob('*.svg'):
            self.assertLess(image.stat().st_size,2500)


def _legacy_app_from_file(*args,**kwargs):
    app=AppTest.from_file(*args,**kwargs)
    app.session_state["data_mode"]="legacy"
    return app
