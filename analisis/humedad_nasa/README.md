# Humedad del suelo, clima y rendimiento (Modelo 1)

Análisis exploratorio previo al modelo: evalúa qué información aportan los datos de la NASA
sobre humedad del suelo y clima para explicar el rendimiento de maíz y soya en Iowa.
Las regresiones y validaciones de aquí sirven para elegir variables; no son el modelo.

Documento con los resultados: "Modelo 1 — Análisis de humedad del suelo y rendimiento en Iowa" (Claude Docs).

## Cómo correrlo

```bash
pip install -r ../requirements.txt
python 00_preparar_series.py
python 01_calidad_tendencia_sequia.py
python 02_smap_superficie_raiz.py
python 03_humedad_rendimiento_story.py
python 06_analisis_condados.py        # ~3 min
python 07_pruebas_extra.py            # ~1 min
python 08_cdl_rotacion_butler.py      # requiere los mapas en ../cdl/datos/ (ver abajo)
python 09_cruces_con_otros_equipos.py # ~2 min
```

Cada script lee de `datos/` y escribe en `salidas/`. Los resultados de referencia ya están en `salidas/`;
si vuelven a correr todo, deben salir idénticos (las semillas aleatorias están fijas).

Los pasos 04 y 05 solo hacen falta para volver a descargar los datos por condado
(ya vienen en `datos/`). Necesitan cuenta de Earthdata (paso 4) e internet.
Antes de confiar en una descarga nueva, córranlos con `--verificar`.

## Qué hace cada paso

| Paso | Script | Qué responde | Métodos |
|---|---|---|---|
| 0 | `00_preparar_series.py` | Convierte las descargas de Giovanni y AppEEARS en series mensuales en m³/m³ y percentiles | Conversión de unidades, percentil por mes |
| 1 | `01_calidad_tendencia_sequia.py` | ¿Los datos están completos? ¿Qué años fueron secos? ¿Hay tendencia? ¿Las fuentes coinciden? | Mann-Kendall + Sen, teoría de rachas, Spearman con IC bootstrap, kappa de Cohen |
| 2 | `02_smap_superficie_raiz.py` | ¿Qué capa de SMAP usar? ¿Importa la hora del día? | Coef. de variación, autocorrelación, correlación cruzada, ciclo diario |
| 3 | `03_humedad_rendimiento_story.py` | ¿La humedad explica el rendimiento en Story County? | Anomalía sin tendencia, Spearman, Mann-Whitney, regresión, validación dejando un año fuera |
| 4 | `04_descargar_nldas_condados.py` | Descarga NLDAS-2 por condado (99 condados, abr-sep 2000-2025) | Earthdata Cloud OPeNDAP, promedio de celdas por condado |
| 5 | `05_descargar_calor_power.py` | Descarga días > 30/32/35 °C por condado | NASA POWER (MERRA-2) |
| 6 | `06_analisis_condados.py` | Lo mismo que el paso 3 con ~2,500 observaciones, más calor y derecho 2020 | Ridge y gradient boosting, validación por año y por distrito, IC remuestreando años |
| 7 | `07_pruebas_extra.py` | ¿Ayudan la lluvia de verano y los días > 35 °C? | Validación dejando un año fuera, sin condados del derecho |
| 8 | `08_cdl_rotacion_butler.py` | ¿Cómo rota Butler County, campo por campo? | Transiciones y patrón de 8 años por píxel del CDL |
| 9 | `09_cruces_con_otros_equipos.py` | ¿Se sostienen los hallazgos de QuickStats y del panel de rotación? | Reproducción de cifras, efectos fijos, pruebas placebo y de futuro |

## Datos (`datos/`)

| Archivo | Fuente | Detalle |
|---|---|---|
| `nldas_iowa_*.csv` | Giovanni, NLDAS_NOAH0125_M v2.0 | Área -93.7, 41.9, -93.3, 42.3 (Story County), mensual 2000-2025 |
| `gldas_iowa_*.csv`, `gldas_puebla_*.csv` | Giovanni, GLDAS_NOAH025_M v2.1 | 0-10 cm, mensual 2000-2025 |
| `smap_l4_appeears.csv` | AppEEARS, SPL4SMGP v008 | Puntos iowa (42.07, -93.5) y puebla (19.01, -97.9), 2024-2025, cada 3 h; capas sm_rootzone, sm_rootzone_pctl, sm_surface |
| `openet_iowa_2021_2026_mm.csv` | OpenET Data Explorer (Raster View) | Ensemble mensual cerca de Story County; extraído de la gráfica del sitio |
| `nass_quickstats_iowa_condados.csv` | USDA NASS QuickStats | Rendimiento de maíz grano, soya y ensilaje, 99 condados, 2000-2025 |
| `nldas_condados_iowa.csv` | Paso 4 | Humedad 0-100 y 0-10 cm (kg/m²), humedad disponible (%), Tair (K), lluvia (kg/m²) |
| `calor_condados_iowa.csv` | Paso 5 | Días de junio-agosto con máxima > 30, 32 y 35 °C |
| `condados_iowa_nombres.json`, `condados_iowa_centroides.json` | Paso 4 | Generados del GeoJSON de condados de EUA |
| `panel_rotacion.csv` | `scripts_cdl_rotacion/s3_efecto_rotacion_panel.py` (equipo) | Indicador de maíz sobre maíz por condado y año |
| `../cdl/datos/cdl_butler_2008_2025.csv` | CropScape GetCDLStat | Acres por cultivo de Butler County (carpeta compartida con `cdl/`) |
| `../cdl/datos/CDL_<año>_19023.tif` | CropScape GetCDLFile | Mapas 2018-2025 de Butler; no van en el repo, se bajan con `python 08_cdl_rotacion_butler.py --descargar` |

## Resultados clave

- NLDAS 0-100 cm coincide con SMAP: Spearman 0.84 (IC 0.59-0.95), kappa 0.62, 24 meses.
- Sin tendencia de humedad significativa 2000-2025 (Mann-Kendall p = 0.51).
- Con 99 condados, humedad de agosto + lluvia de primavera + días > 35 °C bajan el error de prueba
  del maíz 18 % y de la soya 13 % frente a usar solo la tendencia. Gradient boosting no mejora a la lineal en años nuevos.
- En Butler, 39 % de la superficie rota maíz-soya cada año, 28 % rota con un quiebre y 27.5 % es maíz casi continuo
  (44 % en el sureste).
- El efecto de rotar no se puede medir a nivel condado: las pruebas placebo y de futuro también dan "efecto".

## Límites

- Todas las pruebas de rendimiento usan NLDAS, que solo cubre EUA. Falta repetirlas con NASA POWER para probar que escala.
- Las combinaciones de variables se eligieron viendo resultados, así que los errores de prueba son algo optimistas.
- POWER tiene celdas de ~50 km; varios condados comparten la misma.
