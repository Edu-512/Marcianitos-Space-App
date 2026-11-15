"""Paso 8: rotación de cultivos en Butler County (FIPS 19023) con el Cropland Data Layer.

Parte A (tabla del condado, 2008-2025): acres por cultivo de CropScape (GetCDLStat) y el
mínimo de maíz sembrado sobre maíz = max(0, maíz este año - soya el año anterior).
Parte B (píxel por píxel, 2018-2025): transiciones año contra año y patrón de 8 años por píxel
de 30 m. Solo cuenta píxeles con maíz o soya al menos 6 de los 8 años.

Datos (analisis/cdl/datos/, compartidos con los scripts de cdl/): cdl_butler_2008_2025.csv y CDL_<año>_19023.tif (2018-2025).
Uso:
  python 08_cdl_rotacion_butler.py --descargar   # baja tablas y mapas de CropScape (requests)
  python 08_cdl_rotacion_butler.py               # analiza
Salidas: salidas/cdl_butler_resumen.csv, cdl_butler_transiciones.csv, cdl_butler_patrones.csv,
         cdl_butler_cuadrantes.csv, mapa_rotacion_butler_2018_2025.png

Aviso: el CDL se equivoca más en las orillas de los campos, y cada error convierte una rotación
estricta en "rotación con un quiebre" o "irregular". Las clases de pasto, urbano y bosque
cambian de método entre años; no interpretar sus cambios.
"""
import sys

import numpy as np
import pandas as pd
from PIL import Image

from comun import AQUI, SALIDAS

CDL = AQUI.parent / "cdl" / "datos"
CDL.mkdir(parents=True, exist_ok=True)
FIPS = "19023"
ANIOS = list(range(2018, 2026))
MAIZ, SOYA = 1, 5
OTROS_CULTIVOS = {4, 6, 12, 13, 21, 23, 24, 26, 27, 28, 29, 36, 37, 42, 43, 44, 47, 53, 58, 59, 60, 61, 68, 69, 70,
                  71, 205, 221, 225, 229, 241, 243}
ACRES_PIXEL = 900 / 4046.86


def descargar():
    import re
    import requests
    base = "https://nassgeodata.gmu.edu/axis2/services/CDLService"
    tablas = []
    for y in range(2008, 2026):
        url = re.search(r"<returnURL>(.*?)</returnURL>", requests.get(f"{base}/GetCDLStat?year={y}&fips={FIPS}&format=csv", timeout=60).text).group(1)
        t = pd.read_csv(url, skipinitialspace=True)
        t.columns = ["codigo", "categoria", "pixeles", "acres"]
        tablas.append(t.assign(anio=y))
        if y in ANIOS:
            url = re.search(r"<returnURL>(.*?)</returnURL>", requests.get(f"{base}/GetCDLFile?year={y}&fips={FIPS}", timeout=60).text).group(1)
            (CDL / f"CDL_{y}_{FIPS}.tif").write_bytes(requests.get(url, timeout=120).content)
    pd.concat(tablas)[["anio", "codigo", "categoria", "pixeles", "acres"]].to_csv(CDL / "cdl_butler_2008_2025.csv", index=False)


def resumen_condado():
    d = pd.read_csv(CDL / "cdl_butler_2008_2025.csv")
    p = d.pivot_table(index="anio", columns="categoria", values="acres", fill_value=0)
    t = p[["Corn", "Soybeans"]].copy()
    t["pct_maiz_de_maiz_soya"] = 100 * t.Corn / (t.Corn + t.Soybeans)
    t["maiz_sobre_maiz_min_acres"] = (t.Corn - t.Soybeans.shift(1)).clip(lower=0)
    t["maiz_sobre_maiz_min_pct"] = 100 * t.maiz_sobre_maiz_min_acres / t.Corn
    t["barbecho_sin_sembrar"] = p.get("Fallow/Idle Cropland", 0)
    t["avena"] = p.get("Oats", 0)
    t["heno_alfalfa"] = p.get("Alfalfa", 0) + p.get("Other Hay/Non Alfalfa", 0)
    t.round(1).to_csv(SALIDAS / "cdl_butler_resumen.csv")
    return t


def categoria(a):
    c = np.full(a.shape, "N", dtype="<U1")
    c[np.isin(a, list(OTROS_CULTIVOS))] = "O"
    c[a == SOYA] = "S"
    c[a == MAIZ] = "C"
    return c


