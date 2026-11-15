import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
# Verificación del CSV de NASA POWER (Iowa) - versión .py para VS Code
# Cada "# %%" es una celda: en VS Code puedes ejecutarlas una por una (Run Cell) o todo el archivo.
# Requisitos: pip install pandas numpy matplotlib

# %%
try:
    from IPython.display import display
except ImportError:
    display = print

# %% [markdown]
# # Verificación del CSV de NASA POWER (Iowa, Butler County)
# Equipo de modelo · NASA Space Apps 2026 · "Cambio de rumbo"
# 
# Este notebook comprueba la calidad del CSV y valida los hallazgos clave del modelo v1.
# Al final genera `reporte_verificacion.json`, `reporte_verificacion.md` y gráficas PNG para pasar al compañero.
# **Pasos:** sube el CSV a Colab, ajusta `RUTA_CSV` y ejecuta todo (Entorno de ejecución > Ejecutar todo).

# %%
import json, zipfile, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

RUTA_CSV = "datos/POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST.csv"   # mismo folder que este script, o ruta completa
VARS = ["T2M_MAX", "T2M_MIN", "T2MDEW", "GWETROOT", "PRECTOTCORR"]
INICIO, FIN = "2000-01-01", "2025-12-31"
BASE_INI, BASE_FIN = 2000, 2020         # periodo base para percentiles
os.makedirs("salida", exist_ok=True)
reporte = []                            # lista de comprobaciones

def anotar(nombre, ok, detalle=""):
    reporte.append({"comprobacion": nombre, "ok": bool(ok), "detalle": str(detalle)})
    print(("✅" if ok else "⚠️ "), nombre, "-", detalle)

# %% [markdown]
# ## 1. Carga robusta del CSV

# %%
def cargar_power(ruta):
    with open(ruta, encoding="utf-8") as f:
        lineas = f.readlines()
    skip = 0
    for i, l in enumerate(lineas):                 # salta el encabezado de metadatos de POWER
        if "END HEADER" in l.upper():
            skip = i + 1
            break
    df = pd.read_csv(ruta, skiprows=skip)
    df.columns = [c.strip() for c in df.columns]
    if {"YEAR", "DOY"} <= set(df.columns):          # formato de tu archivo: YEAR,DOY
        df["fecha"] = pd.to_datetime(df.YEAR.astype(str), format="%Y") + pd.to_timedelta(df.DOY - 1, unit="D")
    elif {"YEAR", "MO", "DY"} <= set(df.columns):
        df["fecha"] = pd.to_datetime(dict(year=df.YEAR, month=df.MO, day=df.DY))
    else:
        col = next(c for c in df.columns if c.lower() in ("date", "fecha", "time"))
        f = pd.to_datetime(df[col], format="%m/%d/%Y", errors="coerce")   # formato MM/DD/YYYY del viewer
        df["fecha"] = f.fillna(pd.to_datetime(df[col], errors="coerce"))
    df = df.set_index("fecha").sort_index()
    df = df.drop(columns=[c for c in ["YEAR", "DOY", "MO", "DY"] if c in df.columns])
    df = df.replace(-999, np.nan)                  # -999 = faltante en POWER
    return df

df = cargar_power(RUTA_CSV)
print(df.shape)
print("Columnas:", list(df.columns))
df.head()

# %% [markdown]
# ## 2. Estructura y continuidad

# %%
faltan_cols = [v for v in VARS if v not in df.columns]
anotar("Columnas esperadas presentes", not faltan_cols, f"faltan: {faltan_cols}" if faltan_cols else "las 5 variables")

esperado = pd.date_range(INICIO, FIN, freq="D")
anotar("Rango de fechas", df.index.min() == esperado[0] and df.index.max() == esperado[-1],
       f"{df.index.min().date()} a {df.index.max().date()}")
anotar("Número de días = 9,497", len(df) == len(esperado), f"{len(df)} filas vs {len(esperado)} esperadas")
anotar("Sin fechas duplicadas", not df.index.duplicated().any(), f"{df.index.duplicated().sum()} duplicadas")
huecos = esperado.difference(df.index)
anotar("Sin días faltantes en el calendario", len(huecos) == 0, f"{len(huecos)} días ausentes")

v = [c for c in VARS if c in df.columns]
nulos = df[v].isna().sum()
anotar("Sin valores faltantes (-999/NaN)", nulos.sum() == 0, nulos.to_dict())

# %% [markdown]
# ## 3. Revisiones físicas

