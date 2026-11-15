import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,numpy as np
from scipy import stats
c=pd.read_csv('../entradas/clima_butler_por_anio.csv').set_index('anio')
a=pd.read_csv('../entradas/anomalias.csv')
# clasificar por CLIMA, no por rendimiento
def clase(r):
    if r.humedad_agosto_pct<35 or r.dias_mayor_35>=5: return 'seco_caluroso'
    if r.lluvia_mayo_junio_pct>72: return 'humedo_primavera'
    return 'normal'
c['escenario']=c.apply(clase,axis=1)
print('CLASIFICACION POR CLIMA'); 
for e in['seco_caluroso','humedo_primavera','normal']:
    y=sorted(c[c.escenario==e].index); print(' %-18s %2d años: %s'%(e,len(y),y))
print('\nindicadores promedio por escenario')
g=c.groupby('escenario')[['humedad_agosto_pct','dias_mayor_35','lluvia_mayo_junio_pct','temp_julio_c']].mean().round(1)
print(g.to_string())
print('\nVALIDACION: ¿los rendimientos realmente difieren entre estos escenarios?')
for cu in['maiz','soya']:
    x=a[a.cultivo==cu].merge(c[['escenario']],left_on='anio',right_index=True)
    t=x.groupby('escenario').anom_pct.agg(['mean','median','size'])
    t['p10']=x.groupby('escenario').anom_pct.quantile(.1).round(1)
    print(' %s:'%cu); print(t.round(1).to_string())
    gr=[x[x.escenario==e].anom_pct for e in g.index]
    print('   Kruskal-Wallis p=%.4f'%stats.kruskal(*gr).pvalue)
c.to_csv('../entradas/clima_butler_por_anio.csv')
g.to_csv('clima_por_escenario.csv')
