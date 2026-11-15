import rasterio,numpy as np,pandas as pd,geopandas as gpd
from rasterio.features import rasterize
from scipy import ndimage,stats
U='/mnt/user-data/uploads/'; F={2018:'4766fa62-cdl_butler_2018.tif',2024:'47157961-cdl_butler_2024.tif',2025:'f3a99c87-cdl_butler_2025.tif'}
R={}
for y,f in F.items():
    with rasterio.open(U+f) as r: R[y]=r.read(1); tr=r.transform; shp=R[y].shape
a24,a25,a18=R[2024],R[2025],R[2018]
m25=a25==1; print('TRANSICION 2024->2025 (todos los pixeles)')
print('  maiz 2025 tras maiz: %.1f%% | tras soya: %.1f%% | soya 2025 tras soya: %.1f%%'%(100*(m25&(a24==1)).sum()/m25.sum(),100*(m25&(a24==5)).sum()/m25.sum(),100*((a25==5)&(a24==5)).sum()/(a25==5).sum()))
# angulo 2: solo interior de campos (vecindad 3x3 con la misma clase en ambos años)
def interior(a,c): return ndimage.minimum_filter((a==c).astype(np.uint8),3)==1
i25m=interior(a25,1); i24m=interior(a24,1); i24s=interior(a24,5); i25s=interior(a25,5)
den=(i25m&(i24m|i24s)).sum(); print('  solo interior de campos: maiz tras maiz %.1f%% | tras soya %.1f%% (n pixeles %d) | soya tras soya %.1f%%'%(100*(i25m&i24m).sum()/den,100*(i25m&i24s).sum()/den,den,100*(i25s&i24s).sum()/(i25s&(i24m|i24s)).sum()))
# suelo rasterizado
g=gpd.read_file('../ss/shp/soilmu.shp').to_crs(5070); s=pd.read_csv('../ss/suelo_con_area.csv',dtype={'mukey':str})
keys={k:i+1 for i,k in enumerate(sorted(g.MUKEY.unique()))}
mu=rasterize(((geom,keys[k]) for geom,k in zip(g.geometry,g.MUKEY)),out_shape=shp,transform=tr,fill=0,dtype='uint16')
print('pixeles con suelo:',(mu>0).sum(),'acres',round((mu>0).sum()*900/4046.86))
lut=pd.DataFrame({'id':list(keys.values()),'mukey':list(keys.keys())}).merge(s,on='mukey')
def arr(col):
    v=np.full(len(keys)+1,np.nan); v[lut.id.values]=pd.to_numeric(lut[col],errors='coerce').values; return v[mu]
V={c:arr(c) for c in['csr2_iowa','arena_pct','agua_disp_0_150cm','pendiente_pct','om_pct','inund_siembra']}
np.savez_compressed('rejilla.npz',mu=mu,**V)
grupos={'maiz tras maiz':m25&(a24==1),'maiz tras soya':m25&(a24==5),'soya tras maiz':(a25==5)&(a24==1),'maiz 2018+2024+2025':(a18==1)&(a24==1)&m25,'interior: maiz tras maiz':i25m&i24m,'interior: maiz tras soya':i25m&i24s}
out=[]
for n,mk in grupos.items():
    out.append({'grupo':n,'acres':round(mk.sum()*900/4046.86),**{c:np.nanmean(v[mk]) for c,v in V.items()},'pct_arenoso':100*np.nanmean(V['arena_pct'][mk]>50),'pct_csr2>=80':100*np.nanmean(V['csr2_iowa'][mk]>=80),'pct_inundable':100*np.nanmean(V['inund_siembra'][mk]>=50)})
print(pd.DataFrame(out).round(1).to_string(index=False))
# probabilidad de maiz-sobre-maiz segun clase de suelo
cs=m25&((a24==1)|(a24==5)); mm=(a24==1)[cs]
for c,bins in[('csr2_iowa',[0,40,60,75,85,101]),('arena_pct',[0,15,30,50,70,101]),('pendiente_pct',[0,1.5,3,6,10,40]),('inund_siembra',[-1,1,50,101])]:
    b=pd.cut(V[c][cs],bins); t=pd.DataFrame({'b':b,'mm':mm}).groupby('b',observed=True).mm.agg(['mean','size']); t['mean']=(100*t['mean']).round(1); t['acres']=(t['size']*900/4046.86).round(0); print('\n% de maiz 2025 sembrado sobre maiz, por',c); print(t[['mean','acres']].to_string())
