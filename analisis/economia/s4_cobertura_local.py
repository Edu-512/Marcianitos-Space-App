import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,numpy as np
from scipy import stats
t=pd.read_csv('ingreso_por_condado.csv')
out=[]
for k,g in t.dropna(subset=['maiz_rend']).groupby('condado'):
    if len(g)<20: continue
    r=stats.linregress(g.anio,g.maiz_rend); e=r.intercept+r.slope*g.anio
    out.append(pd.DataFrame({'condado':k,'anio':g.anio,'an':100*(g.maiz_rend-e)/e,'precio':g.precio_maiz}))
a=pd.concat(out)
a['an_estatal']=a.groupby('anio').an.transform('mean')      # parte comun (cubierta por el precio)
a['an_local']=a.an-a.an_estatal                              # parte propia del condado (NO cubierta)
print('DESCOMPOSICION DEL RIESGO DE RENDIMIENTO DEL MAIZ')
print('  variacion total %.1f%% = comun a todo el estado %.1f%% + propia del condado %.1f%%'%(a.an.std(),a.an_estatal.std(),a.an_local.std()))
pr=a.groupby('anio').agg(an=('an_estatal','first'),p=('precio','first'))
pr['p_rel']=100*(pr.p/pr.p.rolling(5,center=True,min_periods=3).mean()-1)
print('\n  la parte COMUN si la cubre el precio: correlacion %.2f (cuando el estado rinde mal, el precio sube)'%stats.spearmanr(pr.an,pr.p_rel.fillna(0)).correlation)
print('  la parte PROPIA no la cubre nadie: el precio es el mismo para todos los agricultores del estado')
print('\n  o sea: de la variacion de rendimiento, %.0f%% queda sin cobertura de precio'%(100*a.an_local.var()/a.an.var()))
b=a[a.condado=='BUTLER']
print('\n  Butler 2012: caida total %.0f%% = estatal %.0f%% + propia %.0f%%'%(b[b.anio==2012].an.iloc[0],b[b.anio==2012].an_estatal.iloc[0],b[b.anio==2012].an_local.iloc[0]))
