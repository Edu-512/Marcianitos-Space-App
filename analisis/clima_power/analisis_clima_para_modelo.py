import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
# Perfil climático completo para el modelo - NASA Space Apps 2026 "Cambio de rumbo"
# Equipo de modelo (parte de clima). NASA POWER diario (MERRA-2).
#
# Qué hace: lee el CSV de POWER y EXTRAE toda la información de clima que el modelo
# puede usar (variables derivadas, valores normales por época, extremos, heladas, GDD,
# rachas secas, humedad de suelo, relaciones entre variables y tendencias).
# NO propone un modelo ni un semáforo: solo entrega los insumos de clima.
#
# Uso:  py analisis_clima_para_modelo.py
# Requisitos: pip install pandas numpy   (scipy es opcional: si está, calcula significancia de tendencias)
# Salida (carpeta salida_clima/):
#   clima_para_modelo.md           <- documento principal (se lo pasan al líder del modelo)
#   clima_variables_diarias.csv    <- tabla diaria con todas las variables derivadas (para unir con otras fuentes)
#   clima_normales_por_dia.csv     <- referencia por día del año (media, P10, P25, P50, P75, P90)
#   clima_resumen_anual.csv        <- una fila por año con indicadores clave
#   clima_resumen_mensual.csv      <- climatología mensual
#   clima_perfil.json              <- resumen compacto en JSON
#
# Para otra zona: baja el mismo CSV de POWER (mismos 5 parámetros) y cambia RUTA_CSV.
# La latitud, longitud y elevación se leen solos del encabezado del CSV.

# %%
import json
import os
import re
from statistics import NormalDist

import numpy as np
import pandas as pd

RUTA_CSV = "datos/POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST.csv"
SALIDA = "salida_clima"
BASE_INI, BASE_FIN = 2000, 2020     # periodo base para "lo normal" de cada época
ANCHO_VENTANA = 7                   # +-7 días alrededor de cada fecha
UMBRAL_CALOR = 32                   # día de calor: Tmax >= 32 C (supuesto)
UMBRAL_CALOR_FUERTE = 35
UMBRAL_SECO_MM = 1.0                # día seco: lluvia < 1 mm
BASE_GDD, TOPE_GDD = 10, 30         # grados-día (maíz, supuesto)
MES_INICIO_GDD, MES_FIN_GDD = 5, 10  # GDD acumulado desde 1 de mayo hasta 31 de octubre
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

os.makedirs(SALIDA, exist_ok=True)
try:
    from scipy import stats as _st
except Exception:
    _st = None


# %% [markdown]
# ## 1. Carga

# %%
def cargar_power(ruta):
    with open(ruta, encoding="utf-8") as f:
        lineas = f.readlines()
    skip, meta = 0, {}
    for i, l in enumerate(lineas):
        m = re.search(r"latitude\s+(-?[\d.]+)\s+longitude\s+(-?[\d.]+)", l, re.I)
        if m:
            meta["lat"], meta["lon"] = float(m.group(1)), float(m.group(2))
        m = re.search(r"=\s*([\d.]+)\s*meters", l)
        if m:
            meta["elevacion_m"] = float(m.group(1))
        if "END HEADER" in l.upper():
            skip = i + 1
            break
    df = pd.read_csv(ruta, skiprows=skip)
    df.columns = [c.strip() for c in df.columns]
    if {"YEAR", "DOY"} <= set(df.columns):
        df["fecha"] = pd.to_datetime(df.YEAR.astype(str), format="%Y") + pd.to_timedelta(df.DOY - 1, unit="D")
    else:
        df["fecha"] = pd.to_datetime(dict(year=df.YEAR, month=df.MO, day=df.DY))
    df = df.set_index("fecha").sort_index()
    df = df.drop(columns=[c for c in ["YEAR", "DOY", "MO", "DY"] if c in df.columns]).replace(-999, np.nan)
    return df, meta


df, META = cargar_power(RUTA_CSV)
LAT = META.get("lat", 42.73)
LON = META.get("lon", -92.79)
print(df.shape, df.index.min().date(), "a", df.index.max().date(), META)


# %% [markdown]
# ## 2. Variables derivadas diarias

# %%
def es(t):
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def ra_mm_dia(doy, lat_deg):
    phi = np.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    ra = (24 * 60 / np.pi) * 0.0820 * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))
    return 0.408 * ra


