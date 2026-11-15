import pandas as pd,numpy as np
F="/mnt/user-data/uploads/521ab477-POWER_Point_Daily_20000101_20251231_042d73N_092d79W_LST_1.csv"
d=pd.read_csv(F,skiprows=12)
print('filas',len(d),'| años',d.YEAR.min(),d.YEAR.max(),'| faltantes(-999):',int((d[['T2M','T2M_MAX','PRECTOTCORR','GWETROOT']]==-999).sum().sum()))
d['fecha']=pd.to_datetime(d.YEAR.astype(str)+d.DOY.astype(str),format='%Y%j'); d['mes']=d.fecha.dt.month
r=pd.DataFrame(index=sorted(d.YEAR.unique()))
ago=d[d.mes==8].groupby('YEAR').GWETROOT.mean(); r['humedad_agosto_pct']=(ago.rank(pct=True)*100).round(1); r['humedad_agosto_val']=ago.round(3)
r['dias_mayor_35']=d[d.mes.between(6,8)].assign(c=lambda x:x.T2M_MAX>35).groupby('YEAR').c.sum()
r['dias_mayor_32']=d[d.mes.between(6,8)].assign(c=lambda x:x.T2M_MAX>32).groupby('YEAR').c.sum()
mj=d[d.mes.isin([5,6])].groupby('YEAR').PRECTOTCORR.sum(); r['lluvia_mayo_junio_pct']=(mj.rank(pct=True)*100).round(1); r['lluvia_mayo_junio_mm']=mj.round(0)
r['temp_julio_c']=d[d.mes==7].groupby('YEAR').T2M.mean().round(1)
r.index.name='anio'; r.to_csv('clima_butler_por_anio.csv')
print('\nVERIFICACION 2012 (debe salir seco y caluroso):'); print(r.loc[[2012,2013,2023,2008,2010,2019]].to_string())
print('\naños mas secos en agosto:',list(r.humedad_agosto_pct.nsmallest(4).index))
print('años con mas dias >35C:',dict(r.dias_mayor_35.nlargest(4)))
print('primaveras mas humedas:',list(r.lluvia_mayo_junio_pct.nlargest(4).index))
esc={'seco_caluroso':[2012,2013,2023],'humedo_primavera':[2008,2010,2019]}
esc['normal']=[y for y in r.index if y not in esc['seco_caluroso']+esc['humedo_primavera']]
g=pd.DataFrame({k:r.loc[v,['humedad_agosto_pct','dias_mayor_35','lluvia_mayo_junio_pct','temp_julio_c']].mean().round(1) for k,v in esc.items()}).T
print('\nPROMEDIO POR ESCENARIO'); print(g.to_string())
g.to_csv('clima_por_escenario.csv')