# %%
d = df.copy()
chk = {
 "Tmax >= Tmin":            (d.T2M_MAX < d.T2M_MIN).sum(),
 "Punto de rocío <= Tmax":  (d.T2MDEW > d.T2M_MAX + 0.5).sum(),
 "GWETROOT en [0,1]":       ((d.GWETROOT < 0) | (d.GWETROOT > 1)).sum(),
 "Lluvia >= 0":             (d.PRECTOTCORR < 0).sum(),
 "Tmax en [-50, 55] °C":    ((d.T2M_MAX < -50) | (d.T2M_MAX > 55)).sum(),
 "Lluvia diaria <= 300 mm": (d.PRECTOTCORR > 300).sum(),
}
for k, n in chk.items():
    anotar(f"Física: {k}", n == 0, f"{n} violaciones")

# saltos sospechosos día a día
for c, umbral in [("T2M_MAX", 20), ("T2M_MIN", 20), ("GWETROOT", 0.25)]:
    saltos = (d[c].diff().abs() > umbral).sum()
    anotar(f"Saltos diarios de {c} > {umbral}", saltos < 10, f"{saltos} días (revisar si son muchos)")

# valores repetidos (posible relleno). GWETROOT se queda quieta en invierno (suelo congelado en MERRA-2): se revisa solo abr-oct
for c in ["T2M_MAX", "T2M_MIN", "GWETROOT"]:
    s_ = d[c]
    n = s_.groupby((s_ != s_.shift()).cumsum()).transform("size")
    if c == "GWETROOT":
        racha_inv = n[d.index.month.isin([11, 12, 1, 2, 3])].max()
        racha = n[d.index.month.isin(range(4, 11))].max()
        print(f"GWETROOT: racha máx. en nov-mar = {racha_inv} d (esperable, suelo congelado); no usar GWETROOT invernal como señal")
    else:
        racha = n.max()
    anotar(f"Racha máx. de valores idénticos en {c}" + (" (abr-oct)" if c == "GWETROOT" else ""), racha <= 10, f"{racha} días seguidos")

# %% [markdown]
# ## 4. Estadística descriptiva y climatología

# %%
desc = df[v].describe().T
desc["pct_dias_lluvia>=1mm"] = np.nan
desc.loc["PRECTOTCORR", "pct_dias_lluvia>=1mm"] = (df.PRECTOTCORR >= 1).mean() * 100
display(desc.round(3))

mensual = df.groupby(df.index.month).agg(
    Tmax=("T2M_MAX", "mean"), Tmin=("T2M_MIN", "mean"),
    GWETROOT=("GWETROOT", "mean"), lluvia_mm_mes=("PRECTOTCORR", lambda s: s.sum() / 26))
display(mensual.round(2))
anotar("Ciclo estacional coherente (jul más cálido que ene)", mensual.Tmax[7] > mensual.Tmax[1] + 15,
       f"Tmax ene {mensual.Tmax[1]:.1f} °C, jul {mensual.Tmax[7]:.1f} °C")
anotar("Lluvia anual media plausible para Iowa (600-1200 mm)", 600 < df.PRECTOTCORR.sum()/26 < 1200,
       f"{df.PRECTOTCORR.sum()/26:.0f} mm/año")

fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
mensual.Tmax.plot(ax=ax[0], marker="o"); mensual.Tmin.plot(ax=ax[0], marker="o"); ax[0].set_title("Temperatura media mensual (°C)"); ax[0].legend(["Tmax", "Tmin"])
mensual.lluvia_mm_mes.plot.bar(ax=ax[1]); ax[1].set_title("Lluvia media por mes (mm)")
mensual.GWETROOT.plot(ax=ax[2], marker="o"); ax[2].set_title("GWETROOT medio por mes")
plt.tight_layout(); plt.savefig("salida/climatologia_mensual.png", dpi=150); plt.show()

# %% [markdown]
# ## 5. Años secos y húmedos (validar hallazgos)

# %%
ms = df[(df.index.month >= 5) & (df.index.month <= 9)]
lluvia_msep = ms.groupby(ms.index.year).PRECTOTCORR.sum().rename("lluvia_may_sep_mm")
ja = df[(df.index.month >= 7) & (df.index.month <= 8)]
gw_ja = ja.groupby(ja.index.year).GWETROOT.mean().rename("GWETROOT_jul_ago")
anual = pd.concat([lluvia_msep, gw_ja], axis=1)
display(anual.sort_values("lluvia_may_sep_mm").head(6).round(3))
secos = list(anual.lluvia_may_sep_mm.nsmallest(3).index)
secos_gw = list(anual.GWETROOT_jul_ago.nsmallest(3).index)
anotar("2012 y 2023 entre los 3 años más secos (lluvia may-sep)", {2012, 2023} <= set(secos), f"top 3 secos: {secos}")
anotar("2012 y 2023 entre los 3 años con menor GWETROOT jul-ago", {2012, 2023} <= set(secos_gw), f"top 3: {secos_gw}")

