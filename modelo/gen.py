import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import numpy as np,pandas as pd,json
from scipy import stats
# --- insumos ya calculados en el analisis ---
a=pd.read_csv('entradas/anomalias.csv'); t=pd.read_csv('entradas/quickstats_iowa_limpio.csv')
import sys
dem=pd.read_csv('entradas/parcelas_candidatas.csv') if '--todas' in sys.argv else pd.read_csv('entradas/parcelas_demo.csv')
suelo=pd.read_csv('entradas/ssurgo_butler_variables_modelo.csv')
if 'perfil' not in dem.columns: dem['perfil']=dem.patron
b=t[t.condado=='BUTLER']
# rendimiento esperado 2026 por tendencia del condado
esp={c:float(np.polyval(np.polyfit(b.dropna(subset=[c]).anio,b.dropna(subset=[c])[c],1),2026)) for c in['maiz_rend','soya_rend']}
# escenarios: clasificar los 26 años por la anomalia estatal del maiz
# escenarios definidos por el CLIMA medido (NASA POWER), no por el rendimiento
CLI=pd.read_csv('entradas/clima_butler_por_anio.csv').set_index('anio')
esc={e:sorted(CLI[CLI.escenario==e].index) for e in ['seco_caluroso','humedo_primavera','normal']}
IND=CLI.groupby('escenario')[['humedad_agosto_pct','dias_mayor_35','lluvia_mayo_junio_pct','temp_julio_c']].mean().round(1)
def dist(cultivo,anios):
    v=a[(a.cultivo==cultivo)&(a.anio.isin(anios))].anom_pct
    return {'p10':round(v.quantile(.1),1),'p50':round(v.median(),1),'p90':round(v.quantile(.9),1),'prob_caida_20':round(100*(v<-20).mean(),1)}
PREC={'maiz':4.10,'soya':10.50}
COSTO={'maiz_tras_soya':875,'maiz_tras_maiz':960,'soya_tras_maiz':680}
NITRO={'maiz_tras_soya':124,'maiz_tras_maiz':181}
PENAL={'seco_caluroso':-0.20,'humedo_primavera':-0.18,'normal':-0.06}   # literatura ISU: ~0 en buenos, hasta 27% en malos
C_EROS={'maiz_soya':0.30,'maiz_continuo':0.24,'maiz_soya_cobertura':0.12}
def erosion(r):
    th=np.arctan(r['pend']/100); m=0.2 if r['pend']<1 else 0.3 if r['pend']<3 else 0.4 if r['pend']<5 else 0.5
    LS=(200/72.6)**m*(65.41*np.sin(th)**2+4.56*np.sin(th)+0.065)
    k=float(suelo.factor_k.median())
    return 150*k*LS
MS=json.load(open('entradas/modelo_suelo.json',encoding='utf-8'))
def ajuste_suelo(r):
    """Indice de suelo con variables disponibles en todo EE.UU. (arena, agua disponible 0-150cm, pendiente).
    Validado contra el indice experto de Iowa (Spearman 0.68) y contra vigor medido por satelite (0.22 y 0.13).
    Magnitud anclada a los tres niveles de rendimiento que usa ISU en sus presupuestos (+-10%)."""
    v=MS['coef'][0]*r['arena']+MS['coef'][1]*r['agua150']+MS['coef'][2]*r['pend']+MS['intercept']
    aj=(v/MS['base']-1)*MS['escala']
    return round(float(min(max(aj,-MS['limite']/100),MS['limite']/100)),4)
