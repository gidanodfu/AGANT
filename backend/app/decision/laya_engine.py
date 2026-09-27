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

"""Motor de decisión Laya (segunda opinión), aislado tras una interfaz.

Sólo se invoca para decisiones primarias ``SUSPICIOUS``. Carga en startup
y es opcional: su fallo no cambia el nivel de fallback ni impide READY.
Los scores del checkpoint son *uncalibrated*: se tratan como etiqueta
ordinal, nunca como probabilidad calibrada de fraude.
"""

from __future__ import annotations

import logging
import threading
import time

from ..config import Settings
from ..contracts.decision import DecisionState, LayaResult
from ..contracts.enums import ComponentStatus, Decision, LayaStatus
from ..errors import SAFE_MESSAGES, ErrorCode, LayaError, Severity, ValidationError

logger = logging.getLogger("agant.laya")

_SCHEMA = {
    "type": "object",
    "properties": {
        "risk": {"type": "string", "enum": ["LEGITIMATE", "SUSPICIOUS", "FRAUD"]}
    },
    "required": ["risk"],
}

_DECISION_BY_NAME = {member.value: member for member in Decision}


def _state_payload(state: DecisionState) -> dict:
    evidence = state.evidence
    return {
        "transaction_id": state.transaction_id,
        "type": _transaction_type(state),
        "amount": state.features.amount,
        "origin_old_balance": state.features.origin_old_balance,
        "destination_old_balance": state.features.destination_old_balance,
        "ml_score": evidence.ml.score,
        "rule_score": evidence.rule_score,
        "rules": [rule.rule_id for rule in evidence.rules_triggered],
        "graph": evidence.graph.context.model_dump(),
    }


def _transaction_type(state: DecisionState) -> str:
    for name in ("type_CASH_IN", "type_CASH_OUT", "type_DEBIT", "type_PAYMENT", "type_TRANSFER"):
        if getattr(state.features, name):
            return name.replace("type_", "")
    return "UNKNOWN"


class LayaDecisionEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        enabled = settings.laya_enabled and settings.laya_mode != "disabled"
        self.mode = settings.laya_mode if enabled else "disabled"
        self._enabled = enabled
        self._agent = None
        self._lock = threading.Lock()
        self._error: str | None = None
        self.status = ComponentStatus.DISABLED if not enabled else ComponentStatus.LOADING

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def load_error(self) -> str | None:
        return self._error

    def load(self) -> bool:
        if not self._enabled:
            self.status = ComponentStatus.DISABLED
            return False
        if self.settings.laya_url:
            self.status = ComponentStatus.READY
            logger.info("Laya se usará como servicio remoto en %s", self.settings.laya_url)
            return True
        with self._lock:
            if self._agent is not None:
                return True
            try:
                import laya

                self._agent = laya.load(
                    self.settings.laya_model_id,
                    device=self.settings.laya_device,
                    subfolder=self.settings.laya_active_subfolder,
                    fast=True,
                )
                if self.settings.laya_warmup:
                    self._agent.decide(_warmup_state(), schema=_SCHEMA, return_details=True)
                self.status = ComponentStatus.READY
                self._error = None
                logger.info("Laya cargado (mode=%s, device=%s)", self.mode, self.settings.laya_device)
                return True
            except Exception as exc:  # noqa: BLE001 - se registra y degrada, no se silencia
                self.status = ComponentStatus.UNAVAILABLE
                self._error = type(exc).__name__
                logger.error("fallo al cargar Laya: %s", exc)
                return False

    def evaluate(
        self, state: DecisionState, primary: Decision, *, decide_all: bool = False
    ) -> LayaResult:
        return self.evaluate_batch([state], [primary], decide_all=decide_all)[0]

    def evaluate_batch(
        self,
        states: list[DecisionState],
        primaries: list[Decision],
        *,
        decide_all: bool = False,
        batch_size: int = 32,
    ) -> list[LayaResult]:
        """Evalúa un lote; con ``decide_all`` toda transacción es elegible.

        Usa ``predict_batch`` (micro-batching) y cae a evaluación individual
        si el lote falla, para no perder decisiones.
        """
        results: list[LayaResult | None] = [None] * len(states)
        payloads: list[dict] = []
        pending: list[int] = []
        for index, (state, primary) in enumerate(zip(states, primaries)):
            eligible = decide_all or primary is Decision.SUSPICIOUS
            if not self._enabled:
                results[index] = LayaResult(
                    eligible=eligible, invoked=False, status=LayaStatus.DISABLED, mode=self.mode
                )
            elif not eligible:
                results[index] = LayaResult(
                    eligible=False, invoked=False, status=LayaStatus.SKIPPED, mode=self.mode
                )
            elif self.status is not ComponentStatus.READY:
                results[index] = LayaResult(
                    eligible=True, invoked=False, status=LayaStatus.UNAVAILABLE, mode=self.mode
                )
            else:
                payloads.append(_state_payload(state))
                pending.append(index)

        if pending:
            start = time.perf_counter()
            try:
                parsed = self._predict_many(payloads, max(1, int(batch_size)))
            except Exception as exc:  # noqa: BLE001 - se reporta como estado, no se silencia
                logger.error("fallo de inferencia en Laya: %s", exc)
                for index in pending:
                    results[index] = LayaResult(
                        eligible=True,
                        invoked=True,
                        status=LayaStatus.FAILED,
                        mode=self.mode,
                        error=SAFE_MESSAGES[ErrorCode.LAYA_ERROR],
                    )
            else:
                latency = (time.perf_counter() - start) * 1000.0 / max(1, len(pending))
                for index, (decision, confidence) in zip(pending, parsed):
                    results[index] = LayaResult(
                        eligible=True,
                        invoked=True,
                        status=LayaStatus.SUCCEEDED,
                        decision=decision,
                        confidence=confidence,
                        mode=self.mode,
                        latency_ms=latency,
                    )
        return results

    def _predict_many(self, payloads: list[dict], batch_size: int) -> list[tuple[Decision, float | None]]:
        if self.settings.laya_url:
            return [self._infer_http(payload) for payload in payloads]
        with self._lock:
            raw = self._agent.predict_batch(
                payloads, _questions(), batch_size=batch_size, sort_by_length=False
            )
        return [self._parse(item) for item in raw]

    @staticmethod
    def _parse(result) -> tuple[Decision, float | None]:
        from laya.structured import answers_to_json

        answers = result.get("answers", {}) or {}
        values = answers_to_json(answers, _SCHEMA)
        return _DECISION_BY_NAME.get(values.get("risk"), Decision.SUSPICIOUS), _confidence(result)

    def _infer_http(self, payload: dict) -> tuple[Decision, float | None]:
        import httpx

        timeout = self.settings.request_timeout_ms / 1000.0
        response = httpx.post(
            f"{self.settings.laya_url.rstrip('/')}/decide",
            json={"state": payload},
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        name = body.get("decision")
        return _DECISION_BY_NAME.get(name, Decision.SUSPICIOUS), body.get("confidence")


_QUESTIONS: dict | None = None


def _questions() -> dict:
    global _QUESTIONS
    if _QUESTIONS is None:
        from laya.structured import questions_from_json_schema

        _QUESTIONS = questions_from_json_schema(_SCHEMA)
    return _QUESTIONS


def _confidence(result) -> float | None:
    confidence = result.get("confidence")
    if isinstance(confidence, dict):
        value = confidence.get("risk")
        return float(value) if isinstance(value, (int, float)) else None
    if isinstance(confidence, (int, float)):
        return float(confidence)
    probabilities = result.get("probabilities")
    if isinstance(probabilities, dict):
        risk = probabilities.get("risk")
        if isinstance(risk, dict) and risk:
            try:
                return float(max(risk.values()))
            except (TypeError, ValueError):
                return None
    return None


def _warmup_state() -> dict:
    return {
        "transaction_id": "warmup",
        "type": "PAYMENT",
        "amount": 10.0,
        "origin_old_balance": 10.0,
        "destination_old_balance": 0.0,
    }


_VALID_MODES = {"disabled", "pretrained", "custom"}


def resolve_laya_engine(mode: str, state, subfolder: str | None = None) -> "LayaDecisionEngine":
    """Resuelve el motor Laya para un flujo según el modo pedido.

    Reutiliza el motor ya cargado para ``pretrained``; ``custom`` usa la
    subcarpeta indicada (o la configurada/primera del catálogo) y la carga
    on-demand; ``disabled`` no carga nada.
    """
    settings: Settings = state.settings
    mode = (mode or "disabled").strip().lower()
    if mode not in _VALID_MODES:
        raise ValidationError(
            f"modo Laya inválido: {mode!r}",
            public_message="Modo de Laya inválido. Usa disabled, pretrained o custom.",
        )

    if mode == "disabled":
        return LayaDecisionEngine(
            settings.model_copy(update={"laya_enabled": False, "laya_mode": "disabled"})
        )

    if mode == "custom":
        chosen = (
            (subfolder or "").strip()
            or settings.laya_custom_subfolder
            or (settings.laya_subfolder_list[0] if settings.laya_subfolder_list else None)
        )
        if not chosen:
            raise ValidationError(
                "el modo custom requiere una subcarpeta de checkpoint",
                status=400,
                severity=Severity.WARNING,
                operation="laya",
                public_message=(
                    "El modo Laya 'custom' requiere una subcarpeta de checkpoint. "
                    "Define AGANT_LAYA_SUBFOLDERS o usa 'pretrained'."
                ),
            )
        existing = getattr(state, "laya", None)
        if (
            existing is not None
            and getattr(existing, "enabled", False)
            and getattr(existing, "mode", None) == "custom"
            and getattr(existing.settings, "laya_custom_subfolder", None) == chosen
        ):
            return existing
        engine = LayaDecisionEngine(
            settings.model_copy(
                update={
                    "laya_enabled": True,
                    "laya_mode": "custom",
                    "laya_custom_subfolder": chosen,
                }
            )
        )
        engine.load()
        return engine

    existing = getattr(state, "laya", None)
    if (
        existing is not None
        and getattr(existing, "enabled", False)
        and getattr(existing, "mode", None) == mode
    ):
        return existing

    return LayaDecisionEngine(
        settings.model_copy(update={"laya_enabled": True, "laya_mode": mode})
    )
