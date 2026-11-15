# Suelos de USDA SSURGO (Butler County, IA023)

| Script | Qué hace | Salida |
|---|---|---|
| `s0_agrega_horizontes_0_30cm.py` | Promedia horizontes (0-30 cm, por espesor) y componentes (por porcentaje) | `datos/ssurgo_butler_por_suelo.csv` |
| `s1_tablas_extra.py` | Revisa las tablas de rendimiento por suelo, restricciones e inundación | — |
| `s2_mapa.py` | Lee el mapa de suelos y calcula el área de cada tipo | `suelo_con_area.csv` |
| `s3_variables.py` | Agrega inundación en época de siembra y capa restrictiva | `suelo_agricola.csv`, `suelo_con_area.csv` |
| `s4_productividad.py` | Qué variables explican la productividad (CSR2) | — |
| `s5_mapa_y_tabla_final.py` | Mapa de agua disponible y arena | `ssurgo_mapa_butler.png` |
| `s6_erosion_rusle.py` | Erosión potencial RUSLE por tipo de suelo (antes `genera_variables_modelo.py`) | `erosion_por_suelo.csv` |
| `s7_tabla_final.py` | Arma la tabla de 22 variables del modelo (reconstruido, ver el script) | `ssurgo_butler_variables_modelo.csv` |

La tabla que usa el modelo está en `modelo/entradas/ssurgo_butler_variables_modelo.csv`.
`s7` la escribe aquí para compararla antes de reemplazarla.

## Datos (`datos/`)

Incluidos: `mapunit.csv`, `muaggatt.csv`, `component.csv`, `chorizon.csv` (tablas de SSURGO convertidas a CSV)
y `ssurgo_butler_por_suelo.csv`. Los demás se bajan; ver `datos/PENDIENTE.md` y `../PROCEDENCIA.md`.
