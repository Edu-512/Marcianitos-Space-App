# De dónde salió cada dato crudo

## NASA POWER — `clima_power/datos/`

`POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST.csv`

- Página: https://power.larc.nasa.gov/data-access-viewer/
- Punto: 42.73 N, −92.79 W (centro de Butler County)
- Periodo: 2000-01-01 a 2025-12-31, diario
- Parámetros: `T2M`, `T2M_MAX`, `PRECTOTCORR`, `GWETROOT`
- Comunidad: Agroclimatology — Formato: CSV
- 9,497 filas, 0 valores faltantes

Lo procesa `r4_clima.py`, que saca cuatro indicadores por año (humedad de
raíces en agosto, días arriba de 35 °C, lluvia de mayo-junio, temperatura de
julio) y con ellos arma los tres escenarios del modelo.

## USDA NASS QuickStats — `qs/datos/`

`quickstats_crudo.csv` — 13,916 filas, 2000-2025

- Página: https://quickstats.nass.usda.gov/
- Programa: SURVEY — Sector: CROPS — Grupo: FIELD CROPS
- Commodities: CORN, SOYBEANS, OATS
- Data items: rendimiento (bu/acre) y acres sembrados de los tres cultivos,
  más maíz para silaje en toneladas
- Geografía: COUNTY, estado IOWA (los 99 condados)

Este es el archivo completo. `s2_limpieza.py` lo reduce a maíz y soya para el
modelo; la avena y los acres sembrados siguen aquí sin tocar.

## USDA NRCS SSURGO — `ss/datos/`

- Página: https://websoilsurvey.nrcs.usda.gov/
- Área: IA023 (Butler County, Iowa) — **versión 33, 8 de septiembre de 2026**
- Descarga: pestaña Download Soils Data → SSURGO, área tabular + espacial
- Los archivos originales vienen en `.txt` separados por pipe y sin encabezado;
  los encabezados se tomaron del esquema oficial de SSURGO

Tablas incluidas:

| Archivo | Qué trae |
|---|---|
| `mapunit.csv` | las 134 unidades de mapa del condado |
| `muaggatt.csv` | valores ya agregados por unidad (drenaje, CSR2, inundación) |
| `component.csv` | los componentes de cada unidad, con su porcentaje y pendiente |
| `chorizon.csv` | los horizontes de cada componente: textura, agua, pH, factor K |
| `ssurgo_butler_por_suelo.csv` | resumen intermedio por tipo de suelo |

Cómo se llega a `ssurgo_butler_variables_modelo.csv`:

1. `agrega_horizontes_0_30cm.py` — promedia los horizontes de 0 a 30 cm
   ponderando por su espesor, y los componentes ponderando por su porcentaje
2. `genera_variables_modelo.py` — añade la erosión RUSLE y escribe las 22
   variables finales por unidad de mapa

El shapefile espacial (`soilmu_a_ia023.shp`, 23,905 polígonos) viene de la
misma descarga, carpeta `spatial/`.

## NASA MODIS NDVI — solicitud en AppEEARS

No hay archivo crudo aquí porque son 10 GeoTIFF. Así se pide de nuevo en
https://appeears.earthdatacloud.nasa.gov/ → Extract → **Area**:

- Producto: **MOD13Q1.061**, capa **250m_16_days_NDVI**
- Proyección: Geographic (EPSG:4326) — Formato: GeoTIFF
- Área: recuadro oeste −93.0417, sur 42.5396, este −92.5396, norte 42.9208
- Fechas: 25 de junio a 29 de agosto, de 2024 y 2025

Eso entrega 10 compuestos de 16 días (días del año 177, 193, 209, 225 y 241 de
cada año), de 183 × 241 píxeles a 250 m. Los procesa `s6_ndvi.py`, que se queda
con el NDVI máximo de cada año como medida del vigor del cultivo.

Nota: el NDVI pide cuenta de NASA Earthdata y la solicitud tarda en aprobarse.
