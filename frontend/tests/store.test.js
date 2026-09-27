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

import { getState, ingestEvent } from "../src/store.js";

function flowStatus(sequence) {
  return {
    event_id: "live:flow.status:flow",
    event_type: "flow.status",
    source: "live",
    sequence,
    payload: { state: "running" },
  };
}

test("event_id repetido con distinta secuencia se acepta (progreso no se congela)", () => {
  assert.equal(ingestEvent(flowStatus(1001)), true);
  assert.equal(ingestEvent(flowStatus(1002)), true);
  assert.equal(ingestEvent(flowStatus(1003)), true);
});

test("misma identidad (event_id + sequence) se descarta una vez", () => {
  assert.equal(ingestEvent(flowStatus(2001)), true);
  assert.equal(ingestEvent(flowStatus(2001)), false);
});

test("mismo transaction_id en secuencias distintas no se pierde", () => {
  const event = (sequence) => ({
    event_id: "live:transaction.created:TX-REPETIDA",
    event_type: "transaction.created",
    source: "live",
    sequence,
    payload: { transaction_id: "TX-REPETIDA" },
  });
  assert.equal(ingestEvent(event(1)), true);
  assert.equal(ingestEvent(event(2)), true);
});

test("los contadores por canal crecen pese al tope de la lista", () => {
  const before = getState().counters.transactions;
  for (let i = 0; i < 5; i += 1) {
    ingestEvent({
      event_id: `live:transaction.created:T${i}`,
      event_type: "transaction.created",
      source: "live",
      sequence: i,
      payload: { transaction_id: `T${i}` },
    });
  }
  assert.equal(getState().counters.transactions, before + 5);
});
