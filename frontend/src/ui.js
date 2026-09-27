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

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function fmtMs(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Number(value).toFixed(1)} ms`;
}

export function fmtPct(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(Number(value) * 100).toFixed(digits)} %`;
}

export function fmtScore(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toFixed(4);
}

export function fmtNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toLocaleString("es-PE");
}

const DECISION_META = {
  FRAUD: { cls: "badge-danger", dot: "dot-danger", label: "Fraude" },
  SUSPICIOUS: { cls: "badge-warning", dot: "dot-warning", label: "Sospechosa" },
  LEGITIMATE: { cls: "badge-success", dot: "dot-success", label: "Legítima" },
};

export function decisionBadge(decision) {
  const meta = DECISION_META[decision] || { cls: "badge-neutral", dot: "dot-neutral", label: decision || "—" };
  return `<span class="badge ${meta.cls}"><span class="dot ${meta.dot}"></span>${escapeHtml(meta.label)}</span>`;
}

export function sourceBadge(source) {
  const live = source === "live";
  return `<span class="badge ${live ? "badge-info" : "badge-neutral"}">${live ? "Live" : "Replay"}</span>`;
}

export function statusDot(status) {
  const map = {
    ready: "dot-success",
    loading: "dot-warning animate-pulse",
    disabled: "dot-neutral",
    unavailable: "dot-danger",
    failed: "dot-danger",
  };
  return `<span class="dot ${map[status] || "dot-neutral"}"></span>`;
}

export function decisionRow(payload) {
  const laya = payload.laya || {};
  const latency = payload.latency || {};
  return `
    <tr class="border-b border-line h-9 hover:bg-hover">
      <td class="py-1 pr-3 font-mono text-xs max-w-[12rem] truncate">${escapeHtml(payload.transaction_id)}</td>
      <td class="py-1 pr-3">${sourceBadge(payload.source)}</td>
      <td class="py-1 pr-3">${decisionBadge(payload.primary_decision)}</td>
      <td class="py-1 pr-3 font-mono text-xs text-right tabular-nums">${fmtScore(payload.primary_score)}</td>
      <td class="py-1 pr-3">${decisionBadge(payload.final_decision)}</td>
      <td class="py-1 pr-3 text-xs text-fg-secondary">${escapeHtml(laya.status || "—")}</td>
      <td class="py-1 pr-3 font-mono text-xs text-right tabular-nums">${laya.invoked ? fmtMs(laya.latency_ms) : "—"}</td>
      <td class="py-1 text-xs text-fg-muted text-right tabular-nums">${fmtMs(latency.total_ms)}</td>
    </tr>`;
}

export function transactionRow(payload) {
  return `
    <tr class="border-b border-line h-9 hover:bg-hover">
      <td class="py-1 pr-3 font-mono text-xs max-w-[12rem] truncate">${escapeHtml(payload.transaction_id)}</td>
      <td class="py-1 pr-3">${sourceBadge(payload.source)}</td>
      <td class="py-1 pr-3 text-xs text-fg-secondary">${escapeHtml(payload.type)}</td>
      <td class="py-1 pr-3 font-mono text-xs text-right tabular-nums">${fmtNumber(payload.amount)}</td>
      <td class="py-1 pr-3 font-mono text-xs max-w-[10rem] truncate">${escapeHtml(payload.name_orig)}</td>
      <td class="py-1 font-mono text-xs max-w-[10rem] truncate">${escapeHtml(payload.name_dest)}</td>
    </tr>`;
}

export function metricCard(label, value, icon) {
  return `
    <div class="panel p-3">
      <div class="flex items-center gap-2 text-xs text-fg-muted"><i data-lucide="${icon}" class="w-3.5 h-3.5"></i>${escapeHtml(label)}</div>
      <p class="mt-1 text-lg font-semibold tabular-nums text-fg">${escapeHtml(value)}</p>
    </div>`;
}

