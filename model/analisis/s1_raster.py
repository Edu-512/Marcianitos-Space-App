import rasterio,numpy as np,pandas as pd
U='/mnt/user-data/uploads/'; F={2018:'4766fa62-cdl_butler_2018.tif',2024:'47157961-cdl_butler_2024.tif',2025:'f3a99c87-cdl_butler_2025.tif'}
ref=pd.read_csv(U+'65e0f888-cdl_butler_2008_2025.csv')
for y,f in F.items():
    with rasterio.open(U+f) as r:
        a=r.read(1); print(y,r.crs.to_string()[:40],r.res,a.shape,r.nodata,a.dtype,r.bounds)
        for c,n in[(1,'Corn'),(5,'Soybeans')]:
            px=(a==c).sum(); rr=ref[(ref.anio==y)&(ref.codigo==c)].pixeles.iloc[0]; print('   ',n,px,'vs csv',rr,'acres',round(px*r.res[0]*r.res[1]/4046.86))
