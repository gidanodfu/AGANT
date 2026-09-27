#!/usr/bin/env bash
# AGANT - arranca el backend (y compila el CSS si hace falta).
# Uso:  bash scripts/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${AGANT_PORT:-8000}"
HOST="${AGANT_HOST:-0.0.0.0}"

if [ ! -x .venv/bin/python ]; then
  echo "ERROR: no hay entorno. Ejecuta: bash scripts/setup_env.sh" >&2
  exit 1
fi

if [ -x frontend/node_modules/.bin/tailwindcss ]; then
  (cd frontend && ./node_modules/.bin/tailwindcss -i styles/input.css -o styles/app.css --minify >/dev/null 2>&1) || true
fi

if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "Ya hay algo escuchando en :${PORT}."
else
  echo "Arrancando backend en http://${HOST}:${PORT} ..."
  setsid env AGANT_LOG_LEVEL="${AGANT_LOG_LEVEL:-INFO}" \
    .venv/bin/uvicorn app.main:app --app-dir backend --host "$HOST" --port "$PORT" \
    > /tmp/agant_run.log 2>&1 < /dev/null &
  disown
fi

echo -n "Esperando /health "
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "OK"
    curl -s "http://127.0.0.1:${PORT}/api/v1/system/status" | python3 -m json.tool 2>/dev/null | head -20
    echo
    echo "Panel:      http://localhost:${PORT}/home"
    echo "Nueva:      http://localhost:${PORT}/nueva-transaccion"
    echo "Laya:       http://localhost:${PORT}/laya"
    echo "Grafo:      http://localhost:${PORT}/grafo"
    echo "API docs:   http://localhost:${PORT}/docs"
    exit 0
  fi
  sleep 1.5
  echo -n "."
done
echo
echo "No respondió a tiempo; revisa /tmp/agant_run.log" >&2
exit 1
