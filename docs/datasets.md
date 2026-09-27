# AGANT — Datasets

Los datasets **no** están bajo AGPL-3.0; conservan su licencia de origen y
**no se redistribuyen** (`data/raw/` está en `.gitignore`).

## PaySim

- Nombre: PaySim — Synthetic Financial Datasets for Fraud Detection
  (Lopez-Rojas et al.).
- Archivo esperado: `data/raw/paysim.csv`.
- Filas: **6,362,620** · Fraudes: **8,213** · Marcadas (`isFlaggedFraud`): 16.
- Columnas: `step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig,
  nameDest, oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud`.
- Licencia: **UNKNOWN / NEEDS VERIFICATION**; no se redistribuye.
- Descarga reproducible (espejo HF, sin credenciales):

```bash
.venv/bin/python scripts/download_paysim.py
```

El script es idempotente y verifica esquema y conteo.

## División temporal (`step`)

| Split | Steps | Filas | Fraudes | Tasa |
|---|---|---|---|---|
| train | ≤ 520 | 6,082,007 | 5,781 | 0.000951 |
| validation | 521–631 | 191,147 | 1,180 | 0.006173 |
| test | ≥ 632 | 89,466 | 1,252 | 0.013994 |

La variación de la tasa de fraude entre ventanas es **drift temporal del
dataset**; se documenta, no se oculta (`docs/drift.md`).

## Regla de causalidad

`isFraud` es ground truth: sólo entra en entrenamiento, evaluación y
métricas. **Nunca** como feature de inferencia. Igual para
`newbalanceOrig`/`newbalanceDest` en la ruta online.

## Reproducir

```bash
.venv/bin/python scripts/download_paysim.py     # descarga + verifica
.venv/bin/python scripts/prepare_paysim.py      # DuckDB + splits + drift
.venv/bin/python scripts/prepare_features.py    # memmaps de 15 features
```
