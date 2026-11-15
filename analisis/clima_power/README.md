# Clima diario de NASA POWER (Butler County)

Verifica y resume el CSV diario de NASA POWER (MERRA-2) en el punto 42.73 N, 92.79 W, 2000-2025.

| Script | Qué hace |
|---|---|
| `verificacion_csv_power.py` | 28 comprobaciones de calidad (fechas, faltantes, física, años secos y húmedos conocidos). Salida en `salida/` |
| `analisis_clima_para_modelo.py` | Variables derivadas (ET0, VPD, balance hídrico, grados-día, heladas), normales y extremos. Salida en `salida_clima/` |

Datos: `datos/POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST.csv` (ver `datos/PENDIENTE.md`).
El mismo CSV lo usa `modelo/calibracion/r4_clima.py` para armar los escenarios.
