"""Paso 4: descarga NLDAS-2 mensual (abril-septiembre, 2000-2025) promediado por condado de Iowa.

Variables: SoilM_0_100cm, SoilM_0_10cm, SMAvail_0_100cm (NLDAS_NOAH0125_M) y Tair, Rainf (NLDAS_FORA0125_M).
Fuente: Earthdata Cloud OPeNDAP (el OPeNDAP antiguo de GES DISC está retirado).
Promedio por condado = media de las celdas de 0.125° cuyo centro cae dentro del condado
(1,004 celdas, entre 4 y 20 por condado).

Requisitos: cuenta de Earthdata y `pip install earthaccess shapely requests`.
La primera vez `earthaccess.login()` pide usuario y contraseña (o lee ~/.netrc).

Uso:
  python 04_descargar_nldas_condados.py              # descarga todo -> datos/nldas_condados_iowa.csv
  python 04_descargar_nldas_condados.py --verificar  # baja solo julio 2012 y lo compara con el CSV existente

Nota: los datos del repo se obtuvieron con esta misma lógica ejecutada desde el navegador
(sesión de Earthdata). Este script no se pudo ejecutar desde el entorno donde se escribió,
por eso trae --verificar: córranlo una vez antes de confiar en una descarga nueva.
"""
import json
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from comun import DATOS

GEOJSON_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
FUENTES = {
    "NOAH": ("C1887990023-GES_DISC", "NLDAS_NOAH0125_M", ["SoilM_0_100cm", "SoilM_0_10cm", "SMAvail_0_100cm"]),
    "FORA": ("C1887583680-GES_DISC", "NLDAS_FORA0125_M", ["Tair", "Rainf"]),
}
FILAS = (122, 148)   # latitudes 40.31-43.56 N  (lat = 25.0625 + 0.125 i)
COLS = (226, 279)    # longitudes -96.69 a -90.06 (lon = -124.9375 + 0.125 j)
NCOL = COLS[1] - COLS[0] + 1


def mapa_celdas():
    """Asigna cada celda de la rejilla NLDAS al condado de Iowa que contiene su centro."""
    from shapely.geometry import Point, shape
    cache = DATOS / "geojson_condados_eua.json"
    if not cache.exists():
        urllib.request.urlretrieve(GEOJSON_URL, cache)
    g = json.loads(cache.read_text())
    ia = [(int(f["id"]), f["properties"]["NAME"], shape(f["geometry"])) for f in g["features"] if f["properties"]["STATE"] == "19"]
    celdas = {}
    for a, i in enumerate(range(FILAS[0], FILAS[1] + 1)):
        for b, j in enumerate(range(COLS[0], COLS[1] + 1)):
            p = Point(-124.9375 + 0.125 * j, 25.0625 + 0.125 * i)
            for fips, _, pg in ia:
                if pg.contains(p):
                    celdas[a * NCOL + b] = fips
                    break
    nombres = {str(f): nm for f, nm, _ in ia}
    centros = {str(f): [round(pg.centroid.y, 3), round(pg.centroid.x, 3)] for f, _, pg in ia}
    (DATOS / "condados_iowa_nombres.json").write_text(json.dumps(nombres, ensure_ascii=False))
    (DATOS / "condados_iowa_centroides.json").write_text(json.dumps(centros))
    return celdas


def bajar_mes(sesion, celdas, y, m, clave):
    coll, prod, variables = FUENTES[clave]
    ym = f"{y}{m:02d}"
    ce = ";".join(f"/{v}[0][{FILAS[0]}:{FILAS[1]}][{COLS[0]}:{COLS[1]}]" for v in variables)
    url = (f"https://opendap.earthdata.nasa.gov/collections/{coll}/granules/"
           f"{prod}.2.0%3A{prod}.A{ym}.020.nc.dap.csv?dap4.ce={urllib.parse.quote(ce)}")
    txt = sesion.get(url, timeout=120).text
    acc = {v: {} for v in variables}
    for linea in txt.splitlines():
        if not linea.startswith("/") or "][" not in linea:
            continue
        cab, *vals = [x.strip() for x in linea.split(",")]
        var = cab[1:cab.index("[")]
        fila = int(cab.split("][")[1].rstrip("]"))
        for b, x in enumerate(vals):
            c = celdas.get(fila * NCOL + b)
            x = float(x)
            if c is None or not np.isfinite(x) or x < -9000 or x > 1e19:
                continue
            acc[var].setdefault(c, []).append(x)
    filas = []
    for var, porc in acc.items():
        for fips, xs in porc.items():
            filas.append((y, m, fips, var, float(np.mean(xs))))
    return filas


def main():
    import earthaccess
    earthaccess.login()
    sesion = earthaccess.get_requests_https_session()
    celdas = mapa_celdas()
    print("celdas en Iowa:", len(celdas), "| condados:", len(set(celdas.values())))
    verificar = "--verificar" in sys.argv
    trabajos = [(2012, 7, k) for k in FUENTES] if verificar else [(y, m, k) for y in range(2000, 2026) for m in range(4, 10) for k in FUENTES]
    with ThreadPoolExecutor(6) as ex:
        res = sum(ex.map(lambda t: bajar_mes(sesion, celdas, *t), trabajos), [])
    d = pd.DataFrame(res, columns=["year", "month", "fips", "var", "valor"])
    w = d.pivot_table(index=["year", "month", "fips"], columns="var", values="valor").reset_index()
    w = w[["year", "month", "fips", "SoilM_0_100cm", "SoilM_0_10cm", "SMAvail_0_100cm", "Tair", "Rainf"]]
    if verificar:
        ref = pd.read_csv(DATOS / "nldas_condados_iowa.csv")
        k = w.merge(ref, on=["year", "month", "fips"], suffixes=("", "_ref"))
        dif = {v: round(float((k[v] - k[v + "_ref"]).abs().max()), 3) for v in ["SoilM_0_100cm", "Tair", "Rainf"]}
        print("julio 2012, diferencia máxima contra el CSV del repo:", dif, "(esperado: < 0.1)")
        return
    w.round({"SoilM_0_100cm": 1, "SoilM_0_10cm": 1, "SMAvail_0_100cm": 1, "Tair": 2, "Rainf": 1}).to_csv(DATOS / "nldas_condados_iowa.csv", index=False)
    print("guardado:", len(w), "filas")


if __name__ == "__main__":
    main()
