import numpy as np,pandas as pd
from sklearn.linear_model import LinearRegression,RidgeCV
from sklearn.model_selection import GroupKFold,cross_val_predict
s=pd.read_csv('../ss/ssurgo_butler_variables_modelo.csv',dtype={'mukey':str})
ordd={'Excessively drained':1,'Somewhat excessively drained':2,'Well drained':3,'Moderately well drained':4,'Somewhat poorly drained':5,'Poorly drained':6,'Very poorly drained':7}
s['dren']=s.drenaje.map(ordd)
# NACIONALES: existen en SSURGO de cualquier estado. Excluidos: csr2 (solo Iowa) y factor_t (calificacion de experto)
NAC=['arena_pct','arcilla_pct','om_pct','ph','awc_cm_cm','agua_disp_0_150cm','pendiente_pct','factor_k','dren','inund_siembra','prof_capa_cm']
d=s.dropna(subset=NAC+['csr2_iowa','acres_mapa']).copy()
print('suelos con todas las variables:',len(d),'| %.0f%% del area'%(100*d.acres_mapa.sum()/s.acres_mapa.sum()))
# el drenaje no es lineal (joroba): se parte en dos
d['dren_seco']=np.clip(4-d.dren,0,None); d['dren_humedo']=np.clip(d.dren-4,0,None)
X=NAC[:-3]+['dren_seco','dren_humedo','inund_siembra','prof_capa_cm']; X.remove('dren') if 'dren' in X else None
X=['arena_pct','arcilla_pct','om_pct','ph','awc_cm_cm','agua_disp_0_150cm','pendiente_pct','factor_k','dren_seco','dren_humedo','inund_siembra']
y=d.csr2_iowa.values; w=d.acres_mapa.values
ser=d.nombre.str.split().str[0]
for nom,m in [('lineal',LinearRegression()),('ridge',RidgeCV(alphas=np.logspace(-3,3,25)))]:
    p=cross_val_predict(m,d[X],y,cv=GroupKFold(5),groups=ser)
    r2=1-((y-p)**2*w).sum()/((y-np.average(y,weights=w))**2*w).sum()
    print('%s: R2 ponderado por area, separando familias de suelo = %.2f | error medio %.1f puntos'%(nom,r2,np.average(np.abs(y-p),weights=w)))
m=LinearRegression().fit(d[X],y,sample_weight=w)
print('\ncoeficientes (puntos de indice por unidad):'); print(pd.Series(m.coef_,index=X).round(3).sort_values().to_string())
d['indice']=m.predict(d[X])
base=np.average(d.indice,weights=w)
print('\nindice predicho: media ponderada %.1f | p10 %.1f | p90 %.1f'%(base,np.percentile(d.indice,10),np.percentile(d.indice,90)))
d[['mukey','musym','nombre','acres_mapa','csr2_iowa','indice']].round(2).to_csv('indice_suelo.csv',index=False)
import pickle; pickle.dump({'vars':X,'coef':m.coef_,'intercept':m.intercept_,'base':base},open('modelo_suelo.pkl','wb'))
