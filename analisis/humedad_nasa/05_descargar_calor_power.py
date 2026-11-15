"""Paso 5: días de calor por condado de Iowa (junio-agosto, 2000-2025) desde NASA POWER.

Variable: T2M_MAX diaria (MERRA-2), en el centroide de cada condado.
Calcula por año: días con máxima > 30, > 32 y > 35 °C, máxima media de julio y de junio-agosto.
Aviso: POWER tiene celdas de ~50 km; varios condados comparten la misma celda.

Requisitos: `pip install requests`. No pide cuenta.
Entrada: datos/condados_iowa_centroides.json (lo genera el paso 4)
Uso:
  python 05_descargar_calor_power.py              # -> datos/calor_condados_iowa.csv
  python 05_descargar_calor_power.py --verificar  # baja solo Story County y lo compara con el CSV existente

Nota: los datos del repo se obtuvieron con esta lógica ejecutada desde el navegador; este script
no se pudo ejecutar desde el entorno donde se escribió. Córranlo una vez con --verificar.
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

from comun import DATOS

URL = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M_MAX&community=AG"
       "&longitude={lon}&latitude={lat}&start=20000101&end=20251231&format=JSON")


def calor_condado(fips, lat, lon):
    for intento in range(3):
        try:
            j = requests.get(URL.format(lat=lat, lon=lon), timeout=120).json()
            break
        except Exception:
            if intento == 2:
                raise
            time.sleep(2)
    d = pd.Series(j["properties"]["parameter"]["T2M_MAX"])
    d = d[d > -900]
    d.index = pd.to_datetime(d.index, format="%Y%m%d")
    d = d[d.index.month.isin([6, 7, 8])]
    filas = []
    for y, s in d.groupby(d.index.year):
        jul = s[s.index.month == 7]
        filas.append(dict(fips=int(fips), year=int(y), d30=int((s > 30).sum()), d32=int((s > 32).sum()), d35=int((s > 35).sum()),
                          tmax_jul=round(jul.mean(), 2), tmax_jja=round(s.mean(), 2), ndays=len(s)))
    return filas


def main():
    cen = json.loads((DATOS / "condados_iowa_centroides.json").read_text())
    if "--verificar" in sys.argv:
        cen = {"19169": cen["19169"]}  # Story County
    with ThreadPoolExecutor(3) as ex:
        res = sum(ex.map(lambda kv: calor_condado(kv[0], *kv[1]), cen.items()), [])
    d = pd.DataFrame(res)
    if "--verificar" in sys.argv:
        ref = pd.read_csv(DATOS / "calor_condados_iowa.csv")
        k = d.merge(ref, on=["fips", "year"], suffixes=("", "_ref"))
        print("Story County, diferencia máxima en días > 32 °C:", int((k.d32 - k.d32_ref).abs().max()), "(esperado: 0)")
        return
    d.to_csv(DATOS / "calor_condados_iowa.csv", index=False)
    print("guardado:", len(d), "filas")


if __name__ == "__main__":
    main()
