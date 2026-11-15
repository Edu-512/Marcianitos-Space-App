# Feature 05 — Recommendations: informe de entrega

## 1. Resumen

Rama `feature/05-recommendations`, creada sobre `feature/04-compare-crops`, que todavía no estaba integrada en master al iniciar. Se conserva el inglés confirmado por el equipo y el nombre actual **Mr Corn**. No hay commits, pushes ni implementación de Feature 06.

Recommendations ahora combina el contexto de exploración, el resultado guardado del plan, acciones generales del proveedor y un checklist por contexto. No se añadieron predicciones, dosis ni recomendaciones nuevas.

## 2. Archivos

- `app_pages/recommendations.py`: pantalla, navegación existente, acciones, checklist, nutrición pendiente, riesgos, fuentes y ayuda.
- `components/action_plan.py`: validación del contexto y utilidades de identidad/progreso.
- `components/action_markup.py`: composición editorial con textos escapados y recursos locales.
- `components/action_frontend/action.css`: estilos de la página.
- `app_pages/rotations.py`: cambio mínimo de entrega; agrega el resultado ya calculado a `comparison_context["outcome"]`.
- `tests/test_action_plan.py`: siete pruebas con múltiples casos.
- `README.md` y este informe.

No se modificaron contratos, modelo, fuentes, shell, navegación global, My Field, mapas, chatbot, dependencias ni temas.

## 3. Diseño visual

Se mantiene el único título global **Your Next Steps**. El encabezado editorial muestra el paso 4, una introducción y una ilustración agrícola. Después aparecen contexto, costos/cosecha, acciones, checklist, nutrición, incertidumbre, ayuda y continuación.

Las tarjetas de acciones combinan ilustración, categoría, título, motivo, impacto/rango y costo. Las primeras tres se muestran inicialmente; la primera ocupa el ancho disponible como recurso editorial. Se aclara que el orden viene del proveedor y no constituye una prioridad calculada ni una recomendación principal definida por el modelo.

Los colores heredan el tema con superficies y bordes basados en `currentColor`, conservando los tonos tierra. Tipografía de mayor tamaño para cifras y títulos; detalles por clic, espaciado y bordes redondeados. Los SVG se reutilizan de Feature 04: recursos originales del proyecto, no fotografías de parcelas, sin proveedores externos ni descargas nuevas. La imagen de Mr Corn es el WebP optimizado existente.

## 4. Parcela, plan y escenario

Se usan los nombres existentes: `selected_plot_id`, `selected_plan_key`, `selected_plan_id`, `selected_climate_id` y `comparison_context`.

La proyección local `ActionContext` valida parcela, definición del catálogo, ID real, opción visual, clima y parámetros contra el contexto actual. Comprueba también los IDs del resultado guardado. No crea un segundo contexto persistente que compita con los estados de Feature 04.

La entrada directa sin plan ofrece un botón funcional hacia Compare Crops y conserva acciones generales. Si cambia la parcela, se descartan para la presentación el plan y resultado de la parcela anterior; se solicita confirmar un plan para el nuevo terreno. No se elige automáticamente otra alternativa.

## 5. Fuente actual de recomendaciones

Se conserva `generate_recommendations(plot_id, farmer_priorities)` en `utils/model_interface.py`. Su salida actual es de demostración y depende de la parcela y prioridades. La página no modifica sus reglas, no amplía el algoritmo y no atribuye sus recomendaciones a NASA.

Se preservan todas las acciones devueltas. Si hay más de tres, **View all actions** permite verlas. Se conserva el acceso al gráfico comparativo de impactos en un desplegable. IDs repetidos se presentan una sola vez para no duplicar acciones ni controles. Una respuesta vacía no se traduce en una conclusión de ausencia de riesgo; un fallo muestra información no disponible.

## 6. Alcance general o específico

Todas las acciones actuales se identifican como **General field actions**, basadas en parcela y prioridades. No se filtran por plan/clima porque el contrato no incluye esa relación. Cambiar el escenario puede cambiar el resumen guardado del plan, pero no se afirma que cambie las acciones generales.

El contexto visual de un plan seleccionado no lo convierte en la mejor alternativa ni en una recomendación definitiva. No existe un campo que declare una recomendación principal o prioridad autoritativa; no se inventó ese dato.

