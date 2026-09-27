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
# AGANT - detiene el backend.
set -euo pipefail
pkill -f "[u]vicorn app.main:app" 2>/dev/null || true
sleep 1
if ss -ltn 2>/dev/null | grep -q ':8000 '; then
  echo "Aún ocupado :8000" >&2
else
  echo "AGANT detenido."
fi
