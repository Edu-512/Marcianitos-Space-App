# Field Shift — Adapting Farms with NASA Data

App web para el reto **NASA Space Apps Challenge 2026**. Unifica los cuatro pilares que piden los jueces: comparar rotaciones de cultivos, revelar tradeoffs, entender el riesgo y hacer visible la incertidumbre del modelo.

## Estructura del proyecto

```
App_web/
├── streamlit_app.py            # Punto de entrada: estado compartido, sidebar y navegación (st.navigation)
├── app_pages/                  # Una página por pilar del reto
│   ├── home.py                 # Indicadores clave (KPIs) e histórico satelital de 12 meses
│   ├── map_view.py             # Mapa geoespacial interactivo (pydeck) con capas satelitales
│   ├── rotations.py            # Comparación de rotaciones + tradeoffs + bandas de incertidumbre
│   └── recommendations.py      # Recomendaciones DSS con impacto e intervalo de confianza
├── components/
│   └── uncertainty_chart.py    # Gráficas reutilizables de incertidumbre (Altir/Vega)
├── utils/
│   ├── types.py                # Dataclasses: contrato tipado entre UI y modelo
│   ├── data_sources.py         # Acceso a datos (mock determinista hoy; NASA mañana)
│   └── model_interface.py      # Contrato con el equipo de ML (stubs con TODOs)
├── .streamlit/config.toml      # Tema (verde agrícola, modo claro/oscuro)
└── requirements.txt
```

## Cómo ejecutarlo

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run streamlit_app.py
```

La app abre en `http://localhost:8501`. El selector de lote está en la barra lateral; cada página usa el lote seleccionado.

## Contrato con el equipo del modelo (desarrollo en paralelo)

- **`utils/types.py`** define los dataclasses compartidos (`Plot`, `SatelliteSnapshot`, `RotationScenario`, `ScenarioOutcome`, `PlotRisk`, `Recommendation`). Un cambio de campos requiere acuerdo de ambos equipos.
- **`utils/model_interface.py`** es propiedad del equipo de ML: cada función devuelve hoy un mock determinista y debe reemplazarse por el pipeline real **sin cambiar firmas ni tipos de retorno**. Si cargar el modelo entrenado es costoso, usar `@st.cache_resource`.
- **`utils/data_sources.py`** centraliza el acceso a datos satelitales; reemplazar cada cuerpo con las fuentes reales (NASA POWER, SMAP, MODIS, GPM) manteniendo las firmas.

Las páginas de `app_pages/` solo importan estas funciones: cuando el modelo esté listo, la interfaz no necesita cambios.

## Datos simulados

Todos los datos actuales son mocks deterministas (semilla estable por clave con `zlib.crc32`, no `hash()`). Se reemplazan en las funciones marcadas con `TODO(model team)`.
