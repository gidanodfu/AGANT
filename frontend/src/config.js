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

const hasWindow = typeof window !== "undefined";

export const API_BASE = hasWindow ? window.AGANT_API_BASE || "" : "";
export const WS_BASE = hasWindow
  ? window.AGANT_WS_BASE ||
    (location.protocol === "https:" ? "wss://" : "ws://") + location.host
  : "ws://localhost";

export const METRICS_REFRESH_MS = 2000;
export const RECONNECT_MAX_MS = 15000;
export const RENDER_PER_FRAME = 20;
export const MAX_LIST = 300;
export const MAX_RECENT_TRANSACTIONS = 100;
export const MAX_RECENT_ERRORS = 5;
