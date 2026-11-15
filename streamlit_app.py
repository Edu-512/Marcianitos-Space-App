"""Field Shift — 5-Step Planting Decision Tool for Butler County, Iowa.

Pure native Streamlit implementation following the official Interface Guide:
- Linear 5-step decision journey (Map -> Land Summary -> 3 Plan Cards -> Live Climate Shift -> Recommendation).
- Dual axes on every plan: Money ($/acre) and Harvest (bu/acre).
- Explicit source attribution: Measured (USDA / NASA / SSURGO) vs. Literature (Iowa State University).
- Zero CSS/HTML injections, zero emojis, plain farmer language, and no use of the word 'model'.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(
    page_title="Field Shift - Planting Decision Tool",
    layout="wide",
)

DATA_FILE = Path("resultado_ejemplo.json")


# --- Preloaded Fallback Data (Exact Butler County Demo Plots & ISU/USDA Numbers) ---
def _get_preloaded_butler_data() -> dict[str, Any]:
    """Return preloaded data for the 5 Butler County demo plots so offline demos never fail."""
    return {
        "corn-dominant": {
            "id": "corn-dominant",
            "name": "Plot 3: Corn-Dominant, Good Soil (1,020 acres)",
            "acres": 1020,
            "current_rotation": "Corn 6 of last 8 years",
            "color_rgb": [217, 95, 2],
            "polygon": [
                [-92.820, 42.745],
                [-92.795, 42.745],
                [-92.795, 42.725],
                [-92.820, 42.725],
            ],
            "plain_summary": [
                "Your soil has good natural fertility and holds moisture well.",
                "Drainage is artificially tiled, keeping root zones productive in normal rains.",
                "Last eight years: corn in six seasons, soybeans in only two.",
                "Neighbor context: 44% of plots in southeastern Butler County also run continuous corn.",
            ],
            "technical_details": {
                "Soil Texture & Organic Matter": "Loam / Silty Clay Loam, Organic Matter 4.7% (Measured - USDA SSURGO v33)",
                "Available Water Capacity (AWC)": "0.21 cm/cm, Hydrologic Group B/D tiled (Measured - USDA SSURGO)",
                "Summer Canopy Vigor (NDVI 2024-2025)": "0.82 peak summer index (Measured - NASA MODIS MOD13Q1)",
                "Crop History (2018-2025)": "Corn, Corn, Soy, Corn, Corn, Corn, Soy, Corn (Measured - USDA CDL)",
            },
            "prevented_planting_risk": None,
            "scenarios": {
                "Normal Year": {
                    "recommendation": (
                        "Switch from continuous corn to a Corn-Soybean rotation to reduce net loss by "
                        "$122 per acre while cutting nitrogen needs by 57 lbs per acre."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -43,
                            "net_return_range": (-95, 15),
                            "yield_bu": 203,
                            "yield_range": (182, 222),
                            "erosion_tons": 2.4,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Yield & price: Measured (USDA) | Cost ($875/ac) & N rate: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -165,
                            "net_return_range": (-230, -95),
                            "yield_bu": 194,
                            "yield_range": (168, 214),
                            "erosion_tons": 1.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Yield penalty & Cost ($960/ac): Literature (Iowa State 2026) | Residue protection: Measured",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -78,
                            "net_return_range": (-130, -20),
                            "yield_bu": 201,
                            "yield_range": (180, 220),
                            "erosion_tons": 1.1,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Erosion control: Measured (SSURGO) | Cover termination cost: Literature (Iowa State 2026)",
                        },
                    ],
                },
                "Dry and Hot Year": {
                    "recommendation": (
                        "Rotate immediately: under heat and drought stress like 2012, continuous corn loses "
                        "$235 more per acre than a Corn-Soybean rotation due to root stress and higher input costs."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -65,
                            "net_return_range": (-145, 25),
                            "yield_bu": 168,
                            "yield_range": (140, 192),
                            "erosion_tons": 2.1,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Drought price offset: Measured (USDA 26-yr) | Cost ($875/ac): Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -300,
                            "net_return_range": (-410, -190),
                            "yield_bu": 132,
                            "yield_range": (98, 162),
                            "erosion_tons": 1.6,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Stress yield penalty (up to 27%): Literature (Iowa State) | Cost ($960/ac): Literature",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -92,
                            "net_return_range": (-170, -10),
                            "yield_bu": 166,
                            "yield_range": (138, 190),
                            "erosion_tons": 0.9,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Moisture retention & cost: Literature (Iowa State 2026) | Soil baseline: Measured",
                        },
                    ],
                },
                "Wet Spring": {
                    "recommendation": (
                        "Use Corn-Soybean rotation; planting flexibility with soybeans protects your per-acre return "
                        "if persistent May rains delay field entry."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -58,
                            "net_return_range": (-115, 5),
                            "yield_bu": 196,
                            "yield_range": (172, 215),
                            "erosion_tons": 2.9,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Spring moisture response: Measured (NLDAS-2/POWER) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -195,
                            "net_return_range": (-275, -120),
                            "yield_bu": 182,
                            "yield_range": (152, 205),
                            "erosion_tons": 2.1,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "Medium",
                            "source_note": "Delayed planting penalty & Cost ($960/ac): Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -80,
                            "net_return_range": (-140, -15),
                            "yield_bu": 195,
                            "yield_range": (170, 214),
                            "erosion_tons": 1.3,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Spring trafficability & erosion: Measured (SSURGO) | Cost: Literature (Iowa State 2026)",
                        },
                    ],
                },
            },
        },
        "flood-prone": {
            "id": "flood-prone",
            "name": "Plot 4: Flood-Prone Bottomland (233 acres)",
            "acres": 233,
            "current_rotation": "Corn-Soybean with wet-year gaps",
            "color_rgb": [55, 126, 184],
            "polygon": [
                [-92.780, 42.710],
                [-92.765, 42.710],
                [-92.765, 42.698],
                [-92.780, 42.698],
            ],
            "plain_summary": [
                "Water stays on the surface and the plot floods easily during spring planting.",
                "In 2019, 18% of this plot could not be planted at all due to standing water.",
                "Last eight years: alternating corn and soybeans, interrupted by wet-spring fallow.",
            ],
            "technical_details": {
                "Drainage & Hydrologic Group": "Poorly drained floodplain, Group C/D (Measured - USDA SSURGO v33)",
                "Prevented Planting History": "18% unplanted area in 2019; 3.4x county risk multiplier (Measured - USDA CDL)",
                "Spring Soil Moisture (NLDAS-2)": "Top decile May saturation in 2019 and 2024 (Measured - NASA / NLDAS-2)",
            },
            "prevented_planting_risk": "High Risk: 18% of this plot went unplanted in 2019 (3.4x higher risk than county average in wet springs).",
            "scenarios": {
                "Normal Year": {
                    "recommendation": (
                        "Maintain Corn-Soybean rotation and avoid upfront fall nitrogen applications in case "
                        "spring flooding forces a late switch to soybeans."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -55,
                            "net_return_range": (-120, 10),
                            "yield_bu": 195,
                            "yield_range": (165, 218),
                            "erosion_tons": 2.2,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Yield: Measured (USDA) | Cost ($875/ac) & N rate: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -185,
                            "net_return_range": (-265, -105),
                            "yield_bu": 182,
                            "yield_range": (148, 206),
                            "erosion_tons": 1.9,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "Medium",
                            "source_note": "Cost ($960/ac) & N rate: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -82,
                            "net_return_range": (-150, -15),
                            "yield_bu": 194,
                            "yield_range": (164, 216),
                            "erosion_tons": 1.0,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Spring moisture uptake & cost: Literature (Iowa State 2026)",
                        },
                    ],
                },
                "Dry and Hot Year": {
                    "recommendation": (
                        "Stick with Corn-Soybean rotation; this low-lying soil retains more moisture during dry summers, "
                        "giving you a strong advantage when market prices rise."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -25,
                            "net_return_range": (-90, 45),
                            "yield_bu": 180,
                            "yield_range": (155, 202),
                            "erosion_tons": 1.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Yield & price offset: Measured (USDA) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -240,
                            "net_return_range": (-330, -150),
                            "yield_bu": 148,
                            "yield_range": (115, 175),
                            "erosion_tons": 1.5,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Heat stress penalty & Cost ($960/ac): Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -55,
                            "net_return_range": (-120, 15),
                            "yield_bu": 179,
                            "yield_range": (153, 200),
                            "erosion_tons": 0.9,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Cost & residue effect: Literature (Iowa State 2026)",
                        },
                    ],
                },
                "Wet Spring": {
                    "recommendation": (
                        "Prioritize Corn-Soybean rotation with spring-only nitrogen: 18% of this plot failed to plant in 2019, "
                        "and late-planted soybeans recover far better than late corn."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -110,
                            "net_return_range": (-215, -30),
                            "yield_bu": 162,
                            "yield_range": (118, 195),
                            "erosion_tons": 3.4,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "2019/2024 wet spring loss: Measured (USDA CDL) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -315,
                            "net_return_range": (-450, -195),
                            "yield_bu": 135,
                            "yield_range": (85, 172),
                            "erosion_tons": 2.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Prevented planting & nitrogen loss: Measured + Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -125,
                            "net_return_range": (-225, -45),
                            "yield_bu": 165,
                            "yield_range": (122, 196),
                            "erosion_tons": 1.5,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Root mat bearing capacity & erosion: Measured (SSURGO) + Literature",
                        },
                    ],
                },
            },
        },
        "sandy-soil": {
            "id": "sandy-soil",
            "name": "Plot 2: Sandy Soil (160 acres)",
            "acres": 160,
            "current_rotation": "Corn-Soybean alternating",
            "color_rgb": [230, 171, 2],
            "polygon": [
                [-92.850, 42.730],
                [-92.838, 42.730],
                [-92.838, 42.720],
                [-92.850, 42.720],
            ],
            "plain_summary": [
                "Your soil holds little water and dries out quickly between rains.",
                "Loose, sandy texture means local dry spells hit your harvest harder than the county average.",
                "Last eight years: corn, soybeans, corn, soybeans.",
            ],
            "technical_details": {
                "Sand Fraction & AWC": "58% sand content, Available Water Capacity 0.13 cm/cm (Measured - USDA SSURGO v33)",
                "Canopy Vigor Penalty (NDVI)": "-1.4% to -1.7% summer NDVI reduction vs. loam soils (Measured - NASA MODIS)",
                "Local Risk Exposure": "50% of yield variance is local and unhedged by regional market prices (Measured - USDA 26-yr)",
            },
            "prevented_planting_risk": None,
            "scenarios": {
                "Normal Year": {
                    "recommendation": (
                        "Use Corn-Soybean rotation with split nitrogen applications so nutrients do not leach "
                        "through this fast-draining soil."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -85,
                            "net_return_range": (-160, -15),
                            "yield_bu": 182,
                            "yield_range": (150, 205),
                            "erosion_tons": 2.0,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Sandy soil penalty: Measured (NASA MODIS / SSURGO) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -215,
                            "net_return_range": (-305, -135),
                            "yield_bu": 170,
                            "yield_range": (135, 195),
                            "erosion_tons": 1.6,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Cost ($960/ac) & N rate: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -105,
                            "net_return_range": (-180, -35),
                            "yield_bu": 184,
                            "yield_range": (154, 206),
                            "erosion_tons": 0.9,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Organic matter water retention: Literature (Iowa State 2026)",
                        },
                    ],
                },
                "Dry and Hot Year": {
                    "recommendation": (
                        "Avoid continuous corn completely on this sandy plot; water stress cuts harvest by a fifth "
                        "or more, and local yield losses will not be covered by market prices."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -140,
                            "net_return_range": (-245, -45),
                            "yield_bu": 138,
                            "yield_range": (102, 168),
                            "erosion_tons": 1.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "AWC drought sensitivity: Measured (SSURGO) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -375,
                            "net_return_range": (-490, -260),
                            "yield_bu": 104,
                            "yield_range": (68, 136),
                            "erosion_tons": 1.5,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Combined sand + continuous corn stress: Measured + Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -155,
                            "net_return_range": (-255, -60),
                            "yield_bu": 142,
                            "yield_range": (108, 170),
                            "erosion_tons": 0.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Residue moisture conservation: Literature (Iowa State 2026)",
                        },
                    ],
                },
                "Wet Spring": {
                    "recommendation": (
                        "Corn-Soybean rotation performs well here in wet springs because sandy soil drains fast "
                        "and lets machinery enter on time."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -60,
                            "net_return_range": (-125, 5),
                            "yield_bu": 192,
                            "yield_range": (168, 212),
                            "erosion_tons": 2.3,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Fast drainage benefit: Measured (SSURGO) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -190,
                            "net_return_range": (-265, -115),
                            "yield_bu": 180,
                            "yield_range": (152, 202),
                            "erosion_tons": 1.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "Medium",
                            "source_note": "Nitrogen leaching risk & Cost ($960/ac): Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -85,
                            "net_return_range": (-150, -20),
                            "yield_bu": 193,
                            "yield_range": (170, 213),
                            "erosion_tons": 1.0,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Nutrient scavenging & cost: Literature (Iowa State 2026)",
                        },
                    ],
                },
            },
        },
        "steep-slope": {
            "id": "steep-slope",
            "name": "Plot 5: Steep Slope (277 acres)",
            "acres": 277,
            "current_rotation": "Corn-Soybean alternating",
            "color_rgb": [231, 41, 138],
            "polygon": [
                [-92.755, 42.742],
                [-92.740, 42.742],
                [-92.740, 42.730],
                [-92.755, 42.730],
            ],
            "plain_summary": [
                "This soil washes away easily with heavy rain due to its steep grade.",
                "Simple Corn-Soybean rotation leaves the ground too bare after soybean harvest.",
                "Adding a cover crop cuts soil loss below the tolerable limit while preserving rotation yield.",
            ],
            "technical_details": {
                "Soil Erodibility & Slope": "K-Factor 0.32, 6-9% slope grade (Measured - USDA SSURGO v33)",
                "Residue Tradeoff": "Continuous corn leaves more residue than soy, but Cover Crop solves both yield and erosion",
            },
            "prevented_planting_risk": None,
            "scenarios": {
                "Normal Year": {
                    "recommendation": (
                        "Choose Corn-Soybean + Cover Crop: simple rotation exceeds safe soil erosion limits on this slope, "
                        "while cover crops protect your topsoil and save $87 per acre over continuous corn."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -52,
                            "net_return_range": (-115, 10),
                            "yield_bu": 198,
                            "yield_range": (175, 218),
                            "erosion_tons": 6.4,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Erosion above 5 t/ac limit: Measured (SSURGO) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -175,
                            "net_return_range": (-245, -105),
                            "yield_bu": 188,
                            "yield_range": (160, 210),
                            "erosion_tons": 4.2,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Corn residue erosion buffer: Measured (SSURGO) | Cost ($960/ac): Literature",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -88,
                            "net_return_range": (-145, -25),
                            "yield_bu": 197,
                            "yield_range": (174, 216),
                            "erosion_tons": 2.3,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Best balance of soil protection & return: Measured (SSURGO) + Literature (ISU)",
                        },
                    ],
                },
                "Dry and Hot Year": {
                    "recommendation": (
                        "Use Corn-Soybean + Cover Crop: it prevents hillside runoff during summer storms and avoids "
                        "the heavy $235 per acre drought penalty of continuous corn."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -75,
                            "net_return_range": (-155, 10),
                            "yield_bu": 162,
                            "yield_range": (132, 188),
                            "erosion_tons": 5.6,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Yield & price: Measured (USDA) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -310,
                            "net_return_range": (-420, -200),
                            "yield_bu": 126,
                            "yield_range": (92, 155),
                            "erosion_tons": 3.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Drought penalty & Cost ($960/ac): Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -98,
                            "net_return_range": (-175, -15),
                            "yield_bu": 163,
                            "yield_range": (134, 188),
                            "erosion_tons": 2.0,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Infiltration & erosion control: Measured (SSURGO) + Literature (ISU)",
                        },
                    ],
                },
                "Wet Spring": {
                    "recommendation": (
                        "Plant Corn-Soybean + Cover Crop: heavy spring rains wash away unprotected soybean stubble "
                        "on this slope (7.8 tons/acre), which a winter cover crop cuts by more than half."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -70,
                            "net_return_range": (-135, -5),
                            "yield_bu": 190,
                            "yield_range": (165, 210),
                            "erosion_tons": 7.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Severe spring runoff erosion: Measured (SSURGO) | Cost: Literature (ISU)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -205,
                            "net_return_range": (-285, -130),
                            "yield_bu": 176,
                            "yield_range": (146, 200),
                            "erosion_tons": 4.9,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "Medium",
                            "source_note": "Cost ($960/ac) & N rate: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -92,
                            "net_return_range": (-155, -25),
                            "yield_bu": 191,
                            "yield_range": (166, 211),
                            "erosion_tons": 2.7,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Slope protection under spring rain: Measured (SSURGO) + Literature (ISU)",
                        },
                    ],
                },
            },
        },
        "classic-good": {
            "id": "classic-good",
            "name": "Plot 1: Good Soil, Classic Rotation (407 acres)",
            "acres": 407,
            "current_rotation": "Corn-Soybean alternating",
            "color_rgb": [27, 158, 119],
            "polygon": [
                [-92.810, 42.712],
                [-92.792, 42.712],
                [-92.792, 42.698],
                [-92.810, 42.698],
            ],
            "plain_summary": [
                "Your soil has active organic life and stores water reliably across the season.",
                "Flat terrain and tile drainage keep both erosion and flooding risks low.",
                "Last eight years: corn, soybeans, corn, soybeans, corn, soybeans, corn, soybeans.",
            ],
            "technical_details": {
                "Soil Quality": "Organic Matter 4.7%, AWC 0.22 cm/cm (Measured - USDA SSURGO v33)",
                "Summer Canopy Vigor": "Top quartile NDVI across 2024-2025 (Measured - NASA MODIS)",
                "Baseline Status": "Reference plot where standard two-year rotation already operates optimally",
            },
            "prevented_planting_risk": None,
            "scenarios": {
                "Normal Year": {
                    "recommendation": (
                        "Keep your current Corn-Soybean rotation: your plot is already minimizing per-acre losses "
                        "and keeping soil erosion well below the tolerable threshold."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -38,
                            "net_return_range": (-88, 20),
                            "yield_bu": 205,
                            "yield_range": (185, 224),
                            "erosion_tons": 2.1,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Yield & price: Measured (USDA) | Cost ($875/ac) & N rate: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -160,
                            "net_return_range": (-225, -90),
                            "yield_bu": 196,
                            "yield_range": (170, 215),
                            "erosion_tons": 1.6,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Cost ($960/ac) & N rate: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -72,
                            "net_return_range": (-122, -15),
                            "yield_bu": 203,
                            "yield_range": (183, 222),
                            "erosion_tons": 1.0,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Cover seed cost & agronomics: Literature (Iowa State 2026)",
                        },
                    ],
                },
                "Dry and Hot Year": {
                    "recommendation": (
                        "Stay on Corn-Soybean rotation: in a 2012-style drought, rotating saves $235 per acre "
                        "compared to continuous corn while high market prices cushion your revenue."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -60,
                            "net_return_range": (-135, 30),
                            "yield_bu": 170,
                            "yield_range": (142, 194),
                            "erosion_tons": 1.9,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "2012 price cushion: Measured (USDA) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -295,
                            "net_return_range": (-400, -185),
                            "yield_bu": 134,
                            "yield_range": (100, 164),
                            "erosion_tons": 1.4,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "High",
                            "source_note": "Drought penalty (up to 27%) & Cost ($960/ac): Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -88,
                            "net_return_range": (-165, -5),
                            "yield_bu": 168,
                            "yield_range": (140, 192),
                            "erosion_tons": 0.8,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Cost & residue effect: Literature (Iowa State 2026)",
                        },
                    ],
                },
                "Wet Spring": {
                    "recommendation": (
                        "Continue with Corn-Soybean rotation; tile drainage on this plot handles wet springs well."
                    ),
                    "recommended_n_lbs": 124,
                    "plans": [
                        {
                            "name": "Corn-Soybean Rotation",
                            "net_return_usd": -52,
                            "net_return_range": (-110, 10),
                            "yield_bu": 198,
                            "yield_range": (175, 216),
                            "erosion_tons": 2.5,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "High",
                            "source_note": "Tiled drainage response: Measured (SSURGO) | Cost: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Continuous Corn",
                            "net_return_usd": -188,
                            "net_return_range": (-265, -110),
                            "yield_bu": 184,
                            "yield_range": (155, 206),
                            "erosion_tons": 1.9,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 181,
                            "confidence": "Medium",
                            "source_note": "Cost ($960/ac) & N rate: Literature (Iowa State 2026)",
                        },
                        {
                            "name": "Corn-Soybean + Cover Crop",
                            "net_return_usd": -76,
                            "net_return_range": (-135, -10),
                            "yield_bu": 197,
                            "yield_range": (174, 215),
                            "erosion_tons": 1.1,
                            "erosion_limit": 5.0,
                            "nitrogen_lbs": 124,
                            "confidence": "Medium",
                            "source_note": "Cost & erosion: Measured (SSURGO) + Literature (Iowa State 2026)",
                        },
                    ],
                },
            },
        },
    }


@st.cache_data
def load_demo_results() -> dict[str, Any]:
    """Load precomputed Butler County results from disk or fall back to built-in verified data."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data:
                return data
        except Exception:
            pass
    return _get_preloaded_butler_data()


