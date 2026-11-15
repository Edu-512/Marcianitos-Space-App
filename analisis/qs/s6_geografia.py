import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,numpy as np
from scipy import stats
a=pd.read_csv('anomalias.csv'); t=pd.read_csv('quickstats_iowa_limpio.csv')
for cu,v in[('maiz','maiz_rend'),('soya','soya_rend')]:
    x=a[a.cultivo==cu]
    g=x.groupby('condado').agg(nivel=('esperado','mean'),vol=('anom_pct','std'),p10=('anom_pct',lambda s:s.quantile(.1)),n=('anio','size')); g=g[g.n>=20]
    malos={'maiz':[2012,2013,2010,2020],'soya':[2003,2012,2013]}[cu]
    g['perdida_malos']=x[x.anio.isin(malos)].groupby('condado').anom_pct.mean()
    g['anom_buenos']=x[~x.anio.isin(malos)].groupby('condado').anom_pct.mean()
    print(f'\n{cu} (n={len(g)} condados)')
    for y in['vol','p10','perdida_malos']:
        print(f'  nivel de rendimiento vs {y}: Pearson {g.nivel.corr(g[y]):.2f} | Spearman {g.nivel.corr(g[y],method="spearman"):.2f}')
    g['q']=pd.qcut(g.nivel,4,labels=['Q1 bajo','Q2','Q3','Q4 alto'])
    print(g.groupby('q',observed=True)[['nivel','vol','p10','perdida_malos']].mean().round(1).to_string())
    # angulo: por distrito
    dd=x.groupby('distrito').agg(nivel=('esperado','mean'),vol=('anom_pct','std')); dd['perdida_malos']=x[x.anio.isin(malos)].groupby('distrito').anom_pct.mean()
    print(dd.round(1).sort_values('nivel').to_string())
    b=g.loc['BUTLER']; print('BUTLER: nivel %.1f (percentil %.0f) | volatilidad %.1f (percentil %.0f) | perdida en años malos %.1f%%'%(b.nivel,100*(g.nivel<b.nivel).mean(),b.vol,100*(g.vol<b.vol).mean(),b.perdida_malos))
# superficie
t['prop_maiz']=t.maiz_acres/(t.maiz_acres+t.soya_acres)
s=t.groupby('anio').agg(maiz=('maiz_acres','sum'),soya=('soya_acres','sum'),prop=('prop_maiz','mean'),n=('prop_maiz','count'))
print('\nproporcion de maiz (maiz/(maiz+soya)) por año:'); print(s.prop.round(3).to_string())
print('por condado: min %.2f mediana %.2f max %.2f | Butler %.2f'%(t.groupby('condado').prop_maiz.mean().min(),t.groupby('condado').prop_maiz.mean().median(),t.groupby('condado').prop_maiz.mean().max(),t[t.condado=='BUTLER'].prop_maiz.mean()))
