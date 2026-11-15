import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import pandas as pd,sys
d=pd.read_csv(sys.argv[1] if len(sys.argv)>1 else 'datos/quickstats_iowa_crudo.csv',dtype=str)
print(d.shape); print(list(d.columns))
print(d.head(3).T.to_string())
for c in['Program','Period','Geo Level','State','Commodity','Data Item','Domain','Ag District']:
    print('\n',c,d[c].nunique()); print(d[c].value_counts().head(12).to_string())
print(d['Year'].min(),d['Year'].max(),d['County'].nunique())
print(d['Value'].str.contains(r'[^0-9.,]',na=True).sum(),'valores no numericos'); print(d[d['Value'].str.contains(r'[^0-9.,]',na=True)]['Value'].value_counts().head())
print(d['CV (%)'].value_counts().head())
