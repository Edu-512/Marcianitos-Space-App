# Integración del modelo y diseño

> Informe de la primera integración. La entrega de cinco perfiles y geometrías ilustrativas descrita aquí fue sustituida por la [integración Butler de 167 parcelas](butler-model-integration.md).

Rama de trabajo: `feature/model-map-design`. Interfaz en inglés. Sin commits, pushes ni cambios en el despliegue público.

## Implementación

- Escritorio conserva la barra lateral. En móviles (hasta 767 px) se oculta también su control de apertura; las cuatro páginas aparecen en el dock inferior y `Change plot` en la esquina superior derecha. Se elimina `Case study`.
- La base marrón permanece en ambos temas; se añaden acentos verde azulado, terracota y dorado, con divisores y tarjetas de resultados. El icono flotante y el panel de Mr Corn dejan espacio al dock.
- Explorar muestra un mapa Leaflet con tres tarjetas dentro de un panel lateral (panel inferior en móvil), selector de año y acciones hacia las páginas existentes. La comparación tabular queda plegada. Se conserva la tabla satelital anterior en un apartado independiente, identificado como demostración.
- My Field, Compare Crops, Recommendations y las herramientas de Mr Corn comparten el mismo perfil, clima y plan. Recommendations presenta comprobaciones de presupuesto, suelo, nitrógeno y riesgo derivadas de los campos exportados, sin construir un nuevo algoritmo de recomendación.
- `selected_plot_id` y `selected_climate_id` son el estado canónico. Cambiar de perfil invalida el plan anterior; cambiar de clima actualiza su resultado. El contexto se contrasta con el JSON antes de mostrarlo. El checklist se separa por perfil/clima/plan.
- Las prioridades personales se conservan como notas de planificaci?n: se aclara que no recalculan ni clasifican los planes exportados.
- El modo `Legacy demo`, disponible en `My priorities and data guide` fuera del mapa, conserva las funcionalidades previas con sus datos simulados identificados.

## Procedencia y alcance científico

Se revisó `feature/analisis-datos` (`01d2322`): su README remite a `modelo/` para el consumo de resultados. El motor y sus salidas están en `origin/feature/modelo`, revisión `a711b487fba854bbd13aa857b5b863f2a16b6503`.

Los 19 archivos originales de `modelo/` se importaron sin modificaciones y se compararon byte a byte con esa revisión. `gen.py` no se importa ni se ejecuta en la aplicación: tiene efectos secundarios de escritura. La integración consume `salidas/resultado_ejemplo.json`, validando cinco perfiles, tres climas y tres planes: 45 resultados. La exportación completa de 167 perfiles se conserva, pero aún no se activa por carecer de límites geográficos finales.

No se modificaron `utils/types.py`, `utils/model_interface.py`, el generador ni su calibración. Las operaciones geométricas del frontend generan exclusivamente polígonos ilustrativos para visualizar perfiles; no son entradas del modelo.

Unidades originales: acres; USD/acre; bu/acre para maíz; toneladas/acre/año de erosión; lb/acre de nitrógeno de la fase de maíz. Los cuantiles históricos se presentan como incertidumbre del modelo, no como un pronóstico de cosecha. No se convierten precios ficticios USD/tonelada del demo en precios del modelo.

## Limitaciones que deben conservarse visibles

- Posiciones y polígonos son esquemáticos dentro de Butler County. No representan propiedades verificadas ni son aptos para seleccionar una parcela real. La incorporación de límites reales requiere vincular su identificador al perfil correcto.
- La salida no contiene cultivo actual, secuencia anual por propiedad ni rendimiento de soja. Se muestran como información no suministrada, sin inferirla.
- La rotación con cobertura comparte actualmente rendimiento y economía con maíz-soja; cambia la erosión. El frontend conserva ese resultado sin inventar costos de cobertura.
- La frecuencia exportada de caída del rendimiento puede ser igual entre planes. Se respeta la salida, sin prometer diferencias que el modelo no produce.
- El riesgo de no poder sembrar es una estimación del modelo, no una probabilidad medida para una propiedad verificada. El nitrógeno no constituye una prescripción de aplicación.
- Los cuantiles p10/p90 históricos no garantizan cobertura de un resultado futuro. Los presupuestos fuente incluyen renta; se explicita la diferencia entre rendimiento de maíz y economía de rotación.
- La geometría real y la validación agronómica del modelo siguen pendientes del equipo correspondiente.

