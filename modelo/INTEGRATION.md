# Historical integration provenance

This older delivery is preserved for traceability. It is no longer the runtime source: the application reads `../model/datos_ui/` from the newer Butler delivery. See `../model/INTEGRATION.md`.

Original model files were imported unchanged from `origin/feature/modelo` at commit `a711b487fba854bbd13aa857b5b863f2a16b6503`. All 19 files were compared byte for byte with that revision. The agricultural algorithms and calibration have not been edited.

`feature/analisis-datos` (`01d2322`) documents the research pipeline and refers consumers to this model directory. `PROCEDENCIA_ANALISIS.md` is a copied provenance document from that branch; its original relative links refer to the analysis repository layout.

The initial integration read `salidas/resultado_ejemplo.json` through `utils/field_model.py`: five representative profiles, three climate groups, three rotation plans. `resultado_todas.json` remains available as source material but is not activated in the interface. Final property boundaries and geographic ID mapping are pending; frontend geometry is explicitly schematic.

Do not import `gen.py` into Streamlit: it runs generation, changes its working directory and writes outputs at module scope. Runtime integration needs no additional scientific dependencies beyond the app's existing environment. Generation dependencies and instructions belong to the model's original README and requirements.

Output values, source units and plan/climate IDs are preserved. English labels are presentation only. See `../docs/model-integration-design.md` for limitations, tests and manual checks.
