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

"""Tests del proveedor de ML online."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

from app.config import Settings
from app.contracts.enums import Decision
from app.contracts.transaction import MODEL_FEATURE_NAMES, InferenceFeatures
from app.evidence import MLDecisionProvider
from app.training.train_online import MODEL_FILENAME


def _features(value: float) -> InferenceFeatures:
    return InferenceFeatures(
        step=1.0,
        amount=value,
        origin_old_balance=value,
        destination_old_balance=0.0,
    )


def test_unavailable_without_model(tmp_path: Path):
    settings = Settings(data_dir=str(tmp_path / "d"), results_dir=str(tmp_path / "r"))
    provider = MLDecisionProvider(settings)
    assert provider.load() is False
    result = provider.predict(_features(1.0))
    assert result.available is False and result.score is None


def test_load_and_predict(tmp_path: Path):
    settings = Settings(
        data_dir=str(tmp_path / "d"),
        results_dir=str(tmp_path / "r"),
        threshold_suspicious=0.2,
        threshold_fraud=0.5,
    )
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 15)).astype(np.float32)
    y = (x[:, 0] > 0).astype(int)
    model = RandomForestClassifier(n_estimators=10, random_state=0).fit(x, y)

    settings.models_path.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "feature_names": list(MODEL_FEATURE_NAMES),
            "feature_version": "test",
            "model_version": "test-model",
            "threshold": 0.5,
        },
        settings.models_path / MODEL_FILENAME,
    )

    provider = MLDecisionProvider(settings)
    assert provider.load() is True
    result = provider.predict(_features(500.0))
    assert result.available is True
    assert 0.0 <= result.score <= 1.0
    assert result.decision in (Decision.FRAUD, Decision.SUSPICIOUS, Decision.LEGITIMATE)
    assert result.model_version == "test-model"
    assert result.latency_ms >= 0.0


def test_loads_gbm_artifact_and_honors_threshold(tmp_path: Path):
    settings = Settings(
        data_dir=str(tmp_path / "d"),
        results_dir=str(tmp_path / "r"),
        threshold_suspicious=0.2,
        threshold_fraud=0.9,
    )
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 15)).astype(np.float32)
    y = (x[:, 0] > 0).astype(int)
    model = HistGradientBoostingClassifier(max_iter=10, random_state=0).fit(x, y)
    settings.models_path.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "feature_names": list(MODEL_FEATURE_NAMES),
            "feature_version": "online_v2",
            "model_version": "test-gbm",
            "model_kind": "gbm",
            "threshold": 0.9,
        },
        settings.models_path / MODEL_FILENAME,
    )
    provider = MLDecisionProvider(settings)
    assert provider.load() is True
    result = provider.predict(_features(500.0))
    assert result.available is True
    assert result.model_version == "test-gbm"
