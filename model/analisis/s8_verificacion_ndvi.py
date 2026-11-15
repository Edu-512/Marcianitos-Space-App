import numpy as np,pandas as pd,rasterio,glob,re,statsmodels.formula.api as smf
from rasterio.warp import reproject,Resampling
from scipy import stats
U='/mnt/user-data/uploads/'
S=np.load('cdl_stack.npy'); z=np.load('rejilla.npz'); cell=np.load('ndvi.npz')['cell']
with rasterio.open(U+'4766fa62-cdl_butler_2018.tif') as r: ctr,ccrs,cshp=r.transform,r.crs,(r.height,r.width)
comp={}
for f in sorted(glob.glob(U+'*_NDVI_doy*.tif')):
    y,d=map(int,re.search(r'doy(\d{4})(\d{3})',f).groups())
    with rasterio.open(f) as r: a=r.read(1).astype('float32'); mt,mc=r.transform,r.crs
    a[a<=-3000]=np.nan; o=np.full(cshp,np.nan,'float32'); reproject(a*0.0001,o,src_transform=mt,src_crs=mc,dst_transform=ctr,dst_crs=ccrs,resampling=Resampling.nearest,src_nodata=np.nan,dst_nodata=np.nan); comp[(y,d)]=o
ok=cell>=0; cid=cell[ok]; nc=cid.max()+1
cnt=lambda m: np.bincount(cid,weights=np.nan_to_num(m)[ok].astype(float),minlength=nc)
avg=lambda m: np.divide(cnt(m),np.maximum(cnt(np.isfinite(m)),1))
tot=np.bincount(cid,minlength=nc); val=cnt(S[0]>0)/np.maximum(tot,1)
soil={k:avg(z[k]) for k in['csr2_iowa','arena_pct','agua_disp_0_150cm','pendiente_pct','om_pct']}
print('POR COMPUESTO (diferencia tras-maiz menos tras-soya, en puntos de NDVI y %)')
rows=[]
for Y,i in [(2024,6),(2025,7)]:
    corn=S[i]==1; fc=cnt(corn)/np.maximum(tot,1); ncorn=np.maximum(cnt(corn),1)
    pc=cnt(corn&(S[i-1]==1))/ncorn; ps=cnt(corn&(S[i-1]==5))/ncorn
    base=(tot>=20)&(val>=0.95)&(fc>=0.9)
    g=np.where(base&(pc>=0.9),1,np.where(base&(ps>=0.9),2,0))
    for d in sorted(x[1] for x in comp if x[0]==Y):
        v=avg(comp[(Y,d)]); m1,m2=g==1,g==2
        a,b=v[m1],v[m2]; a,b=a[a>0],b[b>0]
        t=stats.mannwhitneyu(a,b)
        rows.append({'anio':Y,'doy':d,'tras_maiz':a.mean(),'tras_soya':b.mean(),'dif':a.mean()-b.mean(),'dif_pct':100*(a.mean()-b.mean())/b.mean(),'p':t.pvalue,'n1':len(a),'n2':len(b)})
    # integral y regresion con control de suelo
    v=np.nanmean(np.stack([avg(comp[(Y,d)]) for d in sorted(x[1] for x in comp if x[0]==Y)]),0)
    df=pd.DataFrame({'ndvi':v,'g':g,**soil}); df=df[(df.g>0)&(df.ndvi>0)].dropna()
    df['tras_maiz']=(df.g==1).astype(int)
    m=smf.ols('ndvi ~ tras_maiz + csr2_iowa + arena_pct + agua_disp_0_150cm + pendiente_pct + om_pct',df).fit()
    print(f'\n{Y} NDVI medio de temporada, con control de suelo: efecto tras-maiz %+.4f (ee %.4f, p %.3f) | sin control %+.4f'%(m.params.tras_maiz,m.bse.tras_maiz,m.pvalues.tras_maiz,df[df.g==1].ndvi.mean()-df[df.g==2].ndvi.mean()))
    s=np.nanmax(np.stack([avg(comp[(Y,d)]) for d in sorted(x[1] for x in comp if x[0]==Y)]),0)
    print(f'  saturacion: celdas con NDVI max >= 0.92: tras maiz %.0f%% | tras soya %.0f%%'%(100*(s[g==1]>=.92).mean(),100*(s[g==2]>=.92).mean()))
print()
print(pd.DataFrame(rows).round(4).to_string(index=False))