def calcular_variables(d, lat):
    v = pd.DataFrame(index=d.index)
    tmax, tmin, tdew, ll = d.T2M_MAX, d.T2M_MIN, d.T2MDEW, d.PRECTOTCORR
    v["tmax"], v["tmin"], v["tdew"], v["lluvia"], v["gw"] = tmax, tmin, tdew, ll, d.GWETROOT
    v["tmedia"] = (tmax + tmin) / 2
    v["rango_diurno"] = tmax - tmin
    v["deficit_rocio"] = v["tmedia"] - tdew                       # qué tan lejos está el aire de saturarse
    v["hr_aprox"] = (100 * es(tdew) / es(v["tmedia"])).clip(upper=100)   # humedad relativa aprox. (%)
    v["lluvia_7"] = ll.rolling(7).sum()
    v["lluvia_14"] = ll.rolling(14).sum()
    v["lluvia_30"] = ll.rolling(30).sum()
    v["lluvia_60"] = ll.rolling(60).sum()
    seco = ll < UMBRAL_SECO_MM
    v["dias_secos"] = seco.astype(int).groupby((~seco).cumsum()).cumsum()
    v["dias_con_lluvia_30"] = (ll >= UMBRAL_SECO_MM).astype(int).rolling(30).sum()
    tx = tmax.clip(lower=BASE_GDD, upper=TOPE_GDD)
    tn = tmin.clip(lower=BASE_GDD, upper=TOPE_GDD)
    v["gdd"] = (tx + tn) / 2 - BASE_GDD
    en_temp = v.index.month.isin(range(MES_INICIO_GDD, MES_FIN_GDD + 1))
    v["gdd_acum"] = v["gdd"].where(en_temp).groupby(v.index.year).cumsum().where(en_temp)
    v["dias_calor_7"] = (tmax >= UMBRAL_CALOR).astype(int).rolling(7).sum()
    v["dias_calor_30"] = (tmax >= UMBRAL_CALOR).astype(int).rolling(30).sum()
    v["dias_helada_3"] = (tmin <= 0).astype(int).rolling(3).sum()
    v["tmin_min_3"] = tmin.rolling(3).min()
    v["tmax_media_7"] = tmax.rolling(7).mean()
    v["vpd"] = (es(tmax) - es(tdew)).clip(lower=0)
    v["vpd_7"] = v["vpd"].rolling(7).mean()
    v["gw_7"] = d.GWETROOT.rolling(7).mean()
    v["gw_cambio_7"] = d.GWETROOT - d.GWETROOT.shift(7)           # sube o baja la humedad del suelo
    ra = ra_mm_dia(d.index.dayofyear.values, lat)
    v["et0"] = (0.0023 * (v["tmedia"] + 17.8) * np.sqrt(v["rango_diurno"].clip(lower=0)) * ra).clip(lower=0)
    v["et0_30"] = v["et0"].rolling(30).sum()
    v["balance_30"] = v["lluvia_30"] - v["et0_30"]
    return v


V = calcular_variables(df, LAT)
base_mask = ((V.index.year >= BASE_INI) & (V.index.year <= BASE_FIN))


# %% [markdown]
# ## 3. Normales por día del año y percentiles contra la misma época

# %%
STATS_COLS = ["tmax", "tmin", "tdew", "gw", "gw_7", "lluvia", "lluvia_7", "lluvia_30", "vpd_7", "et0", "balance_30"]
doy_all = V.index.dayofyear.values


def ventana_mask(doy_ref, d, ancho):
    dist = np.abs(doy_ref - d)
    return np.minimum(dist, 366 - dist) <= ancho


normales = {}
for d in range(1, 367):
    m = ventana_mask(doy_all[base_mask], d, ANCHO_VENTANA)
    fila = {}
    for c in STATS_COLS:
        x = V[c].values[base_mask][m]
        x = x[~np.isnan(x)]
        if len(x) == 0:
            continue
        fila.update({f"{c}_media": x.mean(), f"{c}_desv": x.std(ddof=1),
                     f"{c}_p10": np.percentile(x, 10), f"{c}_p25": np.percentile(x, 25),
                     f"{c}_p50": np.percentile(x, 50), f"{c}_p75": np.percentile(x, 75),
                     f"{c}_p90": np.percentile(x, 90)})
    fila["n_muestras"] = int(m.sum())
    normales[d] = fila
NORM = pd.DataFrame(normales).T
NORM.index.name = "dia_del_anio"
NORM.to_csv(os.path.join(SALIDA, "clima_normales_por_dia.csv"), float_format="%.3f")


def percentil_epoca(serie):
    vals, out = serie.values, np.full(len(serie), np.nan)
    b_doy, b_vals = doy_all[base_mask], vals[base_mask]
    ok = ~np.isnan(b_vals)
    b_doy, b_vals = b_doy[ok], b_vals[ok]
    for d in range(1, 367):
        ref = np.sort(b_vals[ventana_mask(b_doy, d, ANCHO_VENTANA)])
        idx = np.where(doy_all == d)[0]
        if len(ref) == 0 or len(idx) == 0:
            continue
        x = vals[idx]
        p = 100 * (np.searchsorted(ref, x, "left") + np.searchsorted(ref, x, "right")) / 2 / len(ref)
        p[np.isnan(x)] = np.nan
        out[idx] = p
    return pd.Series(out, index=serie.index)


PCT_COLS = ["tmax", "tmin", "tdew", "gw_7", "lluvia_7", "lluvia_30", "dias_secos", "vpd_7", "balance_30", "et0"]
for c in PCT_COLS:
    V["pct_" + c] = percentil_epoca(V[c])

# anomalías respecto a lo normal de la época
doy_idx = V.index.dayofyear
for c in ["tmax", "tmin", "tdew"]:
    V["anom_" + c] = V[c].values - NORM[c + "_media"].reindex(doy_idx).values
V["razon_lluvia_30"] = V["lluvia_30"].values / NORM["lluvia_30_media"].reindex(doy_idx).values
nd = NormalDist()
V["spi30_aprox"] = V["pct_lluvia_30"].apply(
    lambda p: np.nan if pd.isna(p) else nd.inv_cdf(min(max(p, 0.5), 99.5) / 100))   # índice tipo SPI, aproximado

V.to_csv(os.path.join(SALIDA, "clima_variables_diarias.csv"), float_format="%.3f")


# %% [markdown]
# ## 4. Resúmenes mensual y anual

