"""Paso 9: verificaciones cruzadas con los análisis de QuickStats y del panel de rotación.

A. Reproduce las cifras de QuickStats con la tabla por condado (tendencia, peores años,
   % de variación que explica el año, pérdida de los condados de bajo rendimiento).
B. Prueba si los condados de bajo rendimiento reaccionan más al clima (IC remuestreando años).
C. Panel de rotación: efecto del maíz sobre maíz con efectos fijos de condado y año, más dos
   pruebas de control (placebo con la soya y el indicador del año siguiente).
   Si las pruebas de control dan "efecto", el indicador no mide el efecto de rotar.

Entradas: salidas/tabla_condados.csv (paso 6), datos/condados_iowa_nombres.json,
          datos/panel_rotacion.csv (lo genera scripts_cdl_rotacion/s3_efecto_rotacion_panel.py)
Salida: salidas/R9_cruces.json
"""
import json

import numpy as np
import pandas as pd

from comun import DATOS, SALIDAS

R = {}
d = pd.read_csv(SALIDAS / "tabla_condados.csv")

# ---------- A. cifras de QuickStats
A = {}
for c in ["maiz", "soya"]:
    s = d.groupby("year")[c].mean()
    x = d.dropna(subset=[c + "_anom"])
    ym = x.groupby("year")[c + "_anom"].transform("mean")
    A[c] = dict(tendencia_bu_ac_anio=round(float(np.polyfit(s.index, s.values, 1)[0]), 2),
                peores_anios=d.groupby("year")[c + "_anom"].mean().sort_values().head(5).round(1).to_dict(),
                variacion_explicada_por_anio=round(float(1 - ((x[c + "_anom"] - ym) ** 2).sum() / ((x[c + "_anom"] - x[c + "_anom"].mean()) ** 2).sum()), 2))
m = d.groupby("year")[["maiz_anom", "soya_anom"]].mean()
A["corr_anual_maiz_soya"] = round(float(m.corr().iloc[0, 1]), 2)
media = d.groupby("fips").maiz.mean()
d["bajo"] = d.fips.map(media < media.quantile(.25))
malos = d[d.year.isin([2012, 2013, 2010, 2020])]
A["perdida_anios_malos"] = dict(cuartil_bajo=round(malos[malos.bajo].maiz_anom.mean(), 1), resto=round(malos[~malos.bajo].maiz_anom.mean(), 1))
A["condados_con_dato_2024"] = dict(maiz=int(d[d.year == 2024].maiz.notna().sum()), soya=int(d[d.year == 2024].soya.notna().sum()))
rec = d[d.year >= 2020].groupby("fips").maiz.apply(lambda s: s.isna().sum())
temprano = d[d.year <= 2014].groupby("fips").maiz.mean()
A["faltantes_recientes"] = dict(condados=int((rec > 0).sum()), corr_con_rendimiento=round(float(np.corrcoef(rec, temprano)[0, 1]), 2),
                                rend_con_faltantes=round(temprano[rec > 0].mean(), 1), rend_sin_faltantes=round(temprano[rec == 0].mean(), 1))
b3 = d[(d.fips == 19023) & (d.year == 2003)]
A["butler_2003"] = b3[["soya", "soya_anom", "maiz_anom", "sm100_7_z", "sm100_8_z", "d35_z", "lluvia_jul_ago_z"]].round(2).to_dict("records")[0]
A["butler_percentil_maiz"] = int(round((media < media[19023]).mean() * 100))
R["A_quickstats"] = A

# ---------- B. ¿los condados de bajo rendimiento reaccionan más al clima?
rng = np.random.default_rng(1)
x = d.dropna(subset=["maiz_anom"])
yrs = x.year.unique()


def dif_pendiente(s, v):
    return np.polyfit(s[s.bajo][v], s[s.bajo].maiz_anom, 1)[0] - np.polyfit(s[~s.bajo][v], s[~s.bajo].maiz_anom, 1)[0]


