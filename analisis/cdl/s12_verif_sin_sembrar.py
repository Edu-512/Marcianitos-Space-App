import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import numpy as np,pandas as pd,statsmodels.api as sm
S=np.load('cdl_stack.npy'); z=np.load('rejilla.npz'); ac=900/4046.86
def caso(i):
    F=S[i]==61; agri=(S[i-1]==1)|(S[i-1]==5); desp=(S[i+1]==1)|(S[i+1]==5)
    return F&agri&desp, agri&desp&np.isfinite(z['arena_pct'])
for i,y in [(1,2019),(6,2024)]:
    pp,base=caso(i)
    inu=z['inund_siembra']; a=base&(inu>=50); b=base&(inu<1)
    print('%d: sin sembrar %.0f acres | inundables %.2f%% vs no inundables %.2f%% (%.1fx)'%(y,pp.sum()*ac,100*(pp&a).sum()/max(a.sum(),1),100*(pp&b).sum()/max(b.sum(),1),((pp&a).sum()/max(a.sum(),1))/max((pp&b).sum()/max(b.sum(),1),1e-12)))
pp,base=caso(1)
d=pd.DataFrame({'y':pp[base].astype(int),'inund':(z['inund_siembra'][base]>=50).astype(int),'arena':(z['arena_pct'][base]>50).astype(int),'maldren':0,'pend':z['pendiente_pct'][base]}).dropna()
X=sm.add_constant(d[['inund','arena','pend']]); m=sm.Logit(d.y,X).fit(disp=0)
print('\n2019, modelo logistico (odds ratio):')
print((np.exp(m.params)).round(2).to_string()); print('p:',m.pvalues.round(4).to_dict())
print('\nambos efectos siguen al controlarse mutuamente' if (m.pvalues[['inund','arena']]<0.05).all() else 'uno pierde significancia')
