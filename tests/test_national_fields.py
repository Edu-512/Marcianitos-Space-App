import json
from pathlib import Path
from unittest import TestCase

from components import national_fields as nf

ROOT = Path(__file__).resolve().parents[1]


class NationalFieldsTests(TestCase):
    def test_public_archive_and_layer_are_the_verified_ones(self):
        self.assertEqual(nf.PMTILES_URL, "https://data.source.coop/ftw/usda-csb/csb_2025.pmtiles")
        self.assertEqual(nf.SOURCE_LAYER, "fields")
        self.assertEqual(nf.CROP_YEAR, 2025)

    def test_vendored_libraries_exist_where_static_serving_publishes_them(self):
        config = (ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
        self.assertIn("enableStaticServing = true", config)
        for url in nf.VENDOR.values():
            self.assertTrue(url.startswith("./app/static/"), url)
            self.assertTrue((ROOT / "static" / url.removeprefix("./app/static/")).is_file(), url)
        for name in ["LICENSE-maplibre-gl.txt", "LICENSE-maplibre-gl-leaflet.txt", "LICENSE-pmtiles.txt"]:
            self.assertTrue((ROOT / "static/national_map" / name).is_file(), name)

    def test_colour_groups_use_named_cdl_codes_and_do_not_overlap(self):
        seen = set()
        for label, color, codes in nf.CROP_CLASSES:
            self.assertRegex(color, r"^#[0-9a-f]{6}$")
            for code in codes:
                self.assertIn(code, nf.CDL_NAMES, f"{label}: {code}")
                self.assertNotIn(code, seen)
                seen.add(code)
        expression = nf.fill_color_expression()
        self.assertEqual(expression[:2], ["match", ["to-number", ["get", "cdl"]]])
        self.assertEqual(len(expression), 2 + 2 * len(nf.CROP_CLASSES) + 1)
        self.assertEqual(expression[-1], nf.OTHER_CLASS[1])

    def test_config_is_plain_json_with_a_legend_entry_per_group(self):
        config = json.loads(json.dumps(nf.config()))
        self.assertEqual(len(config["legend"]), len(nf.CROP_CLASSES) + 1)
        self.assertEqual(config["crop_names"]["1"], "Corn")
        self.assertEqual(config["crop_names"]["5"], "Soybeans")
        (south, west), (north, east) = config["bounds"]
        self.assertTrue(south < north and west < east)
