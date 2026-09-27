# Copyright (C) 2026 Josue David (gidanodfu)
# https://github.com/gidanodfu/AGANT
#
# Este archivo es parte de AGANT y se distribuye bajo AGPL-3.0-or-later.
# El paquete `laya` y sus checkpoints son de terceros (Apache-2.0); este
# servicio sólo los invoca.

"""Servicio GPU opcional que envuelve Laya como motor de decisión aislado.

El backend lo consulta por HTTP cuando ``AGANT_LAYA_URL`` está definido;
el navegador nunca se conecta directamente a este servicio.
"""

from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

_SCHEMA = {
    "type": "object",
    "properties": {"risk": {"type": "string", "enum": ["LEGITIMATE", "SUSPICIOUS", "FRAUD"]}},
    "required": ["risk"],
}

_agent = None
_lock = threading.Lock()


def _load():
    global _agent
    import laya

    _agent = laya.load(
        os.environ.get("LAYA_MODEL_ID", "convaiinnovations/laya"),
        device=os.environ.get("LAYA_DEVICE", "cuda"),
        subfolder=os.environ.get("LAYA_SUBFOLDER", "typed-decisions"),
        fast=os.environ.get("LAYA_FAST", "1") not in ("0", "false", "False"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load()
    yield


app = FastAPI(title="AGANT Laya Service", lifespan=lifespan)


class DecideRequest(BaseModel):
    state: dict = Field(description="Estado estructurado de la decisión")


@app.get("/health")
def health() -> dict:
    return {"status": "ready" if _agent is not None else "loading"}


@app.post("/decide")
def decide(request: DecideRequest) -> dict:
    if _agent is None:
        return {"decision": "SUSPICIOUS", "confidence": None, "error": "laya no cargado"}
    with _lock:
        details = _agent.decide(request.state, schema=_SCHEMA, return_details=True)
    confidence = (details.confidence or {}).get("risk")
    return {"decision": details.values.get("risk"), "confidence": confidence}