# %%
def md_tabla(d, dec=1, indice=True, nombre_indice=""):
    d = d.copy()
    cols = ([nombre_indice or (d.index.name or "")] if indice else []) + [str(c) for c in d.columns]
    lineas = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for idx, row in d.iterrows():
        cel = [str(idx)] if indice else []
        for x in row.values:
            if isinstance(x, (float, np.floating)):
                dd = dec.get(d.columns[len(cel) - (1 if indice else 0)], 1) if isinstance(dec, dict) else dec
                cel.append("-" if np.isnan(x) else f"{x:.{dd}f}")
            else:
                cel.append(str(x))
        lineas.append("| " + " | ".join(cel) + " |")
    return "\n".join(lineas)


N_ANIOS = V.index.year.nunique()
mes = V.index.month
mensual = pd.DataFrame(index=range(1, 13))
mensual["Tmax °C"] = V.groupby(mes).tmax.mean()
mensual["Tmin °C"] = V.groupby(mes).tmin.mean()
mensual["Rocío °C"] = V.groupby(mes).tdew.mean()
mensual["Lluvia mm"] = V.groupby(mes).lluvia.sum() / N_ANIOS
mensual["Días lluvia"] = (V.lluvia >= UMBRAL_SECO_MM).groupby(mes).sum() / N_ANIOS
mensual["Suelo (0-1)"] = V.groupby(mes).gw.mean()
mensual["ET0 mm"] = V.groupby(mes).et0.sum() / N_ANIOS
mensual["Balance mm"] = mensual["Lluvia mm"] - mensual["ET0 mm"]
mensual["VPD kPa"] = V.groupby(mes).vpd.mean()
mensual["Días calor"] = (V.tmax >= UMBRAL_CALOR).groupby(mes).sum() / N_ANIOS
mensual["Días helada"] = (V.tmin <= 0).groupby(mes).sum() / N_ANIOS
mensual["GDD"] = V.groupby(mes).gdd.sum() / N_ANIOS
mensual.index = MESES
mensual.index.name = "mes"
mensual.to_csv(os.path.join(SALIDA, "clima_resumen_mensual.csv"), float_format="%.3f")


def doy_a_texto(doy):
    if pd.isna(doy):
        return "-"
    f = pd.Timestamp("2001-01-01") + pd.to_timedelta(int(round(doy)) - 1, unit="D")
    return f"{f.day} {MESES[f.month - 1]}"


def sub(s, meses):
    return s[s.index.month.isin(meses)]


def por_anio(s):
    return s.groupby(s.index.year)


def rachas(seco):
    g = (~seco).cumsum()
    lens = seco.groupby(g).sum()
    return lens[lens > 0]


def fechas_helada(tmin, umbral):
    ult, pri = {}, {}
    for y, s in tmin.groupby(tmin.index.year):
        a = s[(s.index.month <= 7) & (s <= umbral)]
        b = s[(s.index.month >= 8) & (s <= umbral)]
        ult[y] = a.index.dayofyear.max() if len(a) else np.nan
        pri[y] = b.index.dayofyear.min() if len(b) else np.nan
    return pd.Series(ult), pd.Series(pri)


anual = pd.DataFrame(index=sorted(V.index.year.unique()))
anual.index.name = "anio"
anual["tmax_media"] = por_anio(V.tmax).mean()
anual["tmin_media"] = por_anio(V.tmin).mean()
anual["lluvia_anual_mm"] = por_anio(V.lluvia).sum()
anual["lluvia_abr_jun_mm"] = por_anio(sub(V.lluvia, [4, 5, 6])).sum()
anual["lluvia_may_sep_mm"] = por_anio(sub(V.lluvia, range(5, 10))).sum()
anual["suelo_abr_jun"] = por_anio(sub(V.gw, [4, 5, 6])).mean()
anual["suelo_jul_ago"] = por_anio(sub(V.gw, [7, 8])).mean()
anual["dias_lluvia"] = por_anio(V.lluvia >= UMBRAL_SECO_MM).sum()
anual["dias_lluvia_fuerte_25mm"] = por_anio(V.lluvia >= 25).sum()
anual["lluvia_max_1d_mm"] = por_anio(V.lluvia).max()
anual["lluvia_max_7d_mm"] = por_anio(V.lluvia_7).max()
anual["lluvia_max_30d_mm"] = por_anio(V.lluvia_30).max()
anual["dias_calor_32"] = por_anio(V.tmax >= UMBRAL_CALOR).sum()
anual["dias_calor_35"] = por_anio(V.tmax >= UMBRAL_CALOR_FUERTE).sum()
anual["tmax_maxima"] = por_anio(V.tmax).max()
anual["tmin_minima"] = por_anio(V.tmin).min()
anual["gdd_may_sep"] = por_anio(sub(V.gdd, range(5, 10))).sum()
anual["et0_may_sep_mm"] = por_anio(sub(V.et0, range(5, 10))).sum()
anual["balance_may_sep_mm"] = anual["lluvia_may_sep_mm"] - anual["et0_may_sep_mm"]
anual["vpd_jul_ago"] = por_anio(sub(V.vpd, [7, 8])).mean()
rs = {y: rachas(s < UMBRAL_SECO_MM) for y, s in sub(V.lluvia, range(5, 10)).groupby(sub(V.lluvia, range(5, 10)).index.year)}
anual["racha_seca_max_may_sep"] = pd.Series({y: r.max() for y, r in rs.items()})
anual["rachas_secas_7d_may_sep"] = pd.Series({y: int((r >= 7).sum()) for y, r in rs.items()})
anual["rachas_secas_14d_may_sep"] = pd.Series({y: int((r >= 14).sum()) for y, r in rs.items()})
ult0, pri0 = fechas_helada(V.tmin, 0)
ult2, pri2 = fechas_helada(V.tmin, -2)
anual["ultima_helada_prim_0C_doy"], anual["primera_helada_otono_0C_doy"] = ult0, pri0
anual["ultima_helada_prim_-2C_doy"], anual["primera_helada_otono_-2C_doy"] = ult2, pri2
anual["dias_libres_helada_0C"] = anual["primera_helada_otono_0C_doy"] - anual["ultima_helada_prim_0C_doy"]
anual.to_csv(os.path.join(SALIDA, "clima_resumen_anual.csv"), float_format="%.3f")


