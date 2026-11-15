import pandas as pd,numpy as np,statsmodels.formula.api as smf
p=pd.read_csv('panel_rotacion.csv').dropna(subset=['mm_min','anom_pct'])
ya=p.groupby('anio').anom_pct.mean()
p['anio_malo']=p.anio.map(ya)
p['estres']=-p.anio_malo                     # mayor = peor año
print('PRUEBA: ¿la penalizacion del maiz sobre maiz es mayor en años malos? (la literatura dice que si)')
d=p.copy(); d['cl']=d.condado.astype('category').cat.codes
m=smf.ols('anom_pct ~ mm_min*estres + C(condado) + C(anio)',d).fit(cov_type='cluster',cov_kwds={'groups':d.cl})
print('  interaccion mm_min x estres: %+.3f (ee %.3f, p %.3f)'%(m.params['mm_min:estres'],m.bse['mm_min:estres'],m.pvalues['mm_min:estres']))
print('  signo esperado por la literatura: positivo imposible de leer directo; mejor por grupos de año\n')
print('  efecto de mm_min estimado por separado en cada tipo de año:')
for nom,sub in [('años malos (anomalia < -5%)',p[p.anio_malo<-5]),('años normales (-5 a +5)',p[(p.anio_malo>=-5)&(p.anio_malo<=5)]),('años buenos (> +5%)',p[p.anio_malo>5])]:
    if sub.anio.nunique()<3: print('   %-28s pocos años (%d)'%(nom,sub.anio.nunique())); continue
    s=sub.copy(); s['cl']=s.condado.astype('category').cat.codes
    mm=smf.ols('anom_pct ~ mm_min + C(condado) + C(anio)',s).fit(cov_type='cluster',cov_kwds={'groups':s.cl})
    print('   %-28s %+.1f (ee %.1f, p %.3f) | %d años'%(nom,mm.params['mm_min'],mm.bse['mm_min'],mm.pvalues['mm_min'],sub.anio.nunique()))
print('\nCONTEXTO: ¿que tipo de años fueron 2024 y 2025? (los del NDVI)')
print(ya.loc[[2023,2024,2025]].round(1).to_string())
