# Feature 04 — Compare Crops

## 1. Resumen

Implementación en `feature/04-compare-crops`, desde `origin/master` en `53d807c`, con Feature 03 y Mr Corn integrados. El equipo confirmó conservar el inglés. No hay commits, pushes ni implementación de Feature 05.

La pantalla introduce una comparación visual de tres opciones, contexto de parcela, controles climáticos, selección y continuación real. Donde el catálogo no tiene datos, muestra estados pendientes sin inventarlos.

## 2. Archivos creados o modificados

- `app_pages/rotations.py`: pantalla, controles, detalles, simulador anterior y continuación.
- `components/crop_comparison.py`: catálogo de presentación, correspondencia con planes existentes, caché, validación de respuestas y estado.
- `components/compare_markup.py`: HTML de tarjetas, contexto e intervalos, escapando textos externos.
- `components/compare_frontend/compare.css`: estilos limitados a esta pantalla y su continuación.
- `static/compare/{landscape,maize,soy,cover,normal,dry,wet}.svg`: siete ilustraciones locales.
- `streamlit_app.py`: únicamente despacha el bloque de continuación específico cuando la página activa es rotations; las demás páginas conservan su continuación.
- `tests/test_compare_crops.py`: seis pruebas con múltiples casos.
- `tests/test_navigation.py`: el recorrido ahora selecciona explícitamente un plan antes de continuar.
- `README.md` y este informe.

No se modificaron los contratos, proveedores, modelo, mapas, My Field, Recommendations, temas, navegación global ni chatbot.

## 3. Diseño visual

Se conserva el título global para no duplicar H1. Un encabezado editorial compacto muestra una ilustración agrícola, contexto de parcela, hectáreas originales y cultivo registrado. Las tarjetas tienen ilustraciones de proporción uniforme, superficies sutiles, bordes cálidos, espacio interior y tipografía de mayor tamaño para costos y cosecha.

Los colores de texto y superficies heredan el tema. Se usa `currentColor` y mezclas translúcidas para que los estilos no fijen texto oscuro sobre un tema oscuro. El seleccionado se distingue con borde, texto, icono y botón activo. No se cambia la paleta marrón.

No había fotografías agrícolas apropiadas en el proyecto: se utilizó la alternativa permitida de ilustraciones SVG originales. No son imágenes de las parcelas. Son código vectorial local del proyecto, sin recursos de terceros ni descargas en cada interacción; los siete archivos suman 2771 bytes.

## 4. Componentes reutilizables

`resolve_plans` vincula solo definiciones de cultivos compatibles; no trata frijol como soya. `outcome_for` llama al modelo existente y valida los IDs devueltos. `yield_interval` comprueba valores finitos y ordenados. `plan_markup` y `interval_bar` presentan los valores sin calcular nuevas predicciones. `art` admite únicamente nombres internos de recursos. Los controles interactivos son nativos de Streamlit; no hay botones HTML decorativos.

Las cadenas insertadas en HTML se escapan. Las reglas CSS apuntan a clases propias y contenedores con claves; no se alteran selectores internos globales de Streamlit.

## 5. Selector climático

IDs de presentación: `normal`, `dry`, `wet`. El backend no ofrece IDs climáticos, sino parámetros de lluvia/temperatura.

- **Reference season:** 0 % de cambio de lluvia y 0 °C de anomalía, parámetros originales por defecto.
- **Dry & hot:** −30 % y +3.5 °C, extremos que ya existían en los controles del simulador. Se identifica expresamente como prueba ilustrativa, no como escenario local validado ni pronóstico.
- **Wet spring:** seleccionable, con explicación de resultados pendientes. No se sustituye una primavera húmeda por un simple aumento de lluvia estacional: el backend actual no representa momento de siembra, drenaje ni superficie no sembrada. No se llama al modelo para inventar ese resultado.

En escritorio se muestran tres tarjetas visuales; en teléfono un control segmentado compacto con etiquetas que pueden envolver. Ambos actualizan el mismo estado y conservan la parcela. Cambiar el clima conserva el plan si su definición sigue existiendo.

## 6. Tarjetas de comparación

Se presentan exactamente las tres opciones pedidas: Continuous maize, Maize & soybean y Rotation with cover. El catálogo actual solo proporciona una definición compatible con la primera (`maiz-continuo`). Las otras dos muestran **Awaiting model definition**, sus campos pendientes y una acción real para explorar la opción, sin IDs científicos inventados.

