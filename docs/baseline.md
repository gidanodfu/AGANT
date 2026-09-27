# AGANT — Baseline de estabilización

Registro congelado del estado del sistema antes/después de la fase de
estabilización. Sirve de referencia para comparar futuros cambios.

## Commits

| Hito | Commit |
|---|---|
| Línea base (antes de estabilizar) | `d4059e0 chore: línea base del proyecto antes de la estabilización` |
| Correcciones aditivas + licencia | ver `git log` (fase 1) |

## Suites de pruebas

| Suite | Antes | Después |
|---|---|---|
| Backend (pytest) | 116 | **129** |
| Frontend (node:test) | 27 | 27 |

## Métricas del modelo (RF online, 15 features, umbral 0.5)

VALIDATION (`results/metrics/model_validation.json`):
P 0.9217 · R 0.7280 · F1 0.8134 · ROC-AUC 0.9935 · PR-AUC 0.8122.

TEST (`results/metrics/model_test.json`):
P 0.9567 · R 0.7228 · F1 0.8235 · ROC-AUC 0.9920 · PR-AUC 0.8545
(TN 88173 · FP 41 · FN 347 · TP 905).

Umbral óptimo en VALIDATION: **0.5** (`threshold_analysis.json`).

Ablación (`ablation.json`): F1 sin grafo 0.7949 → con grafo 0.8065
(**+0.0115**), aunque ROC-AUC y PR-AUC **empeoran** con grafo en esa
ablación (RF de 15 árboles sobre 2M filas).

## Benchmark e2e

`results/benchmarks/e2e_latest.json` (3,000 tx, batch 32):
total p50 **1.65 ms** · p95 **2.28 ms** · p99 **2.86 ms**; ML p50 1.56 ms;
throughput ≈ 560 tx/s (ruta per-item).

## Diagnóstico de paridad del grafo

`scripts/diagnose_graph_parity.py` (caps LRU 2,000,000 / 2,000,000):

| Métrica | Valor |
|---|---|
| Filas comparadas | 2,400,000 |
| Primera divergencia | índice **1,484,082** |
| Filas divergentes | 55,556 (2.31 %) |
| Diferencia máxima | 82 |
| Orígenes / destinos / aristas reales | 6,353,307 / 2,722,362 / 6,362,620 |

**Conclusión:** los caps online son menores que la cardinalidad real de
PaySim, por lo que las features de grafo online divergen de las offline a
gran escala. La corrección de validez (reentrenar con features acotadas) se
traza como fase posterior.

## Notas

- `frontend/styles/app.css` se regeneró con `npm run build:css`; el conjunto
  de clases resultante es idéntico al anterior (0 pérdidas).
- Cabeceras AGPL-3.0 canónicas en todo el código y la configuración de
  primera parte; `backend/tests/test_license.py` lo verifica.
