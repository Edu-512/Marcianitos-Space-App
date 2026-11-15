import geopandas as gpd, pandas as pd, numpy as np, os
g=gpd.read_file('ss/shp/soilmu.shp')
v=pd.read_csv('ss/ssurgo_butler_variables_modelo.csv',dtype={'mukey':str})
a=pd.read_csv('modelo/ajuste_suelo.csv',dtype={'mukey':str})[['mukey','ajuste_pct']]
g['mukey']=g.MUKEY.astype(str)
cols=['mukey','nombre','csr2_iowa','arena_pct','agua_disp_0_150cm','pendiente_pct','drenaje','inund_siembra','factor_k','om_pct']
d=g.merge(v[cols],on='mukey',how='left').merge(a,on='mukey',how='left')
print('poligonos:',len(d),'| con datos de suelo: %d (%.0f%%)'%(d.csr2_iowa.notna().sum(),100*d.csr2_iowa.notna().mean()))
print('sin datos: tipos ->',d[d.csr2_iowa.isna()].MUSYM.value_counts().head(5).to_dict())
# unir poligonos vecinos del mismo mukey (reduce mucho el conteo)
d=d.to_crs(5070)
u=d.dissolve(by='mukey',aggfunc='first').reset_index()
print('tras unir por tipo de suelo:',len(u),'poligonos')
u['acres']=(u.geometry.area/4046.86).round(1)
u['geometry']=u.geometry.simplify(20)
u=u[['mukey','nombre','csr2_iowa','ajuste_pct','arena_pct','agua_disp_0_150cm','pendiente_pct','drenaje','inund_siembra','factor_k','om_pct','acres','geometry']].round(2)
u.to_crs(4326).to_file('cdl/suelo_butler.geojson',driver='GeoJSON')
print('suelo_butler.geojson: %.0f KB'%(os.path.getsize('cdl/suelo_butler.geojson')/1024))
# version por clase: 5 clases de productividad, disueltas
b=d.copy(); b=b[b.csr2_iowa.notna()]
b['clase']=pd.cut(b.csr2_iowa,[0,50,65,80,90,100],labels=['Muy bajo','Bajo','Medio','Alto','Muy alto'])
c=b.dissolve(by='clase',observed=True).reset_index()[['clase','geometry']]
c['geometry']=c.geometry.simplify(40)
c.to_crs(4326).to_file('cdl/suelo_clases.geojson',driver='GeoJSON')
print('suelo_clases.geojson: %.0f KB  (%d clases)'%(os.path.getsize('cdl/suelo_clases.geojson')/1024,len(c)))
print('\nacres por clase:')
print(b.groupby('clase',observed=True).apply(lambda x:(x.geometry.area.sum()/4046.86),include_groups=False).round(0).to_string())