def top(col, n=5, asc=False, dec=1, fecha=False):
    s = anual[col].sort_values(ascending=asc).head(n)
    if fecha:
        return ", ".join(f"{int(y)} ({doy_a_texto(v)})" for y, v in s.items())
    return ", ".join(f"{int(y)} ({v:.{dec}f})" for y, v in s.items())


# %% [markdown]
# ## 5. Relaciones entre variables y tendencias

# %%
corr_ventanas = {}
for w, c in [(3, None), (7, "lluvia_7"), (14, "lluvia_14"), (30, "lluvia_30"), (60, "lluvia_60")]:
    serie = V.lluvia.rolling(w).sum() if c is None else V[c]
    j = pd.concat([serie, V.gw], axis=1).dropna()
    j = j[j.index.month.isin(range(5, 10))]
    corr_ventanas[f"{w} días"] = j.iloc[:, 0].corr(j.iloc[:, 1])

persist = {}
for lag in [1, 7, 14, 30]:
    j = pd.concat([V.gw, V.gw.shift(lag)], axis=1).dropna()
    j = j[j.index.month.isin([6, 7, 8, 9])]
    persist[f"{lag} d"] = j.iloc[:, 0].corr(j.iloc[:, 1])

pc = ["pct_tmax", "pct_vpd_7", "pct_gw_7", "pct_lluvia_30", "pct_balance_30", "pct_dias_secos"]
cm = V[V.index.month.isin([6, 7, 8])][pc].corr()
cm.columns = [c.replace("pct_", "") for c in cm.columns]
cm.index = [c.replace("pct_", "") for c in cm.index]


def tendencia(serie):
    x, y = serie.index.values.astype(float), serie.values.astype(float)
    ok = ~np.isnan(y)
    if _st is not None:
        r = _st.linregress(x[ok], y[ok])
        return r.slope, r.slope * (x[ok].max() - x[ok].min()), r.pvalue
    p = np.polyfit(x[ok], y[ok], 1)[0]
    return p, p * (x[ok].max() - x[ok].min()), np.nan


tend = {}
for col in ["tmax_media", "tmin_media", "lluvia_anual_mm", "lluvia_may_sep_mm", "dias_calor_32",
            "gdd_may_sep", "suelo_jul_ago", "dias_libres_helada_0C", "racha_seca_max_may_sep"]:
    tend[col] = tendencia(anual[col].dropna())
tend_df = pd.DataFrame(tend, index=["Cambio por año", "Cambio en todo el periodo", "p-valor"]).T
tend_df["¿Significativo (p<0.05)?"] = tend_df["p-valor"].apply(lambda p: "sin calcular" if pd.isna(p) else ("sí" if p < 0.05 else "no"))


# %% [markdown]
# ## 6. Documento principal (.md)

# %%
def prob_helada_despues(ult, mes_dia):
    ref = (pd.Timestamp("2001-" + mes_dia) - pd.Timestamp("2001-01-01")).days + 1
    return float((ult > ref).mean() * 100)


def prob_helada_antes(pri, mes_dia):
    ref = (pd.Timestamp("2001-" + mes_dia) - pd.Timestamp("2001-01-01")).days + 1
    return float((pri < ref).mean() * 100)


helada_tabla = pd.DataFrame({
    "Última helada de primavera": [doy_a_texto(ult0.mean()), doy_a_texto(ult2.mean())],
    "Más temprana": [doy_a_texto(ult0.min()), doy_a_texto(ult2.min())],
    "Más tardía": [doy_a_texto(ult0.max()), doy_a_texto(ult2.max())],
    "Primera helada de otoño": [doy_a_texto(pri0.mean()), doy_a_texto(pri2.mean())],
    "Más temprana ": [doy_a_texto(pri0.min()), doy_a_texto(pri2.min())],
    "Más tardía ": [doy_a_texto(pri0.max()), doy_a_texto(pri2.max())]},
    index=["Tmin ≤ 0 °C", "Tmin ≤ -2 °C"])

riesgo_fechas = pd.DataFrame({
    "% de años": [prob_helada_despues(ult0, "05-01"), prob_helada_despues(ult0, "05-15"),
                  prob_helada_antes(pri0, "10-01"), prob_helada_antes(pri0, "10-15")]},
    index=["Helada (≤0 °C) después del 1 de mayo", "Helada (≤0 °C) después del 15 de mayo",
           "Helada (≤0 °C) antes del 1 de octubre", "Helada (≤0 °C) antes del 15 de octubre"])

