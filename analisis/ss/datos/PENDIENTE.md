# Falta: datos crudos de SSURGO y el script de extracción

1. **Datos crudos** (no se suben, se bajan de https://websoilsurvey.nrcs.usda.gov/ → Download Soils Data → Iowa, Butler County IA023):
   - `shp/soilmu.shp` y sus archivos compañeros (.dbf, .shx, .prj)
   - `tabular/mucrpyd.txt`, `tabular/ccrpyd.txt`, `tabular/crstrcts.txt`, `tabular/cmonth.txt`
2. **Tablas intermedias** que leen los scripts y que no tienen script que las genere:
   - `component.csv`
   - `ssurgo_butler_por_suelo.csv`
3. **El script que genera `ssurgo_butler_variables_modelo.csv`** (la tabla de 22 variables que usa el modelo).

Pedir 2 y 3 a quien hizo el análisis de SSURGO.