def patrones_pixel():
    pila = {y: np.array(Image.open(CDL / f"CDL_{y}_{FIPS}.tif")) for y in ANIOS}
    forma = {a.shape for a in pila.values()}
    assert len(forma) == 1, f"los mapas no tienen el mismo recorte: {forma}"

    # transiciones año contra año
    tr = []
    for y0, y1 in zip(ANIOS[:-1], ANIOS[1:]):
        a, b = pila[y0], pila[y1]
        maiz_hoy = b == MAIZ
        tras_maiz = (maiz_hoy & (a == MAIZ)).sum()
        tras_soya = (maiz_hoy & (a == SOYA)).sum()
        tras_otro = (maiz_hoy & ~np.isin(a, [MAIZ, SOYA])).sum()
        soya_soya = ((b == SOYA) & (a == SOYA)).sum()
        tr.append(dict(anio=y1, pct_maiz_tras_maiz=round(100 * tras_maiz / maiz_hoy.sum(), 1),
                       pct_maiz_tras_soya=round(100 * tras_soya / maiz_hoy.sum(), 1),
                       pct_maiz_tras_otro=round(100 * tras_otro / maiz_hoy.sum(), 1),
                       pct_soya_tras_soya=round(100 * soya_soya / (b == SOYA).sum(), 1)))
    pd.DataFrame(tr).to_csv(SALIDAS / "cdl_butler_transiciones.csv", index=False)

    # patrón de 8 años
    cat = np.stack([categoria(pila[y]) for y in ANIOS])
    es_c, es_s = cat == "C", cat == "S"
    n_cs = (es_c | es_s).sum(0)
    n_c = es_c.sum(0)
    cambios = ((es_c[:-1] & es_s[1:]) | (es_s[:-1] & es_c[1:])).sum(0)
    clase = np.zeros(n_cs.shape, np.uint8)  # 0 = sin maíz/soya la mayoría de años
    ok = n_cs >= 6
    clase[ok] = 5                                     # irregular
    clase[ok & (n_c <= 2)] = 4                        # soya dominante
    clase[ok & (n_c >= 6)] = 3                        # maíz continuo
    clase[ok & (cambios >= 5)] = 2                    # rotación con un quiebre
    clase[ok & (cambios == 7)] = 1                    # rotación estricta
    nombres = {1: "rotacion estricta maiz-soya", 2: "rotacion con 1 quiebre", 3: "maiz continuo (6+ de 8)",
               4: "soya dominante", 5: "irregular"}
    tot = ok.sum()
    pat = pd.DataFrame([(nm, int((clase == k).sum()), round((clase == k).sum() * ACRES_PIXEL), round(100 * (clase == k).sum() / tot, 1))
                        for k, nm in nombres.items()], columns=["patron", "pixeles", "acres", "pct"])
    pat.to_csv(SALIDAS / "cdl_butler_patrones.csv", index=False)

    H, W = clase.shape
    filas = []
    for nom, rs, cs in [("noroeste", slice(0, H // 2), slice(0, (W + 1) // 2)), ("noreste", slice(0, H // 2), slice((W + 1) // 2, W)),
                        ("suroeste", slice(H // 2, H), slice(0, (W + 1) // 2)), ("sureste", slice(H // 2, H), slice((W + 1) // 2, W))]:
        q = clase[rs, cs]
        n = (q > 0).sum()
        filas.append(dict(cuadrante=nom, pct_maiz_continuo=round(100 * (q == 3).sum() / n, 1), pct_rotacion_estricta=round(100 * (q == 1).sum() / n, 1)))
    pd.DataFrame(filas).to_csv(SALIDAS / "cdl_butler_cuadrantes.csv", index=False)

    # mapa
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    colores = ["#ececE8", "#2563eb", "#93bbf5", "#d97706", "#16a34a", "#787878"]
    fondo = pila[ANIOS[-1]] == 0
    img = np.ma.masked_where(fondo, clase)
    fig, ax = plt.subplots(figsize=(8, 8.6))
    ax.imshow(img, cmap=ListedColormap(colores), vmin=0, vmax=5, interpolation="nearest")
    ax.set_axis_off()
    ax.set_title("Butler County, Iowa: patrón de cultivo 2018-2025 por píxel de 30 m (CDL)", loc="left", fontsize=11)
    etiquetas = ["Sin maíz/soya la mayoría de años", "Rotación estricta maíz-soya", "Rotación con 1 quiebre",
                 "Maíz continuo (6+ de 8 años)", "Soya dominante", "Irregular"]
    ax.legend(handles=[Patch(color=c, label=l) for c, l in zip(colores[1:] + colores[:1], etiquetas[1:] + etiquetas[:1])],
              loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=8, frameon=False)
    fig.savefig(SALIDAS / "mapa_rotacion_butler_2018_2025.png", dpi=150, bbox_inches="tight")
    return pat, pd.DataFrame(tr), pd.DataFrame(filas)


if __name__ == "__main__":
    if "--descargar" in sys.argv:
        descargar()
    print(resumen_condado()[["maiz_sobre_maiz_min_pct", "barbecho_sin_sembrar"]].round(1).to_string())
    for t in patrones_pixel():
        print(t.to_string(index=False))
