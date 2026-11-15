import numpy as np,pandas as pd,pickle
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold,cross_val_predict
from scipy import stats
s=pd.read_csv('../ss/ssurgo_butler_variables_modelo.csv',dtype={'mukey':str})
X=['arena_pct','agua_disp_0_150cm','pendiente_pct']
d=s.dropna(subset=X+['csr2_iowa','acres_mapa']).copy(); w=d.acres_mapa.values
m=LinearRegression().fit(d[X],d.csr2_iowa,sample_weight=w)
d['idx']=m.predict(d[X]); base=np.average(d.idx,weights=w)
crudo=100*(d.idx/base-1)
# ANCLA DE MAGNITUD: los presupuestos de ISU usan tres niveles de rendimiento para Iowa (182/202/222 bu),
# o sea +-10% alrededor del medio. Escalamos el indice a ese rango real.
objetivo=10.0
esc=objetivo/((np.percentile(crudo,90)-np.percentile(crudo,10))/2)
d['ajuste_pct']=np.clip(crudo*esc,-18,18)
print('ESCALADO: factor %.3f  (rango crudo p10-p90 = %.0f%% -> escalado = %.0f%%)'%(esc,(np.percentile(crudo,90)-np.percentile(crudo,10)),(d.ajuste_pct.quantile(.9)-d.ajuste_pct.quantile(.1))))
print('ajuste final: p10 %.1f%% | mediana %.1f%% | p90 %.1f%% | min %.1f | max %.1f'%(d.ajuste_pct.quantile(.1),d.ajuste_pct.median(),d.ajuste_pct.quantile(.9),d.ajuste_pct.min(),d.ajuste_pct.max()))
# VALIDACION 1: contra el indice experto de Iowa, con familias de suelo separadas
p=cross_val_predict(LinearRegression(),d[X],d.csr2_iowa,cv=GroupKFold(5),groups=d.nombre.str.split().str[0])
print('\nvalidacion 1 (indice experto CSR2, familias separadas): Spearman %.2f | R2 ponderado %.2f'%(stats.spearmanr(p,d.csr2_iowa).correlation,1-((d.csr2_iowa-p)**2*w).sum()/((d.csr2_iowa-np.average(d.csr2_iowa,weights=w))**2*w).sum()))
# VALIDACION 2: contra vigor medido por satelite, celda por celda
S=np.load('../cdl/cdl_stack.npy'); z=np.load('../cdl/rejilla.npz'); nz=np.load('../cdl/ndvi.npz'); cell=nz['cell']
mp={k:v for k,v in zip(d.mukey,d.ajuste_pct)}
mu=z['mu']; lut=pd.read_csv('../ss/suelo_con_area.csv',dtype={'mukey':str})
import geopandas as gpd
g=gpd.read_file('../ss/shp/soilmu.shp'); keys={k:i+1 for i,k in enumerate(sorted(g.MUKEY.unique()))}
arr=np.full(len(keys)+1,np.nan)
for k,i in keys.items():
    if k in mp: arr[i]=mp[k]
aj=arr[mu]
ok=cell>=0; cid=cell[ok]; nc=cid.max()+1
cnt=lambda a: np.bincount(cid,weights=np.nan_to_num(a)[ok].astype(float),minlength=nc)
avg=lambda a: np.divide(cnt(a),np.maximum(cnt(np.isfinite(a)),1))
tot=np.bincount(cid,minlength=nc); val=cnt(S[0]>0)/np.maximum(tot,1)
res=[]
for Y,i in [(2024,6),(2025,7)]:
    fc=cnt(S[i]==1)/np.maximum(tot,1); nd=avg(nz[f'n{Y}']); a=avg(aj)
    msk=(tot>=20)&(val>=.95)&(fc>=.9)&(nd>0)&np.isfinite(a)
    r=stats.spearmanr(a[msk],nd[msk])
    q=pd.qcut(a[msk],4,labels=['Q1','Q2','Q3','Q4'])
    t=pd.DataFrame({'q':q,'ndvi':nd[msk],'aj':a[msk]}).groupby('q',observed=True).mean()
    print('validacion 2, %d (n=%d celdas de maiz puro): Spearman ajuste-vigor %.2f (p=%.1e)'%(Y,msk.sum(),r.correlation,r.pvalue))
    print('   NDVI por cuartil del ajuste:',dict(t.ndvi.round(4)),'| ajuste medio:',dict(t.aj.round(1)))
    res.append(r.correlation)
d[['mukey','musym','nombre','acres_mapa','csr2_iowa','idx','ajuste_pct']].round(2).to_csv('ajuste_suelo.csv',index=False)
pickle.dump({'vars':X,'coef':m.coef_.tolist(),'intercept':float(m.intercept_),'base':float(base),'escala':float(esc),'limite':18.0},open('modelo_suelo.pkl','wb'))
print('\nFORMULA FINAL  ajuste%% = clip( ( (%.4f*arena + %.4f*agua150 + %.4f*pendiente + %.2f)/%.2f - 1 ) * 100 * %.3f , -18, 18 )'%(*m.coef_,m.intercept_,base,esc))
