import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import geopandas as gpd,pandas as pd,numpy as np
g=gpd.read_file('datos/shp/soilmu.shp'); print(g.shape,list(g.columns),g.crs); print(g.head(3).drop(columns='geometry').to_string())
print('geometrias invalidas:',(~g.is_valid).sum(),'| vacias',g.is_empty.sum(),'| limites',g.total_bounds.round(3))
p=g.to_crs(26915); g['acres']=p.area/4046.8564
print('poligonos',len(g),'| unidades distintas',g.MUKEY.nunique(),'| area total acres',round(g.acres.sum()))
print('tamaño de poligono (acres): mediana %.1f media %.1f p90 %.1f max %.0f'%(g.acres.median(),g.acres.mean(),g.acres.quantile(.9),g.acres.max()))
s=pd.read_csv('datos/ssurgo_butler_por_suelo.csv',dtype={'mukey':str})
a=g.groupby('MUKEY').acres.sum().rename('acres_mapa'); s=s.merge(a,left_on='mukey',right_index=True,how='outer',indicator=True)
print(s._merge.value_counts().to_dict())
s['dif_pct']=100*(s.acres_mapa-s.acres_condado)/s.acres_condado
print('acres tabla %.0f vs acres mapa %.0f | correlacion %.4f | dif mediana %.2f%% | unidades con dif >10%%: %d'%(s.acres_condado.sum(),s.acres_mapa.sum(),s.acres_condado.corr(s.acres_mapa),s.dif_pct.median(),(s.dif_pct.abs()>10).sum()))
print(s[s.dif_pct.abs()>10][['musym','acres_condado','acres_mapa','dif_pct']].round(1).to_string())
s.drop(columns=['_merge','dif_pct']).to_csv('suelo_con_area.csv',index=False)
