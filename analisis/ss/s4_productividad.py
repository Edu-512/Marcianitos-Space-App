import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold,cross_val_predict
from sklearn.inspection import permutation_importance
ag=pd.read_csv('suelo_agricola.csv').dropna(subset=['arena_pct','factor_k','ph']); A=ag.acres_mapa
ordd={'Excessively drained':1,'Somewhat excessively drained':2,'Well drained':3,'Moderately well drained':4,'Somewhat poorly drained':5,'Poorly drained':6,'Very poorly drained':7}
ag['drenaje_ord']=ag.drenaje.map(ordd)
X=['om_pct','awc_cm_cm','arena_pct','arcilla_pct','ph','pendiente_pct','agua_disp_0_150cm','factor_k','factor_t','inund_siembra','prof_capa_cm','drenaje_ord']
def wcorr(x,y,w): mx,my=np.average(x,weights=w),np.average(y,weights=w); return np.average((x-mx)*(y-my),weights=w)/np.sqrt(np.average((x-mx)**2,weights=w)*np.average((y-my)**2,weights=w))
print('RELACION CON CSR2 (indice de productividad), n=',len(ag))
r=[(c,ag[c].corr(ag.csr2_iowa,method='spearman'),ag[c].corr(ag.csr2_iowa),wcorr(ag[c],ag.csr2_iowa,A)) for c in X]
print(pd.DataFrame(r,columns=['var','spearman','pearson','pearson_pond_area']).round(2).sort_values('spearman').to_string(index=False))
print('\nCSR2 por clase de drenaje (ponderado por area):')
g=ag.groupby('drenaje').apply(lambda d:pd.Series({'csr2':np.average(d.csr2_iowa,weights=d.acres_mapa),'pendiente':np.average(d.pendiente_pct,weights=d.acres_mapa),'arena':np.average(d.arena_pct,weights=d.acres_mapa),'awc':np.average(d.awc_cm_cm,weights=d.acres_mapa),'pct_area':100*d.acres_mapa.sum()/A.sum(),'n':len(d)}),include_groups=False)
print(g.loc[list(ordd)].round(1).to_string())
# modelo: ¿las variables nacionales reproducen el CSR2?
kf=KFold(5,shuffle=True,random_state=0); y=ag.csr2_iowa.values
def r2(p): return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
for nom,m in[('lineal',LinearRegression()),('bosque aleatorio',RandomForestRegressor(300,random_state=0,min_samples_leaf=2))]:
    p=cross_val_predict(m,ag[X],y,cv=kf); print(f'{nom}: R2 validacion cruzada {r2(p):.2f} | error medio abs {np.abs(y-p).mean():.1f} puntos CSR2 | R2 ponderado por area {1-np.average((y-p)**2,weights=A)/np.average((y-np.average(y,weights=A))**2,weights=A):.2f}')
# agrupando por serie de suelo (evitar que 83B y 83C caigan en train y test)
from sklearn.model_selection import GroupKFold
ser=ag.nombre.str.split().str[0]; p=cross_val_predict(RandomForestRegressor(300,random_state=0,min_samples_leaf=2),ag[X],y,cv=GroupKFold(5),groups=ser); print('bosque, separando por serie de suelo (prueba mas dura): R2 %.2f | error %.1f'%(r2(p),np.abs(y-p).mean()),'| series:',ser.nunique())
rf=RandomForestRegressor(300,random_state=0,min_samples_leaf=2).fit(ag[X],y); pi=permutation_importance(rf,ag[X],y,n_repeats=30,random_state=0)
print(pd.Series(pi.importances_mean,index=X).sort_values(ascending=False).round(3).to_string())
ag.to_csv('suelo_agricola.csv',index=False)
