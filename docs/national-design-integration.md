# Integración de capa nacional con diseño e IA

Rama de trabajo: `feature/design-integration`. Se integra `origin/feature/model-map-design` (`345d398`) sobre nuestros diseños publicados (`efb6efc`). La fusión queda preparada sin commit ni push, con los conflictos resueltos y MERGE_HEAD pendiente de confirmar mediante el siguiente commit.

## Resolución

Hubo tres conflictos reales: components/field_map.py, map.html y map.js. Se tomaron nuestros archivos como base y se incorporaron los componentes nacionales, su configuración y los callbacks necesarios. Se preservan la marca Know Your Farm, el emblema sin texto, el selector lateral de escritorio, el control móvil, el dock Step #/4, el panel compacto, la ausencia de No background y la corrección que evita volver a la selección inicial al mover el mapa.

La leyenda nacional comienza plegada y se separa de la segunda fila de controles móviles para evitar superposiciones. La PWA permanece retirada: no hay pwa_app.py, manifiesto, worker, rutas o pruebas PWA registrados. Entrada de ejecución y despliegue: streamlit_app.py.

La capa nacional consume teselas PMTiles mediante peticiones parciales en el navegador, con MapLibre y bibliotecas vendorizadas y sus licencias. No carga el archivo nacional completo en Python. El archivo field_shift_modelo.zip se conserva como artefacto recibido en la rama fuente y no se ejecuta ni se utiliza como entrada de la aplicación.

Las parcelas nacionales son de exploración: el popup informa el cultivo registrado. No cambian selected_plot_id ni crean predicciones para regiones no cubiertas. Solo los 167 IDs de Butler vinculados al JSON pueden analizarse; datos, geometrías y algoritmos agrícolas no se modifican.

## IA

La revisión detectó que google-genai, la credencial local y el endpoint ya estaban configurados. No fue necesario cambiar claves ni forzar banderas. Se comprobó realmente el acceso a models/gemini-3.6-flash y un turno completo con llamada a predict_scenario_outcome: parcela 806, maiz_soya_cobertura, normal; Gemini respondió con el margen fuente de −18 USD/acre.

La interfaz local confirma enabled=true para Mr Corn. No se imprimieron ni versionaron credenciales. El despliegue necesita mantener su propia sección google en Secrets de Community Cloud; la clave local no se transfiere mediante Git. Referencia de API: https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash

## Validación

- 47 pruebas Python aprobadas y 15 JavaScript de mapa, capa nacional y chat.
- Mypy de field_map.py y national_fields.py sin errores; compilación Python correcta.
- Sin conflictos pendientes ni errores de diff; ausencia de archivos PWA registrados.
- Flujo HTTP local completo Explore Plots → My Field → Compare Crops → Recommendations → Explore Plots con un campo no destacado.
- Configuración nacional presente en el componente y Mr Corn habilitado.
- Las cuatro bibliotecas estáticas nuevas responden 200, con MIME JavaScript/CSS correcto.
- La prueba nacional utiliza Leaflet real y MapLibre simulado en JSDOM. No constituye validación de WebGL, teselas remotas ni diseño en un navegador real. El host de navegador estuvo indisponible durante esta sesión.

Revisar visualmente zoom/pan sin saltos de selección, View USA, US fields on/off, cultivo del popup nacional, análisis de Butler, panel móvil y chat encima del mapa. El siguiente commit confirma la fusión; después se podrá publicar la rama y abrir el PR hacia master. No se modifica master desde este trabajo.