El resultado económico disponible es **costo en USD/ha**, no ingreso, margen ni beneficio. Se muestra junto al rendimiento disponible en t/ha. No hay horizonte ni rango económico confirmado: se dice expresamente. La secuencia usa el orden proporcionado, sin inventar años ni asignar automáticamente la cobertura a una cosecha comercial.

La cosecha de maíz conserva sus límites suministrados y una barra con estimación y extremos. Para rotaciones mixtas no se reutiliza un rendimiento agregado como rendimiento de cada cultivo; se requieren salidas por cultivo y metodología. La erosión se muestra como índice 0–1, nunca como toneladas ni porcentaje de suelo perdido; no se inventa un límite tolerable. El uso de agua y cambio de materia orgánica aparecen como resultados simulados secundarios cuando están disponibles.

Los cinco planes anteriores siguen accesibles en **More demo plans & original simulator**, incluyendo sus controles de lluvia y temperatura, prioridad, tabla, seis gráficas de tradeoffs, trayectorias y narrativas del proveedor. No se renombraron como planes de soya. Los detalles advierten que los textos de evidencia del proveedor también son simulados.

## 7. Estado compartido

- `selected_plot_id`: parcela global existente, no sustituida por un selector local.
- `selected_climate_id`: clima de presentación persistente.
- `selected_plan_key`: opción visual elegida; puede representar una definición pendiente.
- `selected_plan_id`: ID real del catálogo o `None` si la definición no existe.
- `comparison_context`: parcela (ID/nombre), clima, parámetros, opción visual, plan real y naturaleza simulada.
- `comparison_ready`: habilita la continuación únicamente para una definición y resultado disponibles en el contexto activo.

No se selecciona automáticamente un supuesto ganador ni se convierte un cultivo registrado en una rotación actual confirmada. Al cambiar de parcela se solicita una nueva selección explícita para evitar trasladar una decisión del terreno anterior. Al volver desde Recommendations a la misma parcela, se conserva la selección.

## 8. Información actual reutilizada

`load_plots`, `load_rotation_scenarios`, `predict_scenario_outcome`, `predict_yield_trajectory` y `score_scenario_priority_fit` permanecen intactas. Se conserva el componente `yield_uncertainty_bands` en los detalles originales. Los datos son deterministas de demostración, no observaciones NASA ni resultados reales de Butler County.

Se consultan costo, rendimiento, límites de rendimiento, demanda de riego, nutrientes, materia orgánica, erosión y otros índices existentes. No se calculan nuevos resultados científicos o económicos. Los números ausentes/NaN no se reemplazan con cero.

La caché de resultados usa todos los IDs y parámetros (5 minutos, hasta 128 entradas). No hay dependencias nuevas, consultas de imágenes externas ni llamadas pagadas al chatbot.

## 9. Campos pendientes del equipo de modelo

Definiciones e IDs de maize–soybean y maize–soybean–cover; secuencia y colocación temporal de cobertura; horizonte de cada resultado; rendimientos por cultivo, unidades y método de comparación; tipo de resultado económico, moneda, superficie, supuestos e intervalos; escenarios climáticos respaldados, particularmente primavera húmeda; erosión física y límites si existen; nitrógeno aplicable; riesgos adicionales; metodología y validación de intervalos.

El contrato actual llama CI90 a algunos campos, pero no acredita validación de cobertura. La interfaz conserva los valores y los denomina límites del demo, sin garantizar 90 %. No crea intervalos mediante porcentajes.

## 10. Adaptación móvil

La cuadrícula nativa reduce columnas según el ancho real; las tarjetas no se fuerzan a tres columnas en teléfonos. Hay un resumen compacto de tres filas antes de las tarjetas, ilustraciones proporcionadas y un selector segmentado móvil. Textos y rangos permanecen visibles; detalles secundarios se pliegan. Botones de al menos 44 px y foco visible.

CSS local reserva espacio junto a acciones para Mr Corn, y se conserva la separación inferior del shell para el dock. No se modificaron sus posiciones globales. Estos comportamientos están implementados, pero necesitan confirmar su representación real en navegador.

## 11. Pruebas funcionales

