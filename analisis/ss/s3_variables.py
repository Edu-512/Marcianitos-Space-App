import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,numpy as np,csv
from scipy import stats
s=pd.read_csv('suelo_con_area.csv',dtype={'mukey':str})
# añadir inundacion (cmonth) y capa restrictiva (crstrcts) por componente dominante
U='datos/tabular/'
rd=lambda f:[r for r in csv.reader(open(U+f,encoding='utf-8',errors='replace'),delimiter='|') if r]
comp=pd.read_csv('datos/component.csv',dtype=str); comp['p']=pd.to_numeric(comp.comppct_r)
cm=pd.DataFrame([(r[1],r[2],r[4],r[-2]) for r in rd('cmonth.txt')],columns=['mes','inund','enchar','cokey'])
sev={'':0,'None':0,'Very rare':0,'Rare':1,'Occasional':2,'Frequent':3,'Very frequent':3}
cm['i']=cm.inund.map(sev); cm['e']=cm.enchar.map(sev)
siem=cm[cm.mes.isin(['April','May','June'])].groupby('cokey').agg(inund_siembra=('i','max'),enchar_siembra=('e','max'))
rs=pd.DataFrame([(r[-2],float(r[3])) for r in rd('crstrcts.txt')],columns=['cokey','prof']).groupby('cokey').prof.min()
comp=comp.join(siem,on='cokey').join(rs,on='cokey')
def w(g):
    p=g.p.fillna(0); 
    return pd.Series({'inund_siembra':(g.inund_siembra.fillna(0)>=2).mul(p).sum()/max(p.sum(),1)*100,'enchar_siembra':(g.enchar_siembra.fillna(0)>=2).mul(p).sum()/max(p.sum(),1)*100,'pct_con_capa_restr':g.prof.notna().mul(p).sum()/max(p.sum(),1)*100,'prof_capa_dom':g.sort_values('p').prof.iloc[-1]})
x=comp.groupby('mukey').apply(w,include_groups=False); s=s.join(x,on='mukey')
s['prof_capa_cm']=s.prof_capa_dom.fillna(200)
ag=s[s.csr2_iowa.notna()&s.om_pct.notna()].copy(); A=ag.acres_mapa
print('suelos agricolas con todas las variables:',len(ag),'de',len(s),'| % del area del condado:',round(100*A.sum()/s.acres_mapa.sum(),1))
num=['om_pct','awc_cm_cm','arena_pct','limo_pct','arcilla_pct','ph','pendiente_pct','agua_disp_0_150cm','factor_k','factor_t','inund_siembra','enchar_siembra','prof_capa_cm','csr2_iowa']
def wq(v,wt,q): o=np.argsort(v.values); c=np.cumsum(wt.values[o])/wt.sum(); return v.values[o][np.searchsorted(c,q)]
r=[]
for c in num:
    v=ag[c]; m=np.average(v,weights=A); sd=np.sqrt(np.average((v-m)**2,weights=A))
    r.append((c,v.isna().sum(),round(m,2),round(sd,2),round(sd/abs(m),2) if m else None,wq(v,A,.1),wq(v,A,.5),wq(v,A,.9),round(v.mean(),2)))
print(pd.DataFrame(r,columns=['var','vacios','media_area','desv_area','CV','p10','p50','p90','media_simple']).to_string(index=False))
for c in['drenaje','grupo_hidrologico','clase_tierra','frec_inundacion']:
    print('\n',c); print((100*ag.groupby(c).acres_mapa.sum()/A.sum()).round(1).sort_values(ascending=False).to_string())
ag.to_csv('suelo_agricola.csv',index=False); s.to_csv('suelo_con_area.csv',index=False)
print('\nREDUNDANCIA (|Spearman|>0.7):'); C=ag[num[:-1]].corr(method='spearman')
for i in range(len(C)):
    for j in range(i+1,len(C)):
        if abs(C.iloc[i,j])>.7: print(' ',C.index[i],C.columns[j],round(C.iloc[i,j],2),'| Pearson',round(ag[C.index[i]].corr(ag[C.columns[j]]),2))
