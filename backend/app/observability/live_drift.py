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

"""Drift en vivo de features respecto de la referencia de entrenamiento.

Se actualiza con cada decisión LIVE (no replay) usando las features reales
del ``DecisionState``. Separado del drift offline del dataset.
"""

from __future__ import annotations

import logging

import numpy as np

from ..config import Settings
from ..contracts.transaction import InferenceFeatures

logger = logging.getLogger("agant.drift")


class LiveDriftMonitor:
    def __init__(self, settings: Settings, *, sample: int = 50_000) -> None:
        self.available = False
        self._names: list[str] = []
        self._ref_mean = None
        self._ref_std = None
        try:
            from .drift import reference_stats

            self._names, self._ref_mean, self._ref_std = reference_stats(settings, sample=sample)
            self._sum = np.zeros(len(self._names), dtype=np.float64)
            self._samples = 0
            self.available = True
        except Exception as exc:  # noqa: BLE001 - opcional, no bloquea el arranque
            logger.warning("drift live no disponible: %s", exc)

    def update(self, features: InferenceFeatures) -> None:
        if not self.available:
            return
        self._sum += np.asarray(features.as_vector(), dtype=np.float64)
        self._samples += 1

    def snapshot(self) -> dict:
        if not self.available:
            return {"available": False, "samples": 0}
        if self._samples == 0:
            return {"available": True, "samples": 0}
        mean = self._sum / self._samples
        diff = (mean - self._ref_mean) / (self._ref_std + 1e-9)
        return {
            "available": True,
            "samples": self._samples,
            "feature_means": {name: float(mean[i]) for i, name in enumerate(self._names)},
            "standardized_diff": {name: float(diff[i]) for i, name in enumerate(self._names)},
        }
