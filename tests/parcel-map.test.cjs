const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { JSDOM } = require('../.venv/js-tests/node_modules/jsdom');
const source = fs.readFileSync('components/map_frontend/map.js','utf8');
function setup(camera=null) {
 const dom=new JSDOM('<section class="parcel-map"><div class="map-canvas"></div><button class="fit"></button><button class="county"></button><p class="map-status"></p><p class="map-selection"></p></section>',{runScripts:'outside-only'});
 const w=dom.window, events=[]; let instances=0;
 class MapMock {
  constructor(options){this.options=options;this.center=options.center;this.zoom=options.zoom;this.events={};this.layouts={};this.fits=0;this.jumps=0;instances++;for(const key of ['dragPan','doubleClickZoom','keyboard','touchZoomRotate','scrollZoom','dragRotate'])this[key]={enable(){},disable(){},disableRotation(){}};}
  addControl(){} on(name,layer,handler){this.events[name]=handler||layer;} addSource(_id,value){this.geo=value.data;}
  addLayer(){} getSource(){return {setData:data=>{this.geo=data;}};} setLayoutProperty(id,_key,value){this.layouts[id]=value;}
  getCenter(){return {lng:this.center[0],lat:this.center[1]};} getZoom(){return this.zoom;}
  fitBounds(){this.fits++;} jumpTo(c){this.jumps++;this.center=c.center;this.zoom=c.zoom;}
  getCanvas(){return {style:{}};} resize(){} remove(){this.removed=true;}
 }
 w.maplibregl={Map:MapMock,NavigationControl:class{},AttributionControl:class{}};
 w.ResizeObserver=class{observe(){} disconnect(){}};
 w.eval(source.replace('export default function','window.mountMap = function'));
 const data={camera,basemap:'Mapa normal',interactive:true,bounds:[[-92.81,42.72],[-92.78,42.74]],collection:{type:'FeatureCollection',features:[{properties:{demo_plot_id:'lote-sur',reference_id:'demo-19023-lote-sur',selected:true,name:'Lote Sur'},geometry:{}}]}};
 let cleanup;
 const render=changes=>{Object.assign(data,changes);cleanup?.();cleanup=w.mountMap({parentElement:w.document,data,setStateValue:(name,value)=>events.push({name,value}),setTriggerValue:(name,value)=>events.push({name,value})});};
 render({});const root=w.document.querySelector('.parcel-map');root.map.events.load();
 return {w,data,root,events,render,instances:()=>instances};
}
test('basemap changes preserve exact camera, selection, geometries and map instance',async()=>{
 const t=setup();const map=t.root.map;map.center=[-92.790123456,42.73123456];map.zoom=14.123456789;map.events.moveend();
 const geometry=JSON.stringify(map.geo),fits=map.fits;
 t.render({basemap:'Satelital'});await Promise.resolve();
 assert.equal(t.instances(),1);assert.equal(map.removed,undefined);assert.equal(map.fits,fits);assert.equal(map.jumps,0);
 assert.deepEqual(map.center,[-92.790123456,42.73123456]);assert.equal(map.zoom,14.123456789);assert.equal(JSON.stringify(map.geo),geometry);
 assert.equal(map.layouts.aerial,'visible');assert.equal(map.layouts.normal,'none');
 t.render({basemap:'Sin fondo'});assert.equal(map.layouts.aerial,'none');assert.equal(map.layouts.normal,'none');
 t.w.close();
});
test('remount restores camera without fitting and touch emits explicit demo identity',()=>{
 const camera={center:[-92.79123,42.73123],zoom:15.1234};const t=setup(camera),map=t.root.map;
 assert.equal(map.fits,0);assert.equal(map.zoom,camera.zoom);
 map.events.click({features:[{properties:t.data.collection.features[0].properties}]});
 assert.equal(t.events.at(-1).name,'selected');assert.equal(t.events.at(-1).value.reference_id,'demo-19023-lote-sur');
 map.events.error();assert.match(t.root.querySelector('.map-status').textContent,/Sin fondo/);
 t.root.querySelector('.fit').click();assert.equal(map.fits,1);
 t.w.close();
});
