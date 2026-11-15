import pandas as pd,numpy as np
from scipy import stats
t=pd.read_csv('quickstats_iowa_limpio.csv')
for v in['maiz_rend','soya_rend','avena_rend']:
    s=t.dropna(subset=[v]); a=s.groupby('anio')[v].mean()
    ols=stats.linregress(a.index,a.values); ts=stats.theilslopes(a.values,a.index); sp=stats.spearmanr(a.index,a.values)
    # angulo 2: pendiente por condado (>=20 años)
    sl=[]
    for c,g in s.groupby('condado'):
        if len(g)>=20: sl.append(stats.linregress(g.anio,g[v]).slope)
    sl=np.array(sl)
    # angulo 3: primera mitad vs segunda mitad
    m1,m2=a[a.index<=2012].mean(),a[a.index>=2013].mean()
    # curvatura
    q=np.polyfit(a.index-2012,a.values,2)
    print(f"{v}: OLS {ols.slope:.2f}/año (R2 {ols.rvalue**2:.2f}, p {ols.pvalue:.1e}) | Theil-Sen {ts[0]:.2f} [{ts[2]:.2f},{ts[3]:.2f}] | Spearman {sp.correlation:.2f} | por condado n={len(sl)} mediana {np.median(sl):.2f}, positivos {100*(sl>0).mean():.0f}% | 2000-12 {m1:.1f} vs 2013-25 {m2:.1f} | termino cuadratico {q[0]:.3f}")
# quitar tendencia: lineal por condado -> anomalia % 
out=[]
for v in['maiz_rend','soya_rend']:
    for c,g in t.dropna(subset=[v]).groupby('condado'):
        if len(g)<15: continue
        r=stats.linregress(g.anio,g[v]); esp=r.intercept+r.slope*g.anio
        out.append(pd.DataFrame({'condado':c,'distrito':g.distrito,'anio':g.anio,'cultivo':v[:4],'rend':g[v],'esperado':esp,'anom_pct':100*(g[v]-esp)/esp}))
a=pd.concat(out); a.to_csv('anomalias.csv',index=False); print(a.groupby('cultivo').anom_pct.describe().round(2).to_string())
