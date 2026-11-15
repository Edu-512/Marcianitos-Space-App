"""Explore parcels: frontend data, state callbacks and existing-page integration."""
import json
from dataclasses import replace
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from components.parcel_map import build_rows, color_rows, crop_categories, make_deck, plot_id_from_selection
from utils.data_sources import load_plots
from app_pages import map_view


class ParcelMapTests(TestCase):
    def setUp(self):
        self.plots = load_plots()

    def test_supplied_boundaries_are_converted_without_inventing_geometry(self):
        frame = build_rows(self.plots, 2026, lambda _id, _year: {})
        original = self.plots[0]
        self.assertEqual(frame.iloc[0]['polygon_geo'], [[lon,lat] for lat,lon in original.polygon])
        self.assertEqual(frame.iloc[0]['area_hectares'], original.area_hectares)
        point = replace(original, polygon=())
        row = build_rows([point], 2026, lambda _id, _year: {}).iloc[0]
        self.assertEqual(row['polygon_geo'], [])
        self.assertTrue(row['mappable'])

    def test_missing_indicators_do_not_drop_parcels_or_emit_invalid_json(self):
        def fail(_id, _year):
            raise RuntimeError('source unavailable')
        frame = build_rows(self.plots, 2026, fail)
        self.assertEqual(list(frame['id']), [p.id for p in self.plots])
        colored = color_rows(frame, 'Vegetación', crop_categories(self.plots))
        deck = make_deck(colored, self.plots[0].id, False)
        # parse_constant rejects NaN/Infinity just as the browser JSON parser does.
        json.loads(deck.to_json(), parse_constant=lambda value: self.fail(f'Invalid JSON constant: {value}'))

    def test_categories_come_only_from_registered_crops(self):
        self.assertEqual(set(crop_categories(self.plots)), {p.current_crop for p in self.plots})
        unknown = replace(self.plots[0], current_crop='')
        self.assertEqual(set(crop_categories([unknown])), {'Sin cultivo registrado'})

    def test_selection_validates_layer_and_plot_identity(self):
        valid = tuple(p.id for p in self.plots)
        state = {'selection':{'objects':{'parcelas':[{'id':'lote-sur'}]}}}
        self.assertEqual(plot_id_from_selection(state, valid), 'lote-sur')
        self.assertIsNone(plot_id_from_selection({'selection':{'objects':{'parcelas':[{'id':'unknown'}]}}}, valid))
        self.assertIsNone(plot_id_from_selection({'selection':{'objects':{'unrelated':[{'id':'lote-sur'}]}}}, valid))
        self.assertIsNone(plot_id_from_selection({'selection':{'objects':{'parcelas':None}}}, valid))
        self.assertIsNone(plot_id_from_selection(None, valid))

    def test_selected_outline_and_initial_view_are_stable(self):
        frame = build_rows(self.plots, 2026, lambda _id, _year: {})
        colored = color_rows(frame, 'Cultivos', crop_categories(self.plots))
        first = json.loads(make_deck(colored, 'lote-sur', False).to_json())
        second = json.loads(make_deck(colored, 'lote-este', True).to_json())
        self.assertEqual(first['initialViewState'], second['initialViewState'])
        outline = next(layer for layer in first['layers'] if layer['id']=='seleccion-borde')
        self.assertEqual([row['id'] for row in outline['data']], ['lote-sur'])
        self.assertTrue(all(layer.get('id') for layer in first['layers']))
        self.assertFalse(first['views'][0]['controller']['scrollZoom'])

    def test_map_callback_updates_the_shared_id_without_writing_mounted_selectors(self):
        class State(dict):
            def __setattr__(self, key, value): self[key] = value
        state = State({map_view.MAP_KEY:{'selected':{'plot_id':'lote-este','reference_id':'demo-19023-lote-este'}}})
        with patch.object(map_view.st, 'session_state', state):
            map_view._on_map_select(tuple(p.id for p in self.plots))
        self.assertEqual(state['selected_plot_id'], 'lote-este')
        self.assertNotIn('fs_plot_select', state)


class ExplorePageTests(TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'streamlit_app.py'), default_timeout=20)

    def test_screen_picker_and_sidebar_stay_synchronized_and_continue(self):
        at = self.app().run()
        self.assertFalse(at.exception)
        at.selectbox(key='explore_plot_select').select('lote-sur').run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['selected_plot_id'], 'lote-sur')
        self.assertEqual(at.selectbox(key='fs_plot_select').value, 'lote-sur')
        self.assertEqual(at.main.metric[0].value, '8 ha')
        at.selectbox(key='fs_plot_select').select('lote-este').run()
        self.assertEqual(at.selectbox(key='explore_plot_select').value, 'lote-este')
        self.assertEqual(at.main.metric[0].value, '15 ha')
        at.button(key='continue_map_view').click().run()
        self.assertEqual(at.session_state['page_key'], 'home')
        self.assertEqual(at.session_state['selected_plot_id'], 'lote-este')
        at.button(key='mobile_nav_map_view').click().run()
        self.assertEqual(at.selectbox(key='explore_plot_select').value, 'lote-este')

    def test_all_existing_layers_and_history_remain_available(self):
        at = self.app().run()
        options = at.selectbox(key='explore_layer').options
        self.assertEqual(len(options), 8)
        at.segmented_control(key='explore_basemap').set_value('Satelital').run()
        at.selectbox(key='explore_layer').select('Humedad del suelo').run()
        at.select_slider(key='map_year').set_value(2021).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.dataframe[0].value), 6)
        self.assertTrue(any('simulada' in item.value for item in at.caption))
