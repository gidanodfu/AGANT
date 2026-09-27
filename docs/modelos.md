# AGANT — Modelos

## Modelo online servido (GBM, 15 features)

Modelo servido: **HistGradientBoostingClassifier** con 9 features tabulares +
6 de grafo, elegido por `AGANT_MODEL_KIND` (`gbm` por defecto, `rf` alterno).

- `max_iter=200`, `learning_rate=0.1`, `class_weight=balanced`,
  `random_state=42`.
- Carga única en startup (`MLDecisionProvider.load`); **no** se entrena en
  una petición. En inferencia no hay paralelismo por fila.
- El **umbral** se elige por F1 en VALIDATION y se guarda en el artefacto
  (`MLDecisionProvider` lo respeta); no es un valor mágico en código.
- Artefacto: `results/models/online_model.joblib` (regenerable, fuera de git).
  Métricas: `results/metrics/model_*.json`.

### Métricas (TEST, umbral 0.989 elegido en VALIDATION)

| P | R | F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
|---|---|---|---|---|---|---|---|---|
| 0.8396 | 0.8530 | 0.8463 | 0.9988 | 0.9432 | 88,010 | 204 | 184 | 1068 |

VALIDATION: P 0.7487 · R 0.8661 · F1 0.8031. No son garantía de producción.

### Intervalos de confianza (TEST, bootstrap n=1000)

`scripts/confidence_intervals.py` → `results/metrics/confidence_intervals.json`
(remuestreo con reemplazo; percentiles 2.5–97.5):

| Métrica | Punto | IC 95 % |
|---|---|---|
| precision | 0.8396 | [0.8178, 0.8607] |
| recall | 0.8530 | [0.8333, 0.8724] |
| F1 | 0.8463 | [0.8304, 0.8609] |
| ROC-AUC | 0.9988 | [0.9986, 0.9990] |
| PR-AUC | 0.9432 | [0.9341, 0.9512] |

### Features (`online_v2`)

`step, amount, origin_old_balance, destination_old_balance, type_CASH_IN,
type_CASH_OUT, type_DEBIT, type_PAYMENT, type_TRANSFER` +
`origin_degree_before, destination_degree_before,
origin_unique_destinations_before, destination_unique_origins_before,
edge_count_before, edge_seen_before`.

Las 6 features de grafo se calculan offline con el **mismo `GraphState`** que
la ruta online (mismos caps LRU), de modo que entrenamiento y servicio usan
la misma definición de contexto (paridad por construcción). La versión
anterior (`online_v1`) usaba ventanas SQL sin acotar y divergía del servicio
a gran escala.

## Selección de umbral y ablación

- **Umbral**: barrido sobre VALIDATION (`scripts/thresholds.py`) → mejor F1 en
  **0.989** (`results/metrics/threshold_analysis.json`); el artefacto lo
  persiste y el servicio lo usa.
- **Ablación** (`scripts/evaluate_variants.py`, RF de 15 árboles sobre 2M filas,
  features `online_v2`): F1 sin grafo **0.7949** vs con grafo **0.7833** →
  las 6 features de grafo **no mejoran** F1 bajo paridad (**−0.0117**)
  (`results/metrics/ablation.json`). Con las features `online_v1` (sin acotar)
  la lectura era +0.0115; el signo cambia al hacer consistente offline/online.
- **Registro de experimentos**: `results/experiments/index.json` guarda
  dataset/split/umbral/feature_version/model_version/métricas.

## Selección de modelo y baselines

`scripts/model_selection.py` compara RF y GBM con umbral en VALIDATION y
latencia per-item (`results/metrics/model_selection.json`). El GBM gana
(F1 0.846 vs 0.811; PR-AUC 0.943 vs 0.843; p95 2.86 vs 2.56 ms) y es el
**modelo servido**; el RF queda como alterno (`AGANT_MODEL_KIND=rf`).

`scripts/baselines.py` añade reglas solas (`results/metrics/baselines.json`):

| Modelo | TEST F1 | TEST PR-AUC |
|---|---|---|
| Reglas solas (positivo = FRAUD) | 0.011 | 0.020 |
| GBM (servido, `online_v2`) | **0.846** | **0.943** |
| RF (`online_v2`) | 0.811 | 0.843 |

Las reglas solas son casi inútiles: el ML hace el trabajo.

## Variante audit_only

Una variante con `newbalance*` (post-transacción) existe sólo como
`audit_only` para auditoría/techo teórico; **nunca** se usa online.
Medida (`results/models/random_forest_audit_only.json`): P 0.9736 · R 0.7963 ·
F1 0.8761. Refuerza que la ruta online no puede usar esas features.

## Laya (checkpoints)

- Paquete `laya` 0.3.20 (Apache-2.0); checkpoints
  `convaiinnovations/laya` (`typed-decisions`).
- Los scores son **uncalibrated**: se tratan como etiqueta ordinal, no
  como probabilidad de fraude.
- Se descargan externamente (caché de Hugging Face); no se redistribuyen.

## Entrenar / evaluar

```bash
.venv/bin/python scripts/train.py     # entrena y evalúa validation+test
```
