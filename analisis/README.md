# Análisis de datos — Field Shift

Scripts que validan la información que usa el modelo. Todo es de Iowa (base Butler County), 2000-2025.
La app no importa nada de esta carpeta; lo que la app usa está en `../modelo/`.

## Carpetas

| Carpeta | Qué hay | Responde |
|---|---|---|
| `clima_power/` | Verificación y perfil del CSV diario de NASA POWER | ¿El clima de POWER es confiable para Butler? |
| `qs/` | USDA QuickStats: limpieza, tendencia, años malos, maíz vs soya, geografía, calibración de rangos | ¿Cuánto varía el rendimiento y qué tan bien calibrados están los rangos? |
| `humedad_nasa/` | SMAP, NLDAS, GLDAS, OpenET, 99 condados, CDL Butler, cruces | ¿Qué variables de clima explican el rendimiento? |
| `ss/` | USDA SSURGO: variables de suelo, productividad (CSR2) y erosión | ¿Qué propiedades del suelo importan? |
| `cdl/` | Cropland Data Layer + NDVI: rotación, tierra sin sembrar, parcelas de la demo, intento de medir el efecto de rotar | ¿Cómo se rota y se puede medir su efecto? |
| `economia/` | Precios e ingreso por acre | ¿Pesa más el precio o la cosecha? |
| `ajuste_suelo_versiones/` | Versiones previas del ajuste por suelo (la final está en `../modelo/calibracion/`) | Por qué se eligió la fórmula final |

## Orden para correr

Cada carpeta usa resultados de las anteriores. Los scripts se pueden correr desde cualquier lugar:
cada uno se cambia solo a su carpeta.

1. `clima_power/` (necesita el CSV de POWER)
2. `qs/` → genera `quickstats_iowa_limpio.csv` y `anomalias.csv`
3. `humedad_nasa/` (pasos 00 a 09; ver su README)
4. `ss/` (necesita los datos crudos de SSURGO)
5. `cdl/` (usa `qs/`, `ss/` y los mapas del CDL)
6. `economia/` (usa `qs/`)

## Instalar

```bash
pip install -r analisis/requirements.txt
```

## Qué datos no están en el repo

Los archivos crudos pesados y públicos (mapas CDL, NDVI, shapefile de SSURGO) no se suben.
Cada carpeta explica de dónde bajarlos, y `PROCEDENCIA.md` dice de dónde salió cada dato crudo.
Lo que todavía falta está marcado en `datos/PENDIENTE.md`.
