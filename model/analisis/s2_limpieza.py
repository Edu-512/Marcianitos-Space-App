import pandas as pd,sys
d=pd.read_csv(sys.argv[1],dtype=str)
d['valor']=d['Value'].str.replace(',','').astype(float); d['anio']=d['Year'].astype(int)
m={'CORN - ACRES PLANTED':'maiz_acres','CORN, GRAIN - YIELD, MEASURED IN BU / ACRE':'maiz_rend','SOYBEANS - ACRES PLANTED':'soya_acres','SOYBEANS - YIELD, MEASURED IN BU / ACRE':'soya_rend','OATS - ACRES PLANTED':'avena_acres','OATS - YIELD, MEASURED IN BU / ACRE':'avena_rend','CORN, SILAGE - YIELD, MEASURED IN TONS / ACRE':'ensilaje_rend'}
d['var']=d['Data Item'].map(m)
print('duplicados:',d.duplicated(['anio','County','Ag District','var']).sum())
otros=d[d['County'].str.contains('OTHER')]
print('filas OTHER COUNTIES:',len(otros)); print(otros.groupby('var').size().to_string())
c=d[~d['County'].str.contains('OTHER')]
t=c.pivot_table(index=['County','Ag District','anio'],columns='var',values='valor').reset_index()
t.columns.name=None; t=t.rename(columns={'County':'condado','Ag District':'distrito'})
t.to_csv('quickstats_iowa_limpio.csv',index=False)
print(t.shape,t.condado.nunique(),'condados')
cov=t.groupby('anio')[['maiz_rend','soya_rend','avena_rend','maiz_acres','soya_acres']].count()
print(cov.T.to_string())
print(t[['maiz_rend','soya_rend','avena_rend','ensilaje_rend','maiz_acres','soya_acres','avena_acres']].describe().round(1).to_string())
n=t.groupby('condado')[['maiz_rend','soya_rend']].count(); print('condados con serie completa (26 años) maiz/soya:',(n.maiz_rend==26).sum(),(n.soya_rend==26).sum())
print(t[t.condado=='BUTLER'][['anio','maiz_rend','soya_rend','avena_rend','maiz_acres','soya_acres']].to_string(index=False))
