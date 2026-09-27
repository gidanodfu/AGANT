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

import { rowsToTransactions } from "../src/import.js";

test("convierte filas (ES) y genera transaction_id", () => {
  const { transactions, errors } = rowsToTransactions([
    { tipo: "TRANSFER", importe: "1,250.50", cuenta_origen: "C1", saldo_origen: "2000", cuenta_destino: "C2", saldo_destino: "0" },
  ]);
  assert.deepEqual(errors, []);
  assert.equal(transactions.length, 1);
  assert.equal(transactions[0].type, "TRANSFER");
  assert.equal(transactions[0].amount, 1250.5);
  assert.match(transactions[0].transaction_id, /^imp-/);
});

test("rechaza isFraud", () => {
  const { transactions, errors } = rowsToTransactions([
    { type: "PAYMENT", amount: 10, name_orig: "C1", old_balance_org: 10, name_dest: "M1", old_balance_dest: 0, isFraud: 1 },
  ]);
  assert.equal(transactions.length, 0);
  assert.match(errors[0].error, /isFraud/);
});

test("rechaza tipo inválido y cuentas vacías", () => {
  const { transactions, errors } = rowsToTransactions([
    { type: "NOPE", amount: 10, name_orig: "C1", old_balance_org: 10, name_dest: "M1", old_balance_dest: 0 },
    { type: "PAYMENT", amount: 10, name_orig: "", old_balance_org: 10, name_dest: "M1", old_balance_dest: 0 },
  ]);
  assert.equal(transactions.length, 0);
  assert.equal(errors.length, 2);
});
