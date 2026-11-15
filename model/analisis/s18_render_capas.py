import numpy as np, json
from PIL import Image
z=np.load('/tmp/capas.npz')

def ramp(hexes,n=256):
    c=np.array([[int(h[i:i+2],16) for i in (1,3,5)] for h in hexes],float)
    x=np.linspace(0,1,len(c)); xi=np.linspace(0,1,n)
    return np.stack([np.interp(xi,x,c[:,k]) for k in range(3)],1)

# sequential azul, claro -> oscuro (paleta del sistema, pasos 100-700)
SEQ=ramp(['#cde2fb','#b7d3f6','#9ec5f4','#86b6ef','#6da7ec','#5598e7','#3987e5','#2a78d6','#256abf','#1c5cab','#184f95','#104281','#0d366b'])
# diverging rojo <-> azul con gris neutro al centro
DIV=ramp(['#8f2020','#c13434','#e34948','#ef8a89','#f0efec','#86b6ef','#3987e5','#256abf','#0d366b'])

def png(a,lo,hi,cm,path):
    v=np.clip((a-lo)/(hi-lo),0,1); idx=(v*255).astype('uint8')
    rgb=cm[idx].astype('uint8')
    out=np.zeros(a.shape+(4,),'uint8'); out[...,:3]=rgb
    out[...,3]=np.where(np.isfinite(a),225,0)
    Image.fromarray(out,'RGBA').save(path,optimize=True)
    import os; return os.path.getsize(path)/1024

k=png(z['csr2_iowa'],30,100,SEQ,'cdl/capa_productividad.png')
print('capa_productividad.png: %.0f KB  (CSR2 30-100, azul secuencial)'%k)
k=png(z['arena_pct'],10,70,SEQ,'cdl/capa_arena.png')
print('capa_arena.png: %.0f KB  (arena 10-70%%)'%k)
k=png(z['inund_siembra'],0,100,SEQ,'cdl/capa_riesgo_inundacion.png')
print('capa_riesgo_inundacion.png: %.0f KB  (0-100%%)'%k)

# capa del ajuste del modelo: necesita el ajuste en la rejilla
import pandas as pd, geopandas as gpd, rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
rj=np.load('cdl/rejilla.npz'); mu=rj['mu']
g=gpd.read_file('ss/shp/soilmu.shp'); keys={kk:i+1 for i,kk in enumerate(sorted(g.MUKEY.unique()))}
aj=pd.read_csv('modelo/ajuste_suelo.csv',dtype={'mukey':str}).set_index('mukey').ajuste_pct.to_dict()
arr=np.full(len(keys)+1,np.nan)
for kk,i in keys.items():
    if kk in aj: arr[i]=aj[kk]
A=arr[mu].astype('float32')
with rasterio.open('cdl/patron_rotacion_2018_2025.tif') as s: st,sc,H,W=s.transform,s.crs,*s.shape
tr,w,h=calculate_default_transform(sc,'EPSG:4326',W,H,*rasterio.transform.array_bounds(H,W,st))
D=np.full((h,w),np.nan,'float32')
reproject(A,D,src_transform=st,src_crs=sc,dst_transform=tr,dst_crs='EPSG:4326',resampling=Resampling.nearest,src_nodata=np.nan,dst_nodata=np.nan)
k=png(D,-18,18,DIV,'cdl/capa_ajuste_modelo.png')
print('capa_ajuste_modelo.png: %.0f KB  (-18%% a +18%%, divergente rojo-azul)'%k)
print('\ncon dato: %.0f%% | rango %.1f a %.1f'%(100*np.isfinite(D).mean(),np.nanmin(D),np.nanmax(D)))
