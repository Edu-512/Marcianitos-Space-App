# Contexto del Proyecto: Field Shift: Adapting Farms with NASA Data

## 1. Visión General del Reto

* **Evento:** NASA Space Apps Challenge 2026 (14 y 15 de noviembre de 2026).
* **Nombre del Reto:** *Field Shift: Adapting Farms with NASA Data*.
* **Institución:** NASA Johnson Space Center (JSC).
* **Problema Central:** Los agricultores enfrentan condiciones climáticas cada vez más volátiles e impredecibles (calor extremo, lluvias erráticas, déficit hídrico y degradación de nutrientes en el suelo) que dificultan la planificación agrícola y aumentan el riesgo financiero y productivo.
* **Objetivo General:** Utilizar datos abiertos de observación terrestre de la NASA para ayudar a los agricultores a adaptar sus prácticas agrícolas, evaluar escenarios de rotación de cultivos y tomar decisiones informadas frente a la incertidumbre climática.

## 2. Nuestra Propuesta y Arquitectura Técnica

Desarrollaremos una **aplicación web integral en Python utilizando Streamlit** que unifica los cuatro formatos de solución propuestos por la NASA en una sola plataforma interactiva:

1. **Backend de Análisis de Datos y Modelo Predictivo (Python):**
   * Procesamiento e ingesta de variables satelitales de la NASA (precipitación, humedad del suelo, estrés térmico, índices de vegetación/NDVI y recursos hídricos).
   * Modelado analítico/ML para simular escenarios de rotación de cultivos, cuantificar el riesgo agrícola y calcular intervalos de confianza (incertidumbre).
2. **Mapa Interactivo Geoespacial (Parcelas):**
   * Visualización espacial de las parcelas agrícolas con capas de datos satelitales superpuestas (ej. usando `folium`, `pydeck` o `plotly`), permitiendo inspeccionar el estado histórico y actual de cada lote.
3. **Visualización de Flujo de Datos:**
   * Gráficos interactivos que conectan las variables climáticas y del suelo con el rendimiento esperado, exponiendo visualmente las compensaciones (*tradeoffs*) entre opciones (ej. uso de agua vs. rendimiento vs. desgaste de nutrientes).
4. **Herramienta de Soporte a la Toma de Decisiones (DSS) y Motor de Recomendaciones:**
   * **Funcionalidad clave:** Basándose en el diagnóstico y las predicciones del modelo (déficit hídrico, pérdida de nutrientes, estrés térmico), la app recomendará **tipos específicos de fertilizantes** (ej. liberación controlada, biofertilizantes, balance NPK adaptado) o **métodos agronómicos** (ej. labranza de conservación, cultivos de cobertura, ajuste de riego) para optimizar la cosecha bajo las circunstancias detectadas, mostrando siempre el impacto y margen de incertidumbre de cada recomendación.

## 3. Variables y Capas de Datos Satelitales (Multispectral Stack)

El modelo y las visualizaciones integrarán múltiples fuentes de teledetección (*remote sensing*) de la NASA (APIs/datasets como NASA POWER, SMAP, MODIS, Landsat o GPM):

1. **Precipitación / Lluvia:** Patrones de lluvia, eventos extremos y bandas de precipitación.
2. **Humedad del Suelo (*Soil Moisture*):** Niveles de hidratación superficial y subsuperficial para detectar déficit hidrológico.
3. **Temperatura / Calor (*Thermal Flux / Raster*):** Estrés térmico en cultivos y temperatura de la superficie terrestre.
4. **Vegetación (*Vegetation Index*):** Salud y vigor de los cultivos (NDVI, infrarrojo, retrodispersión de radar).
5. **Recursos Hídricos (*Water*):** Disponibilidad general de agua y dinámica hidrológica.

## 4. Requisitos Obligatorios del Reto (Público Objetivo: Agricultores)

Toda funcionalidad en la app de Streamlit debe responder a cuatro pilares exigidos por el jurado de la NASA:

1. **Comparar rotaciones de cultivos (*Compare rotations*):** Evaluar distintos escenarios y secuencias de siembra en el tiempo.
2. **Revelar compensaciones (*Reveal tradeoffs*):** Mostrar los pros y contras de cada rotación, fertilizante o método recomendado (costo, consumo hídrico, salud del suelo).
3. **Comprender el riesgo (*Understand risk*):** Traducir métricas satelitales complejas en indicadores claros de riesgo a nivel de parcela.
4. **Hacer visible la incertidumbre (*Make uncertainty visible*):** Representar gráficamente los márgenes de error, rangos de probabilidad y variabilidad climática en las predicciones del modelo y en el éxito esperado de las recomendaciones.

## 5. Perfil del Equipo Organizador (Enfoque de Evaluación)

El reto fue diseñado por especialistas del Centro Espacial Johnson (JSC) con enfoque en:

* **Transformación Digital e Ingeniería de Sistemas:** Integración de sistemas complejos y flujos operativos (Sadie Barnett-Boudreau).
* **Arquitectura de Datos y Aplicaciones Web:** Pipelines de datos y herramientas web personalizadas (Anudeep Gogineni).
* **Ciencias de la Tierra y Teledetección:** Monitoreo ambiental mediante imágenes satelitales y de la ISS (Dr. William Stefanov).
* **Machine Learning aplicado a Teledetección:** Extracción de datos accionables a partir de observación terrestre (Alex Stoken).

## 6. Directrices para la IA Asistente

Al colaborar en el código, arquitectura o diseño de este proyecto, prioriza:

* **Stack Tecnológico:** Python, Streamlit (diseño limpio con `st.tabs`, `st.sidebar`, métricas y contenedores), Pandas/NumPy/Scikit-learn para el modelo, y librerías interactivas compatibles con Streamlit (`pydeck`/`folium` para mapas, `plotly` para gráficos con bandas de incertidumbre).
* **Lógica Agronómica Accionable:** Estructurar reglas o modelos híbridos que vinculen claramente las anomalías detectadas en los datos de la NASA (ej. bajo NDVI + alta temperatura + baja humedad) con la recomendación de fertilizantes o prácticas de manejo específicas y sus *tradeoffs*.
* **UX enfocada en el agricultor:** Evitar jerga técnica excesiva en la interfaz; presentar datos, riesgos e incertidumbre de forma visual e intuitiva.