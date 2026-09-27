// Copyright (C) 2026 Josue David (gidanodfu)
// https://github.com/gidanodfu/AGANT
//
// This file is part of AGANT.
//
// AGANT is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of
// the License, or (at your option) any later version.
//
// AGANT is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with AGANT. If not, see <https://www.gnu.org/licenses/>.

import { test } from "node:test";
import assert from "node:assert/strict";

import { activityRow } from "../src/ui.js";
import { errorsList } from "../src/views.js";

function payload(overrides = {}) {
  return {
    transaction_id: "L23143",
    source: "live",
    event_id: "live:decision.created:L23143",
    primary_decision: "LEGITIMATE",
    primary_score: 0.1949,
    final_decision: "LEGITIMATE",
    fallback_level: 0,
    fallback_reason: "grafo y ML disponibles",
    laya: { invoked: false, status: "skipped", decision: null, latency_ms: 0 },
    latency: {
      total_ms: 1.8,
      rules_ms: 0.02,
      ml_ms: 1.5,
      graph_ms: 0.02,
      laya_ms: 0,
      serialization_ms: 0.01,
      event_ms: 0.1,
      fallback_ms: 0.01,
    },
    transaction: {
      type: "TRANSFER",
      amount: 1250.5,
      name_orig: "C123",
      name_dest: "C987",
      step: 700,
      old_balance_org: 1250.5,
      old_balance_dest: 0,
    },
    state: {
      evidence: {
        rules: [{ rule_id: "R002", triggered: true, severity: "warning", reason: "alto riesgo" }],
        ml: { available: true, score: 0.1949, decision: "LEGITIMATE", model_version: "m1", feature_version: "online_v1" },
        graph: {
          status: "ready",
          context: {
            origin_degree_before: 0,
            destination_degree_before: 1,
            origin_unique_destinations_before: 0,
            destination_unique_origins_before: 1,
            edge_count_before: 0,
            edge_seen_before: 0,
          },
        },
      },
      features: {},
    },
    decided_at: "2026-09-26T17:00:00Z",
    ...overrides,
  };
}

test("fila muestra datos reales y oculta Laya ms cuando no se invocó", () => {
  const html = activityRow(payload());
  assert.match(html, /L23143/);
  assert.match(html, /Live/);
  assert.match(html, /TRANSFER/);
  assert.match(html, /1[.,]?250/);
  assert.match(html, /C123/);
  assert.match(html, /C987/);
  assert.match(html, /Omitida/);
  assert.match(html, /—/);
  assert.match(html, /Procesada/);
});

test("fila con Laya invocado muestra la decisión y latencia", () => {
  const html = activityRow(
    payload({
      primary_decision: "SUSPICIOUS",
      primary_score: 0.3742,
      final_decision: "FRAUD",
      laya: { invoked: true, status: "succeeded", decision: "FRAUD", latency_ms: 12.3 },
    })
  );
  assert.match(html, /Sospechosa/);
  assert.match(html, /Fraude/);
  assert.match(html, /12\.3 ms/);
});

test("fila REPLAY conserva el origen y el estado de fallback", () => {
  const html = activityRow(payload({ source: "replay", fallback_level: 1, fallback_reason: "grafo no disponible" }));
  assert.match(html, /Replay/);
  assert.match(html, /Fallback \(nivel 1\)/);
});

test("detalle expandible incluye transacción, reglas y grafo", () => {
  const html = activityRow(payload());
  assert.match(html, /data-detail=/);
  assert.match(html, /R002/);
  assert.match(html, /Grado destino/);
  assert.match(html, /Modelo/);
  assert.match(html, /Total/);
});

test("errorsList muestra system.error", () => {
  const html = errorsList([
    { payload: { code: "LAYA_ERROR", message: "No fue posible completar la evaluación de Laya.", severity: "recoverable", operation: "/api/v1/decision" } },
  ]);
  assert.match(html, /LAYA_ERROR/);
  assert.match(html, /No fue posible completar/);
});

test("errorsList sin errores muestra estado vacío", () => {
  assert.match(errorsList([]), /Sin errores recientes/);
});
