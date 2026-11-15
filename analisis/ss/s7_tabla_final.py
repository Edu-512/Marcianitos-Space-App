import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
"""Paso final: arma la tabla de 22 variables por tipo de suelo que usa el modelo.

RECONSTRUIDO: ningún script original guardaba este archivo. Se reconstruyó comparando
`modelo/entradas/ssurgo_butler_variables_modelo.csv` con `datos/ssurgo_butler_por_suelo.csv`:
las 17 columnas comunes coinciden al 100 % (con "None" traducido a "Ninguna"), y las otras 5
(acres_mapa, inund_siembra, enchar_siembra, prof_capa_cm, pct_con_capa_restr) las agregan s2 y s3.
No se pudo correr sin el mapa de suelos; la primera vez, comparar la salida con la del modelo.

Entrada: suelo_con_area.csv (salida de s3). Salida: ssurgo_butler_variables_modelo.csv (aquí, no en modelo/).
"""
import pandas as pd

COLS = ['mukey', 'musym', 'nombre', 'acres_mapa', 'clase_tierra', 'drenaje', 'grupo_hidrologico', 'pendiente_pct',
        'om_pct', 'awc_cm_cm', 'agua_disp_0_150cm', 'arena_pct', 'limo_pct', 'arcilla_pct', 'ph', 'factor_k',
        'factor_t', 'frec_inundacion', 'inund_siembra', 'enchar_siembra', 'prof_capa_cm', 'pct_con_capa_restr', 'csr2_iowa']
s = pd.read_csv('suelo_con_area.csv', dtype={'mukey': str}, keep_default_na=False, na_values=[''])
s['frec_inundacion'] = s.frec_inundacion.replace({'None': 'Ninguna'})
s[COLS].to_csv('ssurgo_butler_variables_modelo.csv', index=False)

ref = pd.read_csv('../../modelo/entradas/ssurgo_butler_variables_modelo.csv', dtype={'mukey': str})
nuevo = pd.read_csv('ssurgo_butler_variables_modelo.csv', dtype={'mukey': str})
print('igual a la tabla del modelo:', nuevo.round(2).equals(ref.round(2)))
