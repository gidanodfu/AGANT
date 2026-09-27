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

"""Vistas de grafo: global reciente y subgrafo por transacción.

No inventa señales: usa cuentas/aristas observadas y las seis features de
grafo, con descripciones legibles.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Query, Request

from ..contracts import ApiResponse, GRAPH_FEATURE_NAMES
from ..data.paysim_db import connect
from ..errors import AGANTError, ErrorCode
from ..features import read_artifacts
from .deps import get_state

router = APIRouter(prefix="/api/v1", tags=["graph"])

CATEGORIES = ["ACCOUNT", "ORIGIN", "DESTINATION", "EDGE", "HISTORY", "RISK"]

DESCRIPTIONS = {
    "origin_degree_before": "Número de transacciones previas de la cuenta origen",
    "destination_degree_before": "Número de transacciones previas de la cuenta destino",
    "origin_unique_destinations_before": "Cuentas destino distintas que usó antes la cuenta origen",
    "destination_unique_origins_before": "Cuentas origen distintas que enviaron antes a la cuenta destino",
    "edge_count_before": "Veces que se vio antes esta misma arista (origen→destino)",
    "edge_seen_before": "1 si la arista ya existía antes; 0 si es nueva",
}

_DATASET_ID = re.compile(r"^R(\d+)$")


def _is_risky(item: dict, fraud_keys: set[tuple[str, str]]) -> bool:
    """Riesgo = señal del protocolo (``isFlaggedFraud``) o decisión final FRAUD."""
    if bool(item.get("is_flagged_fraud")):
        return True
    return (str(item.get("source")), str(item.get("transaction_id"))) in fraud_keys


def _touch(nodes: dict, edges: dict, origin: str, destination: str, risky: bool) -> None:
    for account, role in ((origin, "ORIGIN"), (destination, "DESTINATION")):
        node = nodes.setdefault(account, {"id": account, "roles": set(), "degree": 0, "risk": False})
        node["roles"].add(role)
        node["degree"] += 1
        node["risk"] = node["risk"] or risky
    key = (origin, destination)
    edge = edges.setdefault(key, {"source": origin, "target": destination, "count": 0})
    edge["count"] += 1


def _finalize(nodes: dict, edges: dict, center: dict | None = None) -> dict:
    node_list = []
    for node in nodes.values():
        roles = node["roles"]
        category = "ACCOUNT" if len(roles) > 1 else next(iter(roles))
        tags = [category]
        if node["degree"] > 1:
            tags.append("HISTORY")
        if node["risk"]:
            tags.append("RISK")
        entry = {"id": node["id"], "category": category, "tags": tags, "degree": node["degree"], "risk": node["risk"]}
        if center and node["id"] in center.values():
            entry["center"] = True
        node_list.append(entry)
    return {"nodes": node_list, "edges": list(edges.values()), "center": center or {}}


def _context_map(values: dict) -> dict:
    return {
        name: {"value": values.get(name), "description": DESCRIPTIONS.get(name, "")}
        for name in GRAPH_FEATURE_NAMES
    }


@router.get("/graph", response_model=ApiResponse[dict])
async def graph(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> ApiResponse[dict]:
    state = get_state(request)
    transactions = state.store.recent_transactions(limit)
    fraud_keys = state.store.fraud_keys()
    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str], dict] = {}
    for tx in transactions:
        origin = str(tx.get("name_orig"))
        destination = str(tx.get("name_dest"))
        _touch(nodes, edges, origin, destination, _is_risky(tx, fraud_keys))
    data = {
        **_finalize(nodes, edges),
        "categories": CATEGORIES,
        "bounded": True,
        "note": "Vista acotada a las últimas transacciones; no es el grafo completo. "
        "RISK = decisión FRAUD o isFlaggedFraud.",
    }
    return ApiResponse.ok(data, request_id=getattr(request.state, "request_id", "-"))


def _dataset_graph(settings, row_id: int, limit: int) -> dict | None:
    conn = connect(settings)
    row = conn.execute(
        "SELECT row_id, step, type, amount, nameOrig, oldbalanceOrg, nameDest, "
        "oldbalanceDest, isFlaggedFraud FROM transactions WHERE row_id = ?",
        [row_id],
    ).fetchone()
    if row is None:
        return None
    origin, destination = row[4], row[6]
    neighbors = conn.execute(
        "SELECT nameOrig, nameDest, isFlaggedFraud FROM transactions "
        "WHERE nameOrig = ? OR nameDest = ? OR nameOrig = ? OR nameDest = ? "
        "ORDER BY step DESC LIMIT ?",
        [origin, origin, destination, destination, limit],
    ).fetchall()

    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str], dict] = {}
    for source, dest, flagged in neighbors:
        _touch(nodes, edges, str(source), str(dest), bool(flagged))

    transaction = {
        "transaction_id": f"R{row[0]}",
        "source": "replay",
        "step": int(row[1]),
        "type": row[2],
        "amount": float(row[3]),
        "name_orig": origin,
        "old_balance_org": float(row[5]),
        "name_dest": destination,
        "old_balance_dest": float(row[7]),
    }

    context_values = None
    try:
        artifacts = read_artifacts(settings)
        features = artifacts.load_features()
        vector = features[row_id - 1]
        context_values = {name: float(vector[9 + i]) for i, name in enumerate(GRAPH_FEATURE_NAMES)}
    except (FileNotFoundError, IndexError, ValueError):
        context_values = None

    return {
        "transaction": transaction,
        "context": _context_map(context_values) if context_values else None,
        "graph": _finalize(nodes, edges, center={"origin": origin, "destination": destination}),
        "dataset_fraud": int(row[8]),
        "note": "Subgrafo del dataset completo (por cuenta), acotado por LIMIT. "
        "RISK = isFlaggedFraud (el dataset no tiene decisiones del modelo).",
    }


def _store_graph(state, transaction_id: str, limit: int) -> dict | None:
    decision = state.store.find_decision(transaction_id)
    if decision is None:
        return None
    transaction = decision.get("transaction") or {"transaction_id": transaction_id}
    origin = transaction.get("name_orig")
    destination = transaction.get("name_dest")
    fraud_keys = state.store.fraud_keys()
    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str], dict] = {}
    for account in (origin, destination):
        for item in state.store.neighborhood(str(account), limit):
            _touch(
                nodes,
                edges,
                str(item.get("name_orig")),
                str(item.get("name_dest")),
                _is_risky(item, fraud_keys),
            )
    if origin and destination:
        _touch(nodes, edges, str(origin), str(destination), _is_risky(transaction, fraud_keys))

    evidence = (decision.get("state") or {}).get("evidence") or {}
    context_values = (evidence.get("graph") or {}).get("context") or None
    return {
        "transaction": transaction,
        "decision": {
            "primary_decision": decision.get("primary_decision"),
            "primary_score": decision.get("primary_score"),
            "final_decision": decision.get("final_decision"),
            "laya": decision.get("laya"),
            "latency": decision.get("latency"),
        },
        "context": _context_map(context_values) if context_values else None,
        "graph": _finalize(nodes, edges, center={"origin": origin, "destination": destination}),
        "note": "Subgrafo de la ventana reciente en memoria (tráfico live). "
        "RISK = decisión FRAUD o isFlaggedFraud.",
    }


@router.get("/transactions/{transaction_id}/graph", response_model=ApiResponse[dict])
async def transaction_graph(
    request: Request,
    transaction_id: str,
    limit: int = Query(default=120, ge=10, le=400),
) -> ApiResponse[dict]:
    state = get_state(request)
    match = _DATASET_ID.match(transaction_id)
    data = None
    if match and state.settings.paysim_csv.exists():
        data = _dataset_graph(state.settings, int(match.group(1)), limit)
    if data is None:
        data = _store_graph(state, transaction_id, limit)
    if data is None:
        raise AGANTError(
            f"transacción no encontrada: {transaction_id}",
            code=ErrorCode.VALIDATION_ERROR,
            status=404,
            public_message="No se encontró la transacción indicada en el dataset ni en la ventana reciente.",
        )
    data["categories"] = CATEGORIES
    data["descriptions"] = DESCRIPTIONS
    return ApiResponse.ok(data, request_id=getattr(request.state, "request_id", "-"))
