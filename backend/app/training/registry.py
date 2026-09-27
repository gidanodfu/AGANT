# Copyright (C) 2026 Josue David (gidanodfu)
# https://github.com/gidanodfu/AGANT
#
# This file is part of AGANT.
#
# AGANT is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# AGANT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with AGANT. If not, see <https://www.gnu.org/licenses/>.

"""Registro de experimentos (dataset/split/umbral/versiones/métricas)."""

from __future__ import annotations

import json
import time
import uuid

from ..config import Settings


def registry_path(settings: Settings):
    return settings.results_path / "experiments" / "index.json"


def append_experiment(settings: Settings, entry: dict) -> dict:
    path = registry_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if path.exists():
        history = json.loads(path.read_text(encoding="utf-8"))
    record = {"id": uuid.uuid4().hex[:12], "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **entry}
    history.append(record)
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return record
