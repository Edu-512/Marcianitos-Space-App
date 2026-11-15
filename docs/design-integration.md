# Integración de diseño general

Rama: `feature/design-integration`, creada desde `feature/map-navigation-polish` (`fe83d88`). Integra los cambios de `origin/style/general-design` (`f345bbb`) con la eliminación de la PWA autorizada por el usuario.

La combinación fue probada con git merge-tree antes de aplicarla: no hubo conflictos de texto. Se aplicó el árbol combinado sin crear un commit. Se excluyeron únicamente dos enlaces de herramientas de desarrollo (`.agents/skills/developing-with-streamlit` y `.claude/skills/developing-with-streamlit`) para conservar las carpetas locales existentes; no son parte del producto.

Se incorporan los espaciados generales, la alineación de tarjetas y las mejoras del chat para el teclado móvil, el viewport visible y el tamaño de los mensajes. Los archivos de mapa, navegación, vistas del modelo, contratos, datos y geometrías se verificaron idénticos a HEAD de la rama anterior. streamlit_app.py conserva nuestros cambios y añade los estilos de la otra rama.

Se retiran pwa_app.py, utils/pwa.py, manifiesto, registro, service worker, pantalla offline e iconos PWA, así como su dependencia explícita starlette y sus pruebas específicas. La aplicación se ejecuta y se despliega con **streamlit_app.py**.

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Validación: 42 pruebas Python y 11 JavaScript aprobadas, mypy sin errores en cinco módulos, diff sin errores de espacios. El recorrido HTTP real completó Explore Plots → My Field → Compare Crops → Recommendations → Explore Plots usando Field 25, Wet spring y cobertura. El selector de escritorio está en Selected Plot de la barra lateral.

La revisión visual real de escritorio/móvil sigue pendiente; JSDOM y la API del agente no sustituyen esa revisión. No se modificó master ni se hicieron commits, pushes, despliegues o pull requests. El siguiente paso es la validación visual, publicación de esta rama y PR hacia master.
## Logo y corrección de selección al mover el mapa

El logo principal de la aplicación usa `static/brand/know-your-farm-logo-v2.png` mediante st.logo. El icono compacto SVG se conserva para la pestaña y espacios pequeños.

Se corrige una condición de carrera: un evento de cámara podía provocar un render con selected_plot_id antiguo antes de confirmar el clic del usuario. El frontend distingue el último valor recibido del servidor de la selección local pendiente. La confirmación no vuelve a centrar el mapa; una elección posterior desde Change plot sigue aplicándose.

El evento de cámara incluye la selección y su campo de origen. Si llega antes del clic, el backend aplica el nuevo campo de forma atómica. Si pertenece a un mapa anterior a una selección posterior desde Change plot, se descarta. La cámara no modifica datos ni algoritmos del modelo.

Validación: 43 pruebas Python y 12 JavaScript aprobadas, con regresiones específicas de clic/pan/respuesta antigua y cambio posterior de selector. Aplicación real iniciada con PNG y selección sincronizada. La interacción visual real sigue pendiente de revisión manual.