planes=[('maiz_soya','Maíz y soya alternados'),('maiz_continuo','Maíz todos los años'),('maiz_soya_cobertura','Maíz y soya con cultivo de cobertura')]
salida=[]
for _,r in dem.iterrows():
    aj=ajuste_suelo(r); ero=erosion(r)
    p_obj={'parcela':{'id':int(r['id']),'perfil':r['perfil'],'acres':round(r['acres']),'rotacion_actual':r['patron'],
            'suelo':{'productividad_csr2':round(r['csr2'],1),'arena_pct':round(r['arena'],1),'agua_disponible_cm':round(r['agua150'],1),
                     'pendiente_pct':round(r['pend'],1),'materia_organica_pct':round(r['om'],1),'riesgo_inundacion_siembra_pct':round(r['inund'],1)},
            'ajuste_por_suelo_pct':round(aj*100,1)},'escenarios':{}}
    for e,anios in esc.items():
        dm,ds=dist('maiz',anios),dist('soya',anios)
        lst=[]
        for pid,nom in planes:
            cont = pid=='maiz_continuo'
            pen = PENAL[e] if cont else 0.0
            ry={k:round(esp['maiz_rend']*(1+v/100)*(1+aj)*(1+pen),1) for k,v in dm.items() if k!='prob_caida_20'}
            costo=COSTO['maiz_tras_maiz'] if cont else (COSTO['maiz_tras_soya']+COSTO['soya_tras_maiz'])/2
            if cont: ing={k:round(v*PREC['maiz']) for k,v in ry.items()}
            else:
                rs={k:round(esp['soya_rend']*(1+v/100)*(1+aj),1) for k,v in ds.items() if k!='prob_caida_20'}
                ing={k:round((ry[k]*PREC['maiz']+rs[k]*PREC['soya'])/2) for k in ry}
            lst.append({'id':pid,'nombre':nom,
                'rendimiento_maiz_bu_acre':ry,
                'economia':{'ingreso_usd_acre':ing,'costo_usd_acre':round(costo),'margen_usd_acre':{k:round(v-costo) for k,v in ing.items()}},
                'suelo':{'erosion_ton_acre_anio':round(ero*C_EROS[pid],1),'arriba_del_limite':bool(ero*C_EROS[pid]>float(suelo.factor_t.median()))},
                'riesgo':{'prob_caida_mayor_20_pct':dm['prob_caida_20'],'prob_no_poder_sembrar_pct':round(0.58+1.4*(r['inund']>=50),2)},
                'fertilizante':{'nitrogeno_lb_acre':NITRO['maiz_tras_maiz'] if cont else NITRO['maiz_tras_soya']},
                'confianza':'media' if cont else 'alta'})
        ci=IND.loc[e]
        p_obj['escenarios'][e]={'anios_historicos':sorted(anios),'n_anios':len(anios),
            'clima':{'humedad_raices_agosto_percentil':float(ci.humedad_agosto_pct),'dias_arriba_35c':float(ci.dias_mayor_35),
                     'lluvia_mayo_junio_percentil':float(ci.lluvia_mayo_junio_pct),'temperatura_julio_c':float(ci.temp_julio_c),
                     'fuente':'NASA POWER (MERRA-2), punto 42.73N 92.79W, 2000-2025'},
            'planes':lst}
    salida.append(p_obj)
doc={'version':'1.0','zona':'Butler County, Iowa (IA023)','moneda':'USD','parcelas':salida,
 'fuentes':{'rendimiento_y_precios':'USDA NASS QuickStats, 2000-2025','suelo':'USDA NRCS SSURGO IA023 v33 (2026-09-08)',
  'rotacion':'USDA NASS Cropland Data Layer 2018-2025','clima':'NASA POWER (MERRA-2) diario 2000-2025, Butler County',
  'penalizacion_rotacion':'Iowa State University Extension (literatura, no medido por nosotros)',
  'costos':'ISU Estimated Costs of Crop Production in Iowa 2026 (incluyen renta de la tierra)',
  'nitrogeno':'ISU Corn Nitrogen Rate Calculator'},
 'advertencias':['La penalizacion del maiz continuo viene de la literatura, no de nuestros datos.',
  'Los rangos p10-p90 estan calibrados: un rango de 80% cubrio el 80% de los casos historicos.',
  'Los costos incluyen renta de la tierra; un agricultor dueño tiene margenes mayores.',
  'Los escenarios se definen por el clima medido, no por el rendimiento.','El ajuste por suelo usa solo variables disponibles en todo EE.UU. y esta validado en un solo condado.']}
json.dump(doc,open('salidas/resultado_todas.json' if '--todas' in sys.argv else 'salidas/resultado_ejemplo.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
x=salida[0]['escenarios']['normal']['planes']
print('EJEMPLO: parcela %d (%s), escenario normal'%(salida[0]['parcela']['id'],salida[0]['parcela']['perfil']))
print(pd.DataFrame([{'plan':p['nombre'],'maiz_p50':p['rendimiento_maiz_bu_acre']['p50'],'margen_p50':p['economia']['margen_usd_acre']['p50'],'margen_p10':p['economia']['margen_usd_acre']['p10'],'erosion':p['suelo']['erosion_ton_acio' if False else 'erosion_ton_acre_anio'],'N_lb':p['fertilizante']['nitrogeno_lb_acre']} for p in x]).to_string(index=False))
y=salida[0]['escenarios']['seco_caluroso']['planes']
print('\nmismo lugar, escenario seco y caluroso:')
print(pd.DataFrame([{'plan':p['nombre'],'maiz_p50':p['rendimiento_maiz_bu_acre']['p50'],'margen_p50':p['economia']['margen_usd_acre']['p50'],'margen_p10':p['economia']['margen_usd_acre']['p10']} for p in y]).to_string(index=False))
print('\narchivo: %s (%d parcelas x 3 escenarios x 3 planes)'%('resultado_todas.json' if '--todas' in sys.argv else 'resultado_ejemplo.json',len(salida)))
