"""Análisis por condado (99 condados de Iowa, 2000-2025).
Une rendimientos NASS con humedad NLDAS-2 y calor (NASA POWER) y compara
regresiones de prueba con validación dejando un año fuera (LOYO) y dejando
un distrito agrícola fuera. Es exploratorio: sirve para elegir variables.

Paso 6. Entradas: datos/nldas_condados_iowa.csv (paso 4), datos/calor_condados_iowa.csv (paso 5),
datos/nass_quickstats_iowa_condados.csv, datos/condados_iowa_nombres.json.
Salidas: salidas/R4_analisis_condados.json, salidas/tabla_condados.csv (condado x año, rendimiento + clima)
Derecho de 2020: 23 condados de la declaración FEMA DR-4557 (asistencia pública).
Tarda unos 5 minutos (bootstrap y validaciones).
"""
import json
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

from comun import DATOS, NASS_CSV, SALIDAS

rng = np.random.default_rng(42)

# ---------- rendimientos ----------
q = pd.read_csv(NASS_CSV)
q = q[(q['Geo Level'] == 'COUNTY') & (q['County'] != 'OTHER COUNTIES (COMBINED)') & q['County ANSI'].notna()]
q['fips'] = 19000 + q['County ANSI'].astype(int)
q['val'] = pd.to_numeric(q['Value'].astype(str).str.replace(',', ''), errors='coerce')
items = {'CORN, GRAIN - YIELD, MEASURED IN BU / ACRE': 'maiz', 'SOYBEANS - YIELD, MEASURED IN BU / ACRE': 'soya'}
q = q[q['Data Item'].isin(items)].assign(cultivo=lambda d: d['Data Item'].map(items))
y = q.pivot_table(index=['fips', 'Year'], columns='cultivo', values='val').reset_index().rename(columns={'Year': 'year'})
dist = q.drop_duplicates('fips').set_index('fips')['Ag District Code'].astype(int)

# ---------- clima ----------
n = pd.read_csv(DATOS / 'nldas_condados_iowa.csv')
n['sm100'] = n.SoilM_0_100cm / 1000  # m3/m3
n['sm10'] = n.SoilM_0_10cm / 100
n['tair'] = n.Tair - 273.15
w = n.pivot_table(index=['fips', 'year'], columns='month', values=['sm100', 'sm10', 'Rainf', 'tair'])
w.columns = [f'{a}_{b}' for a, b in w.columns]
w = w.reset_index()
h = pd.read_csv(DATOS / 'calor_condados_iowa.csv')
d = y.merge(w, on=['fips', 'year']).merge(h[['fips', 'year', 'd30', 'd32', 'd35', 'tmax_jul']], on=['fips', 'year'])
d['lluvia_may_jun'] = d.Rainf_5 + d.Rainf_6
d['lluvia_jul_ago'] = d.Rainf_7 + d.Rainf_8
DERECHO = ['Benton', 'Boone', 'Cedar', 'Clinton', 'Dallas', 'Greene', 'Grundy', 'Guthrie', 'Hardin', 'Iowa', 'Jackson',
           'Jasper', 'Johnson', 'Jones', 'Linn', 'Marshall', 'Muscatine', 'Polk', 'Poweshiek', 'Scott', 'Story', 'Tama', 'Washington']
names = json.load(open(DATOS / 'condados_iowa_nombres.json', encoding='utf-8'))
der_fips = [int(f) for f, nm in names.items() if nm in DERECHO]
assert len(der_fips) == 23, len(der_fips)
d['derecho'] = ((d.year == 2020) & d.fips.isin(der_fips)).astype(int)
d['distrito'] = d.fips.map(dist)

# anomalías climáticas por condado (z por condado), quitan la diferencia geográfica de nivel
CLIM = ['sm100_6', 'sm100_7', 'sm100_8', 'sm10_5', 'lluvia_may_jun', 'lluvia_jul_ago', 'tair_7', 'd30', 'd32', 'd35', 'tmax_jul']
for c in CLIM:
    g = d.groupby('fips')[c]
    d[c + '_z'] = (d[c] - g.transform('mean')) / g.transform('std')

SETS = {
    'solo humedad jul-ago': ['sm100_7_z', 'sm100_8_z'],
    'humedad jun+jul+ago': ['sm100_6_z', 'sm100_7_z', 'sm100_8_z'],
    '+ calor': ['sm100_6_z', 'sm100_7_z', 'sm100_8_z', 'd32_z', 'tair_7_z'],
    '+ calor + lluvia primavera': ['sm100_6_z', 'sm100_7_z', 'sm100_8_z', 'd32_z', 'tair_7_z', 'lluvia_may_jun_z', 'sm10_5_z'],
    '+ calor + lluvia + derecho': ['sm100_6_z', 'sm100_7_z', 'sm100_8_z', 'd32_z', 'tair_7_z', 'lluvia_may_jun_z', 'sm10_5_z', 'derecho'],
}
FULL = SETS['+ calor + lluvia + derecho']


