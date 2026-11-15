import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import csv,collections
# Tablas de SSURGO (IA023) convertidas a CSV con encabezados del esquema oficial; ver PROCEDENCIA.md
T={n:list(csv.DictReader(open(f'datos/{n}.csv',encoding='utf-8'))) for n in ['mapunit','muaggatt','component','chorizon']}
f=lambda v:float(v) if v not in('',None) else None
hz=collections.defaultdict(list)
for h in T['chorizon']: hz[h['cokey']].append(h)
comps=collections.defaultdict(list)
for c in T['component']: comps[c['mukey']].append(c)
V={'om_pct':'om_r','awc_cm_cm':'awc_r','arena_pct':'sandtotal_r','limo_pct':'silttotal_r','arcilla_pct':'claytotal_r','ph':'ph1to1h2o_r'}
def comp_val(co,col):
    s=w=0
    for h in hz[co]:
        t,b,v=f(h['hzdept_r']),f(h['hzdepb_r']),f(h[col])
        if None in(t,b,v): continue
        th=min(b,30)-max(t,0)
        if th>0: s+=v*th; w+=th
    return s/w if w else None
agg={m['mukey']:m for m in T['muaggatt']}
rows=[]
for m in T['mapunit']:
    k=m['mukey']; a=agg[k]; cs=comps[k]
    r={'mukey':k,'musym':m['musym'],'nombre':m['muname'],'acres_condado':m['muacres'],'clase_tierra':m['farmlndcl'],'csr2_iowa':m['iacornsr'],
       'pendiente_pct':a['slopegradwta'],'drenaje':a['drclassdcd'],'grupo_hidrologico':a['hydgrpdcd'],'agua_disp_0_150cm':a['aws0150wta'],'frec_inundacion':a['flodfreqdcd']}
    for n,col in V.items():
        s=w=0
        for c in cs:
            p=f(c['comppct_r']); v=comp_val(c['cokey'],col)
            if p and v is not None: s+=v*p; w+=p
        r[n]=round(s/w,2) if w else ''
    dom=max(cs,key=lambda c:f(c['comppct_r']) or 0) if cs else None
    r['factor_t']=dom['tfact'] if dom else ''
    kw=''
    if dom:
        hs=sorted([h for h in hz[dom['cokey']] if f(h['hzdept_r']) is not None],key=lambda h:f(h['hzdept_r']))
        for h in hs:
            if h['kwfact']!='': kw=h['kwfact']; break
    r['factor_k']=kw
    rows.append(r)
w=csv.DictWriter(open('datos/ssurgo_butler_por_suelo.csv','w',newline='',encoding='utf-8'),fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    if r['musym'] in('41B','84','27B','621','221B','W','135'): print({k:r[k] for k in['musym','om_pct','awc_cm_cm','arena_pct','arcilla_pct','ph','factor_k','factor_t','drenaje','grupo_hidrologico','csr2_iowa']})
print(len(rows))
for n in list(V)+['drenaje','grupo_hidrologico','factor_k','pendiente_pct','agua_disp_0_150cm','csr2_iowa']:
    print(n,'vacios:',sum(1 for r in rows if r[n]==''))
