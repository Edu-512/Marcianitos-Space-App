export default function({parentElement,data,setTriggerValue,setStateValue}) {
 const root=parentElement.querySelector('.field-scene');if(!root)return;
 root.bridge={data,setTriggerValue,setStateValue};
 const q=s=>root.querySelector(s), panel=q('.field-panel');
 const emit=(action)=>root.bridge.setTriggerValue('action',{plot_id:root.pid,climate_id:root.climate,plan_id:root.plan,expanded:root.expanded,source_plot_id:root.serverSelected,action});
 const number=(v,d=1)=>Number.isFinite(Number(v))?Number(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d}):'Not available';
 const element=(tag,text,cls)=>{const el=document.createElement(tag);el.textContent=text;if(cls)el.className=cls;return el;};
 if(!root.map){
  root.serverSelected=data.selected;root.serverClimate=data.climate;root.serverPlan=data.plan;
  root.pid=data.selected;root.climate=data.climate;root.plan=data.plan;root.panelOpen=Boolean(data.view?.open && data.view.plot_id===data.selected);root.expanded=Boolean(data.view?.expanded);
  try {
   const map=root.map=L.map(q('.field-canvas'),{zoomControl:true,scrollWheelZoom:false,attributionControl:false});
   L.control.attribution({position:'bottomleft'}).addTo(map);
   root.tiles={normal:L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'USGS The National Map · US Topo'}),aerial:L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'USDA / USGS The National Map · Orthoimagery'})};
   root.tiles.normal.addTo(map);
   for(const tile of Object.values(root.tiles))tile.on('tileerror',()=>{q('.scene-status').textContent='Background unavailable. Try the other map background; field outlines remain available.';});
   root.layer=L.geoJSON(data.geometry,{style:feature=>({color:feature.properties.plot_id===root.pid?'#b17b28':'#245e59',weight:feature.properties.plot_id===root.pid?3:1.4,fillColor:'#398c86',fillOpacity:.35}),onEachFeature:(feature,layer)=>{layer.on('click',()=>{root.plotClicked=true;selectPlot(feature.properties.plot_id);});}}).addTo(map);
   if(data.camera && (!data.camera.plot_id || data.camera.plot_id===data.selected))map.setView(data.camera.center,data.camera.zoom);else focusPlot();
   root.layer.eachLayer(layer=>{const el=layer.getElement();if(el){el.setAttribute('role','button');el.setAttribute('tabindex','0');el.setAttribute('aria-label',layer.feature.properties.name+' · satellite-derived field');el.onkeydown=ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();selectPlot(layer.feature.properties.plot_id);}};}});
   map.on('moveend',()=>{const center=map.getCenter();const camera={center:[center.lat,center.lng],zoom:map.getZoom(),plot_id:root.pid,source_plot_id:root.serverSelected,climate_id:root.climate,plan_id:root.plan,expanded:root.expanded};const serialized=JSON.stringify(camera);if(root.lastCamera!==serialized){root.lastCamera=serialized;root.bridge.setStateValue('camera',camera);}});
   root.resize=new ResizeObserver(()=>map.invalidateSize());root.resize.observe(root);
   q('.fit').onclick=()=>focusPlot();
   q('.basemap').onchange=ev=>{for(const tile of Object.values(root.tiles))if(map.hasLayer(tile))map.removeLayer(tile);if(root.tiles[ev.target.value])root.tiles[ev.target.value].addTo(map);q('.scene-status').textContent='';};
   L.DomEvent.disableClickPropagation(panel);L.DomEvent.disableScrollPropagation(panel);
  } catch(err){q('.scene-status').textContent='The map could not start. Use Change plot above to access the model profiles.';}
  if(root.map&&data.national)initNational(data.national,data.national_on!==false);
  q('.close').onclick=()=>{root.panelOpen=false;panel.hidden=true;saveView();};
  q('.panel-toggle').onclick=()=>{root.expanded=!root.expanded;renderPanel();saveView();};
  q('.climate').onchange=ev=>{root.climate=ev.target.value;renderPanel();emit('climate');};
  q('.full-comparison').onclick=()=>emit('compare');q('.view-field').onclick=()=>emit('home');
 }
 // Nationwide USDA field outlines: WebGL vector tiles streamed from a public PMTiles
 // archive with HTTP range requests (only the visible tiles; nothing goes through Streamlit).
 function loadScript(src){
  const url=new URL(src,document.baseURI).href;
  return new Promise((ok,fail)=>{
   const found=[...document.querySelectorAll('script[data-fs-vendor]')].find(el=>el.src===url);
   if(found&&found.dataset.loaded){ok();return;}
   const el=found||Object.assign(document.createElement('script'),{src:url,async:false});
   el.dataset.fsVendor='1';el.addEventListener('load',()=>{el.dataset.loaded='1';ok();});el.addEventListener('error',fail);
   if(!found)document.head.append(el);
  });
 }
 async function nationalLibraries(v){
  if(!root.querySelector('link.maplibre-css')){const link=document.createElement('link');link.rel='stylesheet';link.className='maplibre-css';link.href=new URL(v.maplibre_css,document.baseURI).href;root.append(link);}
  if(!window.maplibregl)await loadScript(v.maplibre_js);
  if(!window.pmtiles)await loadScript(v.pmtiles_js);
  if(!L.maplibreGL)await loadScript(v.binding_js);
  if(!window.__fieldShiftPmtiles){window.__fieldShiftPmtiles=new window.pmtiles.Protocol();window.maplibregl.addProtocol('pmtiles',window.__fieldShiftPmtiles.tilev4);}
 }
 function nationalStyle(n){
  return {version:8,sources:{csb:{type:'vector',url:'pmtiles://'+n.url}},layers:[
   {id:'csb-fill',type:'fill',source:'csb','source-layer':n.source_layer,paint:{'fill-color':n.fill_color,'fill-opacity':['interpolate',['linear'],['zoom'],4,0.8,12,0.45]}},
   {id:'csb-line',type:'line',source:'csb','source-layer':n.source_layer,minzoom:9,paint:{'line-color':'#2b1d12','line-opacity':0.5,'line-width':['interpolate',['linear'],['zoom'],9,0.3,14,1.2]}}]};
 }
 function nationalStatus(text){const status=q('.scene-status');if(text)status.textContent=text;else if(status.dataset.national)status.textContent='';status.dataset.national=text?'1':'';}
 async function setNational(on,emitState){
  const n=root.bridge.data.national,map=root.map;if(!n||!map)return;
  root.nationalOn=on;const button=q('.national');button.setAttribute('aria-pressed',String(on));button.textContent=on?'US fields: on':'US fields: off';
  q('.national-legend').hidden=!on;
  if(emitState)root.bridge.setStateValue('national',on);
  if(!on){if(root.national&&map.hasLayer(root.national))map.removeLayer(root.national);nationalStatus('');return;}
  try{
   if(!root.national){
    nationalStatus('Loading US field outlines…');
    await nationalLibraries(n.vendor);
    if(root.map!==map)return;
    if(!map.getPane('nationalFields')){const pane=map.createPane('nationalFields');pane.style.zIndex='350';pane.style.pointerEvents='none';}
    root.national=L.maplibreGL({style:nationalStyle(n),pane:'nationalFields',interactive:false,attributionControl:false,attribution:n.attribution});
   }
   if(!root.nationalOn)return;
   if(!map.hasLayer(root.national))root.national.addTo(map);
   const gl=root.national.getMaplibreMap();
   if(gl&&!gl._fieldShiftHooked){
    gl._fieldShiftHooked=true;
    gl.on('idle',()=>nationalStatus(''));
    gl.on('error',()=>nationalStatus('Some US field tiles could not load. Check your connection; the Butler fields remain available.'));
   }
  }catch(err){
   root.nationalOn=false;button.setAttribute('aria-pressed','false');button.textContent='US fields: off';q('.national-legend').hidden=true;
   nationalStatus('US field outlines could not load (they need internet and WebGL). The Butler fields remain available.');
  }
 }
 function nationalClick(event){
  if(root.plotClicked){root.plotClicked=false;return;}
  const n=root.bridge.data.national;if(!n||!root.nationalOn||!root.national||!root.map.hasLayer(root.national))return;
  const gl=root.national.getMaplibreMap();if(!gl||!gl.getLayer('csb-fill'))return;
  const hit=gl.queryRenderedFeatures(gl.project([event.latlng.lng,event.latlng.lat]),{layers:['csb-fill']})[0];
  if(!hit){root.map.closePopup();return;}
  const code=Number(hit.properties.cdl),box=element('div','','national-popup');
  const crop=!Number.isFinite(code)?'Not recorded':(n.crop_names[String(code)]||`Cropland Data Layer code ${code}`);
  box.append(element('strong',`Crop in ${n.crop_year}: ${crop}`),element('small',`USDA field ID ${hit.properties.CSBID??'not available'} · outline from 2018–2025 satellite data · not a property line`));
  L.popup({maxWidth:270}).setLatLng(event.latlng).setContent(box).openOn(root.map);
 }
 function initNational(n,on){
  const toggle=q('.national'),usa=q('.usa'),legend=q('.national-legend');
  toggle.hidden=false;usa.hidden=false;q('.crop-year').textContent=String(n.crop_year);
  const list=legend.querySelector('ul');list.replaceChildren();
  for(const [label,color] of n.legend){const item=element('li',label);const swatch=element('span','','swatch');swatch.style.background=color;item.prepend(swatch);list.append(item);}
  toggle.onclick=()=>setNational(!root.nationalOn,true);
  usa.onclick=()=>{root.map.closePopup();root.map.fitBounds(n.bounds);if(!root.nationalOn)setNational(true,true);};
  L.DomEvent.disableClickPropagation(legend);L.DomEvent.disableScrollPropagation(legend);
  root.map.on('click',nationalClick);
  setNational(on,false);
 }
 function saveView(){root.bridge.setStateValue('view',{plot_id:root.pid,open:root.panelOpen,expanded:root.expanded});}
 function focusPlot(){
  if(!root.map || !root.layer)return;
  root.layer.eachLayer(layer=>{if(layer.feature.properties.plot_id===root.pid)root.map.fitBounds(layer.getBounds(),{padding:[48,48],maxZoom:16,animate:false});});
 }
 function selectPlot(pid){if(root.pid!==pid){root.plan=null;root.expanded=false;}root.pid=pid;root.panelOpen=true;renderPanel();emit('plot');focusPlot();}

 function renderPanel(){
  const d=root.bridge.data,item=d.profiles[root.pid];if(!item)return;
  panel.hidden=!root.panelOpen;panel.classList.toggle('is-expanded',Boolean(root.expanded));
  q('.panel-toggle').setAttribute('aria-expanded',String(Boolean(root.expanded)));q('.panel-toggle').textContent=root.expanded?'Hide rotations':'View rotations';
  q('.panel-title').textContent=d.names[root.pid];q('.profile-area').textContent=`Profile ${root.pid} · ${number(item.parcela.acres,0)} acres · satellite-derived outline`;
  const climate=q('.climate');climate.replaceChildren();for(const [id,label]of Object.entries(d.climates)){const opt=element('option',label);opt.value=id;climate.append(opt);}climate.value=root.climate;
  const cards=q('.rotation-cards');cards.replaceChildren();
  for(const [id,title]of Object.entries(d.plans)){
   const out=item.escenarios[root.climate]?.planes.find(p=>p.id===id);if(!out)continue;
   const card=element('article','',`rotation-card${root.plan===id?' selected':''}`);card.append(element('h3',title));
   const margin=out.economia.margen_usd_acre,yield_=out.rendimiento_maiz_bu_acre;
   card.append(element('small','Estimated margin · USD/acre'),element('div',number(margin.p50,0),'metric'),element('small',`p10–p90: ${number(margin.p10,0)} to ${number(margin.p90,0)}`),element('p',`Maize: ${number(yield_.p50)} bu/acre`),element('small',`p10–p90: ${number(yield_.p10)} to ${number(yield_.p90)}`),element('p',`Soil loss: ${number(out.suelo.erosion_ton_acre_anio)} ton/acre/year`));
   const button=element('button',root.plan===id?'✓ Selected':'Explore this plan');button.type='button';button.onclick=()=>{root.plan=id;renderPanel();emit('plan');};card.append(button);cards.append(card);
  }
  if(root.layer)root.layer.setStyle(feature=>({color:feature.properties.plot_id===root.pid?'#b17b28':'#245e59',weight:feature.properties.plot_id===root.pid?3:1.4}));
 }
 // Camera reruns may carry the old backend selection while the click is in flight.
 // Hydrate only a genuinely new server value, never reapply its unchanged default.
 if(root.serverSelected!==data.selected){
  root.serverSelected=data.selected;
  if(root.pid!==data.selected){root.pid=data.selected;root.panelOpen=true;root.expanded=false;focusPlot();}
 }
 if(root.serverClimate!==data.climate){root.serverClimate=data.climate;root.climate=data.climate;}
 if(root.serverPlan!==data.plan){root.serverPlan=data.plan;root.plan=data.plan;}
 renderPanel();
 return ()=>queueMicrotask(()=>{if(!root.isConnected){root.resize?.disconnect();root.map?.remove();root.map=null;}});
}
