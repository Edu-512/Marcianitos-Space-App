# Falta: CSV de NASA POWER con 5 variables

Aquí ya está `POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST_1.csv` (T2M, T2M_MAX, PRECTOTCORR, GWETROOT),
que es el que usa el modelo (`modelo/calibracion/r4_clima.py`).

Los dos scripts de esta carpeta usan otro archivo con más variables:
`POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST.csv`, con T2M_MAX, **T2M_MIN**, **T2MDEW**, GWETROOT y PRECTOTCORR.

Se baja en https://power.larc.nasa.gov/data-access-viewer/ con el mismo punto (42.73, -92.79), diario, 2000-2025,
comunidad Agroclimatology, CSV, marcando esas cinco variables. Pedirlo a quien hizo el análisis de clima o bajarlo.
