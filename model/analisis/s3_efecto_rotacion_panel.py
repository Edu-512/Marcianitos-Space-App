import pandas as pd,numpy as np,statsmodels.formula.api as smf
from scipy import stats
t=pd.read_csv('../qs/quickstats_iowa_limpio.csv').sort_values(['condado','anio']); a=pd.read_csv('../qs/anomalias.csv')
t['soya_prev']=t.groupby('condado').soya_acres.shift(1); t['maiz_prev']=t.groupby('condado').maiz_acres.shift(1); t['anio_prev']=t.groupby('condado').anio.shift(1)
t=t[t.anio-t.anio_prev==1].copy()
t['mm_min']=(t.maiz_acres-t.soya_prev).clip(lower=0)/t.maiz_acres      # fraccion minima de maiz sobre maiz
t['prop_maiz']=t.maiz_acres/(t.maiz_acres+t.soya_acres)
# validar el indicador contra el mapa (Butler)
tr=pd.read_csv('/mnt/user-data/uploads/acdb017d-cdl_butler_transiciones.csv'); b=t[t.condado=='BUTLER'].merge(tr,on='anio')
print('Butler: minimo por superficie (QuickStats) vs real por pixel (CDL)'); print(b[['anio','mm_min','pct_maiz_tras_maiz']].assign(mm_min=lambda d:(100*d.mm_min).round(1)).to_string(index=False)); print('  correlacion %.2f (n=%d)'%(b.mm_min.corr(b.pct_maiz_tras_maiz),len(b)))
p=t.merge(a[a.cultivo=='maiz'][['condado','anio','anom_pct']],on=['condado','anio']).merge(a[a.cultivo=='soya'][['condado','anio','anom_pct']].rename(columns={'anom_pct':'anom_soya'}),on=['condado','anio'],how='left')
print('\npanel:',len(p),'condado-años |',p.condado.nunique(),'condados | mm_min media %.2f, desv total %.2f, desv dentro de condado-año %.2f'%(p.mm_min.mean(),p.mm_min.std(),(p.mm_min-p.groupby('condado').mm_min.transform('mean')-p.groupby('anio').mm_min.transform('mean')+p.mm_min.mean()).std()))
def fe(y,x,d=None,extra=''):
    d=p if d is None else d
    d=d.dropna(subset=[y,x]+[c for c in ['prop_maiz','anom_prev'] if c in extra])
    m=smf.ols(f'{y} ~ {x} {extra} + C(condado) + C(anio)',d).fit(cov_type='cluster',cov_kwds={'groups':d.condado.astype('category').cat.codes})
    return m.params[x],m.bse[x],m.pvalues[x]
print('\nEFECTO sobre la anomalia de rendimiento del maiz (%), por cada +1.0 en la fraccion de maiz sobre maiz:')
print('  1) efectos fijos de condado y año: %.1f (ee %.1f, p %.3f)'%fe('anom_pct','mm_min'))
p=p.dropna(subset=['mm_min','anom_pct']).copy()
print('  2) sin efectos fijos (ingenuo): %.1f'%stats.linregress(p.mm_min,p.anom_pct).slope,'| solo efecto de año: %.1f'%smf.ols('anom_pct ~ mm_min + C(anio)',p).fit().params['mm_min'])
# 3) primeras diferencias
p=p.sort_values(['condado','anio']); p['d_mm']=p.groupby('condado').mm_min.diff(); p['d_y']=p.groupby('condado').anom_pct.diff(); q=p.dropna(subset=['d_mm','d_y'])
m=smf.ols('d_y ~ d_mm + C(anio)',q).fit(cov_type='cluster',cov_kwds={'groups':q.condado.astype('category').cat.codes}); print('  3) primeras diferencias con efecto de año: %.1f (ee %.1f, p %.3f)'%(m.params['d_mm'],m.bse['d_mm'],m.pvalues['d_mm']))
# 4) por condado, quitando el efecto del año
p['y_r']=p.anom_pct-p.groupby('anio').anom_pct.transform('mean'); p['x_r']=p.mm_min-p.groupby('anio').mm_min.transform('mean')
r=p.groupby('condado').apply(lambda d:stats.spearmanr(d.x_r,d.y_r)[0] if len(d)>=15 else np.nan,include_groups=False).dropna(); print('  4) correlacion dentro de cada condado (quitando el año): mediana %.2f | negativos %.0f%% de %d condados | prueba de signos p %.3f'%(r.median(),100*(r<0).mean(),len(r),stats.binomtest(int((r<0).sum()),len(r)).pvalue))
print('\nPRUEBAS DE FALSIFICACION')
print('  a) placebo: efecto sobre la SOYA (no deberia haber): %.1f (ee %.1f, p %.3f)'%fe('anom_soya','mm_min',p.dropna(subset=['anom_soya'])))
p['mm_fut']=p.groupby('condado').mm_min.shift(-1); print('  b) maiz sobre maiz del año SIGUIENTE (no deberia predecir): %.1f (ee %.1f, p %.3f)'%fe('anom_pct','mm_fut',p.dropna(subset=['mm_fut'])))
print('  c) controlando la proporcion de maiz del año: %.1f (ee %.1f, p %.3f)'%fe('anom_pct','mm_min',p,'+ prop_maiz'))
p['anom_prev']=p.groupby('condado').anom_pct.shift(1); print('  d) controlando la anomalia del año anterior: %.1f (ee %.1f, p %.3f)'%fe('anom_pct','mm_min',p.dropna(subset=['anom_prev']),'+ anom_prev'))
for nom,d in[('2000-2012',p[p.anio<=2012]),('2013-2025',p[p.anio>=2013]),('sin 2012',p[p.anio!=2012])]: print('  e) %s: %.1f (ee %.1f, p %.3f)'%((nom,)+fe('anom_pct','mm_min',d)))
p.to_csv('panel_rotacion.csv',index=False)
