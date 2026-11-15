import numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
d=pd.read_csv('celdas_ndvi_rotacion.csv')
fig,ax=plt.subplots(1,2,figsize=(11,4.6),sharey=True)
col={'maiz tras soya':'#3b6ea5','maiz tras maiz':'#c2763a'}
for i,Y in enumerate([2024,2025]):
    s=d[d.anio==Y]
    for g in ['maiz tras soya','maiz tras maiz']:
        v=s[s.grupo==g].ndvi
        ax[i].hist(v,bins=np.arange(0.82,0.98,0.004),alpha=.6,label=f'{g} (n={len(v)})',color=col[g],density=True)
        ax[i].axvline(v.mean(),color=col[g],ls='--',lw=1.4)
    ax[i].set_title(f'{Y}',loc='left'); ax[i].set_xlabel('NDVI máximo de verano'); ax[i].legend(fontsize=8,frameon=False)
    ax[i].spines[['top','right']].set_visible(False)
ax[0].set_ylabel('densidad de celdas')
fig.suptitle('Vigor del maíz según el cultivo del año anterior — Butler County, Iowa\nCeldas MODIS de 250 m con 90 % o más de maíz. Línea punteada: promedio. Las dos distribuciones se traslapan.',x=0.01,ha='left',fontsize=10)
plt.tight_layout(rect=(0,0,1,0.88)); plt.savefig('ndvi_rotacion_butler.png',dpi=140)
print(d.groupby(['anio','grupo']).ndvi.agg(['size','mean','std']).round(4).to_string())
