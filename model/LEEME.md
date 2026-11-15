# Field Shift — Entrega del modelo

Butler County, Iowa. NASA Space Apps 2026.

## Qué hay aquí

```
modelo/      el modelo y todo lo que necesita para correr
datos_ui/    lo que consume la interfaz
analisis/    los scripts de todo el análisis, por si hay que rehacer algo
```

## Correr el modelo

```bash
cd modelo
python3 gen.py              # las 5 parcelas de la demo
python3 gen.py --todas      # las 167 parcelas
```

Necesita pandas, numpy y las rutas relativas tal como están en el zip.
Salida: `resultado_ejemplo.json` o `resultado_todas.json`.

## Qué hace el modelo

Para cada parcela calcula, en cada uno de 3 escenarios climáticos y cada
uno de 3 planes de rotación: rendimiento esperado con rango, ingreso,
costo, margen, erosión, riesgo de no poder sembrar y dosis de nitrógeno.

3 escenarios × 3 planes = 9 resultados por parcela.

## Cómo funciona, en cuatro pasos

**1. Base histórica.** 26 años de rendimiento de los 99 condados de Iowa
(USDA QuickStats), sin la tendencia tecnológica, convertidos a desviaciones
porcentuales respecto a lo normal. De ahí sale la distribución de lo que
puede pasar.

**2. Escenarios por clima medido.** Los 26 años se agrupan con 4 indicadores
de NASA POWER: humedad del suelo en agosto, días arriba de 35 °C, lluvia de
mayo-junio y temperatura de julio. No se agrupan por rendimiento, porque eso
confunde la causa con el efecto.

| Escenario | Años | Humedad agosto | Días >35 °C |
|---|---|---|---|
| Seco y caluroso | 9 | percentil 19 | 7.3 |
| Primavera húmeda | 8 | percentil 74 | 0.1 |
| Normal | 9 | percentil 65 | 0.0 |

**3. Ajuste por suelo.** Una fórmula con 3 variables de SSURGO que existen
en todo Estados Unidos:

```
ajuste% = clip( ((-0.3651×arena + 1.6228×agua_150cm - 1.0498×pendiente + 51.77)
                 / 73.21 - 1) × 100 × 0.309 , -18, 18 )
```

Mueve el rendimiento entre -18 % y +12 % según la parcela.

**4. Economía y erosión.** Precios de USDA, costos y dosis de nitrógeno de
Iowa State, erosión con RUSLE según la pendiente y el factor K del suelo.

## Lo que está medido y lo que no

| Componente | Origen | Validación |
|---|---|---|
| Rangos de incertidumbre | Medido | Promete 80 %, cubre 80 % |
| Escenarios climáticos | Medido (NASA POWER) | p<0.0001 entre grupos |
| Ajuste por suelo | Medido (SSURGO) | Correlación 0.68 con CSR2, R² 0.29 |
| Penalización maíz continuo | **Literatura (Iowa State)** | No medible con estos datos |
| Precios y costos | USDA / Iowa State | — |

La penalización del maíz continuo hay que declararla en pantalla. Se intentó
medir por cuatro caminos distintos y las pruebas de falsación fallaron: el
indicador también "predecía" la soya y el año siguiente. El panel de
condados no puede medirla.

## Escalabilidad

El modelo usa solo variables que existen en cualquier condado de Estados
Unidos: QuickStats cubre todos los condados, SSURGO cubre el país, NASA
POWER es global, CDL cubre los 48 estados contiguos.

Para cambiar de región se cambian los archivos de entrada, no el modelo.
Lo único que habría que recalibrar son los precios y costos locales.

## Fuentes

- USDA NASS QuickStats — https://quickstats.nass.usda.gov/
- USDA NRCS Web Soil Survey — https://websoilsurvey.nrcs.usda.gov/
- USDA NASS CropScape (CDL) — https://nassgeodata.gmu.edu/CropScape/
- NASA POWER — https://power.larc.nasa.gov/
- NASA MODIS MOD13Q1 v6.1 vía AppEEARS — https://appeears.earthdatacloud.nasa.gov/
- Estimated Costs of Crop Production in Iowa — Iowa State University Extension
- Corn Following Corn — Iowa State University Extension