export function emptyState(text) {
  return `<p class="text-sm text-muted py-6 text-center">${escapeHtml(text)}</p>`;
}

function layaLabel(laya) {
  const status = laya?.status;
  if (!laya?.invoked) {
    if (status === "disabled") return '<span class="text-muted">Deshabilitada</span>';
    if (status === "unavailable") return '<span class="text-muted">No disponible</span>';
    if (status === "failed") return '<span class="text-danger">Error</span>';
    return '<span class="text-muted">Omitida</span>';
  }
  if (status === "failed") return '<span class="text-danger">Error</span>';
  return decisionBadge(laya.decision);
}

function statusCell(payload) {
  const level = Number(payload.fallback_level ?? 0);
  if (level > 0) {
    return `<span class="inline-flex items-center gap-1.5 text-warning"><span class="dot dot-warning"></span>Fallback (nivel ${level})</span>`;
  }
  return '<span class="inline-flex items-center gap-1.5 text-success"><span class="dot dot-success"></span>Procesada</span>';
}

function detailSection(title, inner) {
  return `<div>
    <h4 class="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">${escapeHtml(title)}</h4>
    <div class="text-sm space-y-0.5">${inner}</div>
  </div>`;
}

function kv(label, value) {
  return `<div class="flex justify-between gap-3"><span class="text-muted">${escapeHtml(label)}</span><span class="font-mono text-right break-all">${value}</span></div>`;
}

function activityDetail(payload) {
  const tx = payload.transaction || {};
  const evidence = payload.state?.evidence || {};
  const graph = evidence.graph?.context || {};
  const ml = evidence.ml || {};
  const laya = payload.laya || {};
  const lat = payload.latency || {};
  const rules = (evidence.rules || []).filter((rule) => rule.triggered);

  const transaction = [
    kv("ID", escapeHtml(payload.transaction_id)),
    kv("Source", sourceBadge(payload.source)),
    kv("Evento", escapeHtml(payload.event_id || "—")),
    kv("Timestamp", escapeHtml(payload.decided_at || "—")),
    kv("Tipo", escapeHtml(tx.type || "—")),
    kv("Importe", fmtNumber(tx.amount)),
    kv("Cuenta origen", escapeHtml(tx.name_orig || "—")),
    kv("Cuenta destino", escapeHtml(tx.name_dest || "—")),
    kv("Paso", escapeHtml(tx.step ?? "—")),
  ].join("");

  const result = [
    kv("Primaria", decisionBadge(payload.primary_decision)),
    kv("Score", fmtScore(payload.primary_score)),
    kv("Final", decisionBadge(payload.final_decision)),
    kv("Fallback", escapeHtml(payload.fallback_reason || "—")),
  ].join("");

  const rulesHtml = rules.length
    ? rules.map((r) => `<div class="flex justify-between gap-3"><span class="font-mono text-xs">${escapeHtml(r.rule_id)}</span><span class="text-right">${escapeHtml(r.reason || r.severity || "")}</span></div>`).join("")
    : '<p class="text-muted">Sin reglas activadas.</p>';

  const mlHtml = [
    kv("Score", fmtScore(ml.score)),
    kv("Decisión", ml.decision ? decisionBadge(ml.decision) : "—"),
    kv("Modelo", escapeHtml(payload.model_version || ml.model_version || "—")),
    kv("Features", escapeHtml(payload.feature_version || ml.feature_version || "—")),
  ].join("");

  const graphHtml = [
    kv("Estado", escapeHtml(evidence.graph?.status || "—")),
    kv("Grado origen", fmtNumber(graph.origin_degree_before)),
    kv("Grado destino", fmtNumber(graph.destination_degree_before)),
    kv("Destinos únicos origen", fmtNumber(graph.origin_unique_destinations_before)),
    kv("Orígenes únicos destino", fmtNumber(graph.destination_unique_origins_before)),
    kv("Aristas previas", fmtNumber(graph.edge_count_before)),
    kv("Arista vista", fmtNumber(graph.edge_seen_before)),
  ].join("");

  const layaHtml = [
    kv("Invocado", laya.invoked ? "sí" : "no"),
    kv("Estado", escapeHtml(laya.status || "—")),
    kv("Resultado", laya.decision ? decisionBadge(laya.decision) : "—"),
    kv("Confianza", laya.confidence != null ? fmtScore(laya.confidence) : "—"),
    kv("Modo", escapeHtml(laya.mode || "—")),
  ].join("");

  const latency = [
    kv("Rules", fmtMs(lat.rules_ms)),
    kv("ML", fmtMs(lat.ml_ms)),
    kv("Graph", fmtMs(lat.graph_ms)),
    kv("Laya", laya.invoked ? fmtMs(lat.laya_ms) : "—"),
    kv("Serialización", fmtMs(lat.serialization_ms)),
    kv("EventBus", fmtMs(lat.event_ms)),
    kv("Fallback", fmtMs(lat.fallback_ms)),
    kv("Total", fmtMs(lat.total_ms)),
  ].join("");

  return `<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    ${detailSection("Transacción", transaction)}
    ${detailSection("Resultado", result)}
    ${detailSection("Laya", layaHtml)}
    ${detailSection("Rules", rulesHtml)}
    ${detailSection("ML", mlHtml)}
    ${detailSection("Graph", graphHtml)}
    <div class="md:col-span-3">${detailSection("Rendimiento", `<div class="grid grid-cols-2 sm:grid-cols-4 gap-2">${latency}</div>`)}</div>
  </div>`;
}

