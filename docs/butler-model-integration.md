# Integración Butler con el diseño de Field Shift

## Resultado

Se mantiene `feature/model-map-design`, con nuestros cambios visuales, y se integra selectivamente la entrega de `feature/butler-model`, revisión `9c2fa4e58ee448e02cd78c8008e24cca6da82cbd`. No se fusiona la interfaz de esa rama ni sus índices y reglas adicionales.

La aplicación utiliza **167 parcelas × 3 climas × 3 rotaciones = 1,503 resultados exportados**. El motor no se ejecuta durante la navegación: se leen sus salidas precalculadas. No se modifican sus algoritmos, `utils/model_interface.py` ni `utils/types.py`.

## Datos y geometría

- Fuente activa: `model/datos_ui/resultado_todas.json`.
- Geometría activa: `model/datos_ui/parcelas_todas.geojson`.
- Unión por identificador exacto; se valida que los conjuntos de IDs coincidan. No existe sustitución silenciosa por polígonos inventados.
- Leaflet recibe las coordenadas originales completas: 142 Polygon, 25 MultiPolygon y 275 anillos interiores. Se preservan todos los fragmentos y huecos, en longitud/latitud.
- El centro de la caja de cada geometría se usa únicamente para compatibilidad con el contrato Plot; el mapa dibuja el GeoJSON completo. El anillo único del contrato Plot nunca reemplaza los multipolígonos del mapa.
- Estos límites se derivan de agrupaciones de píxeles agrícolas del USDA CDL. Son geometrías geográficas basadas en satélite, **no límites catastrales ni propiedades verificadas**.
- La entrega anterior, `modelo/`, se conserva como referencia histórica y ya no alimenta el flujo principal. El modo Legacy demo y su tabla satelital permanecen explícitamente separados y etiquetados como simulados.

## Modelo actualizado

Se preservan las cifras exactas de Butler, incluyendo el supuesto de establecimiento de cobertura de 37 USD/acre y el riesgo de siembra escalado desde la fracción no sembrada observada en 2019. Los costos y márgenes exportados se redondean por separado: el frontend no los recalcula para forzar diferencias entre valores redondeados.

Ejemplo, parcela 806, año normal: margen maíz-soja 20 USD/acre; margen con cobertura −18 USD/acre; riesgo de no poder sembrar 0 %. Parcela 1737: riesgo normal exportado 6.32 %. No se interpretan estas estimaciones como pronósticos garantizados de cosecha o probabilidades futuras medidas.

No se importan los índices heurísticos de riesgo, el score de prioridades, la curva mensual aproximada ni el generador de recomendaciones de la otra interfaz. Nuestra pantalla Recommendations sigue contextualizando los campos exportados del plan y clima elegidos, sin crear un algoritmo agrícola nuevo.

Se conservan las unidades fuente: bu/acre de maíz, USD/acre, ton/acre/año de erosión y lb/acre de nitrógeno de la fase de maíz. El rendimiento de soja, la secuencia anual por propiedad y el cultivo actual no se inventan. Las notas de prioridades no recalculan el modelo.

## Diseño, estado y rendimiento

Se conserva el sidebar en escritorio, el dock inferior y Change plot superior en móvil, los temas y acentos, las tres tarjetas en el panel del mapa, las tablas plegables y Mr Corn. El selector incluye 167 campos: cinco perfiles destacados al principio y el resto por ID.

Los resultados se comparten mediante selected_plot_id, selected_climate_id y selected_plan_id. El contexto y el checklist incluyen la revisión de la entrega: una selección guardada con la versión anterior se invalida. Cambiar de parcela limpia el plan anterior; cambiar de clima actualiza su resultado. Mr Corn usa las mismas salidas y describe la geometría como derivada del satélite.

La lectura e indexación del catálogo se cachean como recursos compartidos de solo lectura, invalidados por archivo y fecha de modificación. Se evita copiar el JSON completo al buscar cada parcela. Los resultados devueltos por result() son copias independientes para no contaminar el catálogo compartido.

Una prueba con la biblioteca Leaflet real detectó que el enlace de teclado se realizaba antes de crear los SVG. Se movió después de inicializar la vista: Enter y Espacio seleccionan el campo y abren sus tarjetas.

## Validación

- Suite Python: 43 pruebas, incluyendo los 1,503 resultados, igualdad exacta con la exportación, asociación de IDs, preservación de geometría, selección de un campo no destacado y descarte de contextos antiguos.
- Suite JavaScript: 13 pruebas de mapa, chat y PWA. Una usa Leaflet 1.9.4 real dentro de JSDOM y comprueba 167 trazados SVG, geometrías exactas con fragmentos/huecos, clic y teclado. Las demás del mapa comprueban tarjetas, eventos y cámara.
- Mypy: 13 módulos modificados, sin errores, con `--explicit-package-bases --follow-imports=silent --ignore-missing-imports`. Se mantiene sin modificar la limitación de tipado preexistente de utils/model_interface.py descrita en el informe anterior.
- Compilación Python y git diff --check sin errores de código/espacios.
- PWA local: selector de 167 campos; Field 25 → My Field → Compare Crops → Wet spring → Rotation with cover → Recommendations → Explore Plots; todas las respuestas listas, sin excepciones. Tabla del modelo expandida: 501 filas.
- 17 archivos importados se comparan byte a byte con el commit fuente. No se carga el pickle ni se ejecuta gen.py.
- No se realizan llamadas de pago al chatbot, commits, pushes ni despliegues.

JSDOM no sustituye la revisión visual en un navegador real ni valida la disponibilidad de las teselas remotas. La revisión visual de escritorio/móvil sigue pendiente; el host de acceso al navegador estuvo indisponible durante esta sesión. No se afirma una validación catastral ni topológica completa con herramientas GIS.

## Comprobación manual

```powershell
.\.venv\Scripts\python.exe -m streamlit run pwa_app.py
```

1. Abrir Explore Plots y pulsar Fit plots: deben aparecer los contornos de los 167 campos, sin cuadrados artificiales.
2. Acercarse a un campo con varios fragmentos o huecos. Pulsarlo y revisar las tres tarjetas; cambiar el tipo de año.
3. Elegir un plan y abrir la comparación. Continuar hasta Recommendations y comprobar campo, clima y cifras.
4. Cambiar de campo con Change plot. El plan anterior debe invalidarse. Probar también un campo sin nombre de perfil destacado, como Field 25.
5. Abrir la tabla plegable: 501 combinaciones para el clima activo. El demo satelital separado debe seguir identificado como simulado.
6. Probar escritorio y teléfono, temas claro/oscuro, zoom y teclado. Revisar que sidebar, dock y burbuja no se superpongan.
7. Mr Corn debe responder usando el campo, plan y clima activos. Una respuesta externa requiere conexión y las credenciales existentes.

Para previsualizar esta sesión se reinició el servidor local tras cambiar el catálogo importado. Si una ejecución antigua sigue mostrando cinco parcelas, reiniciar Streamlit; los imports ya cargados pueden conservar el módulo anterior.