## Archivos principales

`utils/field_model.py`: lectura/validación del JSON y estado compartido, caché invalidada por fecha de modificación.
`utils/data_sources.py`: catálogo de perfiles compatible con el contrato existente.
`components/model_views.py`: vistas conectadas a las salidas exportadas.
`components/field_map.py`, `components/field_map_frontend/`: componente CCv2, Leaflet 1.9.4 vendorizado con licencia BSD y mapas base USGS atribuidos.
`components/navigation.py`, `streamlit_app.py`: navegación y estructura adaptativa.
`components/design_system.py`, `.streamlit/config.toml`: identidad visual.
`utils/ai_chat.py`, `components/chat_widget.py`, `components/chat_frontend/`: contexto y herramientas del asistente.
Los cuatro módulos de `app_pages/` despachan hacia las vistas nuevas y preservan el modo anterior.

La única excepción CSS de compatibilidad con Streamlit es ocultar el sidebar y su botón de apertura en móvil mediante dos `data-testid`: no existe una API nativa de visibilidad según viewport. Los demás estilos propios se limitan a clases/keys controladas por el proyecto. Verificar estos dos selectores cuando se actualice Streamlit.

## Validación

- 39 pruebas Python: regresiones del demo y nuevas pruebas de 5×3×3 resultados, navegación, selección, climas, checklist y herramientas del asistente.
- 12 pruebas JavaScript de mapa, chatbot y PWA. El runner se ejecut? mediante `node -e` cargando los cuatro archivos: el aislamiento por procesos de `node --test` no est? permitido por el entorno (`spawn EPERM`). Las del mapa usan JSDOM y Leaflet simulado: comprueban eventos, tarjetas, estado y cámara, no el renderizado geográfico real.
- Comprobación de tipos y compilación de los módulos modificados.
- Aplicación PWA real iniciada en localhost: recorrido Explore Plots → My Field → Compare Crops → Recommendations, selector móvil de perfil, año seco y primavera húmeda, selección de cobertura y revisión de checklist, regreso al mapa; todas las respuestas `ready`, sin excepciones.
- HTTP local: salud, avatar WebP, manifest y service worker responden 200 con sus tipos MIME esperados.
- No se hicieron llamadas de pago a Gemini ni se imprimieron credenciales.
- No fue posible validar visualmente escritorio/móvil: el host de acceso al navegador no está disponible. La API de agente no evalúa CSS ni renderiza el componente. El sitio público no se actualizó; los cambios solo existen en esta rama local.

## Comprobación manual

Ejecutar desde el repositorio:

```powershell
.\.venv\Scripts\python.exe -m streamlit run pwa_app.py
```

1. Abrir la URL local indicada por Streamlit. Explorar debe mostrar los cinco perfiles ilustrativos.
2. Pulsar un polígono y comprobar las tres tarjetas. Cambiar Normal year / Dry & hot year / Wet spring y revisar cifras y unidades.
3. Elegir un plan y abrir Compare Crops. Continuar a Recommendations; marcar una revisión y regresar para comprobar contexto y persistencia de sesión.
4. Cambiar de perfil: el plan anterior debe invalidarse. Probar el selector lateral y, en móvil, Change plot superior.
5. Abrir y cerrar las tablas plegables. Confirmar que la tabla del demo tiene su propia advertencia.
6. Probar anchos 360, 390, 768 y 1440 px: sin sidebar ni botón de apertura en teléfono, dock fijo y chatbot sin superposición; lateral visible en escritorio. Revisar temas claro/oscuro, teclado, zoom y etiquetas.
7. Abrir Mr Corn y consultar por el plan seleccionado: debe recibir perfil, clima y plan. La respuesta externa requiere las credenciales existentes y conexión.

La PWA necesita servidor para ejecutar Streamlit y conexión para teselas/chatbot; estos cambios no convierten el modelo Python en una aplicación offline.