## 7. Resultados agrícolas y económicos

Compare Crops agrega al contexto la misma instancia de `ScenarioOutcome` que ya presenta. Recommendations únicamente la lee y valida; **no llama a `predict_scenario_outcome` ni ejecuta otro modelo para el resumen**. La prueba vacía la caché y bloquea cualquier nueva predicción para verificarlo.

Costos y cosecha aparecen juntos, con unidades originales: USD/ha y t/ha. El valor monetario es costo, no ingreso, margen ni ganancia. Se conserva el rango suministrado de cosecha y su representación visual de Feature 04. No se inventa rango económico ni horizonte temporal.

El rendimiento de las rotaciones mixtas permanece pendiente hasta tener resultados por cultivo y método comparable; no se suman ni asignan rendimientos agregados a maíz/soya. No hay cifras del PDF ni probabilidades nuevas.

## 8. Checklist

`recommendation_reviews` conserva listas de IDs revisados, separadas mediante una clave estable de parcela, plan/opción visual y clima. Los widgets usan claves derivadas de ese contexto y del ID de recomendación. Un callback sincroniza el estado persistente de sesión; la limpieza de widgets al navegar no elimina el registro de revisión.

Permite marcar y desmarcar, muestra cantidad revisada y progreso y cuenta solo IDs que sigan disponibles. No traslada progreso entre parcelas, planes ni climas. Cambiar de contexto y volver recupera el progreso de ese contexto. No hay checklist ficticio cuando faltan acciones, ni base de datos ni persistencia externa. **Revisada no significa realizada**.

## 9. Fertilización

**Nutrition for your crops** muestra **Nitrogen dose not available**. El contrato actual no proporciona cultivo objetivo, dosis/unidad ni condiciones, fecha o método de aplicación. Una acción de fertilizante NPK no se convierte en dosis de nitrógeno. No se calcula una cantidad universal ni se muestra cero como sustituto. Se documenta la necesidad de verificar condiciones del suelo y criterios agronómicos.

## 10. Mr Corn

Se conserva la burbuja global y su imagen oficial, sin modificar implementación, servicios, comportamiento ni nombre. La ayuda reutiliza el avatar y explica cómo abrir el chat con el icono flotante.

El componente actual recibe la parcela y las prioridades. No recibe automáticamente plan y clima. No existe un mecanismo público de apertura desde esta página, así que no se crea otro chat ni un botón sin efecto. La página indica que el usuario mencione el plan y el clima en la pregunta. La integración automática requerirá coordinación posterior sobre el contexto del asistente.

## 11. Datos pendientes

- Recomendaciones con relación explícita a parcela, plan y escenario, y ámbito general/específico.
- Prioridad o recomendación principal definida por el proveedor.
- Dosis de nitrógeno por cultivo, etapa, condiciones, unidad, fuente y limitaciones.
- Medida objetivo de impacto, horizonte, método y validación de sus intervalos.
- Ingresos/márgenes/beneficios, moneda, supuestos, periodo y rangos económicos.
- Rendimientos por cultivo de rotaciones, planes de soya y respuesta de primavera húmeda pendientes de Feature 04.
- Fechas, periodos, resoluciones, fuentes y naturaleza verificadas.

Los índices generales de riesgo se muestran en detalles como índices simulados 0–1, sin umbrales nuevos ni interpretación como probabilidades futuras. No se inventan riesgos de drenaje, superficie no sembrada o incertidumbre económica.

## 12. Pruebas funcionales

- Suite Python completa: **33 pruebas aprobadas** (26 anteriores y siete nuevas).
- Suite JavaScript de chat/PWA/rutas: **10 aprobadas**.
- Mypy sobre los cuatro módulos implicados: sin errores.
- Compilación y `git diff --check`: sin errores.
- Nuevas comprobaciones: entrada directa y navegación real, resultado guardado sin nueva predicción, regreso y clima conservado, checklist por parcela/plan/clima con marcado/desmarcado, acciones vacías/fallidas, contexto o resultado incorrecto, conservación de más de tres acciones, HTML escapado, intervalos ausentes y navegación a Explore Plots.
- Inicio real: `python -m streamlit run streamlit_app.py` con puerto 8778 y API de agente para revisión.
- API de agente: Recommendations inicia sin excepciones; entrada sin plan; navegación a comparación; selección de maíz y clima seco; continuación; checklist 1/1; regreso y revisión conservada; cambio a South Field con aviso y sin resultados anteriores. El desplegable de impactos abre sin errores.
- No se hicieron consultas pagadas al chatbot.

