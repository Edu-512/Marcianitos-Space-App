"""Paso 3: humedad de la zona de raíces contra rendimiento de maíz y soya (Story County).

Rendimiento como anomalía % contra una tendencia lineal (quita el avance tecnológico).
Métodos: Spearman por ventana (jun, jul, ago, jul-ago, jun-ago, may-sep), IC bootstrap,
Mann-Whitney (años secos p<20 contra el resto), regresión lineal y cuadrática,
validación dejando un año fuera (LOYO) contra el promedio como línea base.
Es exploratorio: sirve para elegir variables, no es el modelo.
Entradas: salidas/ del paso 0, datos/nass_quickstats_iowa_condados.csv
Salidas: salidas/R3_humedad_rendimiento_story.json, story_humedad_rendimiento.csv
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

from comun import SALIDAS, leer_nass
rng=np.random.default_rng(11)
n=pd.read_csv(SALIDAS/'iowa_nldas_mensual.csv',parse_dates=['time']).set_index('time')
g=pd.read_csv(SALIDAS/'iowa_gldas.csv',parse_dates=['time']).set_index('time')
n['g10']=g.sm; n['g10_p']=g.pctl
ns=leer_nass()
R={}
def boot(a,b,B=5000):
    a=np.asarray(a);b=np.asarray(b);idx=rng.integers(0,len(a),(B,len(a)))
    return np.nanpercentile([stats.spearmanr(a[i],b[i])[0] for i in idx],[2.5,97.5]).round(2).tolist()
win={'jun':[6],'jul':[7],'ago':[8],'jul_ago':[7,8],'jun_ago':[6,7,8],'may_sep':[5,6,7,8,9]}
feats={}
for w,ms in win.items():
    sub=n[n.m.isin(ms)].groupby('y')
    feats[f'sm100_p_{w}']=sub.sm100_p.mean(); feats[f'avail_{w}']=sub.avail.mean()
    feats[f'sm10_p_{w}']=sub.sm10_p.mean(); feats[f'g10_p_{w}']=sub.g10_p.mean()
F=pd.DataFrame(feats)
out={}
geos={'STORY':ns[ns.County=='STORY'],'STORY+BOONE':ns[ns.County.isin(['STORY','BOONE'])],'IOWA (media 99 condados)':ns}
yl={}
for gname,gd in geos.items():
    for crop in ['maiz','soya']:
        y=gd[gd.crop==crop].groupby('Year').v.mean()
        t=y.index.values; b=np.polyfit(t,y.values,1); trend=np.polyval(b,t)
        an=(y.values/trend-1)*100
        A=pd.Series(an,index=t,name='anom')
        yl[(gname,crop)]=pd.DataFrame({'y':y,'trend':trend,'anom':an})
        D=F.join(A,how='inner')
        res={'tendencia_bu_ac_anio':round(b[0],2),'n':len(D)}
        cors={c:round(stats.spearmanr(D[c],D.anom)[0],2) for c in F.columns}
        res['spearman']=cors
        out[f'{gname}|{crop}']=res
R['ventanas']=out
# foco: STORY, jul_ago
st={}
for crop in ['maiz','soya']:
    Y=yl[('STORY',crop)]; D=F.join(Y,how='inner')
    x=D['avail_jul_ago']; yv=D.anom
    rho,p=stats.spearmanr(x,yv); r,pp=stats.pearsonr(x,yv)
    lr=stats.linregress(x,yv)
    # LOYO
    pred=[];base=[]
    for yr in D.index:
        tr=D.drop(yr); l=stats.linregress(tr['avail_jul_ago'],tr.anom); pred.append(l.intercept+l.slope*D.loc[yr,'avail_jul_ago']); base.append(tr.anom.mean())
    pred=np.array(pred);base=np.array(base)
    rmse=np.sqrt(np.mean((pred-yv)**2)); rmse0=np.sqrt(np.mean((base-yv)**2))
    # quadratic (exceso + deficit)
    c2=np.polyfit(x,yv,2); r2q=1-np.sum((np.polyval(c2,x)-yv)**2)/np.sum((yv-yv.mean())**2)
    dry=D[D.sm100_p_jul_ago<20].anom; oth=D[D.sm100_p_jul_ago>=20].anom
    mw=stats.mannwhitneyu(dry,oth,alternative='less')
    p2012=pred[list(D.index).index(2012)]
    st[crop]=dict(spearman=round(rho,2),p_spearman=round(p,4),ic95=boot(x,yv),pearson=round(r,2),p_pearson=round(pp,4),
       pendiente_pct_por_punto_avail=round(lr.slope,3),r2_lineal=round(lr.rvalue**2,2),r2_cuadratico=round(r2q,2),
       loyo_rmse=round(rmse,2),rmse_climatologia=round(rmse0,2),mejora_pct=round((1-rmse/rmse0)*100,1),
       anios_secos=dry.index.tolist(),anom_secos_media=round(dry.mean(),1),anom_otros_media=round(oth.mean(),1),mannwhitney_p=round(mw.pvalue,4),
       anom_2012_real=round(D.loc[2012,'anom'],1),anom_2012_pred_sin2012=round(p2012,1),
       anom_2020=round(D.loc[2020,'anom'],1),anom_2021=round(D.loc[2021,'anom'],1),anom_2023=round(D.loc[2023,'anom'],1),
       peores=D.anom.sort_values().head(5).round(1).to_dict(),
       residuos_grandes={int(k):round(v,1) for k,v in (yv-(lr.intercept+lr.slope*x)).sort_values().head(3).items()})
R['story_jul_ago_avail']=st
tab=F[['sm100_p_jul_ago','avail_jul_ago']].join(yl[('STORY','maiz')][['y','anom']].rename(columns={'y':'maiz_bu_ac','anom':'maiz_anom_pct'})).join(yl[('STORY','soya')][['y','anom']].rename(columns={'y':'soya_bu_ac','anom':'soya_anom_pct'}))
tab.round(2).to_csv(SALIDAS/'story_humedad_rendimiento.csv')
json.dump(R,open(SALIDAS/'R3_humedad_rendimiento_story.json','w'),indent=1)
print(json.dumps(R['story_jul_ago_avail'],indent=1))
for k,v in R['ventanas'].items(): print(k,v['tendencia_bu_ac_anio'],{c:v['spearman'][c] for c in ['sm100_p_jun','sm100_p_jul','sm100_p_ago','sm100_p_jul_ago','avail_jul_ago','sm10_p_jul_ago','g10_p_jul_ago','sm100_p_may_sep']})
