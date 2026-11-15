"""Rutas y funciones compartidas por los scripts de humedad del suelo (Modelo 1).

Todos los scripts leen de `datos/` y escriben en `salidas/`, ambas junto a este archivo.
Se pueden cambiar con las variables de entorno DATOS y SALIDAS.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
DATOS = Path(os.environ.get("DATOS", AQUI / "datos"))
SALIDAS = Path(os.environ.get("SALIDAS", AQUI / "salidas"))
SALIDAS.mkdir(parents=True, exist_ok=True)

NASS_CSV = DATOS / "nass_quickstats_iowa_condados.csv"
CORN = "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE"
SOY = "SOYBEANS - YIELD, MEASURED IN BU / ACRE"


def leer_giovanni(ruta):
    """Lee un CSV de 'Time Series, Area-Averaged' de Giovanni (encabezado de metadatos + time,valor)."""
    lineas = Path(ruta).read_text(encoding="utf-8").splitlines()
    ini = next(i for i, l in enumerate(lineas) if l.startswith("time,"))
    d = pd.read_csv(ruta, skiprows=ini)
    d.columns = ["time", "valor"]
    d["time"] = pd.to_datetime(d["time"])
    d.loc[d.valor <= -9000, "valor"] = np.nan  # Fill Value -9999
    return d.set_index("time")["valor"]


def percentil_mensual(s):
    """Percentil de cada mes contra el mismo mes de todos los años (rango / n * 100)."""
    return s.groupby(s.index.month).rank(pct=True) * 100


def leer_nass():
    """Rendimientos de maíz y soya por condado (sin 'OTHER COUNTIES')."""
    ns = pd.read_csv(NASS_CSV)
    ns = ns[ns["Data Item"].isin([CORN, SOY])].copy()
    ns["crop"] = np.where(ns["Data Item"].str.startswith("CORN"), "maiz", "soya")
    ns["v"] = pd.to_numeric(ns["Value"].astype(str).str.replace(",", ""), errors="coerce")
    return ns[~ns.County.str.contains("OTHER")]


def mann_kendall(x):
    """Prueba de tendencia de Mann-Kendall con pendiente de Sen."""
    x = np.asarray(x)
    n = len(x)
    S = 0
    for i in range(n - 1):
        S += np.sign(x[i + 1:] - x[i]).sum()
    var = n * (n - 1) * (2 * n + 5) / 18
    z = (S - np.sign(S)) / np.sqrt(var) if S != 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    sl = [(x[j] - x[i]) / (j - i) for i in range(n) for j in range(i + 1, n)]
    return dict(S=int(S), z=round(z, 2), p=round(p, 3), sen=np.median(sl))


def boot_spearman(a, b, rng, B=5000):
    """Intervalo de confianza 95 % del Spearman por bootstrap."""
    a = np.asarray(a)
    b = np.asarray(b)
    idx = rng.integers(0, len(a), (B, len(a)))
    v = np.array([stats.spearmanr(a[i], b[i])[0] for i in idx])
    return np.nanpercentile(v, [2.5, 97.5]).round(2).tolist()


def kappa(a, b):
    """Kappa de Cohen entre dos clasificaciones binarias."""
    a = np.asarray(a)
    b = np.asarray(b)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return round((po - pe) / (1 - pe), 2)
