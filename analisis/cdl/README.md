# Rotación con Cropland Data Layer y NDVI (Butler County)

| Script | Qué hace | Necesita |
|---|---|---|
| `s1_raster.py` | Revisa los mapas del CDL | mapas CDL |
| `s2_transicion_suelo.py` | Cruza el CDL con el mapa de suelos | mapas CDL, SSURGO |
| `s3_efecto_rotacion_panel.py` | Panel de 99 condados: intento de medir el efecto de maíz sobre maíz | `../qs/` |
| `s4_ocho_anios.py` | Patrón de rotación 2018-2025 por píxel | mapas CDL |
| `s5_secuencias_suelo.py` | Años seguidos de maíz contra suelo | salidas de s2 y s4 |
| `s6_ndvi.py` | Lleva el NDVI de MODIS a la rejilla del CDL | NDVI |
| `s7_prueba_rotacion.py` | Compara vigor de maíz tras maíz contra maíz tras soya | salidas de s2, s4, s6 |
| `s8_verificacion_ndvi.py` | Verificación del NDVI por fechas | NDVI |
| `s9_control_positivo.py` | Control: el NDVI sí distingue maíz de soya y suelo bueno de arenoso | salidas de s2, s4, s6 |
| `s10_grafica.py` | Gráfica de la prueba de rotación | salida de s7 |
| `s11_sin_sembrar.py` | Tierra sin sembrar en 2019 contra suelo | salidas de s2, s4, SSURGO |
| `s12_verif_sin_sembrar.py` | Repite la prueba en 2024 | salidas de s2, s4 |
| `s13_parcelas_demo.py` | Elige las parcelas de la demo | salidas de s2, s4, s11 |
| `s14_interaccion.py` | ¿El maíz continuo pierde más en años malos? | salida de s3 |
| `s15_falsificacion_interaccion.py` | Pruebas de control de s14 | salida de s3 |

Salidas que usa el modelo: `parcelas_demo.csv` y `parcelas_candidatas.csv` (copias en `modelo/entradas/`)
y `patron_rotacion_2018_2025.tif` (copia en `modelo/salidas/`).

## Datos (`datos/`)

- `cdl_butler_2008_2025.csv`: acres por cultivo (incluido).
- `CDL_<año>_19023.tif`, 2018-2025: no se suben. Se bajan con `python ../humedad_nasa/08_cdl_rotacion_butler.py --descargar`.
- `ndvi/*_NDVI_doy*.tif`: MODIS MOD13Q1 v6.1 de AppEEARS. No se suben. Falta documentar la solicitud
  (área, fechas, capa); pedirlo a quien hizo `s6_ndvi.py`.
