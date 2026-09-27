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

import {
  buildTransactionPayload,
  flowStatusHtml,
  generateTransactionId,
  resultErrorHtml,
  resultHtml,
  validateTransaction,
} from "../src/flow.js";

const VALID = {
  type: "TRANSFER",
  step: "700",
  amount: "181.50",
  name_orig: "C1",
  name_dest: "C2",
  old_balance_org: "181.50",
  old_balance_dest: "0",
  is_flagged_fraud: false,
};

test("el payload nunca incluye isFraud", () => {
  const { payload } = buildTransactionPayload(VALID);
  assert.equal("isFraud" in payload, false);
  assert.equal("is_flagged_fraud" in payload, true);
});

test("genera transaction_id cuando no se provee", () => {
  const { payload } = buildTransactionPayload(VALID);
  assert.match(payload.transaction_id, /^ui-/);
  const id = generateTransactionId();
  assert.notEqual(payload.transaction_id, id);
});

test("payload válido se construye con números y tipo", () => {
  const { payload, errors } = buildTransactionPayload(VALID);
  assert.deepEqual(errors, []);
  assert.equal(payload.amount, 181.5);
  assert.equal(payload.step, 700);
  assert.equal(payload.type, "TRANSFER");
  assert.equal(typeof payload.is_flagged_fraud, "boolean");
});

test("rechaza importe negativo y cuentas vacías", () => {
  const { errors } = buildTransactionPayload({ ...VALID, amount: "-1", name_orig: "" });
  assert.ok(errors.some((e) => e.includes("importe")));
  assert.ok(errors.some((e) => e.includes("origen")));
});

test("validateTransaction acepta un payload correcto", () => {
  const { payload } = buildTransactionPayload(VALID);
  assert.deepEqual(validateTransaction(payload), []);
});

test("resultHtml muestra latencia y event_id del backend", () => {
  const html = resultHtml({
    transaction_id: "T1",
    event_id: "live:decision.created:T1",
    source: "live",
    primary_decision: "SUSPICIOUS",
    primary_score: 0.37,
    final_decision: "FRAUD",
    laya: { invoked: true, status: "succeeded", decision: "FRAUD" },
    latency: { total_ms: 8.4, rules_ms: 0.1, ml_ms: 7.0, graph_ms: 0.1, laya_ms: 1.2, serialization_ms: 0.03 },
  });
  assert.match(html, /live:decision\.created:T1/);
  assert.match(html, /8\.4 ms/);
  assert.match(html, /FRAUD/);
});

test("resultErrorHtml no expone stack traces como mensaje", () => {
  const html = resultErrorHtml("No fue posible completar la evaluación de Laya.", "LAYA_ERROR");
  assert.match(html, /LAYA_ERROR/);
  assert.match(html, /fallback/);
});

test("flowStatusHtml reporta métricas del flujo", () => {
  const html = flowStatusHtml({
    state: "running",
    source: "replay",
    processed: 127,
    fraud: 8,
    suspicious: 21,
    legitimate: 98,
    errors: 0,
    throughput_tps: 640.5,
    latency_p95_ms: 18.2,
  });
  assert.match(html, /127/);
  assert.match(html, /Replay/);
  assert.match(html, /18\.2 ms/);
});
