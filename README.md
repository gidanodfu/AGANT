# AGANT — Detección híbrida de fraude financiero

AGANT combina **reglas deterministas**, **Machine Learning** y **contexto
de grafos** para producir evidencia, y usa **Laya** como motor central de
decisión (segunda opinión). El backend es la fuente de verdad; el frontend
consume eventos en tiempo real por WebSocket/SSE. **PaySim**
(6,362,620 transacciones) sirve de dataset público de entrenamiento,
evaluación y replay.

Meta de ingeniería: **p95 < 50 ms** en la ruta online, medida por etapas.

- Licencia del código propio: **AGPL-3.0-or-later** (`LICENSE`, `NOTICE`).
- Terceros y datasets: `THIRD_PARTY_NOTICES.md`.

## Arquitectura

```
Transacción → FeatureBuilder (9 tabulares + 6 grafo)
    ├── RulesEngine        ┐
    ├── MLDecisionProvider ├── Evidence
    └── GraphContextProvider ┘
              │  DecisionStateBuilder → LayaDecisionEngine → FallbackPolicy
              ▼
        Decisión + Explicación → EventBus → WebSocket/SSE → Frontend
```

Sin orquestador monolítico: una composition root (`app/main.py`) conecta
componentes. Ver `docs/arquitectura.md`.

## Requisitos

- Linux/WSL, GPU NVIDIA para Laya (probado: RTX 4060 Laptop, 8 GB).
- Python **3.12**, `uv`. Node 22 (para el CSS). Docker (opcional).

Stack validado: `torch==2.14.0`, `laya==0.3.20`, `tilelang==0.1.14`,
`nvidia-cuda-nvcc` (toolkit que tilelang usa en el fast path).

## Instalación

```bash
bash scripts/setup_env.sh        # Python 3.12 + .venv + dependencias
cp .env.example .env             # ajustar según necesidad
```

## Pipeline de datos y modelos

```bash
.venv/bin/python scripts/download_paysim.py     # descarga + verifica 6.36M filas
.venv/bin/python scripts/prepare_paysim.py      # DuckDB + splits + drift
.venv/bin/python scripts/prepare_features.py    # memmaps float32 (15 features)
.venv/bin/python scripts/train.py               # entrena RF online + evalúa
.venv/bin/python scripts/thresholds.py          # selección de umbral (VALIDATION)
.venv/bin/python scripts/evaluate_variants.py   # audit_only + ablación (± grafo)
```

Variantes: `audit_only` (post-transacción, F1 0.8761, no online) y ablación
(grafo aporta +0.0115 F1). **Modo por lotes**: `batch_size` 32/64 con ML
vectorizado → ~3,400 tx/s vs ~344 tx/s per-item (mismas decisiones). Ver
`docs/rendimiento.md`.

Métricas TEST reproducidas: **P 0.9567 · R 0.7228 · F1 0.8235 ·
ROC-AUC 0.9920 · PR-AUC 0.8545**.

## Ejecutar

```bash
bash scripts/run.sh      # arranca backend (+ compila CSS) y verifica /health
bash scripts/stop.sh     # detiene el backend
```

o manualmente:

```bash
.venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

- Panel: `http://localhost:8000/home` · **Nueva transacción:
  `/nueva-transaccion`** · Transacciones: `/transacciones` · Decisiones
  Laya: `/decisiones` · Grafo: `/grafo`.
- `/home` es una ventana realtime: tabla **«Actividad en tiempo real»** con
  tipo/importe/cuentas, decisión primaria/final, Laya, latencias y **detalle
  expandible** (transacción · resultado · rules · ML · graph · rendimiento),
  más **errores recientes** publicados por el backend.
- Desde `/nueva-transaccion` puedes **crear y enviar** transacciones reales
  y **iniciar/detener un flujo** Live (sintético) o PaySim Replay, viendo el
  resultado inmediato y el avance en vivo. Ver `docs/flujo-interactivo.md`.
- **Importar/Exportar**: junto a *Exportar XLSX* hay *Importar* (procesa las
  transacciones del archivo de verdad). Ver `docs/import.md`.
- **`/laya`**: panel visual para configurar/cargar checkpoints, ver VRAM y
  probar el motor. Modo de decisión `hybrid | laya_all` (Laya decide todo).
- UI extra: tema claro/oscuro, `Ctrl+K`, sparklines, toasts, pausa/reanudar
  feed, filtros persistentes, grafo interactivo y export XLSX.
- API: `docs/api.md` · WebSocket/SSE: `docs/websocket.md`.

## Frontend

HTML/JS + **Tailwind CSS** + **Lucide**, sin React. Rutas `/home`,
`/transacciones`, `/decisiones`, badges LIVE/REPLAY, panel de Laya (sólo
`laya.invoked=true`), estados de conexión, render progresivo con
`requestAnimationFrame` y captura global de errores en español. Build CSS:

```bash
cd frontend && npm install && npm run build:css
```

## Tests

```bash
.venv/bin/python -m pytest        # 129 tests backend
cd frontend && npm test           # 27 tests frontend (node:test)
```

Cubren reglas, features, grafo (paridad offline/online), ML, decisión,
Laya, fallback, errores, API, admin, WebSocket, replay, flujo interactivo,
métricas, drift, concurrencia, licencia y estructura; el frontend cubre el
constructor de payload (nunca incluye `isFraud`), validación y formateo.

## Benchmarks y replay

```bash
.venv/bin/python scripts/benchmark_e2e.py --records 3000 --batch 32
.venv/bin/python scripts/replay.py --max-records 3000
```

Resultado medido (3,000 tx, batch 32): **total p50 1.65 ms · p95 2.28 ms ·
p99 2.86 ms**, ML p50 1.56 ms. Detalle en `docs/rendimiento.md`.

## Diagnóstico de paridad de grafo

```bash
.venv/bin/python scripts/diagnose_graph_parity.py --max-records 500000
```

Compara las features de grafo online (`GraphState` con caps LRU) contra los
memmaps offline y reporta divergencia y cardinalidad real. En PaySim completo
los caps (2M/2M) son menores que las cuentas/aristas reales
(6.35M/2.72M/6.36M), por lo que la paridad se rompe a gran escala. Ver
`docs/baseline.md`.

## Docker

```bash
docker compose up --build              # backend + frontend (nginx)
docker compose --profile gpu up        # + servicio Laya aislado
```

## Estado de la reconstrucción

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Entorno, contratos, errores, arranque | ✅ |
| 1 | PaySim (descarga, DuckDB, splits, memmaps) | ✅ |
| 2 | Features, reglas, ML (métricas = referencia) | ✅ |
| 3 | Decisión, Laya, fallback | ✅ |
| 4 | API, EventBus, WS/SSE, errores | ✅ |
| 5 | Frontend | ✅ |
| 6 | Replay, drift, métricas separadas | ✅ |
| 7 | Tests, benchmarks, Docker, docs | ✅ |
| 8 | Flujo interactivo (`/nueva-transaccion`, Live/Replay) | ✅ |
| 9 | Estabilización: red de seguridad, fixes aditivos, licencia canónica | ✅ |
