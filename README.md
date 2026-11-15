# Field Shift — Adapting Farms with NASA Data

App web para el reto **NASA Space Apps Challenge 2026**. Unifica los cuatro pilares que piden los jueces: comparar rotaciones de cultivos, revelar tradeoffs, entender el riesgo y hacer visible la incertidumbre del modelo.

> 🌽 **Demo en vivo:** ya está desplegada en
> [https://knowyourfarm.streamlit.app/](https://knowyourfarm.streamlit.app/)
> (Streamlit Community Cloud, punto de entrada `pwa_app.py`).

## Estructura del proyecto

```
App_web/
├── streamlit_app.py            # Punto de entrada: navegación nativa, contexto persistente (lote + prioridades) y routing
├── pwa_app.py                  # Punto de entrada PWA: envuelve st.App con rutas de manifiesto, iconos y service worker
├── app_pages/                  # Una página por pilar del reto; cada módulo expone run()
│   ├── home.py                 # My Field: KPIs, tarjetas de suelo, historial de cultivos, calendario estacional e histórico 12 meses
│   ├── map_view.py             # Explore Plots: mapa geoespacial (pydeck) con capas satelitales y scrubbing multi-año (2021–2026)
│   ├── rotations.py            # Compare Crops: selección visual de clima/plan, tarjetas de planes, tradeoffs e incertidumbre
│   └── recommendations.py      # Recommendations: plan de acción DSS por contexto guardado, con impacto, CI y checklist de sesión
├── components/
│   ├── navigation.py           # Navegación nativa (sidebar en escritorio, barra inferior móvil) + selector de parcela compartido
│   ├── palette.py              # Tokens compartidos tierra/verde para mapas y gráficas
│   ├── uncertainty_chart.py    # Gráficas reutilizables de incertidumbre (Altair/Vega)
│   ├── field_overview.py       # Presentación de My Field: tarjetas de suelo, historial de cultivos, eventos de siembra
│   ├── crop_comparison.py      # Adaptadores de Compare Crops: planes, climas y resultados (sin cálculos de modelo)
│   ├── compare_markup.py       # Markup editorial seguro para las tarjetas de plan con arte SVG local
│   ├── action_plan.py          # Estado de Recommendations: ActionContext y seguimiento de acciones revisadas por contexto
│   ├── action_markup.py        # Markup editorial de acciones con datos escapados
│   ├── chat_widget.py          # Asistente Mr Corn: componente CCv2 inline montado en todas las vistas, vía fragment
│   ├── chat_frontend/          # chat.html/js/css que se pasa al componente CCv2 (sin Node/Vite)
│   ├── compare_frontend/       # compare.css de las tarjetas de plan
│   └── action_frontend/        # action.css de las acciones
├── utils/
│   ├── types.py                # Dataclasses frozen: contrato tipado entre UI y modelo
│   ├── data_sources.py         # Acceso a datos (mock determinista hoy; NASA mañana)
│   ├── model_interface.py      # Contrato con el equipo de ML (stubs con TODOs)
│   ├── ai_chat.py              # Backend de Mr Corn: LLM Gemini + function calling sobre las herramientas del modelo
│   ├── chat_state.py           # Estado de conversación local a la sesión y mapeo de eventos
│   └── pwa.py                  # Rutas PWA same-origin sin modificar los archivos instalados de Streamlit
├── pwa/                        # manifest.webmanifest, icons/, offline.html, register.js, service-worker.js
├── static/
│   ├── assistant/              # Avatar de Mr Corn (mr-corn.png/.webp) e ilustración Don Surco
│   └── compare/                # Arte SVG local para tarjetas de plan (maíz, soya, climas)
├── tests/                      # Pruebas Python (unittest) y Node (--test): chat widget, PWA worker, navegación
├── docs/                       # Informes de implementación y validación de las features 03/04/05
├── .streamlit/config.toml      # Paleta tierra/verde con modo claro/oscuro
└── requirements.txt
```

## Funcionalidades

- **Explore Plots** (`app_pages/map_view.py`): mapa geoespacial con pydeck, capas satelitales alternables y scrubbing multi-año (2021–2026) para ver la evolución del estrés en cada parcela.
- **My Field** (`app_pages/home.py`): KPIs de la parcela activa, propiedades de suelo pendientes, historial de cultivos e indicadores simulados con índices de riesgo y fuentes técnicas desplegables, calendario de vulnerabilidad estacional, histórico mensual de 12 meses y registro local en campo.
- **Compare Crops** (`app_pages/rotations.py`): selección visual del clima y de tres planes de siembra, tarjetas comparativas con tradeoffs e intervalos de incertidumbre, y contexto compartido (lote + plan + clima) que alimenta a Recommendations. El simulador climático What-If original sigue disponible en detalles expandibles.
- **Recommendations** (`app_pages/recommendations.py`): plan de acción DSS según el contexto guardado y las prioridades del productor, con alcance, límites e impacto estimado con intervalo de confianza; checklist de sesión que marca las acciones revisadas por contexto.
- **Mr Corn, asistente de IA**: burbuja flotante presente en todas las vistas (ver la sección [Mr Corn: asistente flotante](#mr-corn-asistente-flotante)). Responde preguntas usando un LLM (Gemini) con *function calling* sobre las mismas herramientas del modelo: riesgo de parcela, predicción de escenarios y recomendaciones.
- **PWA instalable**: manifiesto, iconos, service worker y pantalla offline; se instala como app independiente desde el navegador (ver [PWA: instalación y publicación](#pwa-instalación-y-publicación)).
- **Contexto persistente**: `selected_plot_id` conserva la parcela entre vistas; las prioridades del productor y la guía de datos viven en el desplegable lateral **Mis prioridades y guía de datos**.

## Cómo ejecutarlo

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run pwa_app.py
```

La app abre en `http://localhost:8501`. La navegación principal vive en la
barra lateral: **Explore Plots → My Field → Compare Crops →
Recommendations**. La primera vista es el mapa. El selector lateral conserva la
parcela entre secciones mediante `selected_plot_id`; las prioridades y la guía
siguen disponibles en el desplegable **Mis prioridades y guía de datos**.
Mr Corn y el punto de entrada PWA continúan disponibles.

## Despliegue: Streamlit Community Cloud

La webapp ya está publicada en **[https://knowyourfarm.streamlit.app/](https://knowyourfarm.streamlit.app/)**.

- **Main file path:** `pwa_app.py` (activa las rutas de la PWA; con
  `streamlit_app.py` se conserva la interfaz pero sin manifiesto ni worker).
- La URL HTTPS publicada es la que debe usarse para instalarla como app; no una vista incrustada en iframe.
- El asistente Mr Corn requiere los secretos del servidor de Community Cloud:
  `[google] api_key` y `model` en *Settings → Secrets* (o la variable de entorno
  `GOOGLE_API_KEY`). Nunca se versiona la clave. Sin configuración, la burbuja
  sigue visible pero no permite enviar preguntas.
- Community Cloud puede dormir la aplicación por inactividad: la primera carga
  tras un periodo sin uso tarda más (cold start). Instalarla como PWA no mantiene
  despierto el servidor ni conserva una sesión de Streamlit tras cerrarla o reiniciarla.

## Desarrollo asistido con IA

El desarrollo de este proyecto se realizó con apoyo de herramientas de IA para
**escribir código, pruebas de compilación y refactorización**: **Claude Code**,
**LM Studio Bionic** y **Codex**. El equipo revisa manualmente el código final y
las decisiones de diseño; las pruebas automatizadas de `tests/` validan el
comportamiento (chat widget, PWA worker, navegación, planes y recomendaciones).

## Contrato con el equipo del modelo (desarrollo en paralelo)

- **`utils/types.py`** define los dataclasses compartidos (`Plot`, `SatelliteSnapshot`, `RotationScenario`, `ScenarioOutcome`, `PlotRisk`, `Recommendation`, `FarmerPriorities`, `SeasonalWindow`). Todos son `frozen`; los campos nuevos se agregan siempre con valores por defecto. Un cambio de campos requiere acuerdo de ambos equipos.
- **`utils/model_interface.py`** es propiedad del equipo de ML: cada función devuelve hoy un mock determinista y debe reemplazarse por el pipeline real **sin cambiar firmas ni tipos de retorno**. Si cargar el modelo entrenado es costoso, usar `@st.cache_resource`.
- **`utils/data_sources.py`** centraliza el acceso a datos satelitales; reemplazar cada cuerpo con las fuentes reales (NASA POWER, SMAP, MODIS, GPM) manteniendo las firmas.

Las páginas de `app_pages/` solo importan estas funciones: cuando el modelo esté listo, la interfaz no necesita cambios. El backend del chat (`utils/ai_chat.py`) envuelve las mismas funciones, por lo que Mr Corn también pasará a usar predicciones reales sin cambios.

## Datos simulados

Todos los datos actuales son mocks deterministas (semilla estable por clave con `zlib.crc32`, no `hash()`). Se reemplazan en las funciones marcadas con `TODO(model team)`.


## PWA: instalación y publicación

El punto de entrada para la versión instalable es **`pwa_app.py`**. Envuelve la
interfaz existente con `st.App` y añade las rutas del manifiesto, iconos y service
worker en el mismo dominio. Ejecutar `streamlit_app.py` directamente conserva la
interfaz, pero no activa la PWA. No se modifican los archivos instalados de Streamlit.

### Validar en local

```powershell
.\.venv\Scripts\python.exe -m streamlit run pwa_app.py
```

1. Abre `http://localhost:8501` en Chrome o Edge. Espera la primera carga.
2. En DevTools → Application, revisa Manifest y Service Workers: el worker debe
   estar activado, con scope `/`, y el manifiesto sin errores de iconos.
3. Usa la opción de instalación del navegador. Debe abrirse como ventana independiente.
4. Tras la primera visita conectada, activa Offline en DevTools y recarga la
   pestaña: aparecerá una pantalla con **Try again**. Desactiva Offline y reintenta.
5. Revisa escritorio/móvil y ambos temas, además de navegar entre las cuatro vistas.

La instalación depende del navegador; no se fuerza un aviso emergente. En iPhone
usa Safari → Compartir → Añadir a pantalla de inicio. En Android utiliza la opción
Instalar aplicación / Añadir a pantalla de inicio de Chrome.

### Streamlit Community Cloud

- Al publicar, selecciona la rama correspondiente y **Main file path: `pwa_app.py`**.
  Si la aplicación existente usa `streamlit_app.py`, configura una aplicación nueva
  con este punto de entrada si Cloud no permite editarlo.
- Usa la URL HTTPS de la aplicación (`https://<nombre>.streamlit.app/`), abierta
  directamente en el navegador, para instalarla; no una vista incrustada en iframe.
- La implementación está preparada para la raíz del dominio, sin `server.baseUrlPath`.
- Comprueba manifiesto, registro del worker e instalación también en la URL publicada:
  las políticas o cambios del alojamiento pueden afectar las rutas personalizadas.
- Community Cloud puede dormir la aplicación por inactividad. Instalarla no mantiene
  despierto el servidor. La PWA tampoco mantiene una sesión de Streamlit después
  de cerrar la aplicación, recargarla o reiniciar el servidor.

### Alcance sin conexión y actualizaciones

Sin conexión se muestra una pantalla de aviso y reintento. Mapas, comparaciones,
recomendaciones y controles de Streamlit necesitan conexión al servidor. Si se
pierde conexión con una sesión ya abierta, Streamlit conserva su aviso de reconexión;
la pantalla offline aparece al abrir o recargar la aplicación sin red.

Solo se guardan en caché la pantalla offline y los iconos públicos. No se almacenan
respuestas del modelo, parcelas, notas, credenciales, APIs ni sesiones. Las versiones
nuevas del worker esperan al cierre de las ventanas anteriores; no fuerzan la recarga
de una sesión activa. Al cambiar los recursos precargados, incrementa la versión
`CACHE_NAME` en `pwa/service-worker.js`. Los iconos provisionales usan un brote y
surcos agrícolas con la paleta tierra/verde de Field Shift.

### Pruebas de PWA

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --test tests/pwa-worker.test.cjs
```

Node solo se necesita para las pruebas del service worker, no para ejecutar ni
publicar la aplicación. Las pruebas automatizadas no sustituyen la comprobación de
instalación en el navegador y en Community Cloud.


## Mr Corn: asistente flotante

La rama `feature/don-surco-chat` reutiliza el backend de `legy`
(`utils/ai_chat.py`) y lo presenta como un componente **CCv2 inline** en todas las
vistas. No añade una quinta opción a la navegación. El frontend vive en
`components/chat_frontend/` y se pasa al componente como cadenas de código;
no es un paquete CCv2 ni necesita Node/Vite para desplegar.

- Burbuja con el granjero **Mr Corn**, sombrero y espiga en la boca; abre un
  panel lateral que respeta los temas claro/oscuro y la navegación inferior móvil.
- Escape, botón de cerrar, foco de teclado y movimiento reducido.
- Historial separado por lote durante la sesión; se conserva al navegar.
  No se guarda en localStorage, en la caché PWA ni después de reiniciar la sesión.
- Un mensaje a la vez, protección ante eventos duplicados y confirmación para
  borrar una charla. Si cambia el lote o la estrategia se detiene la consulta
  pendiente para no mezclar contextos.
- Los eventos de herramientas se muestran como pasos desplegables; la respuesta
  final aparece cuando llega del backend. `legy` no implementa streaming de tokens.
- La mascota usa una animación CSS sutil al pasar el cursor; no es un sprite animado.

### Activar Gemini

Instala `requirements.txt` y configura los secretos del servidor o de Community
Cloud (nunca la clave en JavaScript ni dentro de los archivos versionados):

```toml
[google]
api_key = "TU_CLAVE"
model = "TU_MODELO_GEMINI_HABILITADO"
```

También se acepta `GOOGLE_API_KEY` como variable de entorno. El modelo conserva
el valor por defecto de `legy`; se recomienda configurar explícitamente uno
habilitado en tu proyecto. Se llama a Gemini solo al enviar una pregunta, nunca
por abrir el panel o cambiar de página. Las pruebas utilizan eventos simulados y
no consumen la API. Si falta el SDK o la configuración, la burbuja sigue disponible
para revisar el diseño, pero no permite enviar preguntas.

Ejecuta `streamlit run pwa_app.py`. El avatar se sirve desde
`/app/static/assistant/mr-corn.png`; para ello se habilita el servidor estático
nativo de Streamlit. Ese directorio contiene únicamente recursos públicos.

### Ilustración

`static/assistant/mr-corn.png` se generó con ImageGen integrado, con fondo
transparente. Prompt de producción: granjero caricaturesco adulto y amistoso,
retrato de busto con sombrero de paja y banda terracota, bigote pequeño, camisa
crema y overol verde; una espiga seca en la comisura de la boca, sin humo;
contornos claros y silueta legible como avatar circular de 64 px, paleta
terracota/durazno/crema/verde, sin texto ni fondo. Animación y encuadre en CSS.


Pruebas funcionales del asistente (sin consumo de Gemini):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
npm install --prefix .venv/js-tests --no-audit --no-fund jsdom
node --test --experimental-test-isolation=none tests/chat-widget.test.cjs tests/pwa-worker.test.cjs
```

`jsdom` se instala únicamente como herramienta de pruebas dentro de `.venv`,
que está ignorado por Git. Comprueba los eventos del panel y el teclado sobre un
DOM simulado; no sustituye una revisión visual en navegador o teléfono real.


## Feature 01: navegación principal

- `components/navigation.py` concentra etiquetas, encabezados, rutas y destino de
  cada botón de continuación, para facilitar traducciones posteriores.
- Se reutilizan las funciones `run()` de las cuatro páginas, con `st.Page`,
  `st.navigation` y enlaces nativos en una barra lateral con marca y contexto.
  La sección activa también se indica por su nombre y número de paso.
- `selected_plot_id` es el identificador compartido; `fs_plot_select` es solo
  el control visual. Antes de montarlo se sincroniza con el identificador, y su
  callback actualiza ese estado. Una selección futura desde el mapa puede escribir
  el mismo identificador sin cambiar contratos. Si desaparece una parcela, se usa
  la primera disponible con un aviso; sin parcelas se muestra un estado vacío.
- El aviso de datos simulados es visible en todas las vistas. Butler County,
  Iowa, es el caso de estudio previsto; las parcelas de demostración actuales
  conservan su ubicación original y **no representan observaciones de Iowa**.
- No se cambiaron `utils/types.py`, `utils/model_interface.py` ni las fuentes
  simuladas. El simulador y los controles que ya existían se conservan; esta
  feature no añade planes ni algoritmos nuevos.
- Se conserva la paleta marrón/tierra aprobada y el texto base de 16 px. En
  escritorio la navegación sigue en la barra lateral nativa. En teléfonos
  (hasta 767 px) aparece una barra flotante inferior con icono sobre el nombre,
  selección resaltada y espacio reservado para no tapar contenido. Su CSS queda
  limitado a contenedores con claves propias. El selector de parcela sigue
  accesible desde el menú lateral móvil; ambos temas se mantienen.
- Las nuevas rutas de navegación reutilizan el encabezado PWA y la pantalla sin
  conexión; esos cambios solo mantienen compatibilidad con la navegación nueva.

### Comprobación manual

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

1. Confirma que inicia en Explore Plots y que hay cuatro enlaces en el orden
   indicado. En teléfonos, usa la barra flotante inferior; abre el menú lateral para cambiar de parcela.
2. Cambia la parcela en el selector lateral.
3. Usa **Analizar esta parcela**, **Comparar mis opciones**, **Ver recomendaciones**
   y **Volver a comparar**. Comprueba el nombre de la parcela activa en cada vista.
4. Navega libremente por los enlaces laterales; la parcela debe conservarse.
5. Abre Mis prioridades y guía de datos; sus funciones existentes siguen accesibles.
6. Revisa ambos temas y el aviso de datos simulados. No interpretes la demostración
   como información real sobre Butler County.
7. Para comprobar instalación PWA y URLs directas, usa `streamlit run pwa_app.py`.

Pruebas de navegación y casos vacíos/inválidos:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --test --experimental-test-isolation=none tests/chat-widget.test.cjs tests/pwa-worker.test.cjs tests/navigation-pwa.test.cjs
```

Los contenidos de análisis conservan parte de sus textos en inglés. Su traducción
completa, selección avanzada en el mapa y adaptación de datos a Iowa quedan fuera
del alcance de esta feature. Persisten avisos de `use_container_width` en las
visualizaciones heredadas; no se han reescrito esas vistas.

## Feature 03: My Field

My Field now presents the selected demo plot, pending soil properties and crop
history, existing simulated indicators and risk indices, and expandable technical
sources, seasonal calendar, monthly history and local ground log. Interface text
remains in English. No agricultural model or data contracts were changed.

See [the implementation and validation report](docs/feature-03-my-field.md) for
integration fields, limitations, tests and manual checks. Mr Corn uses the new
transparent smiling corn avatar without the tractor without changing chat behavior.

## Feature 04: Compare Crops

Compare Crops now offers visual weather selection, three planting-plan cards,
explicit plan selection and shared context for Recommendations. Current model
results are used only where definitions exist. Soybean plans and wet-spring
results remain clearly pending; costs are not presented as profit. The original
plans and simulator remain available in expandable details. Interface text stays
in English and the existing earth-tone themes and Mr Corn are preserved.

See the [implementation and validation report](docs/feature-04-compare-crops.md)
for available data, pending model fields, test results and manual visual checks.

## Feature 05: Recommendations

Recommendations now reuses the saved comparison outcome, validates plot/plan/
weather context and presents the existing general field actions with their
scope and limits. A session checklist tracks reviewed actions per context.
Nitrogen doses remain pending; Mr Corn and existing navigation are preserved.

See the [implementation and validation report](docs/feature-05-recommendations.md)
for data gaps, tests and manual checks. This branch depends on Feature 04.