def anomalia(train, test, crop):
    """Tendencia lineal por condado ajustada SOLO con años de entrenamiento."""
    out_tr, out_te = [], []
    for f, gtr in train.groupby('fips'):
        gtr = gtr.dropna(subset=[crop])
        if len(gtr) < 8:
            continue
        b = np.polyfit(gtr.year, gtr[crop], 1)
        out_tr.append(pd.Series(100 * (gtr[crop] / np.polyval(b, gtr.year) - 1), index=gtr.index))
        gte = test[(test.fips == f)].dropna(subset=[crop])
        if len(gte):
            out_te.append(pd.Series(100 * (gte[crop] / np.polyval(b, gte.year) - 1), index=gte.index))
    return pd.concat(out_tr), (pd.concat(out_te) if out_te else pd.Series(dtype=float))


def make(kind):
    if kind == 'gb':
        return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_depth=3, min_samples_leaf=40, l2_regularization=1.0, random_state=0)
    return Ridge(alpha=1.0)


def cv(crop, feats, kind, group):
    """group='year' -> LOYO; group='distrito' -> deja un distrito agrícola fuera (detrend con todos los años)."""
    preds = pd.Series(dtype=float); trues = pd.Series(dtype=float)
    for g in sorted(d[group].unique()):
        tr, te = d[d[group] != g], d[d[group] == g]
        if group == 'year':
            ytr, yte = anomalia(tr, te, crop)
        else:
            ya, _ = anomalia(d, d.iloc[:0], crop)
            ytr, yte = ya[ya.index.isin(tr.index)], ya[ya.index.isin(te.index)]
        if not len(yte):
            continue
        X = tr.loc[ytr.index, feats]
        if kind == 'base':
            p = np.zeros(len(yte))
        else:
            m = make(kind).fit(X, ytr)
            p = m.predict(te.loc[yte.index, feats])
        preds = pd.concat([preds, pd.Series(p, index=yte.index)]); trues = pd.concat([trues, yte])
    return trues, preds


def metr(t, p):
    rmse = float(np.sqrt(np.mean((t - p) ** 2)))
    return rmse


R = {'n_obs': {}, 'cv': {}, 'spearman': {}, 'anios': {}, 'derecho': {}, 'importancia': {}}
for crop in ['maiz', 'soya']:
    ya, _ = anomalia(d, d.iloc[:0], crop)
    d[crop + '_anom'] = ya
    R['n_obs'][crop] = int(ya.notna().sum())

    # correlaciones agrupadas con IC bootstrap remuestreando AÑOS (los condados de un mismo año no son independientes)
    years = d.year.unique()
    sp = {}
    for c in [x + '_z' for x in CLIM]:
        sub = d[[c, crop + '_anom', 'year']].dropna()
        r0 = spearmanr(sub[c], sub[crop + '_anom']).statistic
        bs = []
        for _ in range(1000):
            yy = rng.choice(years, len(years), replace=True)
            s = pd.concat([sub[sub.year == k] for k in yy])
            bs.append(spearmanr(s[c], s[crop + '_anom']).statistic)
        sp[c] = [round(r0, 3), round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]
    R['spearman'][crop] = sp

    res = {}
    for grp in ['year', 'distrito']:
        t, p = cv(crop, FULL, 'base', grp)
        base = metr(t, p)
        res[f'{grp}|línea base (solo tendencia)'] = round(base, 2)
        for nm, fs in SETS.items():
            t, p = cv(crop, fs, 'ridge', grp)
            res[f'{grp}|lineal {nm}'] = round(metr(t, p), 2)
        t, p = cv(crop, FULL, 'gb', grp)
        res[f'{grp}|gradient boosting (todas)'] = round(metr(t, p), 2)
        if grp == 'year':
            keep = (t, p)
    R['cv'][crop] = res

    # errores por año del gradient boosting y de la lineal completa (LOYO)
    t, p = keep
    tl, pl = cv(crop, FULL, 'ridge', 'year')
    yr = d.loc[t.index, 'year']
    tab = pd.DataFrame({'real': t.groupby(yr).mean(), 'gb': p.groupby(yr).mean(), 'lineal': pl.groupby(yr).mean()}).round(1)
    R['anios'][crop] = tab.loc[[2012, 2013, 2020, 2021, 2023]].to_dict('index')
    R['anios'][crop + '_corr_anual'] = {'gb': round(float(np.corrcoef(tab.real, tab.gb)[0, 1]), 3), 'lineal': round(float(np.corrcoef(tab.real, tab.lineal)[0, 1]), 3)}

    # derecho: anomalía real 2020 en condados afectados vs resto
    z = d[d.year == 2020]
    R['derecho'][crop] = {'afectados': round(float(z[z.derecho == 1][crop + '_anom'].mean()), 1),
                          'resto': round(float(z[z.derecho == 0][crop + '_anom'].mean()), 1)}

    # importancia por permutación del gradient boosting ajustado con todos los datos
    sub = d.dropna(subset=[crop + '_anom'])
    m = make('gb').fit(sub[FULL], sub[crop + '_anom'])
    pi = permutation_importance(m, sub[FULL], sub[crop + '_anom'], n_repeats=10, random_state=0, scoring='neg_root_mean_squared_error')
    R['importancia'][crop] = dict(sorted({f: round(float(v), 2) for f, v in zip(FULL, pi.importances_mean)}.items(), key=lambda kv: -kv[1]))

d.to_csv(SALIDAS / 'tabla_condados.csv', index=False)
json.dump(R, open(SALIDAS / 'R4_analisis_condados.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(R, ensure_ascii=False, indent=1))
