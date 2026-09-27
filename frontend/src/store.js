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

import { MAX_LIST, MAX_RECENT_ERRORS, MAX_RECENT_TRANSACTIONS } from "./config.js";

const SEEN_MAX = 5000;

const state = {
  transactions: [],
  decisions: [],
  laya: [],
  errors: [],
  metrics: null,
  replayMetrics: null,
  stages: null,
  system: null,
  health: null,
  connection: "connecting",
  seen: new Map(),
  decisionByKey: new Map(),
  counters: { events: 0, dropped: 0, transactions: 0, decisions: 0, laya: 0 },
};

const listeners = new Set();

export function getState() {
  return state;
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function emit(channel, item) {
  for (const listener of listeners) listener(channel, item);
}

function push(list, item, max = MAX_LIST) {
  list.push(item);
  if (list.length > max) list.splice(0, list.length - max);
}

export function ingestEvent(event) {
  if (!event || !event.event_id) return false;
  // La identidad incluye la secuencia: un mismo event_id puede repetirse
  // (p. ej. flow.status o reenvíos con igual transaction_id).
  const key = `${event.event_id}:${event.sequence ?? 0}`;
  if (state.seen.has(key)) return false;
  state.seen.set(key, 1);
  if (state.seen.size > SEEN_MAX) {
    state.seen.delete(state.seen.keys().next().value);
  }
  state.counters.events += 1;

  if (event.event_type === "transaction.created") {
    state.counters.transactions += 1;
    push(state.transactions, event);
    emit("transactions", event);
  } else if (event.event_type === "decision.created") {
    state.counters.decisions += 1;
    const payload = event.payload || {};
    if (payload.transaction_id) {
      state.decisionByKey.set(`${event.source}:${payload.transaction_id}`, payload);
    }
    push(state.decisions, event, MAX_RECENT_TRANSACTIONS);
    emit("decisions", event);
  } else if (event.event_type === "laya.decision") {
    state.counters.laya += 1;
    push(state.laya, event);
    emit("laya", event);
  } else if (event.event_type === "system.error") {
    push(state.errors, event, MAX_RECENT_ERRORS);
    emit("errors", event);
  } else {
    emit(event.event_type, event);
  }
  return true;
}

export function setMetrics(snapshot) {
  // Acepta la forma canónica {snapshots:{live,replay},...} y también
  // {live,replay} por si un canal la emitiera sin envoltorio.
  const snaps = snapshot?.snapshots || (snapshot && (snapshot.live || snapshot.replay) ? snapshot : null);
  state.metrics = snaps?.live || null;
  state.replayMetrics = snaps?.replay || null;
  state.stages = snapshot?.stages || null;
  if (snapshot?.event_bus) {
    state.counters.dropped = snapshot.event_bus.events_dropped || 0;
  }
  emit("metrics", state.metrics);
}

export function setSystem(system, health) {
  if (system) state.system = system;
  if (health) state.health = health;
  emit("system", state.system);
}

export function setConnection(connection) {
  state.connection = connection;
  emit("connection", connection);
}
