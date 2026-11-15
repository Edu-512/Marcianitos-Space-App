import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # rutas relativas a esta carpeta
import geopandas as gpd,pandas as pd,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
g=gpd.read_file('datos/shp/soilmu.shp'); s=pd.read_csv('suelo_con_area.csv',dtype={'mukey':str})
g=g.merge(s[['mukey','agua_disp_0_150cm','arena_pct']],left_on='MUKEY',right_on='mukey',how='left').to_crs(26915)
fig,ax=plt.subplots(1,2,figsize=(13,5.6))
for a,c,t,cm in[(ax[0],'agua_disp_0_150cm','Agua que guarda el suelo (cm, hasta 150 cm de profundidad)','YlGnBu'),(ax[1],'arena_pct','Arena en la capa superficial (%)','YlOrBr')]:
    g.plot(column=c,ax=a,cmap=cm,legend=True,linewidth=0,missing_kwds={'color':'#cccccc'},legend_kwds={'shrink':.7}); a.set_title(t,loc='left',fontsize=10); a.set_axis_off()
fig.suptitle('Suelos de Butler County, Iowa (SSURGO, 23,905 polígonos). Gris: agua o sin dato.',x=0.01,y=0.98,ha='left',fontsize=11)
plt.tight_layout(rect=(0,0,1,0.93)); plt.savefig('ssurgo_mapa_butler.png',dpi=130)
cols=['mukey','musym','nombre','acres_mapa','clase_tierra','drenaje','grupo_hidrologico','pendiente_pct','om_pct','awc_cm_cm','agua_disp_0_150cm','arena_pct','limo_pct','arcilla_pct','ph','factor_k','factor_t','frec_inundacion','inund_siembra','enchar_siembra','prof_capa_cm','pct_con_capa_restr','csr2_iowa']

