const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
const {JSDOM}=require('../.venv/js-tests/node_modules/jsdom');
const folder='components/field_map_frontend/';
const raw=JSON.parse(fs.readFileSync('model/datos_ui/resultado_todas.json','utf8'));
function setup(){
 const dom=new JSDOM(fs.readFileSync(folder+'map.html','utf8'),{runScripts:'outside-only'}),w=dom.window,events=[];let instances=0;
 class FakeMap {constructor(){this.events={};this.center=[42.73,-92.79];this.zoom=12;this.fits=0;instances++;}on(k,f){this.events[k]=f;}fitBounds(){this.fits++;return this;}setView(c,z){this.center=c;this.zoom=z;return this;}getCenter(){return {lat:this.center[0],lng:this.center[1]};}getZoom(){return this.zoom;}hasLayer(){return true;}removeLayer(){}invalidateSize(){}remove(){this.removed=true;}}
 w.L={map:()=>new FakeMap(),control:{attribution:()=>({addTo(){}})},tileLayer:()=>({addTo(){return this;},on(){return this;}}),DomEvent:{disableClickPropagation(){},disableScrollPropagation(){}},geoJSON:(data,options)=>{
  const layers=data.features.map(feature=>{const el=w.document.createElement('button');w.document.querySelector('.field-canvas').append(el);const l={feature,events:{},on(k,f){this.events[k]=f;},getElement(){return el;},getBounds(){return [[42.7,-92.8],[42.71,-92.79]];}};options.onEachFeature(feature,l);return l;});
  return {layers,addTo(){return this;},eachLayer(fn){layers.forEach(fn);},getBounds(){return [];},setStyle(){}};
 }};
 w.ResizeObserver=class{observe(){}disconnect(){}};
 w.eval(fs.readFileSync(folder+'map.js','utf8').replace('export default function','window.mountMap=function'));
 const profiles=Object.fromEntries(raw.parcelas.map(p=>[String(p.parcela.id),p]));
 const data={profiles,names:Object.fromEntries(Object.keys(profiles).map(id=>[id,'Profile '+id])),selected:'806',climate:'normal',plan:null,
  plans:{maiz_continuo:'Continuous maize',maiz_soya:'Maize & soybean',maiz_soya_cobertura:'Rotation with cover'},climates:{normal:'Normal',seco_caluroso:'Dry',humedo_primavera:'Wet'},geometry:{features:Object.keys(profiles).map(id=>({properties:{plot_id:id,name:'Profile '+id}}))}};
 let cleanup;function render(p={}){Object.assign(data,p);cleanup?.();cleanup=w.mountMap({parentElement:w.document,data,setTriggerValue:(k,v)=>events.push([k,v]),setStateValue:(k,v)=>events.push([k,v])});}
 render();const root=w.document.querySelector('.field-scene');return {dom,w,data,root,events,render,instances:()=>instances};
}
test('map click opens three cards from the exact profile and emits canonical IDs',()=>{
 const t=setup();assert.equal(t.root.querySelector('.field-panel').hidden,true);
 t.root.layer.layers.find(l=>l.feature.properties.plot_id==='467').events.click();
 assert.equal(t.root.querySelector('.field-panel').hidden,false);assert.equal(t.root.querySelectorAll('.rotation-card').length,3);
 assert.equal(t.events.at(-1)[1].plot_id,'467');
 const source=t.data.profiles['467'].escenarios.normal.planes.find(p=>p.id==='maiz_continuo');
 assert.match(t.root.querySelector('.rotation-card .metric').textContent,new RegExp(String(source.economia.margen_usd_acre.p50)));
 t.root.querySelector('.rotation-card button').click();assert.equal(t.events.at(-1)[1].plan_id,'maiz_continuo');
 t.root.querySelector('.climate').value='seco_caluroso';t.root.querySelector('.climate').dispatchEvent(new t.w.Event('change'));
 assert.equal(t.events.at(-1)[1].climate_id,'seco_caluroso');assert.equal(t.root.querySelectorAll('.rotation-card').length,3);
 t.dom.window.close();
});
test('rerenders preserve map instance and exact camera; close does not change selection',async()=>{
 const t=setup(),map=t.root.map;map.center=[42.73456789,-92.7987654];map.zoom=13.12345;const fits=map.fits;
 t.render({climate:'humedo_primavera'});await Promise.resolve();assert.equal(t.instances(),1);assert.equal(map.fits,fits);assert.equal(map.removed,undefined);
 assert.deepEqual(map.center,[42.73456789,-92.7987654]);assert.equal(map.zoom,13.12345);
 t.root.querySelector('.close').click();assert.equal(t.root.querySelector('.field-panel').hidden,true);assert.equal(t.data.selected,'806');
 t.dom.window.close();
});

