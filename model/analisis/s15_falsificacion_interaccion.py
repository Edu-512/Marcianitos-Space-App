import pandas as pd,numpy as np,statsmodels.formula.api as smf
p=pd.read_csv('panel_rotacion.csv')
ya=p.groupby('anio').anom_pct.mean(); p['anio_malo']=p.anio.map(ya)
def fe(d,y,x):
    d=d.dropna(subset=[y,x]).copy(); d['cl']=d.condado.astype('category').cat.codes
    if d.anio.nunique()<3: return None
    m=smf.ols(f'{y} ~ {x} + C(condado) + C(anio)',d).fit(cov_type='cluster',cov_kwds={'groups':d.cl})
    return m.params[x],m.bse[x],m.pvalues[x],d.anio.nunique()
G=[('malos',p[p.anio_malo<-5]),('normales',p[(p.anio_malo>=-5)&(p.anio_malo<=5)]),('buenos',p[p.anio_malo>5])]
print('PRUEBAS DE FALSIFICACION sobre el hallazgo de la interaccion\n')
print('1) PLACEBO: el mismo efecto sobre la SOYA (no deberia aparecer, el maiz-sobre-maiz no afecta a la soya)')
for n,d in G:
    r=fe(d,'anom_soya','mm_min')
    print('   %-10s %+.1f (ee %.1f, p %.3f)'%(n,*r[:3]) if r else '   %-10s n/d'%n)
print('\n2) FUTURO: maiz-sobre-maiz del año SIGUIENTE (imposible como causa)')
p=p.sort_values(['condado','anio']); p['mm_fut']=p.groupby('condado').mm_min.shift(-1)
for n,d in G:
    r=fe(d,'anom_pct','mm_fut')
    print('   %-10s %+.1f (ee %.1f, p %.3f)'%(n,*r[:3]) if r else '   %-10s n/d'%n)
print('\n3) ¿Que años son los "malos"? y cuantos condados aportan')
print('  ',sorted(p[p.anio_malo<-5].anio.unique()))
print('\n4) Mismo analisis quitando 2012 (el año extremo que podria dominar)')
q=p[(p.anio_malo<-5)&(p.anio!=2012)]; r=fe(q,'anom_pct','mm_min')
print('   años malos sin 2012: %+.1f (ee %.1f, p %.3f) | %d años'%r if r else '   n/d')
print('\n5) Variacion disponible: desviacion de mm_min dentro de condado-año en años malos: %.3f'%(p[p.anio_malo<-5].mm_min-p[p.anio_malo<-5].groupby('condado').mm_min.transform('mean')).std())