gdd_fechas = {}
for etiqueta, (m, d) in {"1 jun": (6, 1), "1 jul": (7, 1), "1 ago": (8, 1), "1 sep": (9, 1), "1 oct": (10, 1)}.items():
    vals = []
    for y in anual.index:
        ant = V.gdd_acum[(V.index.year == y) & ((V.index.month < m) | ((V.index.month == m) & (V.index.day < d)))].dropna()
        vals.append(ant.iloc[-1] if len(ant) else np.nan)
    gdd_fechas[etiqueta] = pd.Series(vals)
gdd_df = pd.DataFrame({k: [v.mean(), v.min(), v.max()] for k, v in gdd_fechas.items()},
                      index=["Promedio", "Mínimo", "Máximo"])

ref_mes = pd.DataFrame(index=MESES)
for nombre, col in [("Tmax °C", "tmax"), ("Suelo 7d", "gw_7"), ("Lluvia 30d mm", "lluvia_30"), ("Balance 30d mm", "balance_30")]:
    g = V[V.index.year <= BASE_FIN].groupby(V[V.index.year <= BASE_FIN].index.month)[col]
    ref_mes[nombre + " P10"] = g.quantile(0.10).values
    ref_mes[nombre + " P50"] = g.quantile(0.50).values
    ref_mes[nombre + " P90"] = g.quantile(0.90).values

calidad = {
    "dias": int(len(df)),
    "faltantes": int(df.isna().sum().sum()),
    "duplicados": int(df.index.duplicated().sum()),
    "tmax_menor_tmin": int((df.T2M_MAX < df.T2M_MIN).sum()),
    "gw_fuera_0_1": int(((df.GWETROOT < 0) | (df.GWETROOT > 1)).sum()),
    "lluvia_negativa": int((df.PRECTOTCORR < 0).sum()),
}

anio_ini, anio_fin = int(V.index.year.min()), int(V.index.year.max())
lluvia_anual_media = anual.lluvia_anual_mm.mean()
md = []
A = md.append
A(f"# Perfil climático para el modelo\n")
A(f"NASA Space Apps 2026 - \"Cambio de rumbo\". Equipo de modelo, parte de clima.  ")
A(f"Fuente única: NASA POWER diario (MERRA-2), {anio_ini}-{anio_fin}. Punto: lat {LAT}, lon {LON}"
  + (f", elevación {META['elevacion_m']:.0f} m" if "elevacion_m" in META else "") + ".  ")
A("Este documento **no propone el modelo**: entrega toda la información de clima que el modelo puede usar. "
  "La tabla diaria completa está en `clima_variables_diarias.csv`.\n")

A("## 1. Lo más importante en pocas líneas\n")
A(f"- **Datos completos y limpios:** {calidad['dias']:,} días, {calidad['faltantes']} faltantes, {calidad['duplicados']} duplicados, sin valores físicamente imposibles.")
A(f"- **Lluvia media anual: {lluvia_anual_media:.0f} mm.** Lo más lluvioso es junio ({mensual.loc['jun', 'Lluvia mm']:.0f} mm) y lo más seco enero ({mensual.loc['ene', 'Lluvia mm']:.0f} mm).")
A(f"- **Julio es el mes más caliente** (Tmax promedio {mensual.loc['jul', 'Tmax °C']:.1f} °C) y enero el más frío (Tmin promedio {mensual.loc['ene', 'Tmin °C']:.1f} °C).")
A(f"- **Temporada sin helada:** la última helada de primavera cae en promedio el {doy_a_texto(ult0.mean())} y la primera de otoño el {doy_a_texto(pri0.mean())} (Tmin ≤ 0 °C), unos {anual.dias_libres_helada_0C.mean():.0f} días libres de helada.")
A(f"- **GDD de mayo a septiembre:** {anual.gdd_may_sep.mean():.0f} °C·día en promedio (de {anual.gdd_may_sep.min():.0f} a {anual.gdd_may_sep.max():.0f}).")
A(f"- **Años secos de verano:** {top('lluvia_may_sep_mm', 3, True)} (lluvia mayo-sep, mm). **Años húmedos de primavera:** {top('lluvia_abr_jun_mm', 3)} (lluvia abr-jun, mm).")
A(f"- **La humedad del suelo sigue mejor a la lluvia de los últimos 14-30 días** (correlación {corr_ventanas['30 días']:.2f} con 30 días y {corr_ventanas['7 días']:.2f} con 7 días, mayo-sep). Entre noviembre y marzo la humedad del suelo no sirve como señal (queda plana, probable suelo congelado).")
A(f"- **La humedad del suelo tiene memoria:** hoy se parece mucho a la de hace 7 días (correlación {persist['7 d']:.2f}) y todavía a la de hace 30 días ({persist['30 d']:.2f}).")
A(f"- **Varios indicadores se mueven juntos** (ver sección 9): por ejemplo, lluvia de 30 días y balance de 30 días ({cm.loc['lluvia_30', 'balance_30']:.2f}), o VPD y humedad del suelo ({cm.loc['vpd_7', 'gw_7']:.2f}). No conviene tratarlos como señales independientes.\n")

