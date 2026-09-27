#!/usr/bin/env bash
# AGANT — Detección híbrida de fraude financiero (reglas + ML + grafo + Laya).
# Copyright (C) 2026 Josue David (gidanodfu)
# https://github.com/gidanodfu/AGANT
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
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
