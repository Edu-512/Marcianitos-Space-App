# Datos de clima: NASA POWER (Butler County, Iowa)

Esta carpeta contiene el archivo diario de clima de Field Shift, tomado de NASA POWER (MERRA-2).

## Archivo

- `POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST.csv`

Está tal como se descargó, sin modificar. Lo usan los scripts de verificación y análisis.

## Datos

- **Fuente:** NASA POWER (MERRA-2), datos diarios, https://power.larc.nasa.gov/
- **Lugar:** un punto en Butler County, Iowa (latitud 42.73, longitud -92.79), elegido como zona de prueba inicial
- **Periodo:** del 01/01/2000 al 31/12/2025 (9,497 días, sin faltantes)
- **Base horaria:** hora solar local (LST)

## Columnas

- YEAR, DOY: año y día del año
- T2MDEW: punto de rocío a 2 m (°C)
- T2M_MAX: temperatura máxima del aire a 2 m (°C)
- T2M_MIN: temperatura mínima del aire a 2 m (°C)
- GWETROOT: humedad del suelo en la zona de raíces (0 a 1)
- PRECTOTCORR: precipitación corregida (mm/día)

Datos de clima: NASA POWER Project, https://power.larc.nasa.gov/