A("## 2. Datos y calidad\n")
A("| Variable | Qué es | Unidad |\n|---|---|---|\n| T2M_MAX / T2M_MIN | Temperatura máxima / mínima del día a 2 m | °C |\n| T2MDEW | Punto de rocío o de escarcha a 2 m | °C |\n| GWETROOT | Humedad del suelo en la zona de raíces | 0 a 1 |\n| PRECTOTCORR | Lluvia corregida | mm/día |\n")
A("- Hora: **LST** (hora solar local), días completos. Resolución espacial de MERRA-2: celda de unos 0.5° × 0.625° (≈ 50 × 60 km).")
A(f"- Revisiones físicas: Tmax < Tmin: {calidad['tmax_menor_tmin']}, humedad de suelo fuera de 0-1: {calidad['gw_fuera_0_1']}, lluvia negativa: {calidad['lluvia_negativa']}.")
A("- ⚠ La lluvia y la temperatura son **modeladas** (reanálisis), no medidas en la parcela. Sirven para comparar contra lo normal, no como medición local.\n")

A("## 3. Variables derivadas disponibles (columnas de `clima_variables_diarias.csv`)\n")
dic = [
    ("tmedia, rango_diurno", "Temperatura media y diferencia Tmax - Tmin", "°C"),
    ("deficit_rocio, hr_aprox", "Tmedia - punto de rocío; humedad relativa aproximada (de Tmedia y rocío)", "°C; %"),
    ("lluvia_7, _14, _30, _60", "Lluvia acumulada de los últimos 7, 14, 30 y 60 días", "mm"),
    ("dias_secos", "Días seguidos con lluvia < 1 mm", "días"),
    ("dias_con_lluvia_30", "Días con lluvia ≥ 1 mm en los últimos 30", "días"),
    ("gdd, gdd_acum", "Grados-día base 10 con tope 30 (diario) y acumulado desde el 1 de mayo hasta el 31 de octubre", "°C·día"),
    ("dias_calor_7, _30", f"Días con Tmax ≥ {UMBRAL_CALOR} °C en los últimos 7 y 30", "días"),
    ("dias_helada_3, tmin_min_3", "Días con Tmin ≤ 0 °C y Tmin más baja en los últimos 3 días", "días; °C"),
    ("tmax_media_7", "Tmax promedio de 7 días", "°C"),
    ("vpd, vpd_7", "Déficit de presión de vapor aprox. (con Tmax y rocío): qué tan seco y 'sediento' está el aire. Diario y promedio de 7 días", "kPa"),
    ("gw_7, gw_cambio_7", "Humedad del suelo promedio de 7 días; cambio frente a hace 7 días", "0-1"),
    ("et0, et0_30", "Evaporación potencial (Hargreaves) diaria y de 30 días", "mm"),
    ("balance_30", "Lluvia de 30 días menos evaporación potencial de 30 días", "mm"),
    ("pct_*", "Percentil (0-100) de cada indicador contra lo normal de esa época (±7 días, base 2000-2020). 50 es lo normal", "0-100"),
    ("anom_tmax, _tmin, _tdew", "Diferencia con la media normal de esa época", "°C"),
    ("razon_lluvia_30", "Lluvia de 30 días dividida entre la normal de esa época (1 = normal)", "razón"),
    ("spi30_aprox", "Índice tipo SPI aproximado de la lluvia de 30 días (negativo = seco, positivo = húmedo; ±1 es moderado, ±2 es extremo)", "desv. estándar"),
]
A("| Columna | Qué es | Unidad |\n|---|---|---|")
for a, b, c in dic:
    A(f"| `{a}` | {b} | {c} |")
A("\n⚠ `vpd` y `et0` son aproximaciones. `spi30_aprox` usa percentiles empíricos y no un ajuste estadístico formal. "
  "Las columnas `pct_*` se calculan con base 2000-2020 (21 años), menos que los 30 ideales.\n")

A("## 4. Clima típico por mes (promedio 2000-2025)\n")
A(md_tabla(mensual, {"Suelo (0-1)": 2, "VPD kPa": 2}, nombre_indice="Mes"))
A("\n- 'Lluvia mm', 'ET0 mm', 'Balance mm', 'Días calor', 'Días helada' y 'GDD' son **totales por mes**, no promedios diarios.")
A("- El balance (lluvia - ET0) es negativo en los meses de verano: el cultivo depende de la reserva de agua del suelo.\n")

A("## 5. Heladas y temporada de crecimiento\n")
A(md_tabla(helada_tabla, nombre_indice="Umbral"))
A("\n" + md_tabla(riesgo_fechas, 0, nombre_indice="Situación"))
A("\n- ⚠ Son temperaturas de MERRA-2 a 2 m en una celda grande. Una estación local puede registrar heladas distintas (sobre todo en hondonadas).")
A("- La ventana de helada que usa un modelo depende del cultivo y de su calendario de siembra: este documento solo da las fechas históricas.\n")
A("**Grados-día acumulados (desde el 1 de mayo) a cada fecha, °C·día:**\n")
A(md_tabla(gdd_df, 0, nombre_indice=""))
A(f"\n- Días de calor por año (Tmax ≥ {UMBRAL_CALOR} °C): promedio {anual.dias_calor_32.mean():.1f}, de {anual.dias_calor_32.min():.0f} a {anual.dias_calor_32.max():.0f}. "
  f"Con Tmax ≥ {UMBRAL_CALOR_FUERTE} °C: promedio {anual.dias_calor_35.mean():.1f}.\n")

