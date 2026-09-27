# AGANT — Drift

El drift se analiza **offline** (dataset) y se mantiene separado de las
métricas **live**. Nunca se usan observaciones de replay como si fueran
live.

## Qué se mide

- **Feature drift**: diferencia estandarizada de medias train vs test por
  feature (`standardized_diff = (μ_test − μ_train) / σ_train`).
- **Label drift**: tasa de fraude train vs test y su ratio.
- **Fraud-rate drift**: evolución temporal por `step` (ver `splits.json`).

## Resultado actual (PaySim)

| Métrica | Valor |
|---|---|
| train fraud rate | 0.000951 |
| test fraud rate | 0.013994 |
| ratio test/train | ≈ 14.7 |

Mayor drift: `step` (3.7σ). Esto refleja que la tasa de fraude crece con
el tiempo en PaySim: es un **fenómeno del dataset**, no comportamiento de
producción.

## Consulta

```bash
curl -s localhost:8000/api/v1/drift | python3 -m json.tool
```

```bash
.venv/bin/python scripts/prepare_paysim.py   # escribe results/metrics/splits.json
```

> No interpretar las métricas de replay como observaciones live.
