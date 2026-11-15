"""Model integration acceptance without altering or rerunning the team generator."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import json

from streamlit.testing.v1 import AppTest
from utils import field_model as fm
from components import field_map

ROOT=Path(__file__).resolve().parents[1]

class ResearchModelTests(TestCase):
    def app(self):
        return AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=25).run()

    def test_source_export_is_the_full_167_by_three_by_three_catalog(self):
        raw=json.loads((ROOT/'model/datos_ui/resultado_todas.json').read_text(encoding='utf-8'))
        self.assertEqual(fm.catalog(),raw)
        self.assertEqual(len(fm.records()),167)
        self.assertEqual(len(fm.CLIMATES),3);self.assertEqual(len(fm.PLANS),3)
        for pid,row in fm.records().items():
            for climate,data in row['escenarios'].items():
                self.assertEqual(set(p['id'] for p in data['planes']),set(fm.PLANS))
                for out in data['planes']:self.assertEqual(fm.result(pid,climate,out['id']),out)
        self.assertEqual(fm.result('806','seco_caluroso','maiz_soya')['rendimiento_maiz_bu_acre']['p50'],218.0)
        json.dumps(fm.catalog(),allow_nan=False)
        with self.assertRaises(ValueError):fm.result('unknown','normal','maiz_soya')

    def test_default_flow_uses_model_ids_and_preserves_plan_and_climate(self):
        at=self.app()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['selected_plot_id'],'806')
        at.button(key='mobile_nav_home').click().run()
        self.assertFalse(at.exception)
        at.button(key='continue_home').click().run()
        for plan in fm.PLANS:
            at.button(key='model_select_'+plan).click().run()
            self.assertEqual(at.session_state['selected_plan_id'],plan)
        at.segmented_control(key='research_climate').set_value('humedo_primavera').run()
        self.assertEqual(at.session_state['selected_climate_id'],'humedo_primavera')
        out=fm.result('806','humedo_primavera',at.session_state['selected_plan_id'])
        self.assertEqual(at.session_state['comparison_context']['outcome'],out)
        at.button(key='continue_rotations').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['page_key'],'recommendations')
        at.button(key='continue_recommendations').click().run()
        self.assertEqual(at.session_state['selected_climate_id'],'humedo_primavera')

    def test_mobile_and_sidebar_selectors_share_state_without_stale_results(self):
        at=self.app()
        at.selectbox(key='fs_mobile_plot_select').select('467').run()
        self.assertEqual(at.selectbox(key='fs_plot_select').value,'467')
        at.button(key='mobile_nav_rotations').click().run()
        at.button(key='model_select_maiz_continuo').click().run()
        at.selectbox(key='fs_plot_select').select('1413').run()
        self.assertEqual(at.selectbox(key='fs_mobile_plot_select').value,'1413')
        self.assertIsNone(at.session_state['selected_plan_id'])
        self.assertTrue(at.button(key='continue_rotations').disabled)
        self.assertFalse(any('Case study:' in c.value for c in at.caption))

    def test_map_actions_validate_ids_and_update_canonical_context(self):
        class State(dict):
            def __getattr__(self,key):return self[key]
            def __setattr__(self,key,value):self[key]=value
        state=State(selected_plot_id='806',selected_climate_id='normal',selected_plan_id=None)
        state[field_map.KEY]={'action':{'plot_id':'467','climate_id':'seco_caluroso','plan_id':'maiz_soya','action':'plan'}}
        with patch.object(field_map.st,'session_state',state):field_map._action()
        self.assertEqual(state['selected_plot_id'],'467')
        self.assertEqual(state['comparison_context']['outcome'],fm.result('467','seco_caluroso','maiz_soya'))
        state[field_map.KEY]={'action':{'plot_id':'invalid','climate_id':'normal','plan_id':'maiz_soya'}}
        with patch.object(field_map.st,'session_state',state):field_map._action()
        self.assertEqual(state['selected_plot_id'],'467')
        features=fm.map_features()['features']
        self.assertEqual(len(features),167)
        self.assertTrue(all(f['properties']['geometry_nature']=='cdl_derived' for f in features))
        for feature in features:
            geom=feature['geometry']
            polygons=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
            for polygon in polygons:
                for ring in polygon:self.assertEqual(ring[0],ring[-1])

    def test_checklist_is_context_scoped_and_direct_entry_does_not_select_a_plan(self):
        at=self.app()
        at.button(key='mobile_nav_recommendations').click().run()
        self.assertEqual(len(at.checkbox),0)
        at.button(key='change_action_plan').click().run()
        at.button(key='model_select_maiz_soya').click().run()
        at.button(key='continue_rotations').click().run()
        check=next(x for x in at.checkbox if x.key.startswith('model_review_'))
        check.check().run()
        at.button(key='change_action_plan').click().run()
        at.segmented_control(key='research_climate').set_value('seco_caluroso').run()
        at.button(key='continue_rotations').click().run()
        self.assertFalse(any(c.value for c in at.checkbox))
        self.assertFalse(at.exception)

    def test_chat_tools_return_model_units_not_legacy_random_values(self):
        from utils import ai_chat
        with patch.object(ai_chat.fm,'enabled',return_value=True):
            with patch.object(ai_chat,'load_satellite_snapshot',side_effect=AssertionError('No legacy values')):
                self.assertEqual(ai_chat.tool_get_plot_status('806')['profile']['id'],806)
            output=ai_chat.tool_predict_scenario_outcome('806','maiz_soya',climate_id='humedo_primavera')
            self.assertEqual(output['outcome'],fm.result('806','humedo_primavera','maiz_soya'))
            self.assertIn('error',ai_chat.tool_predict_scenario_outcome('806','maiz_soya',rainfall_shift_pct=20))
            self.assertNotIn('price_usd_per_tonne',ai_chat.tool_get_crop_price('Maize'))

    def test_geographic_geometry_preserves_all_ids_parts_and_holes(self):
        raw=json.loads((ROOT/'model/datos_ui/parcelas_todas.geojson').read_text(encoding='utf-8'))
        features={str(f['properties']['id']):f for f in raw['features']}
        self.assertEqual(set(features),set(fm.records()))
        drawn={f['id']:f for f in fm.map_features()['features']}
        self.assertEqual(sum(f['geometry']['type']=='MultiPolygon' for f in drawn.values()),25)
        holes=0
        for pid,feature in features.items():
            self.assertEqual(drawn[pid]['geometry'],feature['geometry'])
            geom=feature['geometry']
            polygons=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
            holes+=sum(len(p)-1 for p in polygons)
            lat,lon=fm.plot_position(pid)
            self.assertTrue(42.5<lat<43 and -93.1<lon<-92.5)
        self.assertEqual(holes,275)

    def test_latest_cover_cost_and_planting_risk_are_not_old_demo_outputs(self):
        base=fm.result('806','normal','maiz_soya')
        cover=fm.result('806','normal','maiz_soya_cobertura')
        self.assertEqual(base['economia']['margen_usd_acre']['p50'],20)
        self.assertEqual(cover['economia']['margen_usd_acre']['p50'],-18)
        self.assertEqual(base['riesgo']['prob_no_poder_sembrar_pct'],0)
        self.assertEqual(fm.result('1737','normal','maiz_soya')['riesgo']['prob_no_poder_sembrar_pct'],6.32)
        cover['economia']['margen_usd_acre']['p50']=999999
        self.assertEqual(fm.result('806','normal','maiz_soya_cobertura')['economia']['margen_usd_acre']['p50'],-18)

    def test_non_showcase_parcel_flows_to_recommendations(self):
        at=self.app()
        pid=next(pid for pid in fm.records() if int(pid) not in fm.PROFILE_NAMES)
        at.selectbox(key='fs_mobile_plot_select').select(pid).run()
        at.button(key='mobile_nav_rotations').click().run()
        at.button(key='model_select_maiz_soya_cobertura').click().run()
        at.button(key='continue_rotations').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['selected_plot_id'],pid)
        self.assertEqual(at.session_state['comparison_context']['outcome'],fm.result(pid,'normal','maiz_soya_cobertura'))
    def test_previous_model_delivery_context_is_invalidated(self):
        at=self.app()
        at.button(key='mobile_nav_rotations').click().run()
        at.button(key='model_select_maiz_soya').click().run()
        ctx=dict(at.session_state['comparison_context'])
        ctx['model_revision']='previous-delivery'
        at.session_state['comparison_context']=ctx
        at.run()
        self.assertFalse(at.exception)
        self.assertIsNone(at.session_state['selected_plan_id'])
        self.assertTrue(at.button(key='continue_rotations').disabled)
