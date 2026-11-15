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
│   ├── palette.py              # Tokens compartidos para mapas y gráficas
│   └── uncertainty_chart.py    # Gráficas reutilizables de incertidumbre (Altair/Vega)
├── utils/
│   ├── types.py                # Dataclasses: contrato tipado entre UI y modelo
│   ├── data_sources.py         # Acceso a datos (mock determinista hoy; NASA mañana)
│   └── model_interface.py      # Contrato con el equipo de ML (stubs con TODOs)
├── .streamlit/config.toml      # Paleta tierra/verde con modo claro/oscuro
└── requirements.txt
```

## Cómo ejecutarlo

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run pwa_app.py
```

La app abre en `http://localhost:8501`. La navegación es una barra responsiva de botones nativos (arriba en escritorio, abajo en móvil) y la opción activa se resalta con un pill redondeado; al cambiar de vista no hay recarga del navegador — el estado vive en la sesión. Debajo de la nav hay una barra de contexto persistente: selector de lote, popover **⚙ My Priorities** (pesos de agua/suelo/mercado, forraje, siembra sin labranza y presupuesto hídrico) y popover **? Satellite Guide**; cada página usa el lote y las prioridades seleccionados.

## Contrato con el equipo del modelo (desarrollo en paralelo)

- **`utils/types.py`** define los dataclasses compartidos (`Plot`, `SatelliteSnapshot`, `RotationScenario`, `ScenarioOutcome`, `PlotRisk`, `Recommendation`, `FarmerPriorities`, `SeasonalWindow`). Todos son `frozen`; los campos nuevos se agregan siempre con valores por defecto. Un cambio de campos requiere acuerdo de ambos equipos.
- **`utils/model_interface.py`** es propiedad del equipo de ML: cada función devuelve hoy un mock determinista y debe reemplazarse por el pipeline real **sin cambiar firmas ni tipos de retorno**. Si cargar el modelo entrenado es costoso, usar `@st.cache_resource`.
- **`utils/data_sources.py`** centraliza el acceso a datos satelitales; reemplazar cada cuerpo con las fuentes reales (NASA POWER, SMAP, MODIS, GPM) manteniendo las firmas.

Las páginas de `app_pages/` solo importan estas funciones: cuando el modelo esté listo, la interfaz no necesita cambios.

## Datos simulados

Todos los datos actuales son mocks deterministas (semilla estable por clave con `zlib.crc32`, no `hash()`). Se reemplazan en las funciones marcadas con `TODO(model team)`.


## PWA: instalaci?n y publicaci?n

El punto de entrada para la versi?n instalable es **`pwa_app.py`**. Envuelve la
interfaz existente con `st.App` y a?ade las rutas del manifiesto, iconos y service
worker en el mismo dominio. Ejecutar `streamlit_app.py` directamente conserva la
interfaz, pero no activa la PWA. No se modifican los archivos instalados de Streamlit.

### Validar en local

```powershell
.\.venv\Scripts\python.exe -m streamlit run pwa_app.py
```

1. Abre `http://localhost:8501` en Chrome o Edge. Espera la primera carga.
2. En DevTools ? Application, revisa Manifest y Service Workers: el worker debe
   estar activado, con scope `/`, y el manifiesto sin errores de iconos.
3. Usa la opci?n de instalaci?n del navegador. Debe abrirse como ventana independiente.
4. Tras la primera visita conectada, activa Offline en DevTools y recarga la
   pesta?a: aparecer? una pantalla con **Try again**. Desactiva Offline y reintenta.
5. Revisa escritorio/m?vil y ambos temas, adem?s de navegar entre las cuatro vistas.

La instalaci?n depende del navegador; no se fuerza un aviso emergente. En iPhone
usa Safari ? Compartir ? A?adir a pantalla de inicio. En Android utiliza la opci?n
Instalar aplicaci?n / A?adir a pantalla de inicio de Chrome.

### Streamlit Community Cloud

- Al publicar, selecciona la rama correspondiente y **Main file path: `pwa_app.py`**.
  Si la aplicaci?n existente usa `streamlit_app.py`, configura una aplicaci?n nueva
  con este punto de entrada si Cloud no permite editarlo.
- Usa la URL HTTPS de la aplicaci?n (`https://<nombre>.streamlit.app/`), abierta
  directamente en el navegador, para instalarla; no una vista incrustada en iframe.
- La implementaci?n est? preparada para la ra?z del dominio, sin `server.baseUrlPath`.
- Comprueba manifiesto, registro del worker e instalaci?n tambi?n en la URL publicada:
  las pol?ticas o cambios del alojamiento pueden afectar las rutas personalizadas.
- Community Cloud puede dormir la aplicaci?n por inactividad. Instalarla no mantiene
  despierto el servidor. La PWA tampoco mantiene una sesi?n de Streamlit despu?s de
  cerrar la aplicaci?n, recargarla o reiniciar el servidor.

### Alcance sin conexi?n y actualizaciones

Sin conexi?n se muestra una pantalla de aviso y reintento. Mapas, comparaciones,
recomendaciones y controles de Streamlit necesitan conexi?n al servidor. Si se
pierde conexi?n con una sesi?n ya abierta, Streamlit conserva su aviso de reconexi?n;
la pantalla offline aparece al abrir o recargar la aplicaci?n sin red.

Solo se guardan en cach? la pantalla offline y los iconos p?blicos. No se almacenan
respuestas del modelo, parcelas, notas, credenciales, APIs ni sesiones. Las versiones
nuevas del worker esperan al cierre de las ventanas anteriores; no fuerzan la recarga
de una sesi?n activa. Al cambiar los recursos precargados, incrementa la versi?n
`CACHE_NAME` en `pwa/service-worker.js`. Los iconos provisionales usan un brote y
surcos agr?colas con la paleta tierra/verde de Field Shift.

### Pruebas de PWA

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --test tests/pwa-worker.test.cjs
```

Node solo se necesita para las pruebas del service worker, no para ejecutar ni
publicar la aplicaci?n. Las pruebas automatizadas no sustituyen la comprobaci?n de
instalaci?n en el navegador y en Community Cloud.
