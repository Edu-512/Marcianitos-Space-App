import pandas as pd,numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
a=pd.read_csv('anomalias.csv'); a['res_abs']=a.rend-a.esperado
for cu in['maiz','soya']:
    x=a[a.cultivo==cu]; g=x.groupby('condado').agg(nivel=('esperado','mean'),vol_abs=('res_abs','std'),n=('anio','size')); g=g[g.n>=20]
    g['q']=pd.qcut(g.nivel,4,labels=['Q1','Q2','Q3','Q4'])
    print(cu,'nivel vs volatilidad ABSOLUTA (bu/acre): Spearman %.2f'%g.nivel.corr(g.vol_abs,method='spearman'),g.groupby('q',observed=True).vol_abs.mean().round(1).to_dict())
y=a.groupby(['anio','cultivo']).anom_pct.agg(['mean',lambda s:s.quantile(.1),lambda s:s.quantile(.9)]).unstack()
fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True)
for i,(cu,nom) in enumerate([('maiz','Maíz'),('soya','Soya')]):
    m=y[('mean',cu)]; lo=y[('<lambda_0>',cu)]; hi=y[('<lambda_1>',cu)]
    ax[i].bar(m.index,m.values,color=['#b5483a' if v<-8 else '#3b6ea5' for v in m.values])
    ax[i].vlines(m.index,lo,hi,color='black',lw=1)
    ax[i].axhline(0,color='black',lw=.8); ax[i].set_ylabel('% respecto a lo esperado'); ax[i].set_title(f'{nom}: desviación del rendimiento por año (99 condados de Iowa)',loc='left')
    ax[i].spines[['top','right']].set_visible(False)
ax[1].set_xticks(range(2000,2026)); ax[1].tick_params(axis='x',rotation=90)
fig.text(0.01,0.005,'Barra: promedio de condados. Línea: rango entre el 10 % y el 90 % de los condados. Rojo: años con caída mayor al 8 %. Fuente: USDA NASS QuickStats.',fontsize=8)
plt.tight_layout(rect=(0,0.02,1,1)); plt.savefig('quickstats_anomalias_por_anio.png',dpi=140)
