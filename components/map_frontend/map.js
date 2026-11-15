// MapLibre is vendored above this inline CCv2 module (BSD-3-Clause, 5.24.0).
export default function ({ parentElement, data, setStateValue, setTriggerValue }) {
  const root = parentElement.querySelector('.parcel-map');
  if (!root) return;
  root.bridge = { data, setStateValue, setTriggerValue };
  const canvas = root.querySelector('.map-canvas');
  const status = root.querySelector('.map-status');
  const selection = root.querySelector('.map-selection');
  if (!root.map) {
    try {
      const camera = data.camera || { center: [-92.79, 42.73], zoom: 10.5 };
      const source = (name) => ({ type: 'raster', tiles: [`https://basemap.nationalmap.gov/arcgis/rest/services/${name}/MapServer/tile/{z}/{y}/{x}`], tileSize: 256, maxzoom: 19,
        attribution: name === 'USGSImageryOnly' ? 'USDA / USGS The National Map · Orthoimagery' : 'USGS The National Map · US Topo' });
      root.map = new maplibregl.Map({ container: canvas, center: camera.center, zoom: camera.zoom,
        minZoom: 3, maxZoom: 20, attributionControl: false,
        style: { version: 8, sources: { normal: source('USGSTopo'), aerial: source('USGSImageryOnly') }, layers: [
          { id: 'background', type: 'background', paint: { 'background-color': '#ded6c8' } },
          { id: 'normal', type: 'raster', source: 'normal', layout: { visibility: 'none' } },
          { id: 'aerial', type: 'raster', source: 'aerial', layout: { visibility: 'none' } }
        ] }, locale: { 'NavigationControl.ZoomIn': 'Acercar', 'NavigationControl.ZoomOut': 'Alejar', 'AttributionControl.ToggleAttribution': 'Créditos del mapa' } });
      const map = root.map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
      map.addControl(new maplibregl.AttributionControl({ compact: false }), 'bottom-left');
      const publishCamera = () => {
        const center = map.getCenter();
        const value = { center: [center.lng, center.lat], zoom: map.getZoom() };
        const serialized = JSON.stringify(value);
        if (root.lastCamera !== serialized) {
          root.lastCamera = serialized;
          root.bridge.setStateValue('camera', value);
        }
      };
      map.on('moveend', publishCamera);
      map.on('load', () => {
        map.addSource('fields', { type: 'geojson', data: root.bridge.data.collection });
        map.addLayer({ id: 'fields-fill', type: 'fill', source: 'fields', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.38 } });
        map.addLayer({ id: 'fields-outline', type: 'line', source: 'fields', paint: { 'line-color': '#28583b', 'line-width': 1.3 } });
        map.addLayer({ id: 'fields-selected', type: 'line', source: 'fields', filter: ['==', ['get', 'selected'], true], paint: { 'line-color': '#ffbe63', 'line-width': 3.5 } });
        root.ready = true;
        root.update();
        if (!data.camera) map.fitBounds(root.bridge.data.bounds, { padding: { top: 100, bottom: 85, left: 45, right: 95 }, maxZoom: 15, duration: 0 });
        publishCamera();
      });
      map.on('click', 'fields-fill', (event) => {
        const p = event.features?.[0]?.properties;
        if (p) root.bridge.setTriggerValue('selected', { plot_id: p.demo_plot_id, reference_id: p.reference_id });
      });
      map.on('mouseenter', 'fields-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', 'fields-fill', () => { map.getCanvas().style.cursor = ''; });
      map.on('error', () => { status.textContent = 'No se pudo cargar parte del fondo. Prueba «Sin fondo»; las parcelas son locales.'; });
      root.querySelector('.fit').onclick = () => map.fitBounds(root.bridge.data.bounds, { padding: { top: 100, bottom: 85, left: 45, right: 95 }, maxZoom: 15, duration: 400 });
      root.querySelector('.county').onclick = () => map.jumpTo({ center: [-92.79, 42.73], zoom: 10.5 });
      root.resizeObserver = new ResizeObserver(() => map.resize());
      root.resizeObserver.observe(root);
    } catch (error) {
      status.textContent = 'El navegador no pudo iniciar el mapa WebGL. Puedes elegir una parcela desde la lista.';
    }
  }
  root.update = () => {
    const d = root.bridge.data;
    const active = d.collection.features.find(f => f.properties.selected);
    selection.textContent = active ? `✓ ${active.properties.name} · límites simulados` : 'Sin parcela seleccionada';
    const map = root.map;
    if (!map) return;
    // No setStyle, jumpTo or fitBounds here: a basemap change never moves the camera.
    if (root.ready) {
      map.getSource('fields').setData(d.collection);
      map.setLayoutProperty('normal', 'visibility', d.basemap === 'Mapa normal' ? 'visible' : 'none');
      map.setLayoutProperty('aerial', 'visibility', d.basemap === 'Satelital' ? 'visible' : 'none');
      if (d.basemap === 'Sin fondo') status.textContent = 'Sin fondo externo · geometrías locales de demostración.';
      else if (root.lastBasemap !== d.basemap) status.textContent = '';
      root.lastBasemap = d.basemap;
    }
    for (const name of ['dragPan', 'doubleClickZoom', 'keyboard', 'touchZoomRotate']) {
      if (d.interactive) map[name].enable(); else map[name].disable();
    }
    map.scrollZoom.disable();
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
  };
  root.update();
  return () => {
    // CCv2 also calls cleanup on data updates; keep the map on those updates.
    queueMicrotask(() => {
      if (!root.isConnected) {
        root.resizeObserver?.disconnect();
        root.map?.remove();
        root.map = null;
      }
    });
  };
}
