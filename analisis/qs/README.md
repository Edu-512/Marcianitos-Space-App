# Rendimientos de USDA QuickStats (99 condados de Iowa)

| Script | Qué hace | Salida |
|---|---|---|
| `s1_vista.py` | Muestra cómo viene el archivo crudo | — |
| `s2_limpieza.py` | Limpia y pasa a tabla condado × año | `quickstats_iowa_limpio.csv` |
| `s3_tendencia.py` | Tendencia por condado y anomalía de cada año | `anomalias.csv` |
| `s4_anios.py` | Años malos y cuántos condados afectan | — |
| `s5_maiz_vs_soya.py` | Si maíz y soya fallan juntos | — |
| `s6_geografia.py` | Nivel y volatilidad por condado y distrito | — |
| `s7_verificacion_y_grafica.py` | Verificación en bushels y gráfica | `quickstats_anomalias_por_anio.png` |
| `s8_verificar_hallazgo4.py` | Verifica que los condados que rinden más son más estables | — |
| `s9_calibracion.py` | Comprueba que un rango de 80 % cubre el 80 % de los años | — |

Uso: `python s2_limpieza.py` (lee `datos/quickstats_iowa_crudo.csv`, ver `datos/PENDIENTE.md`) y después `s3` a `s9`.
`anomalias.csv` y `quickstats_iowa_limpio.csv` son entradas del modelo; la copia que usa el modelo está en `modelo/entradas/`.
