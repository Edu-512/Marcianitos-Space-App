import pandas as pd,numpy as np
from scipy import stats
rng=np.random.default_rng(0)
a=pd.read_csv('anomalias.csv')
w=a.pivot_table(index=['condado','anio'],columns='cultivo',values='anom_pct').dropna().reset_index()
print('pares condado-año:',len(w))
print('correlacion maiz-soya  Pearson %.2f | Spearman %.2f'%(w.maiz.corr(w.soya),w.maiz.corr(w.soya,method='spearman')))
y=w.groupby('anio')[['maiz','soya']].mean(); print('a nivel año (n=26): Pearson %.2f | Spearman %.2f'%(y.maiz.corr(y.soya),y.maiz.corr(y.soya,method='spearman')))
d=w.copy(); d[['maiz','soya']]=d[['maiz','soya']]-d.groupby('anio')[['maiz','soya']].transform('mean'); print('quitando el efecto del año (mismo año, distinto condado): Pearson %.2f'%d.maiz.corr(d.soya))
sin=w[~w.anio.isin([2003,2012])]; print('sin 2003 y 2012: Pearson %.2f'%sin.maiz.corr(sin.soya))
print('\nRiesgo por cultivo (anomalia % respecto a lo esperado)')
w['mitad']=(w.maiz+w.soya)/2
def met(s): return pd.Series({'desv':s.std(),'P10':s.quantile(.1),'P05':s.quantile(.05),'prob_perder>10%':100*(s<-10).mean(),'prob_perder>20%':100*(s<-20).mean(),'peor':s.min()})
print(pd.DataFrame({c:met(w[c]) for c in['maiz','soya','mitad']}).round(1).to_string())
# angulo 2: bootstrap por año (los condados del mismo año no son independientes)
an=w.anio.unique(); B=[]
for _ in range(2000):
    s=rng.choice(an,len(an)); b=pd.concat([w[w.anio==k] for k in s])
    B.append([b.maiz.std(),b.soya.std(),b.mitad.std(),100*(b.maiz<-10).mean(),100*(b.soya<-10).mean(),100*(b.mitad<-10).mean()])
B=np.array(B); print('IC 90%% (bootstrap por año): desv maiz [%.1f,%.1f] soya [%.1f,%.1f] mitad [%.1f,%.1f]'%tuple(np.percentile(B[:,i],q) for i in range(3) for q in(5,95)))
print('prob perder>10%%: maiz [%.0f,%.0f] soya [%.0f,%.0f] mitad [%.0f,%.0f]'%tuple(np.percentile(B[:,i],q) for i in range(3,6) for q in(5,95)))
print('veces que la desv de la mitad < min(maiz,soya): %.0f%%'%(100*(B[:,2]<np.minimum(B[:,0],B[:,1])).mean()))
# angulo 3: por condado, serie temporal propia
pc=w.groupby('condado').agg(m=('maiz','std'),s=('soya','std'),h=('mitad','std'),n=('anio','size')); pc=pc[pc.n>=20]
print('por condado (n=%d): desv mediana maiz %.1f soya %.1f mitad %.1f | condados donde mitad < ambos: %.0f%% | maiz mas volatil que soya en %.0f%%'%(len(pc),pc.m.median(),pc.s.median(),pc.h.median(),100*(pc.h<pc[['m','s']].min(axis=1)).mean(),100*(pc.m>pc.s).mean()))
print('\naños en que solo uno falla (media estatal < -8%):'); print(y[(y.maiz<-8)|(y.soya<-8)].round(1).to_string())
