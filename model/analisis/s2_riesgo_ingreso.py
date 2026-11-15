import pandas as pd,numpy as np
from scipy import stats
rng=np.random.default_rng(0)
t=pd.read_csv('ingreso_por_condado.csv')
def anom(d,c):
    out=[]
    for k,g in d.dropna(subset=[c]).groupby('condado'):
        if len(g)<15: continue
        r=stats.linregress(g.anio,g[c]); e=r.intercept+r.slope*g.anio
        out.append(pd.DataFrame({'condado':k,'anio':g.anio,'v':100*(g[c]-e)/e}))
    return pd.concat(out)
print('RIESGO: ¿el dinero es mas o menos volatil que el rendimiento?')
R={}
for c,ry,ri in [('maiz','maiz_rend','ing_maiz'),('soya','soya_rend','ing_soya')]:
    a=anom(t,ry); b=anom(t,ri); R[c]=b
    print(' %s: desviacion del rendimiento %.1f%% -> del ingreso %.1f%% | prob de caer >20%%: %.0f%% -> %.0f%%'%(c,a.v.std(),b.v.std(),100*(a.v<-20).mean(),100*(b.v<-20).mean()))
w=R['maiz'].merge(R['soya'],on=['condado','anio'],suffixes=('_m','_s')).dropna()
w['mitad']=(w.v_m+w.v_s)/2
print('\n correlacion del ingreso maiz-soya: %.2f (en rendimiento era 0.59)'%w.v_m.corr(w.v_s))
print(' desviacion: maiz %.1f | soya %.1f | mitad y mitad %.1f'%(w.v_m.std(),w.v_s.std(),w.mitad.std()))
an=w.anio.unique(); B=np.array([[ (b:=pd.concat([w[w.anio==k] for k in rng.choice(an,len(an))])).v_m.std(),b.v_s.std(),b.mitad.std()] for _ in range(1500)])
print(' diversificar baja la volatilidad del ingreso en %.0f%% de los remuestreos (en rendimiento era 72%%)'%(100*(B[:,2]<np.minimum(B[:,0],B[:,1])).mean()))
y=w.groupby('anio')[['v_m','v_s']].mean()
print('\n PEORES AÑOS POR INGRESO (promedio de condados)'); print(y.sort_values('v_m').head(6).round(1).to_string())
print('\n COMPARACION: un año malo de rendimiento no siempre es malo de dinero')
a=anom(t,'maiz_rend').groupby('anio').v.mean(); b=R['maiz'].groupby('anio').v.mean()
d=pd.DataFrame({'rendimiento':a,'ingreso':b}).round(1)
print(d.loc[[2012,2013,2010,2020,2003,2005,2014,2024]].to_string())
