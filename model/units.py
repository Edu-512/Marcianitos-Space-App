"""US agricultural units -> metric. The single source of conversion factors.

The crop model works in US units (bushels, acres, pounds). The app contract in
``utils/types.py`` is metric. Every conversion goes through this module, and
values are converted *before* any rounding for display.

Quick check: 223 bu/acre corn = 14.00 t/ha · 778 USD/acre = 1,922 USD/ha ·
407 acres = 164.7 ha.
"""

from __future__ import annotations

CORN_BU_PER_ACRE_TO_T_PER_HA = 0.06277
SOY_BU_PER_ACRE_TO_T_PER_HA = 0.06725
USD_PER_ACRE_TO_USD_PER_HA = 2.47105
ACRES_TO_HECTARES = 0.404686
LB_PER_ACRE_TO_KG_PER_HA = 1.12085
SHORT_TONS_PER_ACRE_TO_T_PER_HA = 2.24170

# Derived from the factors above (t/ha per bu/acre × ha per acre = t per bushel),
# so prices stay consistent with the yield conversions.
CORN_TONNES_PER_BUSHEL = CORN_BU_PER_ACRE_TO_T_PER_HA * ACRES_TO_HECTARES
SOY_TONNES_PER_BUSHEL = SOY_BU_PER_ACRE_TO_T_PER_HA * ACRES_TO_HECTARES


def corn_bu_acre_to_t_ha(value: float) -> float:
    return float(value) * CORN_BU_PER_ACRE_TO_T_PER_HA


def soy_bu_acre_to_t_ha(value: float) -> float:
    return float(value) * SOY_BU_PER_ACRE_TO_T_PER_HA


def usd_acre_to_usd_ha(value: float) -> float:
    return float(value) * USD_PER_ACRE_TO_USD_PER_HA


def acres_to_ha(value: float) -> float:
    return float(value) * ACRES_TO_HECTARES


def lb_acre_to_kg_ha(value: float) -> float:
    return float(value) * LB_PER_ACRE_TO_KG_PER_HA


def short_tons_acre_to_t_ha(value: float) -> float:
    return float(value) * SHORT_TONS_PER_ACRE_TO_T_PER_HA


def corn_usd_bu_to_usd_t(value: float) -> float:
    return float(value) / CORN_TONNES_PER_BUSHEL


def soy_usd_bu_to_usd_t(value: float) -> float:
    return float(value) / SOY_TONNES_PER_BUSHEL
