# Clima diario de NASA POWER (Butler County)

Verifica y resume el CSV diario de NASA POWER (MERRA-2) en el punto 42.73 N, 92.79 W, 2000-2025.

| Script | Qué hace |
|---|---|
| `verificacion_csv_power.py` | 28 comprobaciones de calidad (fechas, faltantes, física, años secos y húmedos conocidos). Salida en `salida/` |
| `analisis_clima_para_modelo.py` | Variables derivadas (ET0, VPD, balance hídrico, grados-día, heladas), normales y extremos. Salida en `salida_clima/` |

Datos: estos dos scripts usan `datos/POWER_..._LST.csv` (5 variables, pendiente: ver `datos/PENDIENTE.md`).
El modelo usa otro archivo de la misma carpeta, `datos/POWER_..._LST_1.csv` (4 variables, incluido).
