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

import { API_BASE } from "./config.js";

export class ApiError extends Error {
  constructor(message, { code = "INTERNAL_ERROR", status = 0, details = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function parse(response) {
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return body;
}

async function handle(response) {
  const body = await parse(response);
  if (!response.ok || (body && body.success === false)) {
    const error = body && body.error ? body.error : {};
    throw new ApiError(error.message || "No fue posible completar la solicitud.", {
      code: error.code || "INTERNAL_ERROR",
      status: response.status,
      details: error.details || null,
    });
  }
  return body ? body.data : null;
}

export async function apiGet(path) {
  return handle(await fetch(API_BASE + path, { headers: { Accept: "application/json" } }));
}

export async function apiPost(path, payload) {
  return handle(
    await fetch(API_BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
}
