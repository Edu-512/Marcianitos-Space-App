import numpy as np,pandas as pd
from scipy import stats
S=np.load('cdl_stack.npy'); z=np.load('rejilla.npz'); nz=np.load('ndvi.npz'); cell=nz['cell']
ok=cell>=0; cid=cell[ok]; nc=cid.max()+1
cnt=lambda m: np.bincount(cid,weights=np.nan_to_num(m)[ok].astype(float),minlength=nc)
avg=lambda m: np.divide(cnt(m),np.maximum(cnt(np.isfinite(m)),1))
tot=np.bincount(cid,minlength=nc); val=cnt(S[0]>0)/np.maximum(tot,1)
print('CONTROLES POSITIVOS: ¿el NDVI de MODIS detecta diferencias que SI deberia detectar?')
for Y,i in [(2024,6),(2025,7)]:
    nd=avg(nz[f'n{Y}']); base=(tot>=20)&(val>=0.95)&(nd>0)
    fc=cnt(S[i]==1)/np.maximum(tot,1); fs=cnt(S[i]==5)/np.maximum(tot,1)
    a,b=nd[base&(fc>=.9)],nd[base&(fs>=.9)]
    print(f'\n{Y}  maiz puro (n={len(a)}) vs soya pura (n={len(b)}): %.4f vs %.4f | diferencia %+.2f%% | p=%.1e'%(a.mean(),b.mean(),100*(a.mean()-b.mean())/b.mean(),stats.mannwhitneyu(a,b).pvalue))
    ar=avg(z['arena_pct']); cs=avg(z['csr2_iowa']); m=base&(fc>=.9)
    for nom,lo,hi in [('arena_pct',ar,ar),('csr2_iowa',cs,cs)]:
        q=np.nanquantile(lo[m],[.25,.75]); g1=m&(lo<=q[0]); g2=m&(lo>=q[1])
        x,y=nd[g1],nd[g2]
        print('   maiz en suelos con %s bajo (n=%d) vs alto (n=%d): %.4f vs %.4f | %+.2f%% | p=%.1e'%(nom,g1.sum(),g2.sum(),x.mean(),y.mean(),100*(y.mean()-x.mean())/x.mean(),stats.mannwhitneyu(x,y).pvalue))
