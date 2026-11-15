import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import csv,collections,sys
U='datos/tabular/'
rd=lambda f:[r for r in csv.reader(open(U+f,encoding='utf-8',errors='replace'),delimiter='|') if r]
mu=rd('mucrpyd.txt'); co=rd('ccrpyd.txt'); rs=rd('crstrcts.txt'); cm=rd('cmonth.txt')
for n,t in[('mucrpyd',mu),('ccrpyd',co),('crstrcts',rs),('cmonth',cm)]: print(n,len(t),'filas, campos',set(map(len,t)))
print('mucrpyd: unidades de mapa distintas',len(set(r[-2] for r in mu)),'| cultivos',collections.Counter(r[0] for r in mu))
print('ccrpyd: componentes distintos',len(set(r[-2] for r in co)),'| con valor',sum(1 for r in co if r[3]!=''))
print('crstrcts: componentes',len(set(r[-2] for r in rs)),collections.Counter(r[0] for r in rs))
print('cmonth ejemplo',cm[0]); print(cm[5])
print('componentes',len(set(r[-2] for r in cm)))
for i in range(len(cm[0])-2):
    c=collections.Counter(r[i] for r in cm)
    print(i,len(c),c.most_common(6))
