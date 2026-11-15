import pandas as pd,numpy as np
from scipy import stats
a=pd.read_csv('anomalias.csv'); t=pd.read_csv('quickstats_iowa_limpio.csv')
for cu,v in[('maiz','maiz_rend'),('soya','soya_rend')]:
    x=a[a.cultivo==cu]
    g=x.groupby('anio').anom_pct
    r=pd.DataFrame({'media':g.mean(),'mediana':g.median(),'pct_cond_bajo':g.apply(lambda s:100*(s<0).mean()),'n':g.size()})
    # angulo 2: sin modelo de tendencia: cambio vs promedio de los 3 años previos (estatal)
    s=t.groupby('anio')[v].mean(); r['vs_3prev_pct']=100*(s/s.shift(1).rolling(3).mean()-1)
    print('\n',cu); print(r.round(1).T.to_string())
    print('correlacion entre los dos metodos:',round(r[['media','vs_3prev_pct']].corr(method='spearman').iloc[0,1],2))
    # descomposicion de varianza: año vs condado
    p=x.pivot_table(index='condado',columns='anio',values='anom_pct')
    tot=((p-p.stack().mean())**2).stack().sum(); an=(p.count()*(p.mean()-p.stack().mean())**2).sum(); co=(p.count(axis=1)*(p.mean(axis=1)-p.stack().mean())**2).sum()
    print(f'varianza explicada por el año: {100*an/tot:.0f}% | por el condado: {100*co/tot:.0f}% | resto (condado x año): {100*(1-(an+co)/tot):.0f}%')
    # angulo 2: correlacion media entre pares de condados
    c=p.T.corr(min_periods=15).values; iu=np.triu_indices_from(c,1); print('correlacion media entre condados:',round(np.nanmean(c[iu]),2),'| mediana',round(np.nanmedian(c[iu]),2))
    # angulo 3: dentro del mismo distrito vs distinto
    dist=x.drop_duplicates('condado').set_index('condado').distrito.reindex(p.index).values
    same=dist[iu[0]]==dist[iu[1]]; print('mismo distrito:',round(np.nanmean(c[iu][same]),2),'| distinto distrito:',round(np.nanmean(c[iu][~same]),2))