// Real vendored Leaflet parsing/SVG in a simulated DOM (no basemap network).
test('real Leaflet draws all 167 source geometries with their MultiPolygons and holes',()=>{
 const dom=new JSDOM(fs.readFileSync(folder+'map.html','utf8'),{runScripts:'outside-only',pretendToBeVisual:true,url:'http://localhost/'}),w=dom.window;
 w.SVGSVGElement.prototype.createSVGRect=function(){return {};};
 w.ResizeObserver=class{observe(){}disconnect(){}};
 w.eval(fs.readFileSync(folder+'vendor/leaflet.js','utf8'));
 w.eval(fs.readFileSync(folder+'map.js','utf8').replace('export default function','window.mountMap=function'));
 const geometry=JSON.parse(fs.readFileSync('model/datos_ui/parcelas_todas.geojson','utf8'));
 for(const feature of geometry.features){feature.properties.plot_id=String(feature.properties.id);feature.properties.name='Field '+feature.properties.id;}
 const profiles=Object.fromEntries(raw.parcelas.map(p=>[String(p.parcela.id),p]));
 const data={geometry,profiles,names:Object.fromEntries(Object.keys(profiles).map(id=>[id,'Field '+id])),selected:'806',climate:'normal',plan:null,
  plans:{maiz_continuo:'Continuous maize',maiz_soya:'Maize & soybean',maiz_soya_cobertura:'Rotation with cover'},climates:{normal:'Normal',seco_caluroso:'Dry',humedo_primavera:'Wet'}};
 const events=[];
 w.mountMap({parentElement:w.document,data,setTriggerValue:(k,v)=>events.push(v),setStateValue:()=>{}});
 const root=w.document.querySelector('.field-scene'),layers=root.layer.getLayers();
 assert.equal(root.querySelector('.scene-status').textContent,'');
 assert.equal(layers.length,167);assert.equal(root.querySelectorAll('path.leaflet-interactive').length,167);
 for(const layer of layers){
  assert.deepEqual(JSON.parse(JSON.stringify(layer.toGeoJSON(false).geometry)),geometry.features.find(f=>f.properties.id===layer.feature.properties.id).geometry);
  assert.equal(layer.options.fillRule,'evenodd');
 }
 const multi=layers.find(l=>l.feature.geometry.type==='MultiPolygon');multi.fire('click');
 assert.equal(events.at(-1).plot_id,multi.feature.properties.plot_id);assert.equal(root.querySelectorAll('.rotation-card').length,3);
 const feature=layers.find(l=>l.feature.properties.plot_id==='467');
 feature.getElement().dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
 assert.equal(events.at(-1).plot_id,'467');
 root.map.remove();dom.window.close();
});

test('selection zooms to its field and survives zoom, camera rerenders and panel toggle',()=>{
 const t=setup(),map=t.root.map,initial=map.fits;
 t.root.layer.layers.find(l=>l.feature.properties.plot_id==='467').events.click();
 assert.equal(map.fits,initial+1);assert.equal(t.root.pid,'467');
 t.render({selected:'467',view:{plot_id:'467',open:true,expanded:false}});
 t.root.querySelector('.fit').click();assert.equal(map.fits,initial+2);
 assert.equal(t.root.pid,'467');assert.equal(t.root.querySelector('.field-panel').hidden,false);
 map.events.moveend();t.render({camera:{center:[42.7,-92.8],zoom:15}});
 assert.equal(t.root.pid,'467');assert.equal(t.root.querySelector('.field-panel').hidden,false);
 const fits=map.fits;t.render({selected:'806'});assert.equal(map.fits,fits+1);
 t.root.querySelector('.panel-toggle').click();assert.equal(t.root.querySelector('.panel-toggle').getAttribute('aria-expanded'),'true');
 assert.equal(t.events.at(-1)[0],'view');assert.equal(t.events.at(-1)[1].expanded,true);
 assert.deepEqual(Array.from(t.root.querySelector('.basemap').options,o=>o.value),['normal','aerial']);
 t.dom.window.close();
});

test('a stale camera rerender cannot restore the default field before a click is acknowledged',()=>{
 const t=setup(),map=t.root.map;
 t.root.layer.layers.find(l=>l.feature.properties.plot_id==='467').events.click();
 const fits=map.fits;
 // Backend still reports the initial field while the click request is pending.
 map.events.moveend();t.render({selected:'806',camera:{center:[42.7,-92.8],zoom:14}});
 assert.equal(t.root.pid,'467');assert.equal(map.fits,fits);
 assert.equal(t.root.querySelector('.panel-title').textContent,'Profile 467');
 // Acknowledging the click must not zoom back or replace the camera.
 t.render({selected:'467'});assert.equal(t.root.pid,'467');assert.equal(map.fits,fits);
 // A later, genuine selection through Change plot still wins.
 t.render({selected:'1413'});assert.equal(t.root.pid,'1413');assert.equal(map.fits,fits+1);
 t.dom.window.close();
});
