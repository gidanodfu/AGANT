# AGANT — Rendimiento

Meta de ingeniería: **p95 < 50 ms** en la operación online de decisión,
medida de extremo a extremo y desglosada por etapa.

## Benchmark E2E (`scripts/benchmark_e2e.py`)

3,000 transacciones de PaySim, batch 32, ML cargado, Laya fuera de la
ruta crítica (RTX 4060 Laptop / 8 cores):

| Etapa | p50 | p95 | p99 |
|---|---|---|---|
| features | 0.023 | 0.034 | 0.055 |
| graph | 0.021 | 0.033 | 0.055 |
| rules | 0.013 | 0.022 | 0.045 |
| ML | 1.975 | 2.926 | 3.287 |
| state | 0.012 | 0.020 | 0.037 |
| **total** | **2.10** | **3.09** | **3.48** |

Throughput de la ruta de decisión: ~443 items/s en streaming por ítem.

> Estas cifras son de un batch offline **sin red**. No son garantía de
> producción; el objetivo de 100k tps es una propiedad de arquitectura
> (particionado, colas, réplicas), no de este benchmark.

## Hallazgo de optimización

Con `n_jobs=-1` en inferencia, `predict_proba` de una fila costaba ~16 ms
(overhead de hilos). Con `n_jobs=1` baja a ~2 ms con el GBM servido (~1.6 ms
con el RF anterior). El paralelismo se explotaría por lote, no por petición.
Corrección: una línea en `MLDecisionProvider.load`.

## Procesamiento por lotes (alto rendimiento)

Modo con ML **vectorizado**: las features causales/reglas/grafo se calculan por
ítem y la inferencia ML se agrupa en lotes de `batch_size` (32/64). Mismas
decisiones que el camino per-item (paridad verificada por test y por conteos).

Replay de 20,000 filas de PaySim (RTX 4060 Laptop, sin Laya, modelo GBM), medido real:

| Config | tps | p50 | p95 | p99 |
|---|---|---|---|---|
| batch 1 (per-item) | 435 | 2.00 ms | 2.98 ms | 3.61 ms |
| batch 32 | 4,086 | 0.08 ms | 0.13 ms | 0.19 ms |
| batch 64 | 4,701 | 0.05 ms | 0.10 ms | 0.15 ms |

Ganancia ≈ **9.4×–10.8×**. Los 100k tx/s del benchmark son solo de inferencia ML
aislada; el pipeline completo (features+reglas+grafo+objetos+eventos) da el
número aquí reportado. La publicación de eventos es **muestreada** por defecto
(FRAUD/SUSPICIOUS/Laya + 1 de cada K) para no saturar el WebSocket; las métricas
y el **historial del backend** se mantienen exactos (se procesa en sub-trozos de
≤10k para acotar memoria). La latencia p50/p95 de Laya solo cuenta cuando
`laya.invoked=true`.

```bash
.venv/bin/python scripts/replay.py --max-records 20000 --batch-size 64
```

## Laya

Laya sólo se invoca para `SUSPICIOUS`. Fast path (TileLang + `nvidia-cuda-nvcc`)
activo (al cargar no aparece `fast path unavailable`). Medido:
carga ≈11 s; primera llamada ≈1.5 s (compila kernels); régimen ≈14 ms;
VRAM in-process ≈4 GB (contexto CUDA + pesos + buffers).

Prueba por la API real (replay 5,000 filas de la zona de test, `laya_mode=pretrained`):
36 invocaciones, **36/36 `succeeded`**, latencia por llamada
min 14.4 ms · p50 55.5 ms · p95 92.8 ms · max 272.8 ms. La dispersión bajo
carga de replay confirma que Laya **no** debe estar en la ruta crítica:
su latencia se reporta aparte y sólo cuenta cuando `laya.invoked=true`.

> Operativo: no co‑ejecutar el servicio Laya aislado mientras el backend tiene
> Laya in-process; la suma supera los 8 GB de VRAM.

## Reproducir

```bash
.venv/bin/python scripts/benchmark_e2e.py --records 3000 --batch 32
.venv/bin/python scripts/replay.py --max-records 3000
```

Salida: `results/benchmarks/e2e_latest.json`.
