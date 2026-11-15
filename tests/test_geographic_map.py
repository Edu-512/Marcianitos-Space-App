import json, math
from unittest import TestCase
from unittest.mock import patch

from components.geographic_map import bounds, load_geography, map_features, positions, selection_id, valid_camera, DATA
from components.parcel_map import build_rows, color_rows, crop_categories
from utils.data_sources import load_plots
from app_pages import map_view


def inside(point, ring):
    x,y=point; result=False
    for a,b in zip(ring,ring[1:]):
        if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]: result=not result
    return result


class GeographyTests(TestCase):
    def test_all_demo_vertices_inside_official_butler_boundary_and_closed(self):
        county=json.loads((DATA/'butler-county.json').read_text())['features'][0]
        self.assertEqual(county['properties']['GEOID'],'19023')
        rings=county['geometry']['coordinates']
        fields=load_geography()['features']
        self.assertEqual(len(fields),6)
        self.assertEqual(len({f['id'] for f in fields}),6)
        for f in fields:
            ring=f['geometry']['coordinates'][0]
            self.assertEqual(ring[0],ring[-1])
            self.assertGreaterEqual(len(set(tuple(p) for p in ring)),4)
            for point in positions(f['geometry']):
                self.assertTrue(inside(point,rings[0]))
                self.assertFalse(any(inside(point,hole) for hole in rings[1:]))
            self.assertEqual(f['properties']['kind'],'simulated')
            self.assertIsNone(f['properties']['period'])

    def test_demo_scale_matches_scenario_without_modifying_model_coordinates(self):
        plots={p.id:p for p in load_plots()}
        for f in load_geography()['features']:
            ring=f['geometry']['coordinates'][0]; west,south=ring[0];east,north=ring[2]
            lat=(south+north)/2
            width=(east-west)*111320*math.cos(math.radians(lat));height=(north-south)*111320
            self.assertAlmostEqual(width*height/10000,plots[f['id']].area_hectares,places=5)
            self.assertLess(max(width,height),1000)
            self.assertLess(plots[f['id']].lat,30) # model fixture remains untouched

    def test_geojson_preserves_geometry_and_only_explicit_ids_join(self):
        plots=load_plots();frame=color_rows(build_rows(plots,2026,lambda *_:{}),'Parcelas',crop_categories(plots))
        result=map_features(frame,'lote-sur')
        for original,rendered in zip(load_geography()['features'],result['features']):
            self.assertEqual(original['geometry'],rendered['geometry'])
        self.assertEqual([f['id'] for f in result['features'] if f['properties']['selected']],['lote-sur'])
        json.dumps(result,allow_nan=False)
        self.assertEqual(bounds({'features':[]}),[[-92.85,42.69],[-92.73,42.77]])

    def test_selection_and_camera_validate_untrusted_events(self):
        valid=tuple(p.id for p in load_plots())
        good={'plot_id':'lote-sur','reference_id':'demo-19023-lote-sur'}
        self.assertEqual(selection_id(good,valid),'lote-sur')
        self.assertIsNone(selection_id({**good,'reference_id':'real-field'},valid))
        self.assertIsNone(selection_id({'plot_id':[]},valid))
        self.assertIsNone(valid_camera({'center':[float('nan'),42],'zoom':12}))
        self.assertIsNone(valid_camera({'center':[-92,100],'zoom':12}))
        camera={'center':[-92.791234,42.731234],'zoom':14.123456}
        self.assertEqual(valid_camera(camera),camera)
        class State(dict):
            def __setattr__(self,k,v):self[k]=v
        state=State({map_view.MAP_KEY:{'camera':camera,'selected':good}})
        with patch.object(map_view.st,'session_state',state):
            map_view._on_camera();map_view._on_map_select(valid)
        self.assertEqual(state['explore_camera'],camera)
        self.assertEqual(state['selected_plot_id'],'lote-sur')
