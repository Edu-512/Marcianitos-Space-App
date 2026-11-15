"""My Field acceptance tests: shared state, no invented records, retained tools."""
from dataclasses import replace
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from components.field_overview import number
from utils.data_sources import load_plots, load_satellite_snapshot

ROOT=Path(__file__).resolve().parents[1]

class MyFieldTests(TestCase):
    def app(self):
        at=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
        at.button(key='mobile_nav_home').click().run()
        self.assertFalse(at.exception)
        return at

    def test_sections_selection_and_continuation(self):
        at=self.app()
        plots={p.id:p for p in load_plots()}
        self.assertEqual([x.value for x in at.main.subheader],[plots['806'].name,'What is your soil like?','Crop history','Things to consider','More about this field'])
        at.selectbox(key='fs_plot_select').select('467').run()
        self.assertEqual(at.main.subheader[0].value,plots['467'].name)
        self.assertEqual(at.main.metric[0].value,f"{plots['467'].area_hectares:.1f} ha")
        snapshot=load_satellite_snapshot('467')
        moisture=next(x for x in at.main.metric if x.label=='Soil moisture')
        self.assertEqual(moisture.value,number(snapshot.soil_moisture_pct,1,'%'))
        self.assertTrue(any('No yearly crop records' in x.value for x in at.info))
        self.assertTrue(any('not a surveyed property line' in x.value for x in at.markdown))
        at.button(key='continue_home').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['page_key'],'rotations')
        self.assertEqual(at.session_state['selected_plot_id'],'467')

    def test_missing_data_and_mismatched_plot_are_not_zero_or_diagnoses(self):
        with patch('app_pages.home.load_satellite_snapshot',side_effect=RuntimeError('unavailable')),patch('app_pages.home.compute_plot_risk',return_value=None):
            at=self.app()
            self.assertTrue(all(x.value=='Not available' for x in at.main.metric if x.label!='Recorded area'))
            self.assertTrue(any('No risk level has been assumed' in x.value for x in at.info))
        other=replace(load_satellite_snapshot('467'),plot_id='other')
        with patch('app_pages.home.load_satellite_snapshot',return_value=other):
            at=self.app()
            self.assertEqual(next(x for x in at.main.metric if x.label=='Soil moisture').value,'Not available')
        self.assertEqual(number(0),'0.00')
        for missing in [None,float('nan'),float('inf')]:self.assertEqual(number(missing),'Not available')

    def test_ground_observations_remain_per_plot(self):
        at=self.app()
        at.text_area(key='obs_notes_806').set_value('Test soil observation').run()
        at.button(key='obs_save_806').click().run()
        self.assertEqual(at.session_state['local_ground_notes']['806'][0]['Notes'],'Test soil observation')
        at.selectbox(key='fs_plot_select').select('467').run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.session_state['local_ground_notes'].get('467',[])),0)
        self.assertEqual(at.session_state['local_ground_notes']['806'][0]['Notes'],'Test soil observation')

    def test_future_crop_history_preserves_missing_and_no_crop_without_inference(self):
        at=AppTest.from_string('''
from components.field_overview import crop_history, planting_event
crop_history([{"year":2024,"crop":"Maize","nature":"Simulated"},{"year":2022,"crop":None},{"year":2023,"crop":""}],source="Test fixture")
planting_event()
''').run()
        self.assertFalse(at.exception)
        text=' '.join(x.value for x in at.markdown)
        self.assertIn('No information',text)
        self.assertIn('No crop recorded',text)
        self.assertNotIn('2019',text)
        self.assertTrue(any('no pattern inferred' in x.value for x in at.markdown))