# exceso de lluvia abr-jun
aj = df[(df.index.month >= 4) & (df.index.month <= 6)]
lluvia_aj = aj.groupby(aj.index.year).PRECTOTCORR.sum().rename("lluvia_abr_jun_mm")
gw_aj = aj.groupby(aj.index.year).GWETROOT.mean().rename("GWETROOT_abr_jun")
print("Ranking lluvia abr-jun (mm):"); print(lluvia_aj.sort_values(ascending=False).head(8).round(0))
print("Ranking GWETROOT abr-jun:"); print(gw_aj.sort_values(ascending=False).head(6).round(3))
print("Posición de 2019 -> por lluvia abr-jun:", int(lluvia_aj.rank(ascending=False)[2019]), "| por GWETROOT abr-jun:", int(gw_aj.rank(ascending=False)[2019]))
anotar("2008 y 2013 entre los 3 años más lluviosos abr-jun", {2008, 2013} <= set(lluvia_aj.nlargest(3).index), f"top 3 lluvia: {list(lluvia_aj.nlargest(3).index)}")
anotar("2008, 2013 y 2019 entre los 3 con mayor GWETROOT abr-jun (⚠ eventos de memoria)", {2008, 2013, 2019} <= set(gw_aj.nlargest(3).index), f"top 3 GWETROOT: {list(gw_aj.nlargest(3).index)}")

fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
anual.lluvia_may_sep_mm.plot.bar(ax=ax[0]); ax[0].axhline(anual.lluvia_may_sep_mm.mean(), ls="--", c="k"); ax[0].set_title("Lluvia mayo-sep (mm)")
lluvia_aj.plot.bar(ax=ax[1], color="tab:blue"); ax[1].axhline(lluvia_aj.mean(), ls="--", c="k"); ax[1].set_title("Lluvia abr-jun (mm)")
plt.tight_layout(); plt.savefig("salida/anios_secos_humedos.png", dpi=150); plt.show()

# %% [markdown]
# ## 6. ¿Qué ventana de lluvia explica la humedad de suelo?

# %%
res = {}
for w in [3, 7, 14, 30, 60]:
    acum = df.PRECTOTCORR.rolling(w).sum()
    sub = pd.concat([acum, df.GWETROOT], axis=1).dropna()
    sub = sub[(sub.index.month >= 5) & (sub.index.month <= 9)]
    res[w] = sub.iloc[:, 0].corr(sub.iloc[:, 1])
corr = pd.Series(res, name="corr_GWETROOT_vs_lluvia_acum_may_sep")
print(corr.round(3))
mejor = corr.idxmax()
anotar("Mejor ventana de lluvia para GWETROOT es 14-30 d", mejor in (14, 30), f"mejor={mejor} d, r={corr.max():.2f}; r(30d)={corr[30]:.2f} (esperado ~0.55)")
corr.plot.bar(title="Correlación GWETROOT vs lluvia acumulada (may-sep)"); plt.ylabel("r de Pearson")
plt.tight_layout(); plt.savefig("salida/corr_ventanas.png", dpi=150); plt.show()

# %% [markdown]
# ## 7. Base de percentiles 2000-2020 (ventana ±7 días)

# %%
base = df[(df.index.year >= BASE_INI) & (df.index.year <= BASE_FIN)].copy()
base["doy"] = base.index.dayofyear
n_anios = BASE_FIN - BASE_INI + 1

def n_muestras(doy, ancho=7):
    dist = (base.doy - doy).abs()
    dist = np.minimum(dist, 366 - dist)       # circular
    return (dist <= ancho).sum()

conteos = pd.Series({d: n_muestras(d) for d in range(1, 367)})
print(f"Años en la base: {n_anios}  (30 sería lo ideal)")
print(f"Muestras por ventana: mín {conteos.min()}, mediana {int(conteos.median())}, máx {conteos.max()}")
anotar("Tamaño de muestra por ventana ≥ 250", conteos.min() >= 250, f"mínimo {conteos.min()} (≈{n_anios}×15 esperado)")

