"""Paso 0: convierte las descargas originales en series mensuales limpias.

Entradas (datos/):
  nldas_iowa_SoilM_0_10cm.csv, nldas_iowa_SoilM_0_100cm.csv, nldas_iowa_SMAvail_0_100cm.csv
      Giovanni, NLDAS_NOAH0125_M v2.0, promedio del área -93.7,41.9,-93.3,42.3 (Story County), 2000-2025
  gldas_iowa_SoilMoi0_10cm.csv, gldas_puebla_SoilMoi0_10cm.csv
      Giovanni, GLDAS_NOAH025_M v2.1, Iowa (93W 41N) y Tecamachalco, Puebla (97W 18N), 2000-2025
  smap_l4_appeears.csv
      AppEEARS, SPL4SMGP v008, puntos iowa (42.07, -93.5) y puebla (19.01, -97.9), 2024-2025, cada 3 h

Salidas (salidas/): iowa_nldas_mensual.csv, iowa_gldas.csv, puebla_gldas.csv, smap_mensual.csv

Conversiones: NLDAS 0-10 cm kg/m² ÷ 100 y 0-100 cm ÷ 1000 → m³/m³; GLDAS 0-10 cm ÷ 100.
Percentil = posición de cada mes frente al mismo mes de los 26 años.
"""
import pandas as pd

from comun import DATOS, SALIDAS, leer_giovanni, percentil_mensual

# ---------- NLDAS-2 (Story County)
n = pd.DataFrame({
    "sm10": leer_giovanni(DATOS / "nldas_iowa_SoilM_0_10cm.csv") / 100,
    "sm100": leer_giovanni(DATOS / "nldas_iowa_SoilM_0_100cm.csv") / 1000,
    "avail": leer_giovanni(DATOS / "nldas_iowa_SMAvail_0_100cm.csv"),
})
n["m"] = n.index.month
n["y"] = n.index.year
for c in ["sm10", "sm100", "avail"]:
    n[c + "_p"] = percentil_mensual(n[c])
n.round(4).to_csv(SALIDAS / "iowa_nldas_mensual.csv")

# ---------- GLDAS-2.1 (Iowa y Puebla)
for lugar in ["iowa", "puebla"]:
    g = leer_giovanni(DATOS / f"gldas_{lugar}_SoilMoi0_10cm.csv").to_frame("sm") / 100
    g["y"] = g.index.year
    g["m"] = g.index.month
    g["pctl"] = percentil_mensual(g.sm)
    g["anom"] = g.sm - g.groupby("m").sm.transform("mean")
    g.to_csv(SALIDAS / f"{lugar}_gldas.csv")

# ---------- SMAP L4 (promedio mensual de los datos cada 3 h)
s = pd.read_csv(DATOS / "smap_l4_appeears.csv")
s.columns = ["cat", "id", "lat", "lon", "date", "tile", "y", "x", "rz", "pctl", "surf"]
s["t"] = pd.to_datetime(s.date.str.replace(" UTC", "")).dt.to_period("M")
sm = s.groupby(["id", "t"])[["rz", "pctl", "surf"]].mean().round(3).reset_index()
sm.to_csv(SALIDAS / "smap_mensual.csv", index=False)

print("NLDAS:", len(n), "meses | GLDAS: 2 sitios | SMAP:", len(sm), "meses-sitio")
