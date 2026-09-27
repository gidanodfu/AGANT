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

import { createHistory, sparkline } from "../src/charts.js";
import { decisionToRow } from "../src/export.js";

test("sparkline devuelve polilínea con 2+ valores y vacío con menos", () => {
  assert.match(sparkline([1, 2, 3]), /polyline/);
  assert.doesNotMatch(sparkline([1]), /polyline/);
});

test("createHistory conserva el máximo", () => {
  const history = createHistory(3);
  [1, 2, 3, 4, 5].forEach((v) => history.push(v));
  assert.deepEqual(history.values(), [3, 4, 5]);
});

test("decisionToRow mapea campos del backend y Laya sin invocar", () => {
  const row = decisionToRow({
    transaction_id: "T1",
    source: "live",
    primary_decision: "LEGITIMATE",
    primary_score: 0.19,
    final_decision: "LEGITIMATE",
    laya: { invoked: false, status: "skipped" },
    latency: { total_ms: 1.8 },
    transaction: { type: "TRANSFER", amount: 1250.5, name_orig: "C1", name_dest: "C2" },
    event_id: "live:decision.created:T1",
  });
  assert.equal(row.transaction_id, "T1");
  assert.equal(row.laya_invocado, "no");
  assert.equal(row.laya_latencia_ms, "");
  assert.equal(row.cuenta_origen, "C1");
  assert.equal(row.total_ms, 1.8);
});
