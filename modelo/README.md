# Modelo — Field Shift

Genera lo que muestra la app: para cada parcela de Butler County, 3 escenarios de clima × 3 planes de rotación,
con rendimiento y su rango, ingreso, costo, margen, erosión, riesgo de no poder sembrar y nitrógeno.

## Correr

```bash
pip install -r modelo/requirements.txt
python modelo/gen.py            # 5 parcelas de la demo  -> salidas/resultado_ejemplo.json
python modelo/gen.py --todas    # 167 parcelas            -> salidas/resultado_todas.json
```

`gen.py` solo lee `entradas/` y escribe en `salidas/`; no necesita nada de `analisis/`.

## Carpetas

| Carpeta | Contenido |
|---|---|
| `entradas/` | Lo que lee `gen.py` |
| `salidas/` | Lo que usa la app: `resultado_ejemplo.json`, `resultado_todas.json`, `patron_rotacion_2018_2025.tif` |
| `calibracion/` | Scripts que recalculan el ajuste por suelo y los escenarios de clima |

## De dónde sale cada entrada

| Archivo | Lo genera | Datos de origen |
|---|---|---|
| `anomalias.csv` | `analisis/qs/s3_tendencia.py` | USDA QuickStats |
| `quickstats_iowa_limpio.csv` | `analisis/qs/s2_limpieza.py` | USDA QuickStats |
| `ssurgo_butler_variables_modelo.csv` | `analisis/ss/` s0 → s2 → s3 → s7 | USDA SSURGO |
| `precios_iowa.csv` | `analisis/economia/s1_precios.py` | USDA |
| `clima_butler_por_anio.csv` | `calibracion/r4_clima.py` y `calibracion/r5_reclasificar.py` | NASA POWER |
| `modelo_suelo.json` | `calibracion/r3_calibrar_y_validar.py` | SSURGO + NDVI de MODIS |
| `parcelas_demo.csv`, `parcelas_candidatas.csv` | `analisis/cdl/s13_parcelas_demo.py` | CDL + SSURGO |

`salidas/patron_rotacion_2018_2025.tif` lo genera `analisis/cdl/s4_ocho_anios.py`.

## Recalibrar

En orden: `calibracion/r3_calibrar_y_validar.py` (necesita haber corrido `analisis/ss/` y `analisis/cdl/` s2, s4 y s6),
`calibracion/r4_clima.py` (usa `analisis/clima_power/datos/POWER_..._LST_1.csv`) y `calibracion/r5_reclasificar.py`.
`ajuste_suelo.csv` y `clima_por_escenario.csv` en `calibracion/` son resultados de revisión; `gen.py` no los lee.

## Qué está medido y qué viene de la literatura

| Componente | Origen |
|---|---|
| Rangos de incertidumbre | Medido; un rango de 80 % cubre el 80 % de los años (`analisis/qs/s9_calibracion.py`) |
| Escenarios de clima | Medido con NASA POWER: humedad de agosto, días > 35 °C, lluvia de mayo-junio, temperatura de julio |
| Ajuste por suelo | Medido con SSURGO (arena, agua disponible a 150 cm, pendiente) |
| Penalización por maíz continuo | Literatura (Iowa State); no se pudo medir con estos datos |
| Costos y dosis de nitrógeno | Literatura (Iowa State) |
| Precios | USDA |