## 13. Pruebas visuales

Se consultó el navegador de revisión. El entorno devolvió `browser access host is unavailable`, sin navegadores conectados. No fue posible revisar el renderizado a 1366×768, 1920×1080, 390/360 px o en ambos temas. Las comprobaciones de la API de agente son funcionales, no pruebas de CSS ni solapamientos.

La cuadrícula permite apilar tarjetas y resultados; los controles mantienen tamaño táctil y la página reserva espacio local para acciones/checklist junto a Mr Corn. La separación inferior de la navegación existente se conserva. Estos mecanismos requieren confirmación visual, no se presentan como pruebas ya aprobadas.

## 14. Capturas

No se obtuvieron capturas verificadas de escritorio o móvil. No se presentan maquetas como si fueran capturas de la aplicación.

## 15. Criterios de aceptación

Comprobados funcionalmente: parcela activa, plan/clima conservados y validados, resumen del resultado disponible, rangos suministrados, acciones del proveedor y alcance general, ausencia de dosis inventadas, datos faltantes, fuentes, navegación, checklist y compatibilidad con las pruebas anteriores. Contratos y algoritmos intactos.

Pendientes por datos: acciones específicas de plan/clima, dosis, resultados económicos adicionales, metodología/intervalos validados y resultados ausentes ya documentados en Feature 04.

La composición y adaptación visual están implementadas; los criterios de apariencia, contraste real, alineación, desbordamientos y solapamiento con Mr Corn/dock quedan pendientes de revisión en navegador.

## 16. Limitaciones

Feature 05 depende de Feature 04, todavía fuera de master al crear la rama. Su PR debe coordinarse con la integración previa de Feature 04 para no duplicar sus cambios. Esta tarea no fusiona ramas ni modifica el chatbot para incorporar cambios posteriores de master.

Las acciones son generales aunque exista un plan seleccionado; el coste no es beneficio; la medida del impacto y el periodo no están definidos por el proveedor. Los límites de demo no acreditan cobertura 80/90 %. El checklist dura solo la sesión. Continúan avisos heredados de `use_container_width` en otras vistas; la página nueva usa `width`.

## 17. Preparación para Feature 06

Antes de ampliar personalización, acordar con el equipo de modelo un proveedor con ámbito y contexto explícitos, metodología y unidades. Confirmar intervalos, periodos y dosis cuando se suministren. Cualquier paso de contexto al chatbot deberá coordinarse sin duplicar el asistente. La persistencia externa del checklist requiere una necesidad y alcance propios. No se implementó Feature 06 ni se introdujeron esos contratos.

### Comprobación manual

1. Abrir `http://127.0.0.1:8778/recomendaciones` o ejecutar `.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py`.
2. Entrar directamente a Recommendations: debe explicar la ausencia de plan, ofrecer Compare Crops y mostrar solo las acciones generales existentes.
3. En Compare Crops elegir maíz continuo y un clima con resultados; continuar. Confirmar nombre de parcela, plan, clima y los mismos valores de comparación.
4. Marcar una acción como revisada, volver a comparar y regresar. Desmarcarla y comprobar progreso. Cambiar clima, plan o parcela: el progreso no debe trasladarse a otro contexto. Volver al original recupera sus revisiones.
5. Abrir fuentes, límites, riesgo e impactos. Confirmar unidades, alcance general, campos pendientes y que la dosis de nitrógeno no se inventa.
6. Usar Change my planting plan, Compare Again y Explore another plot; comprobar navegación y contexto. Abrir Mr Corn con su icono flotante.
7. Revisar escritorio y 390/360 px, ambos temas y teclado. Comprobar foco, legibilidad, rangos, ausencia de desbordamiento y que dock/Mr Corn no oculten acciones.
8. Para comprobar la PWA, usar `pwa_app.py` como antes. Esta feature no añade funcionamiento científico sin conexión.