A("## 6. Lluvia y rachas secas\n")
A(f"- Lluvia anual: promedio {lluvia_anual_media:.0f} mm, de {anual.lluvia_anual_mm.min():.0f} a {anual.lluvia_anual_mm.max():.0f} mm (variación entre años: {anual.lluvia_anual_mm.std()/lluvia_anual_media*100:.0f}%).")
A(f"- Lluvia mayo-septiembre: promedio {anual.lluvia_may_sep_mm.mean():.0f} mm, de {anual.lluvia_may_sep_mm.min():.0f} a {anual.lluvia_may_sep_mm.max():.0f} mm (variación entre años: {anual.lluvia_may_sep_mm.std()/anual.lluvia_may_sep_mm.mean()*100:.0f}%).")
A(f"- Días con lluvia ≥ 1 mm: {anual.dias_lluvia.mean():.0f} por año. Días con lluvia fuerte (≥ 25 mm): {anual.dias_lluvia_fuerte_25mm.mean():.1f} por año.")
A(f"- Racha seca más larga de mayo a septiembre (días seguidos < 1 mm): promedio {anual.racha_seca_max_may_sep.mean():.1f} días, máximo {anual.racha_seca_max_may_sep.max():.0f}. "
  f"Rachas de 7 días o más: {anual.rachas_secas_7d_may_sep.mean():.1f} por verano; de 14 días o más: {anual.rachas_secas_14d_may_sep.mean():.2f} por verano.")
A(f"- Mayor lluvia en un solo día de cada año: promedio {anual.lluvia_max_1d_mm.mean():.0f} mm (máximo {anual.lluvia_max_1d_mm.max():.0f} mm). En 7 días: promedio {anual.lluvia_max_7d_mm.mean():.0f} mm. En 30 días: promedio {anual.lluvia_max_30d_mm.mean():.0f} mm.\n")

A("## 7. Humedad del suelo\n")
A("**Qué ventana de lluvia explica mejor la humedad del suelo** (correlación, mayo-septiembre):\n")
A(md_tabla(pd.DataFrame({"Correlación": corr_ventanas}), 2, nombre_indice="Lluvia acumulada de"))
A("\n**Memoria de la humedad del suelo** (correlación con su propio valor de hace N días, jun-sep):\n")
A(md_tabla(pd.DataFrame({"Correlación": persist}), 2, nombre_indice="Hace"))
A(f"\n- Humedad del suelo en julio-agosto: promedio {anual.suelo_jul_ago.mean():.2f}, de {anual.suelo_jul_ago.min():.2f} a {anual.suelo_jul_ago.max():.2f}.")
A("- Por la memoria del suelo, un valor extremo de un día suele reflejar lo que pasó en las semanas anteriores, no solo ese día.")
A("- Entre noviembre y marzo la serie puede quedarse idéntica hasta 48 días (probable suelo congelado en MERRA-2, ⚠ inferencia): **no usarla como señal en invierno**.\n")

A("## 8. Valores de referencia por mes (percentiles 10, 50 y 90, base 2000-2020)\n")
A("Sirven para saber qué es 'bajo', 'normal' o 'alto' en cada mes. La versión por cada día del año está en `clima_normales_por_dia.csv`.\n")
A(md_tabla(ref_mes, 2, nombre_indice="Mes"))
A("")

A("## 9. Qué tanto se parecen entre sí los indicadores\n")
A("Correlación entre percentiles en junio-agosto (1 = se mueven igual; 0 = independientes):\n")
A(md_tabla(cm, 2, nombre_indice=""))
A("\n- Si dos indicadores tienen correlación muy alta, aportan casi la misma información y al combinarlos se cuenta dos veces lo mismo.\n")

A("## 10. Años extremos (para contrastar con otras fuentes)\n")
A("Entre paréntesis va el valor del indicador.\n")
A("| Tipo | Años (top 5) |\n|---|---|")
A(f"| Menos lluvia mayo-sep (mm) | {top('lluvia_may_sep_mm', 5, True)} |")
A(f"| Suelo más seco jul-ago (0-1) | {top('suelo_jul_ago', 5, True, 3)} |")
A(f"| Racha seca más larga may-sep (días) | {top('racha_seca_max_may_sep', 5, False, 0)} |")
A(f"| Más lluvia abril-junio (mm) | {top('lluvia_abr_jun_mm')} |")
A(f"| Suelo más húmedo abril-junio (0-1) | {top('suelo_abr_jun', 5, False, 3)} |")
A(f"| Más días de calor (Tmax ≥ {UMBRAL_CALOR} °C) | {top('dias_calor_32', 5, False, 0)} |")
A(f"| Más GDD mayo-sep | {top('gdd_may_sep', 5, False, 0)} |")
A(f"| Menos GDD mayo-sep | {top('gdd_may_sep', 5, True, 0)} |")
A(f"| Última helada de primavera más tardía (fecha) | {top('ultima_helada_prim_0C_doy', 5, False, 0, True)} |")
A(f"| Primera helada de otoño más temprana (fecha) | {top('primera_helada_otono_0C_doy', 5, True, 0, True)} |")
A("\n⚠ Estos rankings son de los datos modelados. **No están confirmados con una fuente oficial** (por ejemplo, NOAA/NCEI o el resumen climático de Iowa): falta ese paso para presentarlos como eventos reales.\n")

A("## 11. Tendencias 2000-2025\n")
A(md_tabla(tend_df, {"Cambio por año": 3, "Cambio en todo el periodo": 2, "p-valor": 3}, nombre_indice="Indicador"))
sig = [k for k, v in tend.items() if not pd.isna(v[2]) and v[2] < 0.05]
A("\n- Con 26 años, una tendencia es indicativa y no concluyente. Si una fila dice 'no' en significativo, no hay que presentarla como cambio real.")
if sig:
    A(f"- Solo salió significativo: {', '.join(sig)}. Como se probaron {len(tend)} indicadores, uno puede salir significativo por azar: tómalo con cautela y no lo presentes como cambio climático sin respaldo adicional.\n")
