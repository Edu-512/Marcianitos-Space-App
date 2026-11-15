import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import numpy as np,pandas as pd
from scipy import stats
rng=np.random.default_rng(0)
S=np.load('cdl_stack.npy'); z=np.load('rejilla.npz'); nz=np.load('ndvi.npz'); cell=nz['cell']
ok=cell>=0; cid=cell[ok]; nc=cid.max()+1
cnt=lambda m: np.bincount(cid,weights=m[ok].astype(float),minlength=nc)
tot=np.bincount(cid,minlength=nc)
val=cnt(S[0]>0)   # pixeles con dato CDL
soil={k:np.divide(cnt(np.nan_to_num(z[k]))  ,np.maximum(cnt(np.isfinite(z[k])),1)) for k in['csr2_iowa','arena_pct','agua_disp_0_150cm','pendiente_pct','om_pct']}
res={}
for Y,i in [(2024,6),(2025,7)]:
    corn=S[i]==1; prev_c=S[i-1]==1; prev_s=S[i-1]==5
    fc=cnt(corn)/np.maximum(tot,1); ncorn=np.maximum(cnt(corn),1)
    pc=cnt(corn&prev_c)/ncorn; ps=cnt(corn&prev_s)/ncorn
    nd=np.divide(cnt(np.nan_to_num(nz[f'n{Y}'])),np.maximum(cnt(np.isfinite(nz[f'n{Y}'])),1))
    d=pd.DataFrame({'cid':np.arange(nc),'tot':tot,'val':val/np.maximum(tot,1),'fc':fc,'pc':pc,'ps':ps,'ndvi':nd,**soil})
    d=d[(d.tot>=20)&(d.val>=0.95)&(d.ndvi>0)]
    d['grupo']=np.where((d.fc>=0.9)&(d.pc>=0.9),'maiz tras maiz',np.where((d.fc>=0.9)&(d.ps>=0.9),'maiz tras soya',''))
    res[Y]=d[d.grupo!=''].copy()
    g=res[Y].groupby('grupo')
    print(f'\n=== {Y} === celdas MODIS puras: {dict(g.size())}')
    print(g[['ndvi','csr2_iowa','arena_pct','agua_disp_0_150cm','pendiente_pct','om_pct']].mean().round(3).to_string())
    a=res[Y][res[Y].grupo=='maiz tras maiz'].ndvi; b=res[Y][res[Y].grupo=='maiz tras soya'].ndvi
    dif=a.mean()-b.mean(); u=stats.mannwhitneyu(a,b)
    boot=np.array([rng.choice(a,len(a)).mean()-rng.choice(b,len(b)).mean() for _ in range(4000)])
    print('  NDVI: tras maiz %.4f vs tras soya %.4f | diferencia %+.4f (%.2f%%) | IC95 [%+.4f,%+.4f] | Mann-Whitney p=%.1e'%(a.mean(),b.mean(),dif,100*dif/b.mean(),*np.percentile(boot,[2.5,97.5]),u.pvalue))
    print('  mediana: %.4f vs %.4f | desv %.4f / %.4f'%(a.median(),b.median(),a.std(),b.std()))
pd.concat([v.assign(anio=k) for k,v in res.items()]).to_csv('celdas_ndvi_rotacion.csv',index=False)
