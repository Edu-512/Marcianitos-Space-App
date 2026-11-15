# Suelos de USDA SSURGO (Butler County, IA023)

| Script | Qué hace | Salida |
|---|---|---|
| `s1_tablas_extra.py` | Revisa las tablas de rendimiento por suelo, restricciones e inundación | — |
| `s2_mapa.py` | Lee el mapa de suelos y calcula el área de cada tipo | `suelo_con_area.csv` |
| `s3_variables.py` | Agrega inundación en época de siembra y capa restrictiva | `suelo_agricola.csv`, `suelo_con_area.csv` |
| `s4_productividad.py` | Qué variables explican la productividad (CSR2) | — |
| `s5_mapa_y_tabla_final.py` | Mapa de agua disponible y arena | `ssurgo_mapa_butler.png` |

La tabla final que usa el modelo es `modelo/entradas/ssurgo_butler_variables_modelo.csv`.
Ver `datos/PENDIENTE.md`: falta el script que la genera y los datos crudos.
