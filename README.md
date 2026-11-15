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

La app abre en `http://localhost:8501`. La navegación principal vive en la
barra lateral: **Explore Plots → My Field → Compare Crops →
Recommendations**. La primera vista es el mapa. El selector lateral conserva la
parcela entre secciones mediante `selected_plot_id`; las prioridades y la guía
siguen disponibles en el desplegable **Mis prioridades y guía de datos**.
Mr Corn y el punto de entrada PWA continúan disponibles.

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


## Mr Corn: asistente flotante

La rama `feature/don-surco-chat` reutiliza el backend de `legy`
(`utils/ai_chat.py`) y lo presenta como un componente **CCv2 inline** en todas las
vistas. No a?ade una quinta opci?n a la navegaci?n. El frontend vive en
`components/chat_frontend/` y se pasa al componente como cadenas de c?digo;
no es un paquete CCv2 ni necesita Node/Vite para desplegar.

- Burbuja con el granjero **Mr Corn**, sombrero y espiga en la boca; abre un
  panel lateral que respeta los temas claro/oscuro y la navegaci?n inferior m?vil.
- Escape, bot?n de cerrar, foco de teclado y movimiento reducido.
- Historial separado por lote durante la sesi?n; se conserva al navegar.
  No se guarda en localStorage, en la cach? PWA ni despu?s de reiniciar la sesi?n.
- Un mensaje a la vez, protecci?n ante eventos duplicados y confirmaci?n para
  borrar una charla. Si cambia el lote o la estrategia se detiene la consulta
  pendiente para no mezclar contextos.
- Los eventos de herramientas se muestran como pasos desplegables; la respuesta
  final aparece cuando llega del backend. `legy` no implementa streaming de tokens.
- La mascota usa una animaci?n CSS sutil al pasar el cursor; no es un sprite animado.

### Activar Gemini

Instala `requirements.txt` y configura los secretos del servidor o de Community
Cloud (nunca la clave en JavaScript ni dentro de los archivos versionados):

```toml
[google]
api_key = "TU_CLAVE"
model = "TU_MODELO_GEMINI_HABILITADO"
```

Tambi?n se acepta `GOOGLE_API_KEY` como variable de entorno. El modelo conserva
el valor por defecto de `legy`; se recomienda configurar expl?citamente uno
habilitado en tu proyecto. Se llama a Gemini solo al enviar una pregunta, nunca
por abrir el panel o cambiar de p?gina. Las pruebas utilizan eventos simulados y
no consumen la API. Si falta el SDK o la configuraci?n, la burbuja sigue disponible
para revisar el dise?o, pero no permite enviar preguntas.

Ejecuta `streamlit run pwa_app.py`. El avatar se sirve desde
`/app/static/assistant/mr-corn.png`; para ello se habilita el servidor est?tico
nativo de Streamlit. Ese directorio contiene ?nicamente recursos p?blicos.

### Ilustraci?n

`static/assistant/mr-corn.png` se gener? con ImageGen integrado, con fondo
transparente. Prompt de producci?n: granjero caricaturesco adulto y amistoso,
retrato de busto con sombrero de paja y banda terracota, bigote peque?o, camisa
crema y overol verde; una espiga seca en la comisura de la boca, sin humo;
contornos claros y silueta legible como avatar circular de 64 px, paleta
terracota/durazno/crema/verde, sin texto ni fondo. Animaci?n y encuadre en CSS.


Pruebas funcionales del asistente (sin consumo de Gemini):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
npm install --prefix .venv/js-tests --no-audit --no-fund jsdom
node --test --experimental-test-isolation=none tests/chat-widget.test.cjs tests/pwa-worker.test.cjs
```

`jsdom` se instala ?nicamente como herramienta de pruebas dentro de `.venv`,
que est? ignorado por Git. Comprueba los eventos del panel y el teclado sobre un
DOM simulado; no sustituye una revisi?n visual en navegador o tel?fono real.


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
