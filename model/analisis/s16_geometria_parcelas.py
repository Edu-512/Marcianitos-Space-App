import numpy as np, pandas as pd, rasterio, os
from rasterio.features import shapes
from scipy import ndimage
import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import unary_union

pat=np.load('patron.npy')
with rasterio.open('patron_rotacion_2018_2025.tif') as s: tr,crs=s.transform,s.crs
lab,n=ndimage.label(pat>0,structure=np.ones((3,3)))
cand=pd.read_csv('parcelas_candidatas.csv')

geoms=[]
for i in cand.id:
    m=(lab==i).astype('uint8')
    geoms.append(unary_union([shape(g) for g,v in shapes(m,mask=m.astype(bool),transform=tr) if v==1]))
g=gpd.GeoDataFrame(cand,geometry=geoms,crs=crs)
g['acres_geom']=(g.geometry.area/4046.86).round(1)
err=(g.acres_geom-g.acres).abs().max()
print('167 parcelas vectorizadas | maximo error de area: %.2f acres'%err)
g4=g.to_crs(4326)
g4.to_file('parcelas_todas.geojson',driver='GeoJSON')
print('parcelas_todas.geojson: %.0f KB'%(os.path.getsize('parcelas_todas.geojson')/1024))
# version simplificada para web
gs=g.copy(); gs['geometry']=gs.geometry.simplify(15)
gs.to_crs(4326).to_file('parcelas_todas_simple.geojson',driver='GeoJSON')
print('simplificado a 15 m: %.0f KB'%(os.path.getsize('parcelas_todas_simple.geojson')/1024))

# VERIFICACION 2: las coordenadas caen donde dice SSURGO?
ss=gpd.read_file('../ss/shp/soilmu.shp').to_crs(crs)
cen=gpd.GeoDataFrame(geometry=g.geometry.centroid,crs=crs)
j=gpd.sjoin(cen,ss,how='left',predicate='within')
print('\ncentroides que caen dentro de un poligono SSURGO de Butler: %d de %d'%(j.MUKEY.notna().sum(),len(g)))
# el suelo bajo la parcela coincide con lo que registramos?
sv=pd.read_csv('../ss/ssurgo_butler_variables_modelo.csv',dtype={'mukey':str})[['mukey','arena_pct']]
j=j.reset_index(drop=True); j['mukey']=j.MUKEY.astype(str)
chk=j.merge(sv,on='mukey',how='left'); chk['arena_csv']=g.arena.values
ok=chk.dropna(subset=['arena_pct'])
print('correlacion arena (shapefile en el centroide) vs arena (promedio de la parcela): %.2f  n=%d'%(ok.arena_pct.corr(ok.arena_csv),len(ok)))
