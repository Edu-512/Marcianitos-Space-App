import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import numpy as np,pandas as pd
from scipy import ndimage
S=np.load('cdl_stack.npy'); z=np.load('rejilla.npz'); pat=np.load('patron.npy'); ac=900/4046.86
pp=np.load('sin_sembrar_2019.npy')
# "parcelas": grupos conexos con el mismo patron de 8 años
lab,n=ndimage.label(pat>0,structure=np.ones((3,3)))
print('componentes conexos:',n)
sz=np.bincount(lab.ravel()); grandes=np.where(sz*ac>=40)[0]; grandes=grandes[grandes>0]
print('con 40 acres o mas:',len(grandes))
rows=[]
for i in grandes:
    m=lab==i; p=np.bincount(pat[m],minlength=6)
    if p.max()/m.sum()<0.8: continue   # patron homogeneo
    k=p.argmax()
    rows.append({'id':int(i),'acres':m.sum()*ac,'patron':k,'csr2':np.nanmean(z['csr2_iowa'][m]),'arena':np.nanmean(z['arena_pct'][m]),'agua150':np.nanmean(z['agua_disp_0_150cm'][m]),'pend':np.nanmean(z['pendiente_pct'][m]),'inund':np.nanmean(z['inund_siembra'][m]),'om':np.nanmean(z['om_pct'][m]),'pct_sin_sembrar19':100*pp[m].mean()})
d=pd.DataFrame(rows).dropna(); nom={1:'rotacion estricta',2:'rotacion con quiebre',3:'maiz dominante',4:'irregular',5:'soya dominante'}
d['patron']=d.patron.map(nom)
print('parcelas homogeneas de 40+ acres:',len(d))
print(d.groupby('patron').agg(n=('id','size'),acres=('acres','mean'),csr2=('csr2','mean')).round(1).to_string())
print('\nCANDIDATAS PARA LA DEMO (perfiles contrastantes)')
sel={}
sel['Buen suelo, rotacion clasica']=d[(d.patron=='rotacion estricta')&(d.csr2>=85)&(d.arena<25)&(d.inund<2)].nlargest(1,'acres')
sel['Suelo arenoso, poca agua']=d[(d.arena>=55)&(d.agua150<18)].nlargest(1,'acres')
sel['Maiz dominante, buen suelo']=d[(d.patron=='maiz dominante')&(d.csr2>=85)].nlargest(1,'acres')
sel['Propensa a no poder sembrarse']=d[(d.inund>=50)|(d.pct_sin_sembrar19>5)].nlargest(1,'acres')
sel['Pendiente fuerte, erosion']=d[d.pend>=6].nlargest(1,'acres')
out=[]
for k,v in sel.items():
    if len(v): r=v.iloc[0].to_dict(); r['perfil']=k; out.append(r)
o=pd.DataFrame(out)[['perfil','id','acres','patron','csr2','arena','agua150','pend','inund','om','pct_sin_sembrar19']]
print(o.round(1).to_string(index=False))
d.round(2).to_csv('parcelas_candidatas.csv',index=False); o.round(2).to_csv('parcelas_demo.csv',index=False)
