import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,numpy as np
from scipy import stats
raw="""2025 4.1 10.5
2024 4.25 9.95
2023 4.61 12.2
2022 6.62 14.2
2021 6.1 13.4
2020 4.64 11.1
2019 3.5 8.48
2018 3.59 8.46
2017 3.31 9.25
2016 3.3 9.34
2015 3.52 8.91
2014 3.71 9.96
2013 4.49 13.1
2012 6.92 14.4
2011 6.2 12.6
2010 5.23 11.2
2009 3.59 9.52
2008 4.1 10.2
2007 4.29 10.5
2006 3.03 6.58
2005 1.94 5.54
2004 1.99 5.76
2003 2.37 7.7
2002 2.22 5.54
2001 1.9 4.35
2000 1.75 4.49"""
p=pd.DataFrame([l.split() for l in raw.split('\n')],columns=['anio','precio_maiz','precio_soya']).astype(float); p['anio']=p.anio.astype(int)
p.to_csv('precios_iowa.csv',index=False)
print('PRECIOS (USD/bushel, precio recibido, año comercial, Iowa)')
print('  maiz: min %.2f (%d) max %.2f (%d) | soya: min %.2f (%d) max %.2f (%d)'%(p.precio_maiz.min(),p.loc[p.precio_maiz.idxmin(),'anio'],p.precio_maiz.max(),p.loc[p.precio_maiz.idxmax(),'anio'],p.precio_soya.min(),p.loc[p.precio_soya.idxmin(),'anio'],p.precio_soya.max(),p.loc[p.precio_soya.idxmax(),'anio']))
print('  el precio varia mucho mas que el rendimiento: CV maiz %.0f%% vs rendimiento ~11%% | CV soya %.0f%%'%(100*p.precio_maiz.std()/p.precio_maiz.mean(),100*p.precio_soya.std()/p.precio_soya.mean()))
print('  relacion de precios soya/maiz: media %.2f | rango %.2f a %.2f'%((p.precio_soya/p.precio_maiz).mean(),(p.precio_soya/p.precio_maiz).min(),(p.precio_soya/p.precio_maiz).max()))
t=pd.read_csv('../qs/quickstats_iowa_limpio.csv').merge(p,on='anio')
t['ing_maiz']=t.maiz_rend*t.precio_maiz; t['ing_soya']=t.soya_rend*t.precio_soya
b=t[t.condado=='BUTLER']
print('\nINGRESO BRUTO POR ACRE (rendimiento x precio), Butler County')
print('  maiz: media $%.0f | min $%.0f (%d) | max $%.0f (%d)'%(b.ing_maiz.mean(),b.ing_maiz.min(),b.loc[b.ing_maiz.idxmin(),'anio'],b.ing_maiz.max(),b.loc[b.ing_maiz.idxmax(),'anio']))
print('  soya: media $%.0f | min $%.0f (%d) | max $%.0f (%d)'%(b.ing_soya.mean(),b.ing_soya.min(),b.loc[b.ing_soya.idxmin(),'anio'],b.ing_soya.max(),b.loc[b.ing_soya.idxmax(),'anio']))
print('\n¿EL PRECIO COMPENSA LAS MALAS COSECHAS? (correlacion precio vs rendimiento estatal)')
s=t.groupby('anio')[['maiz_rend','soya_rend','precio_maiz','precio_soya']].mean()
for c in['maiz','soya']:
    r=stats.spearmanr(s[f'{c}_rend'],s[f'precio_{c}']); print('  %s: Spearman %.2f (p %.3f)'%(c,r.correlation,r.pvalue))
# quitando tendencia de ambos
for c in['maiz','soya']:
    ry=s[f'{c}_rend']-np.poly1d(np.polyfit(s.index,s[f'{c}_rend'],1))(s.index)
    rp=np.log(s[f'precio_{c}'])-np.poly1d(np.polyfit(s.index,np.log(s[f'precio_{c}']),1))(s.index)
    print('  %s sin tendencia: Spearman %.2f (p %.3f)'%(c,*stats.spearmanr(ry,rp)))
t.to_csv('ingreso_por_condado.csv',index=False)
