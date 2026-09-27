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
| Backend (pytest) | 116 | **130** |
| Frontend (node:test) | 27 | 27 |

## Métricas del modelo (RF online, 15 features, umbral 0.5)

| Split | Versión | P | R | F1 | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|
| TEST | `online_v1` | 0.9567 | 0.7228 | 0.8235 | 0.9920 | 0.8545 |
| TEST | **`online_v2`** | 0.9290 | 0.7212 | **0.8121** | 0.9883 | 0.8425 |
| VALIDATION | `online_v1` | 0.9217 | 0.7280 | 0.8134 | 0.9935 | 0.8122 |
| VALIDATION | **`online_v2`** | 0.8731 | 0.7288 | **0.7945** | 0.9894 | 0.7942 |

Umbral óptimo en VALIDATION (`online_v2`): **0.55** (el artefacto conserva 0.5).

`audit_only` (post-transacción, no online): F1 0.8761 (sin cambios).

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

## Benchmark e2e

`results/benchmarks/e2e_latest.json` (3,000 tx, batch 32, ruta per-item):
total p50 1.65 ms · p95 2.28 ms · p99 2.86 ms; ML p50 1.56 ms.

## Notas

- `frontend/styles/app.css` regenerado con `npm run build:css`; conjunto de
  clases idéntico al anterior (0 pérdidas).
- Cabeceras AGPL-3.0 canónicas en código y configuración de primera parte;
  `backend/tests/test_license.py` lo verifica.
