# AGANT — Modelos

## Random Forest online (15 features)

Modelo online de referencia: **RandomForestClassifier** con 9 features
tabulares + 6 de grafo.

- `n_estimators=20`, `max_depth=20`, `min_samples_leaf=2`,
  `max_features=sqrt`, `class_weight=balanced_subsample`, `random_state=42`.
- Carga única en startup (`MLDecisionProvider.load`); **no** se entrena en
  una petición. En inferencia `n_jobs=1` (evita overhead por llamada).
- Artefacto: `results/models/random_forest_online.joblib` (regenerable,
  fuera de git). Métricas: `results/metrics/model_*.json`.

### Métricas (TEST, umbral 0.5)

| P | R | F1 | ROC-AUC | PR-AUC | TN | FP | FN | TP |
|---|---|---|---|---|---|---|---|---|
| 0.9290 | 0.7212 | 0.8121 | 0.9883 | 0.8425 | 88,145 | 69 | 349 | 903 |

VALIDATION: P 0.8731 · R 0.7288 · F1 0.7945. Ambas reproducen el benchmark
de referencia del proyecto (no son garantía de producción).

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
  **0.55** (`results/metrics/threshold_analysis.json`); el artefacto conserva
  0.5.
- **Ablación** (`scripts/evaluate_variants.py`, RF de 15 árboles sobre 2M filas,
  features `online_v2`): F1 sin grafo **0.7949** vs con grafo **0.7833** →
  las 6 features de grafo **no mejoran** F1 bajo paridad (**−0.0117**)
  (`results/metrics/ablation.json`). Con las features `online_v1` (sin acotar)
  la lectura era +0.0115; el signo cambia al hacer consistente offline/online.
- **Registro de experimentos**: `results/experiments/index.json` guarda
  dataset/split/umbral/feature_version/model_version/métricas.

## Baselines

`scripts/baselines.py` compara contra reglas solas y un
`HistGradientBoostingClassifier` (200 iteraciones, pesos balanceados, umbral
elegido en VALIDATION) con las mismas 15 features (`results/metrics/baselines.json`):

| Modelo | TEST F1 | TEST PR-AUC |
|---|---|---|
| Reglas solas (positivo = FRAUD) | 0.011 | 0.020 |
| HistGradientBoosting @0.989 | **0.846** | **0.943** |
| RF online servido (`online_v2`) | 0.812 | 0.843 |

El GBM **supera** al RF servido; las reglas solas son casi inútiles. El RF
está poco ajustado y es una línea de mejora abierta.

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
