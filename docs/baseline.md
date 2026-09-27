# AGANT — Baseline de estabilización

Registro congelado del estado del sistema a lo largo de la fase de
estabilización. Sirve de referencia para comparar futuros cambios.

## Commits de referencia

- Línea base inicial: `d4059e0 chore: línea base del proyecto antes de la estabilización`.
- Correcciones aditivas + licencia: ver `git log` (fase 1).
- Paridad de grafo (`online_v2`): ver `git log` (fase B).

## Suites de pruebas

| Suite | Inicio | Actual |
|---|---|---|
| Backend (pytest) | 116 | **143** |
| Frontend (node:test) | 27 | 29 |

## Métricas del modelo (15 features `online_v2`)

Modelo servido: **HistGradientBoosting** (umbral 0.989 elegido en VALIDATION).

| Split | Modelo | P | R | F1 | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|
| TEST | `online_v1` (RF) | 0.9567 | 0.7228 | 0.8235 | 0.9920 | 0.8545 |
| TEST | `online_v2` (RF) | 0.9290 | 0.7212 | 0.8121 | 0.9883 | 0.8425 |
| TEST | **`online_v2` (GBM, servido)** | 0.8396 | 0.8530 | **0.8463** | 0.9988 | **0.9432** |
| VALIDATION | `online_v2` (RF) | 0.8731 | 0.7288 | 0.7945 | 0.9894 | 0.7942 |
| VALIDATION | **`online_v2` (GBM)** | 0.7487 | 0.8661 | **0.8031** | 0.9990 | 0.9153 |

Selección (`scripts/model_selection.py`): RF vs GBM con umbral en VALIDATION y
latencia per-item. Gana el GBM (F1 0.846 vs 0.811; PR-AUC 0.943 vs 0.843;
p95 2.86 vs 2.56 ms → ratio 1.12, dentro del margen de 1.5).

`audit_only` (post-transacción, no online): F1 0.8761 (sin cambios).

### Intervalos de confianza (TEST, bootstrap n=1000)

`scripts/confidence_intervals.py` (modelo servido): F1 0.8463 [0.8304, 0.8609],
PR-AUC 0.9432 [0.9341, 0.9512], recall 0.8530 [0.8333, 0.8724]. Detalle en
`docs/modelos.md`.

## Cambio de features (`online_v1` → `online_v2`)

- **Motivo:** las 6 features de grafo offline usaban ventanas SQL sin acotar,
  mientras la ruta online usa `GraphState` con LRU acotado (caps 2M/2M). A
  gran escala ambas definiciones divergían (skew entrenamiento/servicio).
- **Fix:** la construcción offline ahora usa el **mismo `GraphState`** que
  online, con los mismos caps. Paridad por construcción.
- **Efecto:** las métricas bajan ligeramente (ver tabla); la ablación del
  grafo cambia de signo.

## Diagnóstico de paridad del grafo

`scripts/diagnose_graph_parity.py` (caps 2,000,000 / 2,000,000):

| Métrica | `online_v1` (antes) | `online_v2` (ahora) |
|---|---|---|
| Filas comparadas | 2,400,000 | 2,400,000 |
| Primera divergencia | índice 1,484,082 | — |
| Filas divergentes | 55,556 (2.31 %) | **0 (0.00 %)** |
| Diferencia máxima | 82 | **0** |
| Orígenes / destinos / aristas reales | 6,353,307 / 2,722,362 / 6,362,620 | ídem |

## Ablación del grafo (VALIDATION, RF 15 árboles / 2M filas)

| Versión | F1 sin grafo | F1 con grafo | Delta |
|---|---|---|---|
| `online_v1` | 0.7949 | 0.8065 | +0.0115 |
| **`online_v2`** | 0.7949 | 0.7833 | **−0.0117** |

Bajo paridad, las features de grafo **no mejoran** el F1 en la ablación.

## Baselines (TEST, features `online_v2`)

`scripts/baselines.py` → `results/metrics/baselines.json`.

| Modelo | P | R | F1 | PR-AUC |
|---|---|---|---|---|
| Reglas solas (positivo = FRAUD) | 1.000 | 0.006 | 0.011 | 0.020 |
| Reglas solas (positivo = FRAUD o SUSPICIOUS) | 0.031 | 0.994 | 0.061 | 0.031 |
| GBM servido @0.989 (elegido en VALIDATION) | 0.840 | 0.853 | **0.846** | **0.943** |
| RF alterno @0.599 | 0.955 | 0.705 | 0.811 | 0.843 |

Lectura honesta:

- Las **reglas deterministas solas son casi inútiles** (F1 ≈ 0.01 con
  positivo=FRAUD; al relajar a SOSPECHOSAS marcan casi todo).
- El **GBM supera al RF** en F1 y PR-AUC con las mismas 15 features y el mismo
  split temporal, por lo que pasó a ser el modelo servido.
- El umbral 0.5 del GBM no es comparable por los pesos balanceados; se
  selecciona en VALIDATION (0.989).

## Benchmark e2e

`results/benchmarks/e2e_latest.json` (3,000 tx, batch 32, ruta per-item, GBM):
total p50 2.10 ms · p95 3.09 ms · p99 3.48 ms; ML p50 1.98 ms (~443 tx/s).
Replay por lotes: 435 tps (batch 1) → 4,701 tps (batch 64).

## Notas

- `frontend/styles/app.css` regenerado con `npm run build:css`; conjunto de
  clases idéntico al anterior (0 pérdidas).
- Cabeceras AGPL-3.0 canónicas en código y configuración de primera parte;
  `backend/tests/test_license.py` lo verifica.
