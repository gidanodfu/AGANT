#!/usr/bin/env bash
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
