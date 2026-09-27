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

"""Proveedor de ML online: carga única del modelo y puntuación por transacción."""

from __future__ import annotations

import logging
import time

import numpy as np

from ..config import Settings
from ..contracts.enums import Decision
from ..contracts.evidence import MLResult
from ..contracts.transaction import InferenceFeatures

logger = logging.getLogger("agant.ml")


class MLDecisionProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None
        self._model_version: str | None = None
        self._feature_version: str | None = None
        self._threshold_fraud: float | None = None
        self._error: str | None = None

    @property
    def available(self) -> bool:
        return self._model is not None

    @property
    def model_version(self) -> str | None:
        return self._model_version

    @property
    def feature_version(self) -> str | None:
        return self._feature_version

    @property
    def load_error(self) -> str | None:
        return self._error

    def load(self) -> bool:
        from ..training.train_online import MODEL_FILENAME

        model_path = self.settings.models_path / MODEL_FILENAME
        if not model_path.exists():
            self._error = f"modelo ausente: {model_path.name}"
            return False
        try:
            import joblib

            artifact = joblib.load(model_path)
            self._model = artifact["model"]
            # n_jobs>1 añade overhead por llamada en inferencias de una fila;
            # el paralelismo se explota por lote, no por petición.
            if hasattr(self._model, "n_jobs"):
                self._model.n_jobs = 1
            self._model_version = artifact.get("model_version")
            self._feature_version = artifact.get("feature_version")
            # El umbral de fraude viaja con el artefacto (seleccionado en
            # VALIDATION); si falta, se usa el de configuración.
            raw_threshold = artifact.get("threshold")
            self._threshold_fraud = (
                float(raw_threshold) if isinstance(raw_threshold, (int, float)) else None
            )
            self._error = None
            return True
        except Exception as exc:  # noqa: BLE001 - se registra, no se silencia
            self._error = type(exc).__name__
            logger.error("no fue posible cargar el modelo: %s", exc)
            return False

    def _decide(self, score: float) -> Decision:
        fraud_threshold = (
            self._threshold_fraud if self._threshold_fraud is not None else self.settings.threshold_fraud
        )
        if score >= fraud_threshold:
            return Decision.FRAUD
        if score >= self.settings.threshold_suspicious:
            return Decision.SUSPICIOUS
        return Decision.LEGITIMATE

    def predict(self, features: InferenceFeatures) -> MLResult:
        if self._model is None:
            return MLResult(available=False, model_version=self._model_version)
        start = time.perf_counter()
        vector = np.asarray([features.as_vector()], dtype=np.float32)
        score = float(self._model.predict_proba(vector)[0, 1])
        latency = (time.perf_counter() - start) * 1000.0
        return MLResult(
            available=True,
            score=score,
            decision=self._decide(score),
            model_version=self._model_version,
            feature_version=self._feature_version,
            latency_ms=latency,
        )

    def predict_batch(self, features_list: list[InferenceFeatures]) -> list[MLResult]:
        """Inferencia vectorizada para un bloque (alto rendimiento)."""
        if not features_list:
            return []
        if self._model is None:
            return [MLResult(available=False, model_version=self._model_version) for _ in features_list]
        matrix = np.asarray([item.as_vector() for item in features_list], dtype=np.float32)
        start = time.perf_counter()
        scores = self._model.predict_proba(matrix)[:, 1]
        block_ms = (time.perf_counter() - start) * 1000.0
        per_item = block_ms / len(features_list)
        return [
            MLResult(
                available=True,
                score=float(score),
                decision=self._decide(float(score)),
                model_version=self._model_version,
                feature_version=self._feature_version,
                latency_ms=per_item,
            )
            for score in scores
        ]
