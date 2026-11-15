import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import numpy as np,pandas as pd
from scipy import stats
S=np.load('cdl_stack.npy'); z=np.load('rejilla.npz'); ac=900/4046.86
# 2018..2025 -> indices 0..7 ; barbecho = 61
for i,y in enumerate(range(2018,2026)):
    print(y,'barbecho acres %.0f'%((S[i]==61).sum()*ac))
F=S[1]==61  # 2019
agri=(S[0]==1)|(S[0]==5)   # era cultivo en 2018
despues=(S[2]==1)|(S[2]==5)
pp=F&agri&despues          # sin sembrar en 2019 pero cultivo antes y despues = siembra impedida
print('\n2019: barbecho %.0f acres | de ellos, cultivo en 2018 y 2020: %.0f acres (%.0f%%)'%(F.sum()*ac,pp.sum()*ac,100*pp.sum()/max(F.sum(),1)))
base=agri&((S[2]==1)|(S[2]==5))&np.isfinite(z['csr2_iowa'])
print('base de comparacion (cultivo en 2018 y 2020):','%.0f acres'%(base.sum()*ac))
dr=z['drenaje'] if 'drenaje' in z else None
s=pd.read_csv('../ss/suelo_con_area.csv',dtype={'mukey':str})
ordd={'Excessively drained':1,'Somewhat excessively drained':2,'Well drained':3,'Moderately well drained':4,'Somewhat poorly drained':5,'Poorly drained':6,'Very poorly drained':7}
import rasterio
from rasterio.features import rasterize
import geopandas as gpd
g=gpd.read_file('../ss/datos/shp/soilmu.shp').to_crs(5070)
with rasterio.open('datos/CDL_2018_19023.tif') as r: tr,shp=r.transform,(r.height,r.width)
mp=dict(zip(s.mukey,s.drenaje.map(ordd)))
dro=rasterize(((geom,int(0 if pd.isna(mp.get(k)) else (mp.get(k) or 0))) for geom,k in zip(g.geometry,g.MUKEY)),out_shape=shp,transform=tr,fill=0,dtype='uint8')
print('\nSIN SEMBRAR EN 2019 SEGUN DRENAJE DEL SUELO')
rows=[]
for k,n in sorted(ordd.items(),key=lambda x:x[1]):
    m=base&(dro==n)
    if m.sum()<2000: continue
    rows.append({'drenaje':k,'acres_cultivables':m.sum()*ac,'pct_sin_sembrar':100*(pp&m).sum()/m.sum(),'inund':np.nanmean(z['inund_siembra'][m]),'arena':np.nanmean(z['arena_pct'][m])})
d=pd.DataFrame(rows); print(d.round(2).to_string(index=False))
mal=base&(dro>=5); bien=base&(dro>0)&(dro<=4)
a,b=100*(pp&mal).sum()/mal.sum(),100*(pp&bien).sum()/bien.sum()
print('\nmal drenado (%.0f acres): %.2f%% sin sembrar | bien drenado (%.0f acres): %.2f%% | razon %.1fx'%(mal.sum()*ac,a,bien.sum()*ac,b,a/max(b,1e-9)))
print('prueba chi2: p=%.1e'%stats.chi2_contingency([[ (pp&mal).sum(), mal.sum()-(pp&mal).sum()],[(pp&bien).sum(), bien.sum()-(pp&bien).sum()]])[1])
# control: inundacion declarada en SSURGO
inu=base&(z['inund_siembra']>=50); noi=base&(z['inund_siembra']<1)
print('control, suelos inundables en siembra: %.2f%% vs no inundables %.2f%%'%(100*(pp&inu).sum()/max(inu.sum(),1),100*(pp&noi).sum()/max(noi.sum(),1)))
np.save('sin_sembrar_2019.npy',pp)
