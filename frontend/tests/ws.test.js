// AGANT — Detección híbrida de fraude financiero (reglas + ML + grafo + Laya).
// Copyright (C) 2026 Josue David (gidanodfu)
// https://github.com/gidanodfu/AGANT
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

import { test } from "node:test";
import assert from "node:assert/strict";

import { resumePath } from "../src/ws.js";

test("resumePath sin secuencia no añade query", () => {
  assert.equal(resumePath("/api/v1/ws/events", 0), "/api/v1/ws/events");
});

test("resumePath con secuencia añade last_sequence", () => {
  assert.equal(
    resumePath("/api/v1/ws/events", 42),
    "/api/v1/ws/events?last_sequence=42",
  );
});
