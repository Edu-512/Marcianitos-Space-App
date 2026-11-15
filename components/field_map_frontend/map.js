export default function({parentElement,data,setTriggerValue,setStateValue}) {
 const root=parentElement.querySelector('.field-scene');if(!root)return;
 root.bridge={data,setTriggerValue,setStateValue};
 const q=s=>root.querySelector(s), panel=q('.field-panel');
 const emit=(action)=>root.bridge.setTriggerValue('action',{plot_id:root.pid,climate_id:root.climate,plan_id:root.plan,expanded:root.expanded,action});
 const number=(v,d=1)=>Number.isFinite(Number(v))?Number(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d}):'Not available';
 const element=(tag,text,cls)=>{const el=document.createElement(tag);el.textContent=text;if(cls)el.className=cls;return el;};
 if(!root.map){
  root.pid=data.selected;root.climate=data.climate;root.plan=data.plan;root.panelOpen=Boolean(data.view?.open && data.view.plot_id===data.selected);root.expanded=Boolean(data.view?.expanded);
  try {
   const map=root.map=L.map(q('.field-canvas'),{zoomControl:true,scrollWheelZoom:false,attributionControl:false});
   L.control.attribution({position:'bottomleft'}).addTo(map);
   root.tiles={normal:L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'USGS The National Map · US Topo'}),aerial:L.tileLayer('https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'USDA / USGS The National Map · Orthoimagery'})};
   root.tiles.normal.addTo(map);
   for(const tile of Object.values(root.tiles))tile.on('tileerror',()=>{q('.scene-status').textContent='Background unavailable. Try the other map background; field outlines remain available.';});
   root.layer=L.geoJSON(data.geometry,{style:feature=>({color:feature.properties.plot_id===root.pid?'#b17b28':'#245e59',weight:feature.properties.plot_id===root.pid?3:1.4,fillColor:'#398c86',fillOpacity:.35}),onEachFeature:(feature,layer)=>{layer.on('click',()=>selectPlot(feature.properties.plot_id));}}).addTo(map);
   if(data.camera && (!data.camera.plot_id || data.camera.plot_id===data.selected))map.setView(data.camera.center,data.camera.zoom);else focusPlot();
   root.layer.eachLayer(layer=>{const el=layer.getElement();if(el){el.setAttribute('role','button');el.setAttribute('tabindex','0');el.setAttribute('aria-label',layer.feature.properties.name+' · satellite-derived field');el.onkeydown=ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();selectPlot(layer.feature.properties.plot_id);}};}});
   map.on('moveend',()=>{const center=map.getCenter();const camera={center:[center.lat,center.lng],zoom:map.getZoom(),plot_id:root.pid};const serialized=JSON.stringify(camera);if(root.lastCamera!==serialized){root.lastCamera=serialized;root.bridge.setStateValue('camera',camera);}});
   root.resize=new ResizeObserver(()=>map.invalidateSize());root.resize.observe(root);
   q('.fit').onclick=()=>focusPlot();
   q('.basemap').onchange=ev=>{for(const tile of Object.values(root.tiles))if(map.hasLayer(tile))map.removeLayer(tile);if(root.tiles[ev.target.value])root.tiles[ev.target.value].addTo(map);q('.scene-status').textContent='';};
   L.DomEvent.disableClickPropagation(panel);L.DomEvent.disableScrollPropagation(panel);
  } catch(err){q('.scene-status').textContent='The map could not start. Use Change plot above to access the model profiles.';}
  q('.close').onclick=()=>{root.panelOpen=false;panel.hidden=true;saveView();};
  q('.panel-toggle').onclick=()=>{root.expanded=!root.expanded;renderPanel();saveView();};
  q('.climate').onchange=ev=>{root.climate=ev.target.value;renderPanel();emit('climate');};
  q('.full-comparison').onclick=()=>emit('compare');q('.view-field').onclick=()=>emit('home');
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
 if(root.pid!==data.selected){root.pid=data.selected;root.panelOpen=true;root.expanded=false;focusPlot();}
 root.climate=data.climate;root.plan=data.plan;renderPanel();
 return ()=>queueMicrotask(()=>{if(!root.isConnected){root.resize?.disconnect();root.map?.remove();root.map=null;}});
}
