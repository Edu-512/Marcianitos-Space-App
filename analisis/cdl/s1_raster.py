import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import rasterio,numpy as np,pandas as pd
U='datos/'; F={2018:'CDL_2018_19023.tif',2024:'CDL_2024_19023.tif',2025:'CDL_2025_19023.tif'}
ref=pd.read_csv(U+'cdl_butler_2008_2025.csv')
for y,f in F.items():
    with rasterio.open(U+f) as r:
        a=r.read(1); print(y,r.crs.to_string()[:40],r.res,a.shape,r.nodata,a.dtype,r.bounds)
        for c,n in[(1,'Corn'),(5,'Soybeans')]:
            px=(a==c).sum(); rr=ref[(ref.anio==y)&(ref.codigo==c)].pixeles.iloc[0]; print('   ',n,px,'vs csv',rr,'acres',round(px*r.res[0]*r.res[1]/4046.86))
