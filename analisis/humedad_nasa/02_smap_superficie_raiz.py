"""Paso 2: SMAP L4, capa superficial (0-5 cm) contra zona de raíces (0-100 cm) y ciclo diario.

Métodos: coeficiente de variación, autocorrelación, correlación cruzada de cambios diarios,
respuesta de la raíz tras días de lluvia (cambio superficial > p95), ciclo diario en hora local (UTC-6).
Entrada: datos/smap_l4_appeears.csv (punto iowa 42.07, -93.5; 2024-2025)
Salidas: salidas/R2_smap_superficie_raiz.json, smap_ciclo_diario.csv, smap_diario_iowa.csv
"""
import json

import numpy as np
import pandas as pd

from comun import DATOS, SALIDAS
rng=np.random.default_rng(7)
R={}
s=pd.read_csv(DATOS/'smap_l4_appeears.csv')
s.columns=['cat','id','lat','lon','date','tile','y','x','rz','pctl','surf']
s['t']=pd.to_datetime(s.date.str.replace(' UTC',''))
i=s[s.id=='iowa'].set_index('t')[['rz','surf']]
d=i.resample('D').mean()
R['smap_sup_vs_raiz']=dict(r_diaria=round(d.surf.corr(d.rz),2),sd_surf=round(d.surf.std(),3),sd_rz=round(d.rz.std(),3),
  cv_surf=round(d.surf.std()/d.surf.mean()*100,1),cv_rz=round(d.rz.std()/d.rz.mean()*100,1),
  autocorr_lag1_surf=round(d.surf.autocorr(1),3),autocorr_lag1_rz=round(d.rz.autocorr(1),3),
  autocorr_lag30_surf=round(d.surf.autocorr(30),2),autocorr_lag30_rz=round(d.rz.autocorr(30),2))
# cross-correlation of daily changes: surface leads rootzone?
ds=d.surf.diff(); dr=d.rz.diff()
R['smap_sup_vs_raiz']['xcorr_cambios']={L:round(ds.shift(L).corr(dr),2) for L in [0,1,2,3,5,7]}
# respuesta a eventos de lluvia: dias con aumento sup > p95
th=ds.quantile(0.95); ev=ds[ds>th].index
resp=[]
for t in ev:
    w=d.rz.loc[t-pd.Timedelta(days=1):t+pd.Timedelta(days=10)]
    if len(w)>=11: resp.append((w.values-w.values[0]))
resp=np.array(resp); R['smap_sup_vs_raiz']['respuesta_raiz_tras_lluvia']=dict(n=len(resp),max_media=round(resp.mean(0).max(),4),dia_max=int(resp.mean(0).argmax()-1))
# ciclo diario (hora local CDT/CST ~ UTC-6)
i2=i.copy(); i2['hl']=(i2.index.hour-6)%24; i2['mes']=i2.index.month
anom=i2.copy()
for c in ['surf','rz']: anom[c]=i2[c]-i2[c].groupby(i2.index.date).transform('mean')
dc=anom.groupby('hl')[['surf','rz']].mean()
R['ciclo_diario']=dict(amplitud_surf=round(dc.surf.max()-dc.surf.min(),4),amplitud_rz=round(dc.rz.max()-dc.rz.min(),5),
  hora_max_surf=int(dc.surf.idxmax()),hora_min_surf=int(dc.surf.idxmin()),
  amp_verano=round((lambda x:x.max()-x.min())(anom[anom.mes.isin([6,7,8])].groupby('hl').surf.mean()),4),
  amp_invierno=round((lambda x:x.max()-x.min())(anom[anom.mes.isin([12,1,2])].groupby('hl').surf.mean()),4),
  rel_amp_vs_sd_diaria=round((dc.surf.max()-dc.surf.min())/d.surf.std(),2))
dc.round(5).to_csv(SALIDAS/'smap_ciclo_diario.csv'); d.to_csv(SALIDAS/'smap_diario_iowa.csv')
json.dump(R,open(SALIDAS/'R2_smap_superficie_raiz.json','w'),indent=1)
print(json.dumps(R,indent=1)); print(dc.round(4))
