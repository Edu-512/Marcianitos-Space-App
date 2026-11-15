# Field Shift — Adapting Farms with NASA Data

App web para el reto **NASA Space Apps Challenge 2026**. Unifica los cuatro pilares que piden los jueces: comparar rotaciones de cultivos, revelar tradeoffs, entender el riesgo y hacer visible la incertidumbre del modelo.

## Estructura del proyecto

```
App_web/
├── streamlit_app.py            # Punto de entrada: navegación, barra de contexto persistente (lote + prioridades) y routing
├── app_pages/                  # Una página por pilar del reto; cada módulo expone run()
│   ├── home.py                 # KPIs, calendario de vulnerabilidad estacional, histórico 12 meses y registro local
│   ├── map_view.py             # Mapa geoespacial (pydeck) con capas satelitales y scrubbing multi-año (2021–2026)
│   ├── rotations.py            # Rotaciones + simulador climático What-If, tradeoffs e incertidumbre
│   └── recommendations.py      # Plan de acción DSS según prioridades del productor, con impacto y CI
├── components/
│   ├── navigation.py           # Barra de navegación responsiva con botones nativos (arriba en escritorio, abajo en móvil)
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

La app abre en `http://localhost:8501`. La navegación es una barra responsiva de botones nativos (arriba en escritorio, abajo en móvil) y la opción activa se resalta con un pill redondeado; al cambiar de vista no hay recarga del navegador — el estado vive en la sesión. Debajo de la nav hay una barra de contexto persistente: selector de lote, popover **⚙ My Priorities** (pesos de agua/suelo/mercado, forraje, siembra sin labranza y presupuesto hídrico) y popover **? Satellite Guide**; cada página usa el lote y las prioridades seleccionados.

## Contrato con el equipo del modelo (desarrollo en paralelo)

- **`utils/types.py`** define los dataclasses compartidos (`Plot`, `SatelliteSnapshot`, `RotationScenario`, `ScenarioOutcome`, `PlotRisk`, `Recommendation`, `FarmerPriorities`, `SeasonalWindow`). Todos son `frozen`; los campos nuevos se agregan siempre con valores por defecto. Un cambio de campos requiere acuerdo de ambos equipos.
- **`utils/model_interface.py`** es propiedad del equipo de ML: cada función devuelve hoy un mock determinista y debe reemplazarse por el pipeline real **sin cambiar firmas ni tipos de retorno**. Si cargar el modelo entrenado es costoso, usar `@st.cache_resource`.
- **`utils/data_sources.py`** centraliza el acceso a datos satelitales; reemplazar cada cuerpo con las fuentes reales (NASA POWER, SMAP, MODIS, GPM) manteniendo las firmas.

Las páginas de `app_pages/` solo importan estas funciones: cuando el modelo esté listo, la interfaz no necesita cambios.

## Datos simulados

Todos los datos actuales son mocks deterministas (semilla estable por clave con `zlib.crc32`, no `hash()`). Se reemplazan en las funciones marcadas con `TODO(model team)`.