B = {}
for v in ["sm100_8_z", "d35_z"]:
    bs = [dif_pendiente(pd.concat([x[x.year == k] for k in rng.choice(yrs, len(yrs))]), v) for _ in range(1000)]
    B[v] = dict(diferencia=round(float(dif_pendiente(x, v)), 2), ic95=np.percentile(bs, [2.5, 97.5]).round(2).tolist())
R["B_interaccion_suelo_clima"] = B

# ---------- C. panel de rotación
p = pd.read_csv(DATOS / "panel_rotacion.csv")
nm = json.load(open(DATOS / "condados_iowa_nombres.json", encoding="utf-8"))
inv = {v.upper().replace("'", "").replace(" ", ""): int(k) for k, v in nm.items()}
p["fips"] = p.condado.str.replace("'", "").str.replace(" ", "").map(inv)
assert p.fips.notna().all()
x = p.merge(d.drop(columns=["bajo"]), left_on=["fips", "anio"], right_on=["fips", "year"])
rng = np.random.default_rng(0)
yrs = x.anio.unique()


def quitar_efectos(s, c):
    v = s[c].copy()
    for _ in range(20):
        v = v - v.groupby(s.fips).transform("mean")
        v = v - v.groupby(s.anio).transform("mean")
    return v


def efecto_fijo(y, xv):
    s = x.dropna(subset=[y, xv])
    b = lambda t: np.polyfit(quitar_efectos(t, xv), quitar_efectos(t, y), 1)[0]
    bs = [b(pd.concat([s[s.anio == k] for k in rng.choice(yrs, len(yrs), replace=False)[:20]])) for _ in range(300)]
    return dict(efecto=round(float(b(s)), 1), ic95=np.percentile(bs, [2.5, 97.5]).round(1).tolist())


C = {"maiz_sobre_maiz_a_rend_maiz": efecto_fijo("anom_pct", "mm_min"),
     "placebo_a_rend_soya": efecto_fijo("anom_soya", "mm_min"),
     "futuro_a_rend_maiz": efecto_fijo("anom_pct", "mm_fut")}
x["alto"] = x.mm_min > x.groupby("anio").mm_min.transform("median")


def dif_alto(s, v):
    return np.polyfit(s[s.alto][v], s[s.alto].anom_pct, 1)[0] - np.polyfit(s[~s.alto][v], s[~s.alto].anom_pct, 1)[0]


C["sensibilidad_clima_maiz_continuo"] = {}
for v in ["sm100_8_z", "d35_z", "lluvia_may_jun_z"]:
    bs = [dif_alto(pd.concat([x[x.anio == k] for k in rng.choice(yrs, len(yrs))]), v) for _ in range(800)]
    C["sensibilidad_clima_maiz_continuo"][v] = dict(diferencia=round(float(dif_alto(x, v)), 2), ic95=np.percentile(bs, [2.5, 97.5]).round(2).tolist())
a = x.groupby("anio")[["d_mm", "lluvia_may_jun_z", "sm10_5_z", "anom_prev"]].mean()
C["cambio_anual_vs_clima_spearman"] = a.corr(method="spearman").d_mm.round(2).drop("d_mm").to_dict()
z = x[x.anio == 2012]
C["perdida_2012"] = dict(mas_maiz_continuo=round(z[z.alto].anom_pct.mean(), 1), menos=round(z[~z.alto].anom_pct.mean(), 1))
C["corr_maiz_continuo_vs_rendimiento_condado"] = round(float(np.corrcoef(x.groupby("fips").mm_min.mean(), x.groupby("fips").maiz_rend.mean())[0, 1]), 2)
C["por_distrito"] = p.groupby("distrito").mm_min.mean().round(2).sort_values().to_dict()
R["C_panel_rotacion"] = C

json.dump(R, open(SALIDAS / "R9_cruces.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(R, ensure_ascii=False, indent=1, default=float))