else:
    A("- Ningún indicador salió significativo.\n")

A("## 12. Cómo unir esto con las demás fuentes del equipo\n")
A("- **Clave de unión:** la fecha (diaria) y la ubicación (lat/lon). Los datos son de la celda MERRA-2 que contiene el punto; para otro lugar hay que bajar el CSV de ese punto.")
A("- **Hora:** los días son en hora solar local (LST), no UTC. Si otra fuente viene en UTC, puede haber un desfase de horas en los límites del día.")
A("- **Si otra fuente es mensual o por temporada:** usa `clima_resumen_mensual.csv` y `clima_resumen_anual.csv`.")
A("- **Percentiles (`pct_*`)** están en la misma escala 0-100, así que se pueden comparar entre variables distintas.")
A("- **Unidades:** temperaturas en °C, lluvia y evaporación en mm, humedad del suelo entre 0 y 1, VPD en kPa.\n")

A("## 13. Límites que hay que declarar\n")
A("1. **Una sola fuente:** NASA POWER (MERRA-2). Lluvia modelada, sin IMERG ni estaciones locales.")
A("2. **Base de 21 años** (2000-2020) para lo 'normal', en vez de 30. Los años 2000-2020 están dentro de la base: compararlos contra ella es en-muestra.")
A("3. **Celda grande** (≈ 50 × 60 km): no captura diferencias locales de lluvia, heladas ni suelos.")
A("4. **VPD y ET0 aproximados;** GDD, calor (32 °C), helada y día seco (1 mm) usan umbrales supuestos para maíz.")
A("5. **Solo un punto probado** (Butler County, Iowa). Para otra zona se repite con su propio CSV.")
A("6. **Variables que este CSV no trae:** viento, radiación solar, humedad relativa medida y nieve. POWER ofrece otros parámetros que se podrían pedir (⚠ nombres exactos sin verificar).\n")

A("## 14. Archivos generados\n")
A("| Archivo | Para qué sirve |\n|---|---|")
A("| `clima_variables_diarias.csv` | Todas las variables derivadas, una fila por día. Para unir con otras fuentes |")
A("| `clima_normales_por_dia.csv` | Media y percentiles por día del año |")
A("| `clima_resumen_anual.csv` | Indicadores por año (lluvia, calor, heladas, GDD, rachas secas...) |")
A("| `clima_resumen_mensual.csv` | Clima típico por mes |")
A("| `clima_perfil.json` | Resumen compacto en JSON |")

with open(os.path.join(SALIDA, "clima_para_modelo.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")


# %% [markdown]
# ## 7. Perfil en JSON

# %%
def r(x, n=2):
    return None if pd.isna(x) else round(float(x), n)


perfil = {
    "fuente": "NASA POWER diario (MERRA-2), hora LST",
    "ubicacion": {"lat": LAT, "lon": LON, "elevacion_m": META.get("elevacion_m")},
    "periodo": [anio_ini, anio_fin], "base_normales": [BASE_INI, BASE_FIN],
    "calidad": calidad,
    "anual": {"lluvia_mm": r(anual.lluvia_anual_mm.mean(), 0), "lluvia_may_sep_mm": r(anual.lluvia_may_sep_mm.mean(), 0),
              "tmax_media": r(anual.tmax_media.mean()), "tmin_media": r(anual.tmin_media.mean()),
              "dias_calor_32": r(anual.dias_calor_32.mean(), 1), "gdd_may_sep": r(anual.gdd_may_sep.mean(), 0),
              "dias_libres_helada_0C": r(anual.dias_libres_helada_0C.mean(), 0)},
    "heladas_0C": {"ultima_primavera_media": doy_a_texto(ult0.mean()), "primera_otono_media": doy_a_texto(pri0.mean())},
    "mensual": mensual.round(2).to_dict(orient="index"),
    "correlacion_suelo_vs_lluvia_acumulada": {k: r(v) for k, v in corr_ventanas.items()},
    "persistencia_suelo": {k: r(v) for k, v in persist.items()},
    "anios_extremos": {
        "menos_lluvia_may_sep": [int(i) for i in anual.lluvia_may_sep_mm.nsmallest(5).index],
        "mas_lluvia_abr_jun": [int(i) for i in anual.lluvia_abr_jun_mm.nlargest(5).index],
        "suelo_mas_seco_jul_ago": [int(i) for i in anual.suelo_jul_ago.nsmallest(5).index],
        "mas_dias_calor": [int(i) for i in anual.dias_calor_32.nlargest(5).index]},
    "advertencias": ["Lluvia y temperatura modeladas (MERRA-2), celda ~50x60 km",
                     "Base de normales de 21 anios", "Eventos historicos sin confirmar con fuente oficial",
                     "VPD y ET0 aproximados; umbrales supuestos para maiz"],
}
with open(os.path.join(SALIDA, "clima_perfil.json"), "w", encoding="utf-8") as f:
    json.dump(perfil, f, ensure_ascii=False, indent=2)

print("Listo. Archivos en:", os.path.abspath(SALIDA))
for n in sorted(os.listdir(SALIDA)):
    print(" -", n)
