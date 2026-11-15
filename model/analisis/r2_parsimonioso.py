import numpy as np,pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold,cross_val_predict
s=pd.read_csv('../ss/ssurgo_butler_variables_modelo.csv',dtype={'mukey':str})
ordd={'Excessively drained':1,'Somewhat excessively drained':2,'Well drained':3,'Moderately well drained':4,'Somewhat poorly drained':5,'Poorly drained':6,'Very poorly drained':7}
s['dren']=s.drenaje.map(ordd)
d=s.dropna(subset=['arena_pct','agua_disp_0_150cm','pendiente_pct','om_pct','dren','csr2_iowa','acres_mapa']).copy()
d['dren_seco']=np.clip(4-d.dren,0,None); d['dren_humedo']=np.clip(d.dren-4,0,None)
y=d.csr2_iowa.values; w=d.acres_mapa.values; ser=d.nombre.str.split().str[0]
print('colinealidad entre candidatas (Pearson):')
C=d[['arena_pct','agua_disp_0_150cm','om_pct','awc_cm_cm','pendiente_pct','factor_k']].corr().round(2)
print(C.to_string())
def prueba(X,nom):
    p=cross_val_predict(LinearRegression(),d[X],y,cv=GroupKFold(5),groups=ser)
    r2=1-((y-p)**2*w).sum()/((y-np.average(y,weights=w))**2*w).sum()
    m=LinearRegression().fit(d[X],y,sample_weight=w)
    print('%-52s R2=%.2f err=%.1f  signos: %s'%(nom,r2,np.average(np.abs(y-p),weights=w),dict(zip(X,np.sign(m.coef_).astype(int)))))
    return r2,m
prueba(['arena_pct'],'solo arena')
prueba(['agua_disp_0_150cm'],'solo agua disponible')
prueba(['arena_pct','agua_disp_0_150cm'],'arena + agua')
prueba(['arena_pct','agua_disp_0_150cm','pendiente_pct'],'arena + agua + pendiente')
prueba(['arena_pct','agua_disp_0_150cm','pendiente_pct','om_pct'],'+ materia organica')
r2,m=prueba(['arena_pct','agua_disp_0_150cm','pendiente_pct','om_pct','dren_seco','dren_humedo'],'+ drenaje partido')
X=['arena_pct','agua_disp_0_150cm','pendiente_pct','om_pct','dren_seco','dren_humedo']
print('\ncoeficientes del elegido:'); print(pd.Series(m.coef_,index=X).round(3).to_string()); print('intercepto %.1f'%m.intercept_)
d['indice']=np.clip(m.predict(d[X]),5,100); base=np.average(d.indice,weights=w)
d['ajuste_pct']=100*(d.indice/base-1)
print('\nindice: base %.1f | rango p10-p90: %.1f a %.1f'%(base,d.indice.quantile(.1),d.indice.quantile(.9)))
print('ajuste de rendimiento: p10 %.1f%% | p50 %.1f%% | p90 %.1f%%'%(d.ajuste_pct.quantile(.1),d.ajuste_pct.median(),d.ajuste_pct.quantile(.9)))
d[['mukey','musym','nombre','acres_mapa','csr2_iowa','indice','ajuste_pct']].round(2).to_csv('indice_suelo.csv',index=False)
import pickle; pickle.dump({'vars':X,'coef':m.coef_,'intercept':m.intercept_,'base':float(base)},open('modelo_suelo.pkl','wb'))
