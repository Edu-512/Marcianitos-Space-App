# Precios e ingreso por acre

| Script | Qué hace | Salida |
|---|---|---|
| `s1_precios.py` | Precios de maíz y soya en Iowa 2000-2025 (USDA) e ingreso por condado | `precios_iowa.csv`, `ingreso_por_condado.csv` |
| `s2_riesgo_ingreso.py` | Riesgo de cosecha contra riesgo de ingreso | — |
| `s3_verificacion.py` | Verifica el caso de Butler 2012 (cosecha baja, ingreso alto) | — |
| `s4_cobertura_local.py` | Cuánto del riesgo local cubre el precio | — |

Necesita `../qs/quickstats_iowa_limpio.csv`. Los precios vienen escritos dentro de `s1_precios.py`.
`precios_iowa.csv` es entrada del modelo (copia en `modelo/entradas/`).
