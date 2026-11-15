# Ajustes de interacción y presentación del mapa

Implementados en `feature/map-navigation-polish`, sin modificar datos, geometrías ni cálculos del modelo.

- Seleccionar un campo desde el mapa o Change plot centra y ajusta el zoom a su geometría. Zoom to field vuelve al campo activo; los controles de zoom no cambian el ID seleccionado.
- Cámara y ventana de información se guardan por separado en la sesión. El panel conserva su estado al redibujar; los selectores abren el panel del nuevo campo.
- Se retira No background. Ante un fallo de teselas se ofrece probar el otro fondo sin ocultar los contornos locales.
- Change plot se presenta arriba a la derecha, con botón mayor, en escritorio y móvil. La barra lateral conserva el nombre del campo; el selector de escritorio se traslada al popover derecho.
- El mapa crea un contexto de apilamiento propio para que las capas de Leaflet y el panel no cubran el asistente flotante.
- En teléfono la información se presenta en una tarjeta flotante compacta, con View rotations / Hide rotations. La ventana ocupa como máximo 44% del mapa y deja libre el lateral derecho para Mr Corn.
- Plan inputs & complete output presenta ingreso, costos, nitrógeno, riesgo y confianza con etiquetas y unidades; se elimina el visor JSON.
- La cabecera móvil del dock muestra únicamente Step #/4.
- Se retira el anuncio general Research model solicitado. Los avisos de procedencia, incertidumbre y límites se conservan en sus detalles pertinentes y el demo sigue identificado.

Validación: 45 pruebas Python y 14 JavaScript aprobadas; mypy en los cuatro módulos Python cambiados y compilación sin errores. Las pruebas del mapa incluyen Leaflet real en JSDOM, eventos de selección, zoom, teclado, cámara y panel desplegable. El agente HTTP comprueba arranque, cambio de campo, comparación sin JSON/anuncio y paso a recomendaciones.

El host de acceso al navegador sigue indisponible: no se afirma una revisión visual real del apilamiento ni de los tamaños móviles. Revisar manualmente a 360/390 px y en escritorio: seleccionar una parcela, usar +/− y Zoom to field, desplegar/plegar rotaciones, abrir Mr Corn encima del mapa, cambiar el campo desde el control derecho y abrir los detalles de Compare Crops. Conservar tema claro/oscuro y teclado. No se realizan commits ni pushes.
