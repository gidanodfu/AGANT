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

"""Tests de la selección de modelo (construcción y criterio)."""

from __future__ import annotations

import numpy as np
import pytest

from app.training.model_selection import build_model, choose_winner


def _comparison(gbm_f1: float, rf_f1: float, gbm_p95: float, rf_p95: float) -> dict:
    return {
        "candidates": {
            "rf": {"test": {"f1": rf_f1}, "latency_ms": {"p95": rf_p95}},
            "gbm": {"test": {"f1": gbm_f1}, "latency_ms": {"p95": gbm_p95}},
        }
    }


def test_build_model_fits_and_predicts():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(60, 15)).astype(np.float32)
    y = (x[:, 0] > 0).astype(int)
    for kind in ("rf", "gbm"):
        model = build_model(kind)
        model.fit(x, y)
        scores = model.predict_proba(x)[:, 1]
        assert scores.shape == (60,)


def test_build_model_rejects_unknown():
    with pytest.raises(ValueError):
        build_model("nope")


def test_choose_winner_requires_quality_and_latency():
    assert choose_winner(_comparison(0.85, 0.81, 3.0, 2.0))["winner"] == "gbm"
    # mejor calidad pero latencia excesiva -> RF
    assert choose_winner(_comparison(0.85, 0.81, 4.0, 2.0))["winner"] == "rf"
    # peor calidad -> RF
    assert choose_winner(_comparison(0.80, 0.81, 2.0, 2.0))["winner"] == "rf"
