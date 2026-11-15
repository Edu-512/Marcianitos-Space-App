import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import rasterio,numpy as np,glob,re
from rasterio.warp import reproject,Resampling
U='datos/'
fs=sorted(glob.glob(U+'ndvi/*_NDVI_doy*.tif'))
print(len(fs),'archivos')
with rasterio.open(fs[0]) as r: print('NDVI:',r.crs,r.res,r.shape,r.nodata,r.dtypes,r.bounds)
A={}
for f in fs:
    y,d=re.search(r'doy(\d{4})(\d{3})',f).groups()
    with rasterio.open(f) as r: a=r.read(1).astype(float); mt,mc,ms=r.transform,r.crs,r.shape
    a[a<=-3000]=np.nan; A.setdefault(int(y),[]).append((int(d),a*0.0001))
for y in A: print(y,'compuestos doy',sorted(d for d,_ in A[y]))
mx={y:np.nanmax(np.stack([a for _,a in v]),0) for y,v in A.items()}
for y,m in mx.items(): print(y,'NDVI max: validos %.1f%% | min %.2f mediana %.2f max %.2f'%(100*np.isfinite(m).mean(),np.nanmin(m),np.nanmedian(m),np.nanmax(m)))
# rejilla CDL de referencia
with rasterio.open(U+'CDL_2018_19023.tif') as r: ctr,ccrs,cshp=r.transform,r.crs,(r.height,r.width)
idx=np.arange(ms[0]*ms[1],dtype='int32').reshape(ms)
cell=np.full(cshp,-1,'int32'); reproject(idx,cell,src_transform=mt,src_crs=mc,dst_transform=ctr,dst_crs=ccrs,resampling=Resampling.nearest,src_nodata=None,dst_nodata=-1)
ndvi_c={}
for y,m in mx.items():
    o=np.full(cshp,np.nan); reproject(m.astype('float32'),o,src_transform=mt,src_crs=mc,dst_transform=ctr,dst_crs=ccrs,resampling=Resampling.nearest,src_nodata=np.nan,dst_nodata=np.nan); ndvi_c[y]=o
print('celdas MODIS que tocan el condado:',len(np.unique(cell[cell>=0])),'| pixeles CDL con NDVI 2025: %.1f%%'%(100*np.isfinite(ndvi_c[2025]).mean()))
np.savez_compressed('ndvi.npz',cell=cell,**{f'n{y}':v for y,v in ndvi_c.items()})
