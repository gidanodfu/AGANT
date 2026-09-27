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

import {
  decisionBadge,
  escapeHtml,
  fmtMs,
  fmtNumber,
  fmtScore,
  sourceBadge,
  statusDot,
} from "./ui.js";

export const TX_TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"];

export function generateTransactionId() {
  const stamp = Date.now().toString(36);
  const random = Math.random().toString(36).slice(2, 8);
  return `ui-${stamp}-${random}`;
}

function toNumber(value) {
  if (value === "" || value === null || value === undefined) return NaN;
  return Number(value);
}

export function validateTransaction(payload) {
  const errors = [];
  if (!TX_TYPES.includes(payload.type)) errors.push("Tipo de operación inválido.");
  if (!(payload.amount >= 0)) errors.push("El importe debe ser un número mayor o igual a 0.");
  if (!(payload.old_balance_org >= 0)) errors.push("El saldo origen debe ser mayor o igual a 0.");
  if (!(payload.old_balance_dest >= 0)) errors.push("El saldo destino debe ser mayor o igual a 0.");
  if (!payload.name_orig) errors.push("La cuenta origen es obligatoria.");
  if (!payload.name_dest) errors.push("La cuenta destino es obligatoria.");
  if (!Number.isInteger(payload.step) || payload.step < 0) errors.push("El paso debe ser un entero ≥ 0.");
  return errors;
}

/** Construye el payload del contrato Transaction. Nunca incluye isFraud. */
export function buildTransactionPayload(input = {}) {
  const payload = {
    transaction_id: (input.transaction_id || "").trim() || generateTransactionId(),
    step: Number.isFinite(Number(input.step)) ? Math.trunc(Number(input.step)) : 0,
    type: input.type || "TRANSFER",
    amount: toNumber(input.amount),
    name_orig: (input.name_orig || "").trim(),
    old_balance_org: toNumber(input.old_balance_org),
    name_dest: (input.name_dest || "").trim(),
    old_balance_dest: toNumber(input.old_balance_dest),
    is_flagged_fraud: Boolean(input.is_flagged_fraud),
  };
  return { payload, errors: validateTransaction(payload) };
}

const STATUS_STYLES = {
  idle: "text-fg-muted",
  processing: "text-warning",
  success: "text-success",
  warning: "text-warning",
  error: "text-danger",
};

export function statusPill(status, label) {
  return `<span class="inline-flex items-center gap-1.5 text-sm font-medium ${STATUS_STYLES[status] || ""}">${statusDot(status === "success" ? "ready" : status === "processing" ? "loading" : status === "error" ? "failed" : "disabled")}${escapeHtml(label)}</span>`;
}

export function resultHtml(result) {
  if (!result) return "";
  const laya = result.laya || {};
  const latency = result.latency || {};
  const stages = [
    ["Reglas", latency.rules_ms],
    ["ML", latency.ml_ms],
    ["Grafo", latency.graph_ms],
    ["Laya", laya.invoked ? latency.laya_ms : null],
    ["Serialización", latency.serialization_ms],
  ];
  return `
    <dl class="text-sm space-y-2">
      <div class="flex items-center justify-between"><dt class="text-muted">Estado</dt><dd>${statusPill("success", "Procesada")}</dd></div>
      <div class="flex items-center justify-between"><dt class="text-muted">Transacción</dt><dd class="font-mono text-xs">${escapeHtml(result.transaction_id)}</dd></div>
      <div class="flex items-center justify-between"><dt class="text-muted">Evento</dt><dd class="font-mono text-[11px] break-all text-right">${escapeHtml(result.event_id || "—")}</dd></div>
      <div class="flex items-center justify-between"><dt class="text-muted">Source</dt><dd>${sourceBadge(result.source)}</dd></div>
      <div class="flex items-center justify-between"><dt class="text-muted">Primaria</dt><dd>${decisionBadge(result.primary_decision)}</dd></div>
      <div class="flex items-center justify-between"><dt class="text-muted">Score</dt><dd class="font-mono">${fmtScore(result.primary_score)}</dd></div>
      <div class="flex items-center justify-between"><dt class="text-muted">Laya</dt><dd>${laya.invoked ? escapeHtml(laya.status) + " → " + escapeHtml(String(laya.decision || "—")) : escapeHtml(laya.status || "—")}</dd></div>
      <div class="flex items-center justify-between"><dt class="text-muted">Final</dt><dd>${decisionBadge(result.final_decision)}</dd></div>
      <div class="flex items-center justify-between border-t border-line pt-2"><dt class="text-muted">Latencia total</dt><dd class="font-mono font-semibold">${fmtMs(latency.total_ms)}</dd></div>
      <div class="grid grid-cols-5 gap-1 pt-1 text-center text-[11px] text-muted">
        ${stages.map(([label, value]) => `<div><div class="font-mono text-fg">${value === null || value === undefined ? "—" : fmtMs(value)}</div>${label}</div>`).join("")}
      </div>
    </dl>`;
}

export function resultErrorHtml(message, code) {
  return `
    <div class="text-sm">
      ${statusPill("error", "No se pudo procesar")}
      <p class="mt-2 text-muted">${escapeHtml(message)}</p>
      ${code ? `<p class="mt-1 font-mono text-xs text-muted">Código: ${escapeHtml(code)}</p>` : ""}
      <p class="mt-1 text-xs text-muted">Se aplicó la política de fallback de AGANT.</p>
    </div>`;
}

function fmtEta(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m} min ${s} s` : `${s} s`;
}

export function flowStatusHtml(status) {
  if (!status) return "";
  const remaining = (status.total || 0) - (status.processed || 0);
  const tps = Number(status.throughput_tps || 0);
  const eta = tps > 0 && remaining > 0 ? fmtEta(remaining / tps) : "—";
  const rows = [
    ["Estado", escapeHtml(status.state)],
    ["Procesadas", `${fmtNumber(status.processed)} / ${fmtNumber(status.total)}`],
    ["Fraudes", fmtNumber(status.fraud)],
    ["Sospechosas", fmtNumber(status.suspicious)],
    ["Legítimas", fmtNumber(status.legitimate)],
    ["Errores", fmtNumber(status.errors)],
    ["Throughput", `${tps.toFixed(0)} tx/s`],
    ["Latencia p95", fmtMs(status.latency_p95_ms)],
    ["Modo", escapeHtml(status.decision_mode || "hybrid")],
    ["ETA", status.state === "running" ? eta : "—"],
  ];
  const source = status.source
    ? `<span class="ml-2">${sourceBadge(status.source)}</span>`
    : "";
  const dot =
    status.state === "running"
      ? "loading"
      : status.state === "finished"
        ? "ready"
        : status.state === "error"
          ? "failed"
          : "disabled";
  let note = "";
  if (status.state === "error") {
    note = `<p class="mt-2 text-sm text-danger">El flujo falló${status.error ? ` (${escapeHtml(status.error)})` : ""}. Se aplicó la política de fallback.</p>`;
  } else if (status.laya_mode === "pretrained" && !status.laya_active) {
    note = `<p class="mt-2 text-xs text-warning">Laya no está disponible en este servidor; las decisiones usan fallback.</p>`;
  }
  return `
    <div class="flex items-center gap-1 text-sm font-medium">${statusDot(dot)}${escapeHtml(status.state)}${source}</div>
    <dl class="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
      ${rows.map(([label, value]) => `<div><dt class="text-xs text-muted">${label}</dt><dd class="font-mono">${value}</dd></div>`).join("")}
    </dl>${note}`;
}
