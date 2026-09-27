#!/usr/bin/env bash
# AGANT - detiene el backend.
set -euo pipefail
pkill -f "[u]vicorn app.main:app" 2>/dev/null || true
sleep 1
if ss -ltn 2>/dev/null | grep -q ':8000 '; then
  echo "Aún ocupado :8000" >&2
else
  echo "AGANT detenido."
fi
