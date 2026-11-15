import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
# Antes se llamaba genera_variables_modelo.py. Lee la tabla final de suelos y calcula la erosión potencial RUSLE.
import numpy as np,pandas as pd
s=pd.read_csv('../../modelo/entradas/ssurgo_butler_variables_modelo.csv',dtype={'mukey':str})
s=s[s.csr2_iowa.notna()&s.factor_k.notna()&s.pendiente_pct.notna()].copy()
lam=200.0  # longitud de pendiente supuesta, pies (tipica en Iowa)
th=np.arctan(s.pendiente_pct/100.0)
m=np.select([s.pendiente_pct<1,s.pendiente_pct<3,s.pendiente_pct<5],[0.2,0.3,0.4],0.5)
s['LS']=(lam/72.6)**m*(65.41*np.sin(th)**2+4.56*np.sin(th)+0.065)
R=150.0  # erosividad de la lluvia, Iowa centro-norte
s['erosion_base']=R*s.factor_k*s.LS      # ton/acre/año antes del factor de cobertura
s['veces_sobre_T']=s.erosion_base/s.factor_t
A=s.acres_mapa; w=lambda c:np.average(s[c],weights=A)
print('EROSION POTENCIAL POR PARCELA (R x K x LS, sin factor de cobertura)')
print('  promedio ponderado por area: %.1f ton/acre/año | mediana %.1f | p90 %.1f | max %.1f'%(w('erosion_base'),s.erosion_base.median(),s.erosion_base.quantile(.9),s.erosion_base.max()))
print('  factor T promedio: %.1f ton/acre/año'%w('factor_t'))
q=pd.qcut(s.erosion_base,4,labels=['Q1 baja','Q2','Q3','Q4 alta'])
print(s.groupby(q,observed=True).apply(lambda d:pd.Series({'erosion':np.average(d.erosion_base,weights=d.acres_mapa),'pendiente':np.average(d.pendiente_pct,weights=d.acres_mapa),'factor_k':np.average(d.factor_k,weights=d.acres_mapa),'acres':d.acres_mapa.sum(),'pct_area':100*d.acres_mapa.sum()/A.sum()}),include_groups=False).round(1).to_string())
print('\nCon factores de cobertura de la literatura (C), la erosion de cada plan es erosion_base x C:')
for n,C in [('maiz continuo',0.24),('maiz-soya alternado',0.30),('maiz-soya + cultivo de cobertura',0.12)]:
    e=s.erosion_base*C; print('  %-34s promedio %.1f ton/acre/año | %% del area arriba de su factor T: %.0f%%'%(n,np.average(e,weights=A),100*A[(e>s.factor_t)].sum()/A.sum()))
print('\n(Los valores de C son de la literatura y deben citarse; R=150 y longitud de pendiente=200 pies son supuestos declarados.)')
s[['mukey','musym','nombre','acres_mapa','pendiente_pct','factor_k','factor_t','LS','erosion_base','veces_sobre_T']].round(3).to_csv('erosion_por_suelo.csv',index=False)
