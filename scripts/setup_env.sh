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
# AGANT - preparacion idempotente del entorno (Python 3.12 + CUDA).
# Uso:  bash scripts/setup_env.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: se requiere 'uv' (https://docs.astral.sh/uv/)." >&2
  exit 1
fi

echo "[1/3] Python 3.12"
uv python install 3.12

echo "[2/3] Entorno virtual"
uv venv --python 3.12 .venv

echo "[3/3] Dependencias"
uv pip install -r requirements.txt

echo "Validando GPU/torch..."
.venv/bin/python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
PY

echo "Entorno listo. Activar con: source .venv/bin/activate"