- Suite completa Python: **26 pruebas aprobadas**, incluyendo las 20 anteriores.
- Pruebas JavaScript de chatbot y rutas.
- Pruebas nuevas: correspondencia sin sustituir soya por frijol; IDs futuros del proveedor; selección y contexto al navegar; cambio de parcela; planes pendientes; primavera húmeda sin llamada al modelo; respuesta ausente/ID incorrecto; cambios de resultados con entradas; HTML escapado; unidades, índices y límites inválidos; control climático móvil.
- Mypy con `--explicit-package-bases`: sin errores en los cuatro módulos implicados.
- Compilación y `git diff --check`: sin errores.
- Inicio real mediante `python -m streamlit run streamlit_app.py`, en puerto 8777 para revisión.
- API de agente: sin excepciones al usar South Field, seleccionar maíz, cambiar a seco/húmedo/normal, explorar opciones pendientes y abrir el simulador anterior. Se comprobaron sus cuatro alternativas adicionales. Ir a Recommendations y volver conserva South Field y la selección. No se hicieron llamadas a la API del chatbot.

## 12. Pruebas visuales

Se intentó acceder al navegador de pruebas. El inventario devolvió `browser access host is unavailable`, sin navegadores conectados. No se verificó la representación en 1366×768, 1920×1080, 390 px, 360 px ni ambos temas. No se afirma que esas pruebas pasaron. La API de agente comprueba funcionamiento, no CSS renderizado ni solapamientos.

## 13. Capturas

No se obtuvieron capturas verificadas del navegador. No se sustituyen por maquetas que puedan confundirse con la aplicación funcionando.

## 14. Criterios cumplidos y pendientes

Implementados y comprobados funcionalmente: lectura de parcela, tres tarjetas y selección explícita, clima persistente, resultados disponibles por entrada, unidades y rangos suministrados, detalles, navegación condicionada y contexto, identificación del demo, datos ausentes y contratos intactos. Las cuatro secciones existentes siguen disponibles y los tests anteriores pasan.

Pendientes por datos: comparación numérica completa entre tres planes, ingresos/márgenes y rangos económicos, rendimientos por cultivo de las rotaciones, primavera húmeda, nitrógeno y riesgos no suministrados. No se marca la comparación científica completa como aprobada.

Implementados para revisión visual: encabezado agrícola, tarjetas, ilustraciones uniformes, tipografía, selección no dependiente solo del color, temas heredados, cuadrícula adaptable y acciones con margen. **Los criterios visuales de aceptación quedan pendientes de revisión en navegador**, incluyendo alineación, contraste, desbordamiento y solapamiento con Mr Corn/dock.

## 15. Límites y conexión con Feature 05

Recommendations actualmente consume la parcela y prioridades, no el plan ni el clima. La pantalla explica esa limitación antes de continuar. Feature 05 deberá leer `comparison_context`, validar el ID de plan y sus parámetros y usar el servicio acordado con el equipo, sin deducir recomendaciones en el frontend.

Persisten avisos heredados de `use_container_width` en otras páginas. No se ampliaron cambios a esas features. No se migró el mapa ni se cambiaron algoritmos, contratos, fuentes o dependencias.

### Comprobación manual

1. Abrir `http://127.0.0.1:8777/comparar` o iniciar `.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py` y entrar a Compare Crops.
2. Cambiar de parcela y comprobar el contexto. Ver las tres tarjetas; solo maíz tiene definición y resultados del catálogo actual.
3. Elegir maíz y cambiar Normal → Dry & hot: comprobar rendimiento, límites y demanda de agua. Cambiar a Wet spring: resultados pendientes y continuación deshabilitada, sin pérdida de selección.
4. Elegir las opciones de soya/cobertura: el estado seleccionado cambia; no aparecen cifras ni IDs inventados. Volver a maíz y Normal.
5. Abrir detalles, explicación de rangos y **More demo plans & original simulator**. Comprobar las alternativas anteriores, controles, tradeoffs y trayectorias.
6. Continuar a Recommendations y volver; comprobar parcela, clima y plan. Cambiar de parcela y confirmar que se solicita selección explícita.
7. Revisar 1366×768 y 1920×1080, luego 390/360 px, temas claro/oscuro y teclado. Confirmar legibilidad, foco, columnas, rangos visibles, ausencia de desbordamiento global y que Mr Corn/barra inferior no ocultan acciones.
