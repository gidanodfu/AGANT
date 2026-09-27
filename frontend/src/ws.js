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

import { RECONNECT_MAX_MS, WS_BASE } from "./config.js";

export const CONNECTION_LABELS = {
  connecting: "Conectando…",
  connected: "Conectado",
  reconnecting: "Reconectando…",
  disconnected: "Sin conexión",
  error: "Error de conexión",
};

export function createSocket({ path = "/api/v1/ws/events", onEvent, onState }) {
  let socket = null;
  let attempt = 0;
  let timer = null;
  let stopped = false;
  let state = "connecting";

  function update(next) {
    state = next;
    if (onState) onState(next);
  }

  function connect() {
    if (stopped) return;
    update(attempt === 0 ? "connecting" : "reconnecting");
    try {
      socket = new WebSocket(WS_BASE + path);
    } catch (error) {
      schedule();
      return;
    }
    socket.onopen = () => {
      attempt = 0;
      update("connected");
    };
    socket.onmessage = (event) => {
      if (!onEvent) return;
      try {
        onEvent(JSON.parse(event.data));
      } catch {
        /* evento no interpretable: se ignora */
      }
    };
    socket.onerror = () => {
      update("error");
    };
    socket.onclose = () => {
      if (stopped) return;
      socket = null;
      schedule();
    };
  }

  function schedule() {
    const delay = Math.min(RECONNECT_MAX_MS, 500 * 2 ** attempt);
    attempt += 1;
    update("reconnecting");
    timer = setTimeout(connect, delay);
  }

  function close() {
    stopped = true;
    if (timer) clearTimeout(timer);
    if (socket) socket.close();
    update("disconnected");
  }

  connect();
  return { close, get state() { return state; } };
}