# estabilidad: percentil 90 de lluvia 30 d y de Tmax con base completa vs mitad
def p_ventana(serie, doy, q, ancho=7):
    dist = (base.doy - doy).abs(); dist = np.minimum(dist, 366 - dist)
    return base.loc[dist <= ancho, serie].quantile(q)
for c in ["T2M_MAX", "GWETROOT"]:
    p = pd.Series({d: p_ventana(c, d, 0.9) for d in range(1, 366, 5)})
    print(f"P90 de {c}: rango a lo largo del año = {p.min():.2f} a {p.max():.2f}")

# %% [markdown]
# ## 8. Umbrales del modelo: cuántos días se activan

# %%
umbrales = {
  "Días de calor (Tmax >= 32 °C)": (df.T2M_MAX >= 32),
  "Días de helada (Tmin <= 0 °C)": (df.T2M_MIN <= 0),
  "Días secos (< 1 mm)": (df.PRECTOTCORR < 1),
  "Lluvia fuerte (>= 25 mm)": (df.PRECTOTCORR >= 25),
}
for k, s in umbrales.items():
    print(f"{k}: {s.sum()} días ({s.mean()*100:.1f}%) · por año ≈ {s.sum()/26:.1f}")

# helada solo en ventanas relevantes para maíz (abr-may, sep-oct)
m = df.index.month
helada_ventana = ((df.T2M_MIN <= 0) & m.isin([4, 5, 9, 10]))
anotar("Heladas en abr-may/sep-oct ocurren (el semáforo puede activarse)", helada_ventana.sum() > 0, f"{helada_ventana.sum()} días en 26 años")

# GDD base 10 tope 30
tmax_c = df.T2M_MAX.clip(upper=30).clip(lower=10); tmin_c = df.T2M_MIN.clip(upper=30).clip(lower=10)
gdd = ((tmax_c + tmin_c) / 2 - 10)
gdd_msep = gdd[(gdd.index.month >= 5) & (gdd.index.month <= 9)].groupby(gdd[(gdd.index.month >= 5) & (gdd.index.month <= 9)].index.year).sum()
print("GDD may-sep (base 10, tope 30): media", round(gdd_msep.mean()), "rango", round(gdd_msep.min()), "-", round(gdd_msep.max()))
anotar("GDD may-sep plausible para Iowa (1,200-1,900 °C·día; ≈2,200-3,400 °F·día)", 1200 < gdd_msep.mean() < 1900, f"media {gdd_msep.mean():.0f} °C·día")

# %% [markdown]
# ## 9. Tendencia (aviso sobre no estacionariedad)

# %%
anual_t = df.groupby(df.index.year).agg(Tmax=("T2M_MAX", "mean"), Tmin=("T2M_MIN", "mean"), lluvia=("PRECTOTCORR", "sum"))
for c in anual_t.columns:
    pend = np.polyfit(anual_t.index, anual_t[c], 1)[0]
    print(f"Tendencia {c}: {pend:+.3f} por año ({pend*26:+.2f} en 26 años)")
print("Nota: con 26 años la tendencia es indicativa, no concluyente.")

# %% [markdown]
# ## 10. Reporte para el compañero

# %%
ok = sum(r["ok"] for r in reporte)
resumen = {"total_comprobaciones": len(reporte), "ok": ok, "con_aviso": len(reporte) - ok,
           "archivo": RUTA_CSV, "dias": int(len(df)), "base_percentiles": f"{BASE_INI}-{BASE_FIN}"}
with open("salida/reporte_verificacion.json", "w", encoding="utf-8") as f:
    json.dump({"resumen": resumen, "comprobaciones": reporte}, f, ensure_ascii=False, indent=2)

with open("salida/reporte_verificacion.md", "w", encoding="utf-8") as f:
    f.write(f"# Reporte de verificación del CSV\n\n{ok}/{len(reporte)} comprobaciones OK\n\n")
    f.write("| Comprobación | Estado | Detalle |\n|---|---|---|\n")
    for r in reporte:
        f.write(f"| {r['comprobacion']} | {'OK' if r['ok'] else 'AVISO'} | {r['detalle']} |\n")

with zipfile.ZipFile("verificacion_csv.zip", "w") as z:
    for fn in os.listdir("salida"):
        z.write(os.path.join("salida", fn), fn)
print(resumen)

try:
    from google.colab import files
    files.download("verificacion_csv.zip")
except Exception:
    pass
