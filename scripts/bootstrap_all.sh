#!/usr/bin/env bash
# AGANT - pipeline completo reproducible (idempotente).
# Uso:  bash scripts/bootstrap_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"

echo "[1/6] Entorno"
bash scripts/setup_env.sh

echo "[2/6] Dataset PaySim"
"$PY" scripts/download_paysim.py

echo "[3/6] DuckDB + splits + drift"
"$PY" scripts/prepare_paysim.py

echo "[4/6] Features (memmaps)"
"$PY" scripts/prepare_features.py

echo "[5/6] Entrenamiento + evaluación"
"$PY" scripts/train.py
"$PY" scripts/thresholds.py
"$PY" scripts/evaluate_variants.py

echo "[6/6] Benchmark E2E"
"$PY" scripts/benchmark_e2e.py --records 3000 --batch 32

echo "AGANT listo. Backend:  .venv/bin/uvicorn app.main:app --app-dir backend --port 8000"
