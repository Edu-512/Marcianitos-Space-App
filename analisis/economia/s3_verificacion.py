import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,numpy as np
from scipy import stats
t=pd.read_csv('ingreso_por_condado.csv'); b=t[t.condado=='BUTLER'].sort_values('anio')
print('VERIFICACION 1: ingreso bruto crudo de Butler, sin quitar tendencia (USD/acre)')
print(b[['anio','maiz_rend','precio_maiz','ing_maiz']].assign(ing_maiz=lambda d:d.ing_maiz.round(0)).to_string(index=False))
print('\n  media del periodo: $%.0f | 2012: $%.0f (%+.0f%% vs media) aunque el rendimiento cayo %.0f%%'%(b.ing_maiz.mean(),b.loc[b.anio==2012,'ing_maiz'].iloc[0],100*(b.loc[b.anio==2012,'ing_maiz'].iloc[0]/b.ing_maiz.mean()-1),100*(122.0/183.6-1)))
print('\nVERIFICACION 2: comparar contra promedio movil de 5 años centrado (sin suponer tendencia lineal)')
s=t.groupby('anio')[['maiz_rend','ing_maiz','precio_maiz']].mean()
for c in['maiz_rend','ing_maiz']:
    mm=s[c].rolling(5,center=True,min_periods=3).mean(); an=100*(s[c]/mm-1)
    print('  %s: desviacion %.1f%% | peores: %s'%(c,an.std(),dict(an.nsmallest(3).round(0))))
mm_r=100*(s.maiz_rend/s.maiz_rend.rolling(5,center=True,min_periods=3).mean()-1); mm_i=100*(s.ing_maiz/s.ing_maiz.rolling(5,center=True,min_periods=3).mean()-1)
print('  2012 con este metodo: rendimiento %+.0f%% | ingreso %+.0f%%'%(mm_r[2012],mm_i[2012]))
print('  correlacion rendimiento-ingreso (anual): %.2f'%mm_r.corr(mm_i))
print('\nVERIFICACION 3: precio vs rendimiento, tres metodos')
yl=s.maiz_rend; pr=s.precio_maiz
print('  crudo Spearman %.2f | ambos vs media movil 5a: %.2f | primeras diferencias: %.2f'%(stats.spearmanr(yl,pr).correlation,stats.spearmanr(mm_r.dropna(),(100*(pr/pr.rolling(5,center=True,min_periods=3).mean()-1)).dropna()).correlation,stats.spearmanr(yl.diff().dropna(),pr.diff().dropna()).correlation))
print('\nVERIFICACION 4: ¿los precios de maiz y soya se mueven juntos?')
p=pd.read_csv('precios_iowa.csv')
print('  Spearman precios %.2f | en primeras diferencias %.2f'%(stats.spearmanr(p.precio_maiz,p.precio_soya).correlation,stats.spearmanr(p.precio_maiz.diff().dropna(),p.precio_soya.diff().dropna()).correlation))
