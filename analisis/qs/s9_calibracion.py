import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,numpy as np
a=pd.read_csv('anomalias.csv')
print('CALIBRACION DE LOS RANGOS: se construye el rango con los otros 25 años y se revisa si el año omitido cae dentro')
for cu in['maiz','soya']:
    x=a[a.cultivo==cu]; anios=sorted(x.anio.unique())
    for niv in[50,80,90]:
        lo_q,hi_q=(100-niv)/2,100-(100-niv)/2; cob=[];cobp=[]
        for y in anios:
            tr=x[x.anio!=y].anom_pct; lo,hi=np.percentile(tr,[lo_q,hi_q])
            te=x[x.anio==y].anom_pct
            cob.append(((te>=lo)&(te<=hi)).mean())          # por condado-año
            cobp.append(lo<=te.mean()<=hi)                   # por año (promedio estatal)
        print(f'  {cu}: rango que promete {niv}% -> cubre {100*np.mean(cob):.0f}% de los casos condado-año | {100*np.mean(cobp):.0f}% de los años completos')
print('\nPor que falla a nivel de año: los condados de un mismo año no son independientes.')
print('Rango construido con la distribucion de AÑOS (promedio estatal por año), no de condado-año:')
for cu in['maiz','soya']:
    x=a[a.cultivo==cu]; ya=x.groupby('anio').anom_pct.mean(); anios=list(ya.index)
    for niv in[50,80,90]:
        lo_q,hi_q=(100-niv)/2,100-(100-niv)/2
        c=[np.percentile(ya.drop(y),lo_q)<=ya[y]<=np.percentile(ya.drop(y),hi_q) for y in anios]
        print(f'  {cu}: promete {niv}% -> cubre {100*np.mean(c):.0f}% de los años (n=26)')
