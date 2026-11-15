# Butler delivery provenance

Source: `origin/feature/butler-model` at **9c2fa4e58ee448e02cd78c8008e24cca6da82cbd**.

The 17 original files listed below are copied byte for byte, without changing the engine, its inputs or its outputs. This integration document is additional frontend documentation.

Runtime reads only `datos_ui/resultado_todas.json` and `datos_ui/parcelas_todas.geojson`. The app joins all 167 IDs exactly and displays three plans in three historical climate groups. It never runs `modelo/gen.py` or loads `modelo_suelo.pkl`; they are retained for provenance with the source engine inputs.

Analysis scripts document how the CDL groups were selected and vectorized. Their intermediate raster/NPY/SSURGO geometry inputs are not all included here, so they are not a standalone geometry regeneration package. Original relative instructions belong to the source delivery layout.

The geometries represent satellite-derived agricultural regions, not verified ownership or cadastral boundaries. The old top-level `../modelo/` directory is retained as historical provenance, not runtime input. No scientific dependency is added to serve these exported JSON files.

See [the integration report](../docs/butler-model-integration.md) for design, state, validation and limitations.

| Original file | SHA-256 |
|---|---|
| `model/LEEME.md` | `f9ab97b0ad8075a3132274f9708e634c724ef0b63957ddf6a40bed27aa106917` |
| `model/analisis/PROCEDENCIA.md` | `8a416ed385f87cb5bfdaf318a8d5e2c4e4c01587b516ea5216a60ac368233e3b` |
| `model/analisis/s13_parcelas_demo.py` | `ba31e007d417d3a4b16e35c2a228e5aa6938e979cfbdc5f4545b656c7e9bf4bd` |
| `model/analisis/s16_geometria_parcelas.py` | `4c112431df855e608e18270c087cbec7dcd3035168533d51dad6a91736b86dd1` |
| `model/datos_ui/parcelas_candidatas.csv` | `76064198821d6c700f12ba9a92a1418c74d23acc0aa97a04f18cc710ac84cece` |
| `model/datos_ui/parcelas_demo.csv` | `1aa74a09584a3a331059ab62e69619b1dce114bc10348abdc1e8aadfe1127332` |
| `model/datos_ui/parcelas_todas.geojson` | `374932ae1b32dfb2bf7a5b17f272af3b610882d3bf40cea68026422b950d435f` |
| `model/datos_ui/resultado_todas.json` | `bee1e5759228e49cc62d8e9e43e4fc65de87508089ede2e7a853e0737f39dd9f` |
| `model/modelo/ajuste_suelo.csv` | `2c4bdf8e19bbed16a1ec11083122ea18c299fad331563867be55cc5d618e83e1` |
| `model/modelo/anomalias.csv` | `94d0d74badd6391cfa31bb2cef563926c4346b069d010e48cd169f44a5177e0e` |
| `model/modelo/clima_butler_por_anio.csv` | `78c9d1e18373221d9e7bcc07e2581637dd2482cfcb98c1e1f8d1cb6260cd7050` |
| `model/modelo/clima_por_escenario.csv` | `e110b36917147b685673bbc0d9f42bca2b96f2bf055734765bbd25888c18a3a0` |
| `model/modelo/gen.py` | `5f6fe77bb17db37ce3a36425b5bf3d0f54ee7fecc8bda3ac686b3fdfb09f8580` |
| `model/modelo/modelo_suelo.pkl` | `d5737d006dbc2e85ae6e49359f5521df5df67d8604309374ffddfda80cc89d0a` |
| `model/modelo/precios_iowa.csv` | `e8bc039cc7e4dbb847d8b1c5f334a0b0c789cae750ab66cb4b07b19882e00add` |
| `model/modelo/quickstats_iowa_limpio.csv` | `c1c7cd7f6a53653b36f77ba509607ef636d6a5c0b372a1a8c84de46e776564c8` |
| `model/modelo/ssurgo_butler_variables_modelo.csv` | `de1dbffa9109ae6d5dcabb3542239787c8a8ce5861a1d6b31c1adecef2508779` |
