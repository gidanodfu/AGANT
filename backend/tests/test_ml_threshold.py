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

"""Caracteriza de dónde toma el umbral el proveedor de ML."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from app.config import Settings
from app.contracts.enums import Decision
from app.contracts.transaction import MODEL_FEATURE_NAMES
from app.evidence import MLDecisionProvider
from app.training.train_online import MODEL_FILENAME


def _write_model(settings: Settings, *, threshold: float | None) -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 15)).astype(np.float32)
    y = (x[:, 0] > 0).astype(int)
    model = RandomForestClassifier(n_estimators=5, random_state=0).fit(x, y)
    artifact = {
        "model": model,
        "feature_names": list(MODEL_FEATURE_NAMES),
        "feature_version": "test",
        "model_version": "test",
    }
    if threshold is not None:
        artifact["threshold"] = threshold
    settings.models_path.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, settings.models_path / MODEL_FILENAME)


def test_threshold_from_settings_when_artifact_lacks_it(tmp_path: Path):
    settings = Settings(
        data_dir=str(tmp_path / "d"),
        results_dir=str(tmp_path / "r"),
        threshold_suspicious=0.2,
        threshold_fraud=0.5,
    )
    _write_model(settings, threshold=None)
    provider = MLDecisionProvider(settings)
    assert provider.load() is True
    assert provider._decide(0.1) is Decision.LEGITIMATE
    assert provider._decide(0.3) is Decision.SUSPICIOUS
    assert provider._decide(0.6) is Decision.FRAUD
