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

"""Punto de entrada del backend AGANT (FastAPI).

Composition root sin lógica de negocio: construye componentes, valida
arranque y conecta canales. Las decisiones viven en sus módulos.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .api import (
    routes_decision,
    routes_drift,
    routes_flow,
    routes_frontend,
    routes_graph,
    routes_import,
    routes_laya,
    routes_observability,
    routes_replay,
)
from .api.state import AppState, Store
from .config import Settings, get_settings
from .contracts import ApiResponse, Event, EventType, Source
from .decision import DecisionEngine, DecisionStateBuilder, LayaDecisionEngine
from .decision.batch_engine import BatchDecisionEngine
from .errors import AGANTError, ErrorManager, ValidationError
from .events import EventBus
from .evidence.engine import EvidenceEngine
from .evidence.graph_provider import GraphContextProvider
from .evidence.ml_provider import MLDecisionProvider
from .observability import LiveDriftMonitor, MetricsCollector, collect_startup_report
from .replay import ReplayController
from .service import DecisionService
from .ws import routes_ws

logger = logging.getLogger("agant")


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _build_state(settings: Settings) -> AppState:
    errors = ErrorManager()
    ml = MLDecisionProvider(settings)
    graph = GraphContextProvider(settings)
    evidence = EvidenceEngine(settings, graph_provider=graph, ml=ml)
    laya = LayaDecisionEngine(settings)
    engine = DecisionEngine(
        settings,
        evidence_engine=evidence,
        laya_engine=laya,
        state_builder=DecisionStateBuilder(settings),
    )
    metrics = MetricsCollector()
    errors.metrics = metrics
    batch_engine = BatchDecisionEngine(
        settings,
        None,
        laya,
        batch_size=settings.batch_size,
        graph=evidence.graph_provider,
        ml=evidence.ml,
        rules=evidence.rules,
        features=evidence.feature_builder,
    )
    return AppState(
        settings=settings,
        errors=errors,
        bus=EventBus(subscriber_queue=settings.max_events, history_size=settings.event_history),
        metrics=metrics,
        store=Store(),
        decision_engine=engine,
        ml=ml,
        laya=laya,
        live_drift=LiveDriftMonitor(settings),
        batch_engine=batch_engine,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    state: AppState = app.state.services
    if state.ml is not None:
        state.ml.load()
    if state.laya is not None:
        state.laya.load()
    report = collect_startup_report(state.settings, ml=state.ml, laya=state.laya)
    state.startup_report = report
    logger.info(report.summary())
    for component in report.components:
        if component.status.value not in ("ready", "disabled", "loading"):
            logger.warning("componente %s: %s (%s)", component.name, component.status.value, component.detail)
    try:
        yield
    finally:
        if state.replay is not None and state.replay.running():
            await state.replay.stop()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _publish_system_error(request: Request, payload_error, request_id: str) -> None:
    services = request.app.state.services
    bus = services.bus
    sequence = bus.next_sequence()
    bus.publish(
        Event(
            event_id=f"system:{EventType.SYSTEM_ERROR.value}:{sequence}",
            event_type=EventType.SYSTEM_ERROR,
            source=Source.LIVE,
            sequence=sequence,
            payload={
                "code": payload_error.code.value,
                "message": payload_error.message,
                "severity": payload_error.severity.value,
                "operation": request.url.path,
                "request_id": request_id,
            },
        )
    )


async def _agant_error_handler(request: Request, exc: AGANTError) -> JSONResponse:
    manager: ErrorManager = request.app.state.services.errors
    error = manager.log(exc, request_id=_request_id(request), operation=request.url.path)
    payload_error = manager.error_response(exc)
    _publish_system_error(request, payload_error, _request_id(request))
    body = ApiResponse[object].fail(payload_error, request_id=_request_id(request))
    return JSONResponse(status_code=error.status, content=body.model_dump(mode="json"))


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    manager: ErrorManager = request.app.state.services.errors
    error = ValidationError("validación de entrada", details={"campos": len(exc.errors())})
    manager.log(error, request_id=_request_id(request), operation=request.url.path)
    payload_error = manager.error_response(error)
    _publish_system_error(request, payload_error, _request_id(request))
    body = ApiResponse[object].fail(payload_error, request_id=_request_id(request))
    return JSONResponse(status_code=error.status, content=body.model_dump(mode="json"))


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    manager: ErrorManager = request.app.state.services.errors
    error = manager.log(exc, request_id=_request_id(request), operation=request.url.path)
    payload_error = manager.error_response(exc)
    _publish_system_error(request, payload_error, _request_id(request))
    body = ApiResponse[object].fail(payload_error, request_id=_request_id(request))
    return JSONResponse(status_code=error.status, content=body.model_dump(mode="json"))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    _configure_logging(settings)

    app = FastAPI(title="AGANT API", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.services = _build_state(settings)
    app.state.services.replay = ReplayController(app.state.services)
    app.state.decision_service = DecisionService(app.state.services)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Admin-Token", "X-Request-ID"],
    )

    @app.middleware("http")
    async def _assign_request_id(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.3f}"
        return response

    app.add_exception_handler(AGANTError, _agant_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)

    @app.get("/health", response_model=ApiResponse[dict])
    async def health(request: Request) -> ApiResponse[dict]:
        report = request.app.state.services.startup_report
        degraded = [component.name for component in report.degraded] if report is not None else []
        # En modo estricto, cualquier componente degradado (p. ej. modelo o
        # dataset ausente) marca el servicio como degradado; por defecto se
        # mantiene el comportamiento previo (solo componentes requeridos).
        ready = report is None or (report.ready and (not settings.health_strict or not degraded))
        return ApiResponse.ok(
            {
                "status": "ready" if ready else "degraded",
                "version": __version__,
                "env": settings.env,
                "degraded_components": degraded,
            },
            request_id=_request_id(request),
        )

    app.include_router(routes_decision.router)
    app.include_router(routes_observability.router)
    app.include_router(routes_replay.router)
    app.include_router(routes_flow.router)
    app.include_router(routes_import.router)
    app.include_router(routes_laya.router)
    app.include_router(routes_drift.router)
    app.include_router(routes_graph.router)
    app.include_router(routes_ws.router)
    routes_frontend.mount_frontend(app, settings.frontend_path)
    return app


app = create_app()
