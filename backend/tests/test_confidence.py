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

"""Tests del bootstrap de intervalos de confianza."""

from __future__ import annotations

import numpy as np

from app.training.confidence import bootstrap_ci


def _sample(seed: int = 0):
    rng = np.random.default_rng(seed)
    y = np.array([0] * 90 + [1] * 10)
    scores = np.concatenate([rng.uniform(0.0, 0.5, 90), rng.uniform(0.5, 1.0, 10)])
    return y, scores


def test_bootstrap_reports_ordered_ci():
    y, scores = _sample()
    result = bootstrap_ci(y, scores, 0.5, n=60, seed=1, metrics=("precision", "recall", "f1"))
    assert set(result["ci"]) == {"precision", "recall", "f1"}
    for key in ("precision", "recall", "f1"):
        ci = result["ci"][key]
        assert ci["count"] > 0
        assert ci["low"] <= ci["mean"] <= ci["high"]


def test_bootstrap_is_deterministic():
    y, scores = _sample()
    first = bootstrap_ci(y, scores, 0.5, n=20, seed=7, metrics=("f1",))
    second = bootstrap_ci(y, scores, 0.5, n=20, seed=7, metrics=("f1",))
    assert first["ci"]["f1"]["mean"] == second["ci"]["f1"]["mean"]
