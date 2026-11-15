import rasterio,numpy as np,pandas as pd
from rasterio.warp import reproject,Resampling
from scipy import ndimage
U='/mnt/user-data/uploads/'
F={2018:'4766fa62-cdl_butler_2018.tif',2019:'41adf908-CDL_2019_19023.tif',2020:'4eb4222d-CDL_2020_19023.tif',2021:'f9a47e1a-CDL_2021_19023.tif',2022:'a7adf553-CDL_2022_19023.tif',2023:'31a649ee-CDL_2023_19023.tif',2024:'47157961-cdl_butler_2024.tif',2025:'f3a99c87-cdl_butler_2025.tif'}
with rasterio.open(U+F[2018]) as r: prof=r.profile; tr=r.transform; crs=r.crs; shp=(r.height,r.width)
ref=pd.read_csv(U+'65e0f888-cdl_butler_2008_2025.csv'); R={}
for y,f in F.items():
    with rasterio.open(U+f) as r:
        a=r.read(1); same=(r.transform==tr and a.shape==shp)
        if not same:
            b=np.zeros(shp,a.dtype); reproject(a,b,src_transform=r.transform,src_crs=r.crs,dst_transform=tr,dst_crs=crs,resampling=Resampling.nearest); 
            print(y,'rejilla distinta:',r.crs.to_string()[:12],r.res,a.shape,'-> realineado'); a=b
        R[y]=a
    c=[(a==k).sum() for k in(1,5)]; e=[ref[(ref.anio==y)&(ref.codigo==k)].pixeles.iloc[0] for k in(1,5)]
    print(y,'maiz',c[0],'vs',e[0],'(%+.2f%%)'%(100*(c[0]-e[0])/e[0]),'| soya',c[1],'vs',e[1],'(%+.2f%%)'%(100*(c[1]-e[1])/e[1]))
S=np.stack([R[y] for y in sorted(R)]); np.save('cdl_stack.npy',S)
trc=pd.read_csv(U+'acdb017d-cdl_butler_transiciones.csv').set_index('anio'); print('\nTRANSICIONES: mio vs compañero (% del maiz sembrado sobre maiz | % soya sobre soya)')
for i,y in enumerate(sorted(R)):
    if i==0: continue
    a,b=S[i],S[i-1]; m=a==1; print(y,'%.1f vs %.1f | %.1f vs %.1f'%(100*(m&(b==1)).sum()/m.sum(),trc.loc[y,'pct_maiz_tras_maiz'],100*((a==5)&(b==5)).sum()/(a==5).sum(),trc.loc[y,'pct_soya_tras_soya']))
# patrones de 8 años
M=(S==1); So=(S==5); nm=M.sum(0); ns=So.sum(0); base=(nm+ns)>=6
seq=np.where(M,1,np.where(So,2,0)); cambios=((seq[1:]!=seq[:-1])&(seq[1:]>0)&(seq[:-1]>0)).sum(0); pares=((seq[1:]>0)&(seq[:-1]>0)).sum(0); rep=pares-cambios
pat=np.zeros(shp,np.uint8)
pat[base&(nm>=6)]=3; pat[base&(ns>=6)&(pat==0)]=5
pat[base&(pat==0)&((nm+ns)==8)&(rep==0)]=1; pat[base&(pat==0)&((nm+ns)==8)&(rep==1)]=2; pat[base&(pat==0)]=4
nom={1:'rotacion estricta',2:'rotacion con 1 quiebre',3:'maiz 6+ de 8',4:'irregular',5:'soya dominante'}
pc=pd.read_csv(U+'24837b3a-cdl_butler_patrones.csv'); print('\nPATRONES 2018-2025 (mi clasificacion) | acres | % || compañero %')
tot=base.sum()
for k,n in nom.items(): print('  %-24s %7.0f %5.1f'%(n,(pat==k).sum()*900/4046.86,100*(pat==k).sum()/tot))
print(pc[['patron','acres','pct']].to_string(index=False))
print('maiz los 8 años: %.0f acres'%((nm==8).sum()*900/4046.86))
prof.update(dtype='uint8',count=1,compress='lzw',nodata=0)
with rasterio.open('patron_rotacion_2018_2025.tif','w',**prof) as d: d.write(pat,1)
np.save('patron.npy',pat)
