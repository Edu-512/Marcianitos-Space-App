"""Nationwide USDA Crop Sequence Boundaries layer for the research map.

The browser streams only the visible vector tiles from a public PMTiles
archive with HTTP range requests; nothing passes through Streamlit's memory.

Verified 2026-11-15 against the official GeoParquet in the same repository:
the tile attribute ``cdl`` equals the ``CDL2025`` column (the 2025 crop), and
``CSBYEARS`` is ``1825`` (boundaries derived from 2018-2025 satellite data).
"""
from __future__ import annotations

#: Public, CORS-enabled archive (4.9 GB, zoom 0-14). No bucket of our own needed.
PMTILES_URL = "https://data.source.coop/ftw/usda-csb/csb_2025.pmtiles"
SOURCE_LAYER = "fields"
CROP_YEAR = 2025
ATTRIBUTION = ("USDA NASS Crop Sequence Boundaries 2018–2025 · Cropland Data Layer 2025 "
               "· via Source Cooperative / Fields of the World")
#: Leaflet maxZoom is 19; MapLibre overzooms the z14 tiles, so no gaps when zooming in.
CONUS_BOUNDS = [[24.4, -125.0], [49.5, -66.9]]
#: Served by Streamlit static serving (``[server] enableStaticServing = true``).
VENDOR = {
    "maplibre_js": "./app/static/national_map/maplibre-gl-4.7.1.js",
    "maplibre_css": "./app/static/national_map/maplibre-gl-4.7.1.css",
    "pmtiles_js": "./app/static/national_map/pmtiles-3.2.1.js",
    "binding_js": "./app/static/national_map/leaflet-maplibre-gl-0.0.22.js",
}

#: Official USDA NASS Cropland Data Layer legend names. Codes not listed are
#: shown as "Cropland Data Layer code N" rather than guessed.
CDL_NAMES = {
    1: "Corn", 2: "Cotton", 3: "Rice", 4: "Sorghum", 5: "Soybeans", 6: "Sunflower",
    10: "Peanuts", 11: "Tobacco", 12: "Sweet corn", 13: "Popcorn or ornamental corn", 14: "Mint",
    21: "Barley", 22: "Durum wheat", 23: "Spring wheat", 24: "Winter wheat",
    25: "Other small grains", 26: "Double crop: winter wheat / soybeans", 27: "Rye", 28: "Oats",
    29: "Millet", 30: "Speltz", 31: "Canola", 32: "Flaxseed", 33: "Safflower", 34: "Rape seed",
    35: "Mustard", 36: "Alfalfa", 37: "Other hay (non-alfalfa)", 38: "Camelina", 39: "Buckwheat",
    41: "Sugar beets", 42: "Dry beans", 43: "Potatoes", 44: "Other crops", 45: "Sugarcane",
    46: "Sweet potatoes", 47: "Miscellaneous vegetables and fruits", 48: "Watermelons",
    49: "Onions", 50: "Cucumbers", 51: "Chickpeas", 52: "Lentils", 53: "Peas", 54: "Tomatoes",
    55: "Caneberries", 56: "Hops", 57: "Herbs", 58: "Clover / wildflowers", 59: "Sod / grass seed",
    60: "Switchgrass", 61: "Fallow / idle cropland", 66: "Cherries", 67: "Peaches", 68: "Apples",
    69: "Grapes", 70: "Christmas trees", 71: "Other tree crops", 72: "Citrus", 74: "Pecans",
    75: "Almonds", 76: "Walnuts", 77: "Pears", 92: "Aquaculture", 111: "Open water",
    121: "Developed / open space", 122: "Developed / low intensity",
    123: "Developed / medium intensity", 124: "Developed / high intensity", 131: "Barren",
    141: "Deciduous forest", 142: "Evergreen forest", 143: "Mixed forest", 152: "Shrubland",
    176: "Grassland / pasture", 190: "Woody wetlands", 195: "Herbaceous wetlands",
    204: "Pistachios", 205: "Triticale", 206: "Carrots", 207: "Asparagus", 208: "Garlic",
    209: "Cantaloupes", 210: "Prunes", 211: "Olives", 212: "Oranges", 213: "Honeydew melons",
    214: "Broccoli", 215: "Avocados", 216: "Peppers", 217: "Pomegranates", 218: "Nectarines",
    219: "Greens", 220: "Plums", 221: "Strawberries", 222: "Squash", 223: "Apricots",
    224: "Vetch", 225: "Double crop: winter wheat / corn", 226: "Double crop: oats / corn",
    227: "Lettuce", 228: "Double crop: triticale / corn", 229: "Pumpkins",
    236: "Double crop: winter wheat / sorghum", 237: "Double crop: barley / corn",
    238: "Double crop: winter wheat / cotton", 239: "Double crop: soybeans / cotton",
    240: "Double crop: soybeans / oats", 241: "Double crop: corn / soybeans",
    242: "Blueberries", 243: "Cabbage", 244: "Cauliflower", 245: "Celery", 246: "Radishes",
    247: "Turnips", 248: "Eggplants", 249: "Gourds", 250: "Cranberries",
    254: "Double crop: barley / soybeans",
}

#: Colour groups for the map legend (label, fill colour, CDL codes).
CROP_CLASSES = [
    ("Corn", "#e0b400", [1, 12, 13]),
    ("Soybeans", "#2f8f4e", [5]),
    ("Wheat and small grains", "#b98547", [21, 22, 23, 24, 25, 27, 28, 29, 30, 205]),
    ("Double crop", "#8a5fb0", [26, 225, 226, 228, 236, 237, 238, 239, 240, 241, 254]),
    ("Hay and pasture", "#9cbf7a", [36, 37, 58, 59, 60, 176]),
]
OTHER_CLASS = ("Other crops and land", "#8c8c8c")


def fill_color_expression() -> list:
    """MapLibre ``match`` expression colouring fields by their 2025 crop group."""
    expression: list = ["match", ["to-number", ["get", "cdl"]]]
    for _label, color, codes in CROP_CLASSES:
        expression += [codes, color]
    return expression + [OTHER_CLASS[1]]


def config() -> dict:
    """Everything the browser needs; plain JSON for the CCv2 component."""
    return {
        "url": PMTILES_URL,
        "source_layer": SOURCE_LAYER,
        "crop_year": CROP_YEAR,
        "attribution": ATTRIBUTION,
        "bounds": CONUS_BOUNDS,
        "vendor": VENDOR,
        "fill_color": fill_color_expression(),
        "legend": [[label, color] for label, color, _codes in CROP_CLASSES] + [list(OTHER_CLASS)],
        "crop_names": {str(code): name for code, name in CDL_NAMES.items()},
    }
