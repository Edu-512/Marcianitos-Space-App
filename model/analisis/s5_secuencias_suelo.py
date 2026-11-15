import numpy as np,pandas as pd
from scipy import ndimage
S=np.load('cdl_stack.npy'); pat=np.load('patron.npy'); z=np.load('rejilla.npz'); ac=900/4046.86
M=S==1; So=S==5
# años consecutivos de maiz que lleva cada pixel de maiz (1 = primer año tras soya)
run=np.zeros(S.shape,np.uint8)
for i in range(S.shape[0]): run[i]=np.where(M[i],(run[i-1] if i>0 else 0)+1,0)
print('MAIZ de 2022-2025 segun cuantos años seguidos lleva (solo pixeles con historial conocido):')
r=[]
for i in range(4,8):
    m=M[i]; prev_s=So[i-1]; 
    d={'anio':2018+i,'1er año (tras soya)':(m&prev_s).sum(),'2o año':(m&(run[i]==2)&So[i-2]).sum(),'3er año':(m&(run[i]==3)&So[i-3]).sum(),'4+ años':(m&(run[i]>=4)).sum()}
    t=sum(v for k,v in d.items() if k!='anio'); r.append({k:(v if k=='anio' else round(100*v/t,1)) for k,v in d.items()})
print(pd.DataFrame(r).to_string(index=False))
# tras cuantos años de maiz se vuelve a soya
print('\nSOYA de 2022-2025: cuantos años de maiz hubo justo antes'); r=[]
for i in range(4,8):
    s=So[i]; d={1:(s&(run[i-1]==1)).sum(),2:(s&(run[i-1]==2)).sum(),3:(s&(run[i-1]>=3)).sum(),'soya':(s&So[i-1]).sum()}; t=sum(d.values()); r.append({'anio':2018+i,'1 año de maiz':round(100*d[1]/t,1),'2 años':round(100*d[2]/t,1),'3+ años':round(100*d[3]/t,1),'soya':round(100*d['soya']/t,1)})
print(pd.DataFrame(r).to_string(index=False))
# patron vs suelo
nom={1:'rotacion estricta',3:'maiz 6+ de 8',4:'irregular / con quiebres'}; p2=np.where(pat==2,4,pat); out=[]
for k,n in nom.items():
    m=p2==k; out.append({'patron':n,'acres':round(m.sum()*ac),'csr2':np.nanmean(z['csr2_iowa'][m]),'arena':np.nanmean(z['arena_pct'][m]),'agua_150':np.nanmean(z['agua_disp_0_150cm'][m]),'pendiente':np.nanmean(z['pendiente_pct'][m]),'%arenoso':100*np.nanmean(z['arena_pct'][m]>50),'%csr2>=80':100*np.nanmean(z['csr2_iowa'][m]>=80)})
m8=M.sum(0)==8; out.append({'patron':'maiz los 8 años','acres':round(m8.sum()*ac),'csr2':np.nanmean(z['csr2_iowa'][m8]),'arena':np.nanmean(z['arena_pct'][m8]),'agua_150':np.nanmean(z['agua_disp_0_150cm'][m8]),'pendiente':np.nanmean(z['pendiente_pct'][m8]),'%arenoso':100*np.nanmean(z['arena_pct'][m8]>50),'%csr2>=80':100*np.nanmean(z['csr2_iowa'][m8]>=80)})
print('\nSUELO POR PATRON DE 8 AÑOS'); print(pd.DataFrame(out).round(1).to_string(index=False))
base=(p2>0); print('\n% de maiz dominante (6+ de 8) por clase de suelo:')
for c,b in[('csr2_iowa',[0,40,60,75,85,101]),('arena_pct',[0,15,30,50,70,101])]:
    t=pd.DataFrame({'b':pd.cut(z[c][base],b),'d':(p2==3)[base],'e':(p2==1)[base]}).groupby('b',observed=True).agg(maiz_dom=('d','mean'),estricta=('e','mean'),n=('d','size')); print(c); print((t.assign(maiz_dom=100*t.maiz_dom,estricta=100*t.estricta,acres=t.n*ac)[['maiz_dom','estricta','acres']]).round(1).to_string())
# grupos listos para la prueba NDVI (interior de campo, 3x3)
G={}
for i in range(1,8):
    im=ndimage.minimum_filter((M[i]&M[i-1]).astype(np.uint8),3)==1; isy=ndimage.minimum_filter((M[i]&So[i-1]).astype(np.uint8),3)==1; G[2018+i]=(im.sum()*ac,isy.sum()*ac)
print('\nGrupos para la prueba NDVI (acres en interior de campo): año: maiz tras maiz | maiz tras soya'); print({k:(round(a),round(b)) for k,(a,b) in G.items()})
