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

import { graphDetail, graphElements } from "../src/graph.js";
import { flowStatusHtml } from "../src/flow.js";

const DATA = {
  transaction: {
    transaction_id: "R42",
    source: "replay",
    type: "TRANSFER",
    amount: 1250.5,
    name_orig: "C1",
    name_dest: "C2",
  },
  context: {
    origin_degree_before: { value: 3, description: "Transacciones previas de la cuenta origen" },
    destination_degree_before: { value: 1, description: "Transacciones previas de la cuenta destino" },
  },
  decision: {
    primary_decision: "SUSPICIOUS",
    primary_score: 0.37,
    final_decision: "FRAUD",
    laya: { invoked: true, decision: "FRAUD" },
  },
  graph: {
    nodes: [
      { id: "C1", category: "ORIGIN", degree: 3, risk: false },
      { id: "C2", category: "DESTINATION", degree: 1, risk: true },
    ],
    edges: [{ source: "C1", target: "C2", count: 2 }],
  },
  note: "Subgrafo de prueba",
};

test("graphElements construye nodos y aristas con color/riesgo", () => {
  const elements = graphElements(DATA.graph);
  const nodes = elements.filter((el) => el.data && el.data.category);
  const edges = elements.filter((el) => el.data && el.data.source);
  assert.equal(nodes.length, 2);
  assert.equal(edges.length, 1);
  const risky = nodes.find((el) => el.data.id === "C2");
  assert.equal(risky.data.risk, true);
  assert.equal(risky.data.color, "#dc2626");
  assert.equal(edges[0].data.weight, 2);
});

test("graphDetail incluye descripciones, transacción y decisión", () => {
  const html = graphDetail(DATA);
  assert.match(html, /Transacciones previas de la cuenta origen/);
  assert.match(html, /R42/);
  assert.match(html, /Fraude/);
  assert.match(html, /Subgrafo de prueba/);
});

test("flowStatusHtml incluye ETA cuando el flujo corre", () => {
  const html = flowStatusHtml({
    state: "running",
    total: 100000,
    processed: 50000,
    throughput_tps: 5000,
    fraud: 1,
    suspicious: 0,
    legitimate: 0,
    errors: 0,
    latency_p95_ms: 1.2,
  });
  assert.match(html, /ETA/);
  assert.match(html, /50,000 \/ 100,000/);
});
