import pandas as pd,numpy as np
from scipy import stats
rng=np.random.default_rng(1)
a=pd.read_csv('anomalias.csv'); a['res']=a.rend-a.esperado
for cu,malos in[('maiz',[2012,2013,2010,2020]),('soya',[2003,2012,2013])]:
    x=a[a.cultivo==cu]; niv=x.groupby('condado').esperado.mean(); x=x.join(niv.rename('nivel'),on='condado')
    x['q']=x.condado.map(pd.qcut(niv,4,labels=['Q1','Q2','Q3','Q4']))
    print('\n',cu,'| brecha Q1 - resto por año malo (puntos %):')
    for y in malos:
        d=x[x.anio==y]; print('  ',y,round(d[d.q=='Q1'].anom_pct.mean(),1),'vs',round(d[d.q!='Q1'].anom_pct.mean(),1),'| Spearman nivel-anomalia',round(d.nivel.corr(d.anom_pct,method='spearman'),2))
    # todos los años: ¿en cuantos años Q1 queda mas lejos de cero que el resto?
    g=x.groupby(['anio','q'],observed=True).anom_pct.mean().unstack(); resto=x[x.q!='Q1'].groupby('anio').anom_pct.mean()
    print('   años (de 26) en que |Q1| > |resto|:',int((g.Q1.abs()>resto.abs()).sum()),'| pendiente de Q1 sobre resto (amplificacion): %.2f'%stats.linregress(resto,g.Q1).slope)
    # control geografico: dentro del mismo distrito
    x['nivel_rel']=x.nivel-x.groupby('distrito').nivel.transform('mean')
    vol=x.groupby('condado').agg(vol=('res','std'),volp=('anom_pct','std'),nr=('nivel_rel','first'),dist=('distrito','first'),niv=('nivel','first'))
    vol['vol_rel']=vol.vol-vol.groupby('dist').vol.transform('mean'); vol['volp_rel']=vol.volp-vol.groupby('dist').volp.transform('mean')
    print('   DENTRO del distrito: nivel vs volatilidad abs Spearman %.2f (p %.3f) | en %%: %.2f (p %.3f)'%(*stats.spearmanr(vol.nr,vol.vol_rel),*stats.spearmanr(vol.nr,vol.volp_rel)))
    m=x[x.anio.isin(malos)].groupby('condado').anom_pct.mean(); vol['perd']=m; vol['perd_rel']=vol.perd-vol.groupby('dist').perd.transform('mean')
    print('   DENTRO del distrito: nivel vs perdida en años malos Spearman %.2f (p %.3f) | ENTRE distritos (n=9): %.2f'%(*stats.spearmanr(vol.nr,vol.perd_rel,nan_policy='omit'),stats.spearmanr(vol.groupby('dist').niv.mean(),vol.groupby('dist').perd.mean())[0]))
