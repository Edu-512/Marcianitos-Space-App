const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
const {JSDOM}=require('../.venv/js-tests/node_modules/jsdom');
const folder='components/field_map_frontend/';
const raw=JSON.parse(fs.readFileSync('model/datos_ui/resultado_todas.json','utf8'));

// Real Leaflet + map.js; MapLibre is stubbed because jsdom has no WebGL.
function setup(nationalOn=true){
 const dom=new JSDOM(fs.readFileSync(folder+'map.html','utf8'),{runScripts:'outside-only',pretendToBeVisual:true,url:'http://localhost/'}),w=dom.window;
 w.SVGSVGElement.prototype.createSVGRect=function(){return {};};
 w.ResizeObserver=class{observe(){}disconnect(){}};
 w.eval(fs.readFileSync(folder+'vendor/leaflet.js','utf8'));
 const calls={protocols:[],layers:[],hits:[]};
 const gl={handlers:{},on(k,f){this.handlers[k]=f;},getLayer:id=>id==='csb-fill',project:p=>({x:p[0],y:p[1]}),
  queryRenderedFeatures:(point,opts)=>{calls.query={point,opts};return calls.hits;}};
 w.maplibregl={addProtocol:(name,fn)=>calls.protocols.push([name,typeof fn])};
 w.pmtiles={Protocol:class{constructor(){this.tilev4=()=>{};}}};
 w.L.maplibreGL=options=>{const layer=new w.L.Layer();layer.options=Object.assign({},options);calls.layers.push(layer);
  layer.onAdd=function(map){this._added=map.getPane(options.pane);return this;};layer.onRemove=function(){this._added=null;};layer.getMaplibreMap=()=>gl;return layer;};
 w.eval(fs.readFileSync(folder+'map.js','utf8').replace('export default function','window.mountMap=function'));
 const geometry=JSON.parse(fs.readFileSync('model/datos_ui/parcelas_todas.geojson','utf8'));
 for(const f of geometry.features){f.properties.plot_id=String(f.properties.id);f.properties.name='Field '+f.properties.id;}
 const profiles=Object.fromEntries(raw.parcelas.map(p=>[String(p.parcela.id),p]));
 const national={url:'https://data.source.coop/ftw/usda-csb/csb_2025.pmtiles',source_layer:'fields',crop_year:2025,attribution:'USDA NASS CSB',
  bounds:[[24.4,-125],[49.5,-66.9]],vendor:{maplibre_js:'a.js',maplibre_css:'a.css',pmtiles_js:'b.js',binding_js:'c.js'},
  fill_color:['match',['to-number',['get','cdl']],[1],'#e0b400','#8c8c8c'],legend:[['Corn','#e0b400'],['Other crops and land','#8c8c8c']],crop_names:{'1':'Corn','5':'Soybeans'}};
 const data={geometry,profiles,names:Object.fromEntries(Object.keys(profiles).map(id=>[id,'Field '+id])),selected:'806',climate:'normal',plan:null,
  plans:{maiz_continuo:'Continuous maize',maiz_soya:'Maize & soybean',maiz_soya_cobertura:'Rotation with cover'},climates:{normal:'Normal',seco_caluroso:'Dry',humedo_primavera:'Wet'},national,national_on:nationalOn};
 const events=[];
 w.mountMap({parentElement:w.document,data,setTriggerValue:(k,v)=>events.push([k,v]),setStateValue:(k,v)=>events.push([k,v])});
 return {dom,w,root:w.document.querySelector('.field-scene'),calls,gl,events};
}
const settle=()=>new Promise(r=>setTimeout(r,0));

test('US fields load as a WebGL layer between the basemap and the Butler plots',async()=>{
 const t=setup();await settle();
 assert.deepEqual(t.calls.protocols,[['pmtiles','function']]);assert.equal(t.calls.layers.length,1);
 const layer=t.calls.layers[0],style=layer.options.style;
 assert.equal(style.sources.csb.url,'pmtiles://https://data.source.coop/ftw/usda-csb/csb_2025.pmtiles');
 assert.ok(style.layers.every(l=>l['source-layer']==='fields'));
 assert.equal(layer.options.pane,'nationalFields');assert.equal(t.root.map.getPane('nationalFields').style.zIndex,'350');
 assert.ok(t.root.map.hasLayer(layer));assert.equal(layer.getAttribution(),'USDA NASS CSB');
 assert.equal(t.root.querySelector('.national-legend').hidden,false);assert.equal(t.root.querySelectorAll('.national-legend li').length,2);
 assert.equal(t.root.querySelector('.national').getAttribute('aria-pressed'),'true');
 assert.equal(t.root.layer.getLayers().length,167);
 t.root.map.remove();t.dom.window.close();
});

test('clicking a US field shows its recorded 2025 crop as text; Butler clicks keep the plot panel',async()=>{
 const t=setup();await settle();const map=t.root.map;
 t.calls.hits=[{properties:{cdl:5,CSBID:'191825003690436'}}];
 map.fire('click',{latlng:L_latlng(t.w,42.74,-92.81)});
 const popup=t.root.querySelector('.national-popup');
 assert.ok(popup);assert.match(popup.textContent,/Crop in 2025: Soybeans/);assert.match(popup.textContent,/191825003690436/);
 assert.equal(JSON.stringify(t.calls.query.opts),'{"layers":["csb-fill"]}');
 t.calls.hits=[{properties:{cdl:999,CSBID:'<img src=x onerror=alert(1)>'}}];
 map.fire('click',{latlng:L_latlng(t.w,42.75,-92.82)});
 const unknown=t.root.querySelector('.national-popup');
 assert.match(unknown.textContent,/Cropland Data Layer code 999/);assert.equal(unknown.querySelector('img'),null);
 map.closePopup();
 const plot=t.root.layer.getLayers().find(l=>l.feature.properties.plot_id==='467');plot.fire('click');
 assert.equal(t.root.querySelector('.national-popup'),null);assert.equal(t.root.querySelector('.field-panel').hidden,false);
 t.root.map.remove();t.dom.window.close();
});

test('the toggle removes the layer, remembers the choice, and Whole US turns it back on',async()=>{
 const t=setup(false);await settle();
 assert.equal(t.calls.layers.length,0);assert.equal(t.root.querySelector('.national-legend').hidden,true);
 t.root.querySelector('.national').click();await settle();
 assert.deepEqual(t.events.at(-1),['national',true]);assert.ok(t.root.map.hasLayer(t.calls.layers[0]));
 t.root.querySelector('.national').click();await settle();
 assert.deepEqual(t.events.at(-1),['national',false]);assert.equal(t.root.map.hasLayer(t.calls.layers[0]),false);
 t.root.querySelector('.usa').click();await settle();
 assert.ok(t.root.map.hasLayer(t.calls.layers[0]));assert.ok(t.root.map.getZoom()<=5);
 t.root.map.remove();t.dom.window.close();
});

function L_latlng(w,lat,lng){return w.L.latLng(lat,lng);}
