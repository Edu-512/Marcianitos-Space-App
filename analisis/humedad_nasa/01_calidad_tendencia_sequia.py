"""Paso 1: calidad, años extremos, tendencia, sequías y acuerdo entre fuentes (Story County, Iowa).

Métodos: Mann-Kendall + pendiente de Sen; teoría de rachas (umbrales de percentil 10/20/30);
Spearman con IC bootstrap (5000); kappa de Cohen con umbral p < 20; correlación con desfase.
Entradas: salidas/ del paso 0, datos/nass_quickstats_iowa_condados.csv, datos/openet_iowa_2021_2026_mm.csv
Salida: salidas/R1_calidad_sequia_acuerdo.json
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

from comun import DATOS, SALIDAS, leer_nass
rng=np.random.default_rng(42)
R={}
# ---------- datos
n=pd.read_csv(SALIDAS/'iowa_nldas_mensual.csv',parse_dates=['time']).set_index('time')
g=pd.read_csv(SALIDAS/'iowa_gldas.csv',parse_dates=['time']).set_index('time')
n['g10']=g.sm; n['g10_p']=g.pctl
s=pd.read_csv(SALIDAS/'smap_mensual.csv'); s=s[s.id=='iowa'].copy(); s['time']=pd.to_datetime(s.t.astype(str)); s=s.set_index('time')
ns=leer_nass()
def mk(x):
    x=np.asarray(x); n_=len(x); S=0
    for i in range(n_-1): S+=np.sign(x[i+1:]-x[i]).sum()
    var=n_*(n_-1)*(2*n_+5)/18; z=(S-np.sign(S))/np.sqrt(var) if S!=0 else 0
    p=2*(1-stats.norm.cdf(abs(z)))
    sl=[(x[j]-x[i])/(j-i) for i in range(n_) for j in range(i+1,n_)]
    return dict(S=int(S),z=round(z,2),p=round(p,3),sen=np.median(sl))
def boot_r(a,b,f=lambda a,b: stats.spearmanr(a,b)[0],B=5000):
    a=np.asarray(a);b=np.asarray(b);idx=rng.integers(0,len(a),(B,len(a)))
    v=np.array([f(a[i],b[i]) for i in idx]); return np.nanpercentile(v,[2.5,97.5]).round(2).tolist()
# ---------- calidad
R['calidad']=dict(nldas_meses=len(n), nldas_huecos=int(n[['sm10','sm100','avail']].isna().sum().sum()),
   smap_meses=len(s), nass_obs=len(ns), nass_condados=ns.County.nunique(),
   story=ns[ns.County=='STORY'].groupby('crop').Year.agg(['min','max','count']).to_dict())
# ---------- temporada abr-sep
gs=n[n.m.between(4,9)].groupby('y')[['sm10','sm100','avail','g10']].mean()
jja=n[n.m.isin([7,8])].groupby('y')[['sm100','avail','sm100_p','avail_p','sm10_p','g10_p']].mean()
R['extremos_sm100']=dict(secos=gs.sm100.sort_values().head(5).round(3).to_dict(),humedos=gs.sm100.sort_values().tail(3).round(3).to_dict(),media=round(gs.sm100.mean(),3),cv=round(gs.sm100.std()/gs.sm100.mean()*100,1))
# ---------- tendencia
R['tendencia']={c:mk(gs[c].values) for c in ['sm100','avail','sm10','g10']}
for c in R['tendencia']: R['tendencia'][c]['sen_decada']=round(R['tendencia'][c]['sen']*10,4)
# ---------- eventos de sequia (run theory) sobre percentil mensual sm100
def runs(p,th):
    ev=[];cur=[]
    for t,v in p.items():
        if v<th: cur.append((t,v))
        else:
            if cur: ev.append(cur); cur=[]
    if cur: ev.append(cur)
    return [dict(inicio=str(e[0][0])[:7],fin=str(e[-1][0])[:7],meses=len(e),sev=round(sum(th-v for _,v in e),1),min_p=round(min(v for _,v in e),1)) for e in ev]
ev={}
for th in [10,20,30]:
    e=runs(n.sm100_p,th); ev[th]=dict(n=len(e),meses_total=sum(x['meses'] for x in e),dur_media=round(np.mean([x['meses'] for x in e]),1),dur_max=max(x['meses'] for x in e),
        top=sorted(e,key=lambda x:-x['sev'])[:5])
R['eventos']=ev
# eventos de 2+ meses en temporada
# ---------- acuerdo entre fuentes
def kappa(a,b):
    a=np.asarray(a);b=np.asarray(b);po=(a==b).mean();pe=a.mean()*b.mean()+(1-a.mean())*(1-b.mean());return round((po-pe)/(1-pe),2)
A={}
A['nldas10_vs_gldas10']=dict(spearman=round(stats.spearmanr(n.sm10_p,n.g10_p)[0],2),ic95=boot_r(n.sm10_p,n.g10_p),kappa_p20=kappa(n.sm10_p<20,n.g10_p<20),n=len(n))
A['nldas100_vs_gldas10']=dict(spearman=round(stats.spearmanr(n.sm100_p,n.g10_p)[0],2),ic95=boot_r(n.sm100_p,n.g10_p),kappa_p20=kappa(n.sm100_p<20,n.g10_p<20),n=len(n))
A['nldas10_vs_nldas100']=dict(spearman=round(stats.spearmanr(n.sm10_p,n.sm100_p)[0],2),ic95=boot_r(n.sm10_p,n.sm100_p),kappa_p20=kappa(n.sm10_p<20,n.sm100_p<20),n=len(n))
k=n.join(s[['rz','pctl','surf']],how='inner')
A['nldas100_vs_smap']=dict(spearman=round(stats.spearmanr(k.sm100_p,k.pctl)[0],2),ic95=boot_r(k.sm100_p,k.pctl),pearson=round(stats.pearsonr(k.sm100_p,k.pctl)[0],2),kappa_p20=kappa(k.sm100_p<20,k.pctl<20),n=len(k),mae_pct=round(np.mean(abs(k.sm100_p-k.pctl)),1))
A['gldas10_vs_smap']=dict(spearman=round(stats.spearmanr(k.g10_p,k.pctl)[0],2),ic95=boot_r(k.g10_p,k.pctl),n=len(k))
# lag (SMAP vs NLDAS)
A['lag_smap_nldas']={L:round(stats.spearmanr(k.pctl.shift(L).dropna(),k.sm100_p.loc[k.pctl.shift(L).dropna().index])[0],2) for L in [-1,0,1]}
# OpenET anual
oe=pd.read_csv(DATOS/'openet_iowa_2021_2026_mm.csv'); oe['y']=oe.mes.str[:4].astype(int); oe['m']=oe.mes.str[5:].astype(int)
oj=oe[oe.m.isin([7,8])].groupby('y').agg(ET=('ET','sum'),ETo=('ETo','sum')); oj['ETof']=oj.ET/oj.ETo
oj=oj.join(jja[['sm100_p','avail']]).dropna()
A['openet_jul_ago_vs_nldas']=dict(anios=oj.index.tolist(),ETof=oj.ETof.round(2).tolist(),sm100_p=oj.sm100_p.round(0).tolist(),spearman=round(stats.spearmanr(oj.ETof,oj.sm100_p)[0],2),n=len(oj))
R['acuerdo']=A
json.dump(R,open(SALIDAS/'R1_calidad_sequia_acuerdo.json','w',encoding='utf-8'),default=str,indent=1,ensure_ascii=False)
print(json.dumps(R,default=str,indent=1,ensure_ascii=False))