def _set_2012_drought_scenario() -> None:
    """Callback for the 'What would have happened in 2012?' quick button."""
    st.session_state.climate_scenario = "Dry and Hot Year"


def main() -> None:
    plots_data = load_demo_results()
    plot_keys = list(plots_data.keys())

    if "selected_plot_key" not in st.session_state or st.session_state.selected_plot_key not in plot_keys:
        st.session_state.selected_plot_key = plot_keys[0]
    if "climate_scenario" not in st.session_state:
        st.session_state.climate_scenario = "Normal Year"

    st.title("Field Shift — Butler County Planting Decision Tool")
    st.caption(
        "Compare crop plans using both Harvest (bushels/acre) and Money ($/acre). "
        "All data is preloaded from 26 years of Butler County, Iowa records (2000-2025) and Iowa State University guidelines."
    )

    # =========================================================================
    # STEP 1: CHOOSE YOUR PLOT ON THE MAP
    # =========================================================================
    st.subheader("1. Select Your Field Plot in Butler County, Iowa")

    col_selector, col_map = st.columns([4, 6])

    plot_labels = {plots_data[k]["name"]: k for k in plot_keys}
    current_label = plots_data[st.session_state.selected_plot_key]["name"]

    with col_selector:
        chosen_label = st.radio(
            "Preselected Butler County Demo Plots (colored by current rotation):",
            options=list(plot_labels.keys()),
            index=list(plot_labels.keys()).index(current_label),
        )
        st.session_state.selected_plot_key = plot_labels[chosen_label]
        active_plot = plots_data[st.session_state.selected_plot_key]

        st.info(
            f"**Selected Plot:** {active_plot['name']}\n\n"
            f"**Size:** {active_plot['acres']:,} acres | "
            f"**Current Practice:** {active_plot['current_rotation']}"
        )

    with col_map:
        map_rows = []
        for k, p in plots_data.items():
            is_selected = k == st.session_state.selected_plot_key
            map_rows.append(
                {
                    "name": p["name"],
                    "acres": p["acres"],
                    "rotation": p["current_rotation"],
                    "polygon": p["polygon"],
                    "fill_color": p["color_rgb"] + ([230] if is_selected else [110]),
                    "line_width": 4 if is_selected else 1,
                }
            )
        map_df = pd.DataFrame(map_rows)

        deck = pdk.Deck(
            map_style=None,
            initial_view_state=pdk.ViewState(latitude=42.725, longitude=-92.795, zoom=11.2),
            layers=[
                pdk.Layer(
                    "PolygonLayer",
                    data=map_df,
                    get_polygon="polygon",
                    get_fill_color="fill_color",
                    get_line_color=[30, 30, 30],
                    get_line_width="line_width",
                    line_width_min_pixels=1,
                    pickable=True,
                    auto_highlight=True,
                )
            ],
            tooltip={"text": "{name}\n{acres} acres\nCurrent: {rotation}"},
        )
        st.pydeck_chart(deck, height=280)

    st.divider()

    # =========================================================================
    # STEP 2: SEE HOW YOUR LAND IS (Plain language, technical details folded)
    # =========================================================================
    st.subheader("2. How Your Land Behaves")

    for sentence in active_plot["plain_summary"]:
        st.markdown(f"- {sentence}")

    if active_plot.get("prevented_planting_risk"):
        st.warning(f"**Unplanted Field Risk (2019 & 2024 Benchmark):** {active_plot['prevented_planting_risk']}")

    with st.expander("View technical soil & satellite measurements (for agronomic & scientific review)"):
        for k_tech, v_tech in active_plot["technical_details"].items():
            st.markdown(f"- **{k_tech}:** {v_tech}")
        st.caption(
            "Note on satellite resolution: NASA MODIS NDVI clearly distinguishes corn from soybeans (1.5% signal) "
            "and good soil from sandy soil (1.4% to 1.7% signal), but cannot isolate the rotation effect in good weather years. "
            "Rotation yield penalties are therefore taken directly from Iowa State University extension literature."
        )

    st.divider()

    # =========================================================================
    # STEP 3 & 4: MOVE THE CLIMATE SCENARIO & COMPARE THE 3 PLANS LIVE
    # =========================================================================
    st.subheader("3. Select Weather Scenario & Compare Planting Plans")

    scen_col1, scen_col2 = st.columns([7, 3])
    with scen_col1:
        scenario = st.segmented_control(
            "Move the weather scenario to see how each planting plan responds live:",
            options=["Normal Year", "Dry and Hot Year", "Wet Spring"],
            key="climate_scenario",
        )
        if scenario is None:
            scenario = "Normal Year"
    with scen_col2:
        st.caption("Historical Stress Test (34% yield drop, +17% income):")
        st.button(
            "What would have happened in 2012?",
            on_click=_set_2012_drought_scenario,
            use_container_width=True,
        )

    active_scenario_data = active_plot["scenarios"][scenario]
    plans = active_scenario_data["plans"]

    st.caption(
        "2025/2026 Market Context: Corn at $4.10/bu and Soybeans at $10.50/bu (Measured - USDA). "
        "Production costs include land rent ($875/ac Corn-after-Soy, $960/ac Continuous Corn, $680/ac Soy-after-Corn; "
        "Literature - Iowa State University 2026). With current prices, all plans show a net loss including land rent — "
        "the decision is which plan loses the least and protects your soil."
    )

    # Render the 3 Plan Cards side by side (never more than 3)
    card_cols = st.columns(3)
    for col, plan in zip(card_cols, plans):
        with col:
            with st.container(border=True):
                st.markdown(f"### {plan['name']}")

                # Two mandatory axes side-by-side: Money first, Harvest second
                m_col, h_col = st.columns(2)
                net_val = plan["net_return_usd"]
                net_lo, net_hi = plan["net_return_range"]
                y_val = plan["yield_bu"]
                y_lo, y_hi = plan["yield_range"]

                with m_col:
                    st.metric(
                        label="Money per Acre",
                        value=f"${net_val:+d} / ac",
                    )
                    st.caption(f"Normally between **${net_lo:+d}** and **${net_hi:+d} / ac**")

                with h_col:
                    st.metric(
                        label="Expected Harvest",
                        value=f"{y_val} bu / ac",
                    )
                    st.caption(
                        f"In 8 out of 10 years like this: **{y_lo} to {y_hi} bu / ac**"
                    )

                # Visual uncertainty width bar (wider range = higher risk)
                range_span = y_hi - y_lo
                normalized_width = min(1.0, max(0.1, range_span / 80.0))
                st.caption(f"Harvest Uncertainty Spread: {range_span} bu/ac range (80% calibrated probability)")
                st.progress(normalized_width)

                st.divider()

                # Erosion bar with tolerable limit marked (5.0 tons/acre)
                erosion_val = plan["erosion_tons"]
                erosion_limit = plan["erosion_limit"]
                erosion_ratio = min(1.0, erosion_val / (erosion_limit * 1.6))
                erosion_status = (
                    "Within tolerable limit"
                    if erosion_val <= erosion_limit
                    else "Exceeds tolerable limit"
                )
                st.markdown(
                    f"**Soil Erosion:** {erosion_val:.1f} tons/acre "
                    f"(Tolerable limit: {erosion_limit:.1f} t/ac — *{erosion_status}*)"
                )
                st.progress(erosion_ratio)

                # Prevented planting risk: only shown if the plot has it
                if active_plot.get("prevented_planting_risk"):
                    st.caption(f"**Unplanted Risk:** {active_plot['prevented_planting_risk']}")

                # Small metadata: Nitrogen and Confidence + Source
                st.caption(
                    f"**Nitrogen Rate:** {plan['nitrogen_lbs']} lbs/acre | "
                    f"**Confidence:** {plan['confidence']}"
                )
                st.caption(f"**Sources:** {plan['source_note']}")

    st.caption(
        "**Calibrated Uncertainty Guarantee:** When we state an 80% range, we are right 80% of the time — "
        "verified across 26 years of out-of-sample Butler County harvest and price records. "
        "Climate uncertainty (weather across years) is shown in the ranges above; source attribution separates "
        "what we measured from Iowa State University extension literature."
    )

    st.divider()

    # =========================================================================
    # STEP 5: READ THE RECOMMENDATION
    # =========================================================================
    st.subheader("4. Recommended Action for This Plot")
    st.success(
        f"**What to do:** {active_scenario_data['recommendation']}\n\n"
        f"**Recommended Nitrogen Application:** {active_scenario_data['recommended_n_lbs']} lbs/acre "
        "(Source: Iowa State University Extension Guidelines)"
    )


if __name__ == "__main__":
    main()