export function activityRow(payload) {
  const tx = payload.transaction || {};
  const laya = payload.laya || {};
  const lat = payload.latency || {};
  const rid = `act-${Math.random().toString(36).slice(2, 10)}`;
  const summary = `<tr class="border-b border-line hover:bg-hover cascade-enter">
    <td class="py-1 pr-3 whitespace-nowrap max-w-[12rem] truncate">
      <button type="button" data-detail="${rid}" class="inline-flex items-center gap-1 font-mono text-xs text-fg hover:underline focus-ring rounded">
        <i data-lucide="chevron-right" class="w-3 h-3 text-fg-muted"></i>${escapeHtml(payload.transaction_id)}
      </button>
    </td>
    <td class="py-1 pr-3">${sourceBadge(payload.source)}</td>
    <td class="py-1 pr-3 text-xs text-fg-secondary">${escapeHtml(tx.type || "—")}</td>
    <td class="py-1 pr-3 text-right font-mono text-xs tabular-nums">${fmtNumber(tx.amount)}</td>
    <td class="py-1 pr-3 font-mono text-xs max-w-[10rem] truncate">${escapeHtml(tx.name_orig || "—")}</td>
    <td class="py-1 pr-3 font-mono text-xs max-w-[10rem] truncate">${escapeHtml(tx.name_dest || "—")}</td>
    <td class="py-1 pr-3">${decisionBadge(payload.primary_decision)}</td>
    <td class="py-1 pr-3 font-mono text-xs text-right tabular-nums">${fmtScore(payload.primary_score)}</td>
    <td class="py-1 pr-3 text-xs">${layaLabel(laya)}</td>
    <td class="py-1 pr-3">${decisionBadge(payload.final_decision)}</td>
    <td class="py-1 pr-3 font-mono text-xs text-right tabular-nums">${laya.invoked ? fmtMs(laya.latency_ms) : "—"}</td>
    <td class="py-1 pr-3 font-mono text-xs text-right tabular-nums">${fmtMs(lat.total_ms)}</td>
    <td class="py-1 text-xs">${statusCell(payload)}</td>
  </tr>`;
  const detail = `<tr id="${rid}" class="hidden"><td colspan="13" class="bg-control p-4">${activityDetail(payload)}</td></tr>`;
  return summary + detail;
}
