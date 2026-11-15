# Clima diario de NASA POWER (Butler County)

Verifica y resume el CSV diario de NASA POWER (MERRA-2) en el punto 42.73 N, 92.79 W, de 2000 a 2025.

## Scripts

| Script | Qué hace |
|---|---|
| `verificacion_csv_power.py` | 28 comprobaciones de calidad (fechas, faltantes, física, años secos y húmedos conocidos). Salida en `salida/` |
| `analisis_clima_para_modelo.py` | Variables derivadas (ET0, VPD, balance hídrico, grados-día, heladas), normales y extremos. Salida en `salida_clima/` |

## Datos

Los dos scripts usan `datos/POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST.csv`

## Resultado de la verificación

De las 28 comprobaciones, 27 pasaron. El único aviso es una racha de 21 días con el mismo valor de humedad del suelo en septiembre-octubre de 2022, que consideramos plausible.
