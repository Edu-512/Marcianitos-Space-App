"""Paso 7: pruebas extra dejando un año fuera.

Agrega lluvia de julio-agosto y días > 35 °C, entrena sin los condados del derecho de 2020
y guarda el promedio anual real contra la prueba (la serie de la gráfica del documento).
Aviso: esta combinación se eligió viendo resultados, así que su error es algo optimista.
Entrada: salidas/tabla_condados.csv (paso 6). Salidas: salidas/R4b_pruebas_extra.json, maiz_anual_real_vs_prueba.csv
"""
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from comun import SALIDAS
d = pd.read_csv(SALIDAS / 'tabla_condados.csv')
def anomalia(train, test, crop):
    tr, te = [], []
    for f, g in train.groupby('fips'):
        g = g.dropna(subset=[crop])
        if len(g) < 8: continue
        b = np.polyfit(g.year, g[crop], 1)
        tr.append(100*(g[crop]/np.polyval(b, g.year)-1))
        t = test[test.fips == f].dropna(subset=[crop])
        if len(t): te.append(100*(t[crop]/np.polyval(b, t.year)-1))
    return pd.concat(tr), (pd.concat(te) if te else pd.Series(dtype=float))
base = ['sm100_6_z','sm100_7_z','sm100_8_z','d32_z','tair_7_z','lluvia_may_jun_z','sm10_5_z']
S = {'mejor anterior': base, '+ lluvia jul-ago': base+['lluvia_jul_ago_z'], 'humedad jul-ago + lluvia jul-ago': ['sm100_7_z','sm100_8_z','lluvia_jul_ago_z'],
     '+ lluvia jul-ago + días>35': base+['lluvia_jul_ago_z','d35_z']}
out = {}
for crop in ['maiz','soya']:
    for nm, fs in S.items():
        T, P, Dm = [], [], []
        for yv in sorted(d.year.unique()):
            tr, te = d[(d.year != yv) & (d.derecho == 0)], d[d.year == yv]
            ytr, yte = anomalia(tr, te, crop)
            m = Ridge(alpha=1.0).fit(tr.loc[ytr.index, fs], ytr)
            T.append(yte); P.append(pd.Series(m.predict(te.loc[yte.index, fs]), index=yte.index))
        T, P = pd.concat(T), pd.concat(P); der = d.loc[T.index, 'derecho'] == 1
        r = lambda a, b: round(float(np.sqrt(np.mean((a-b)**2))), 2)
        yr = d.loc[T.index,'year']
        out[f'{crop}|{nm}'] = {'rmse_todo': r(T, P), 'rmse_sin_derecho': r(T[~der], P[~der]), 'base_sin_derecho': r(T[~der], 0*T[~der]),
                               '2012_pred': round(float(P[yr==2012].mean()),1), 'corr_anual': round(float(np.corrcoef(T.groupby(yr).mean(), P.groupby(yr).mean())[0,1]),3)}
json.dump(out, open(SALIDAS / 'R4b_pruebas_extra.json','w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in out.items(): print(k, v)

# serie anual de la gráfica: maíz, todas las variables + días > 35 °C, sin condados del derecho
fs = base + ['lluvia_jul_ago_z', 'd35_z']
T, P = [], []
for yv in sorted(d.year.unique()):
    tr, te = d[(d.year != yv) & (d.derecho == 0)], d[d.year == yv]
    ytr, yte = anomalia(tr, te, 'maiz')
    m = Ridge(alpha=1.0).fit(tr.loc[ytr.index, fs], ytr)
    T.append(yte); P.append(pd.Series(m.predict(te.loc[yte.index, fs]), index=yte.index))
T, P = pd.concat(T), pd.concat(P); yr = d.loc[T.index, 'year']
pd.DataFrame({'real': T.groupby(yr).mean().round(1), 'prueba': P.groupby(yr).mean().round(1)}).to_csv(SALIDAS / 'maiz_anual_real_vs_prueba.csv')
