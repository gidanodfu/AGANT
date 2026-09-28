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

import {
  activityRow,
  decisionRow,
  emptyState,
  escapeHtml,
  fmtMs,
  fmtNumber,
  metricCard,
  statusDot,
  transactionRow,
} from "./ui.js";

export const NAV = [
  { path: "/home", group: "Operación", label: "Inicio", icon: "layout-dashboard", title: "Panel", subtitle: "Estado general del sistema" },
  { path: "/nueva-transaccion", group: "Operación", label: "Nueva transacción", icon: "plus-circle", title: "Nueva transacción", subtitle: "Crear, enviar y observar el procesamiento" },
  { path: "/transacciones", group: "Operación", label: "Transacciones", icon: "arrow-left-right", title: "Transacciones", subtitle: "Flujo en tiempo real" },
  { path: "/decisiones", group: "Análisis", label: "Decisiones", icon: "gavel", title: "Decisiones", subtitle: "Solo evaluaciones de Laya" },
  { path: "/grafo", group: "Análisis", label: "Grafo", icon: "share-2", title: "Grafo", subtitle: "Contexto de relación (acotado)" },
  { path: "/laya", group: "Motor", label: "Laya", icon: "brain", title: "Laya", subtitle: "Configurar y probar el motor de decisión" },
];

export function renderLayaPage() {
  const field = "mt-1 w-full control";
  return `
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div class="panel">
        <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center gap-2">
          <i data-lucide="settings-2" class="w-4 h-4"></i> Configurar Laya
        </div>
        <div class="p-4 space-y-3">
          <label class="block text-sm"><span class="text-muted">Modo</span>
            <select id="laya-mode-toggle" class="${field}">
              <option value="disabled">disabled</option>
              <option value="pretrained" selected>pretrained</option>
              <option value="custom">custom</option>
            </select>
          </label>
          <label class="block text-sm"><span class="text-muted">Checkpoint</span>
            <select id="laya-subfolder" class="${field}"></select>
          </label>
          <label class="inline-flex items-center gap-2 text-sm"><input id="laya-warmup" type="checkbox" checked /> warm-up al cargar</label>
          <div class="flex items-center gap-2">
            <button id="laya-load" class="btn btn-primary disabled:opacity-60">
              <i data-lucide="download-cloud" class="w-4 h-4"></i> <span id="laya-load-label">Cargar</span>
            </button>
            <button id="laya-test" class="btn">
              <i data-lucide="flask-conical" class="w-4 h-4"></i> Probar
            </button>
          </div>
          <p id="laya-load-status" class="text-xs text-muted"></p>
          <p class="text-[11px] text-warning">Cargar un checkpoint consume VRAM y puede tardar ~1 min. Los scores de Laya son ordinales no calibrados.</p>
        </div>
      </div>
      <div class="panel">
        <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center gap-2">
          <i data-lucide="activity" class="w-4 h-4"></i> Estado
        </div>
        <div class="p-4" id="laya-status"></div>
      </div>
    </section>
    <section class="mt-5 panel">
      <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center gap-2">
        <i data-lucide="braces" class="w-4 h-4"></i> Resultado / preview del estado enviado a Laya
      </div>
      <pre id="laya-result" class="p-4 text-xs overflow-auto max-h-80">—</pre>
    </section>`;
}

const COMPONENT_LABELS = {
  config: "Configuración",
  gpu: "GPU",
  dataset: "Dataset",
  model: "Modelo",
  laya: "Laya",
};

export function renderNewTransaction() {
  const field = "mt-1 w-full control";
  return `
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div class="panel">
        <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center gap-2">
          <i data-lucide="plus-circle" class="w-4 h-4"></i> Crear transacción
        </div>
        <form id="tx-form" class="p-4 space-y-3" novalidate>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label class="text-sm"><span class="text-muted">Tipo de operación</span>
              <select id="f-type" class="${field}">
                <option value="TRANSFER" selected>TRANSFER</option>
                <option value="CASH_OUT">CASH_OUT</option>
                <option value="CASH_IN">CASH_IN</option>
                <option value="PAYMENT">PAYMENT</option>
                <option value="DEBIT">DEBIT</option>
              </select>
            </label>
            <label class="text-sm"><span class="text-muted">Paso (step)</span>
              <input id="f-step" type="number" min="0" value="700" class="${field}" />
            </label>
            <label class="text-sm"><span class="text-muted">Importe</span>
              <input id="f-amount" type="number" min="0" step="0.01" value="181.00" class="${field}" />
            </label>
            <label class="text-sm flex items-end gap-2 pb-1.5">
              <input id="f-flagged" type="checkbox" class="mb-1.5" />
              <span class="text-muted">Marcada por el protocolo (isFlaggedFraud)</span>
            </label>
            <label class="text-sm"><span class="text-muted">Cuenta origen</span>
              <input id="f-orig" value="C123456" class="${field}" />
            </label>
            <label class="text-sm"><span class="text-muted">Cuenta destino</span>
              <input id="f-dest" value="C654321" class="${field}" />
            </label>
            <label class="text-sm"><span class="text-muted">Saldo origen</span>
              <input id="f-bal-orig" type="number" min="0" step="0.01" value="181.00" class="${field}" />
            </label>
            <label class="text-sm"><span class="text-muted">Saldo destino</span>
              <input id="f-bal-dest" type="number" min="0" step="0.01" value="0.00" class="${field}" />
            </label>
          </div>
          <div class="flex flex-wrap items-end gap-2">
            <label class="text-sm"><span class="text-muted">Plantilla</span>
              <select id="tx-preset" class="${field}">
                <option value="">—</option>
                <option value="transfer-grande">Transferencia grande</option>
                <option value="cashout-vaciado">CASH_OUT vacía cuenta</option>
                <option value="payment-normal">Pago normal</option>
              </select>
            </label>
            <button id="tx-random" type="button" class="btn">
              <i data-lucide="dice-5" class="w-4 h-4"></i> Aleatoria
            </button>
          </div>
          <p class="text-[11px] text-muted">isFraud no se envía: es ground truth y nunca entra al motor de inferencia.</p>
          <div class="flex flex-wrap items-center gap-2">
            <button id="tx-submit" type="submit" class="btn btn-primary disabled:opacity-60">
              <i data-lucide="send" class="w-4 h-4"></i><span id="tx-submit-label">Procesar transacción</span>
            </button>
            <button id="tx-clear" type="button" class="btn">
              <i data-lucide="eraser" class="w-4 h-4"></i> Limpiar
            </button>
            <span id="tx-status" class="ml-auto"></span>
          </div>
          <p id="tx-errors" class="text-xs text-danger"></p>
        </form>
      </div>
      <div class="panel">
        <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center gap-2">
          <i data-lucide="clipboard-check" class="w-4 h-4"></i> Resultado
        </div>
        <div id="tx-result" class="p-4">${emptyState("Sin procesar todavía.")}</div>
      </div>
    </section>

    ${renderFlowPanel("flow", { defaultBatch: 1, defaultCount: 1000 })}`;
}

export function renderFlowPanel(prefix, { defaultBatch = 1, defaultCount = 1000, defaultBlock = 100000 } = {}) {
  const field = "mt-1 w-full control";
  const opt = (value, label, selected) =>
    `<option value="${value}"${selected ? " selected" : ""}>${label}</option>`;
  const countOptions = [
    [100, "100"],
    [1000, "1000"],
    [10000, "10000"],
    [100000, "100000"],
    ["all", "Todo el dataset (6,362,620)"],
  ]
    .map(([value, label]) => opt(value, label, value === defaultCount))
    .join("");
  return `
    <section class="mt-6 panel">
      <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center gap-2">
        <i data-lucide="waves" class="w-4 h-4"></i> Procesamiento por lotes
      </div>
      <div class="p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-fg-muted mb-3">Configuración del job</p>
        <div class="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <label class="text-sm"><span class="text-muted">Fuente</span>
            <select id="${prefix}-source" class="${field}">
              <option value="live" selected>Live</option>
              <option value="replay">PaySim Replay</option>
            </select>
          </label>
          <label class="text-sm"><span class="text-muted">Cantidad</span>
            <select id="${prefix}-count" class="${field}">
              ${countOptions}
              <option value="custom">Personalizado</option>
            </select>
          </label>
          <label class="text-sm hidden" id="${prefix}-custom-wrap"><span class="text-muted">Personalizado</span>
            <input id="${prefix}-custom" type="number" min="1" max="100000" value="500" class="${field}" />
          </label>
          <label class="text-sm"><span class="text-muted">Bloque</span>
            <input id="${prefix}-block" type="number" min="1" max="1000000" value="${defaultBlock}" class="${field}" />
          </label>
          <label class="text-sm"><span class="text-muted">Batch size</span>
            <select id="${prefix}-batch" class="${field}">
              ${opt(1, "1 (per-item)", defaultBatch === 1)}
              ${opt(32, "32", defaultBatch === 32)}
              ${opt(64, "64", defaultBatch === 64)}
            </select>
          </label>
          <label class="text-sm"><span class="text-muted">Modo Laya</span>
            <select id="${prefix}-laya" class="${field}">
              <option value="disabled" selected>Deshabilitado</option>
              <option value="pretrained">Pretrained</option>
              <option value="custom" disabled>Custom (no configurado)</option>
            </select>
          </label>
          <label class="text-sm hidden" id="${prefix}-subfolder-wrap"><span class="text-muted">Checkpoint (Custom)</span>
            <select id="${prefix}-subfolder" class="${field}"></select>
          </label>
          <p id="${prefix}-vram-note" class="hidden text-[11px] text-warning">Cargar un checkpoint custom consume VRAM adicional y puede tardar ~1 min.</p>
          <label class="text-sm"><span class="text-muted">Publicación</span>
            <select id="${prefix}-publish" class="${field}">
              <option value="sampled" selected>Muestreada</option>
              <option value="all">Todas</option>
            </select>
          </label>
          <label class="text-sm"><span class="text-muted">Modo decisión</span>
            <select id="${prefix}-decision-mode" class="${field}">
              <option value="hybrid" selected>Híbrido (Laya solo SOSPECHOSAS)</option>
              <option value="laya_all">Laya decide todo</option>
            </select>
          </label>
          <p id="${prefix}-mode-note" class="hidden text-[11px] text-warning">Modo Laya-todo: Laya evalúa cada transacción (más lento, usa GPU).</p>
        </div>
        <p class="text-[11px] text-fg-muted mt-2">Batch mayor = inferencia ML vectorizada · Bloque = filas por bloque · Laya solo evalúa SOSPECHOSAS.</p>
        <div class="flex items-center gap-2 mt-3">
          <button id="${prefix}-start" class="btn btn-primary">
            <i data-lucide="play" class="w-4 h-4"></i> <span id="${prefix}-start-label">Iniciar</span>
          </button>
          <button id="${prefix}-stop" class="btn btn-danger">
            <i data-lucide="square" class="w-4 h-4"></i> Detener
          </button>
        </div>
        <div class="mt-4 pt-4 border-t border-line">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-fg-muted mb-2">Estado del job</p>
          <div id="${prefix}-progress">${emptyState("Sin flujo en curso.")}</div>
        </div>
      </div>
    </section>`;
}

export function renderHome(state) {
  return `
    <section class="grid grid-cols-2 lg:grid-cols-4 gap-3" id="home-metrics">
      ${metricCards(state.metrics)}
    </section>
    <section class="grid grid-cols-2 gap-3 mt-3" id="home-sparklines"></section>

    <section class="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-5">
      <div class="panel">
        <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center gap-2">
          <i data-lucide="server" class="w-4 h-4"></i> Estado del sistema
        </div>
        <div class="p-3" id="home-system">${systemList(state.system)}</div>
      </div>
      <div class="panel">
        <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center gap-2">
          <i data-lucide="alert-triangle" class="w-4 h-4"></i> Errores recientes
        </div>
        <div class="p-3 max-h-[220px] overflow-auto scroll-thin" id="home-errors">${errorsList(state.errors)}</div>
      </div>
    </section>

    <section class="mt-5 panel min-w-0">
      <div class="px-3 py-2 border-b border-line text-sm font-medium flex items-center justify-between gap-2">
        <span class="flex items-center gap-2"><i data-lucide="activity" class="w-4 h-4"></i> Actividad en tiempo real</span>
        <span class="flex items-center gap-2">
          <span id="home-connection" class="text-xs text-muted"></span>
          ${dataToolbar("act")}
        </span>
      </div>
      <div class="px-3 pt-3">${filterBar("act", { laya: true })}</div>
      <div class="overflow-x-auto scroll-thin max-h-[560px]">
        <table class="w-full text-sm min-w-[1100px]">
          <thead class="text-xs text-muted sticky top-0 bg-canvas">
            <tr class="border-b border-line text-left">
              <th class="py-1.5 pr-3 font-medium">ID</th>
              <th class="py-1.5 pr-3 font-medium">Origen</th>
              <th class="py-1.5 pr-3 font-medium">Tipo</th>
              <th class="py-1.5 pr-3 font-medium text-right">Importe</th>
              <th class="py-1.5 pr-3 font-medium">Cuenta origen</th>
              <th class="py-1.5 pr-3 font-medium">Cuenta destino</th>
              <th class="py-1.5 pr-3 font-medium">Primaria</th>
              <th class="py-1.5 pr-3 font-medium">Score</th>
              <th class="py-1.5 pr-3 font-medium">Laya</th>
              <th class="py-1.5 pr-3 font-medium">Final</th>
              <th class="py-1.5 pr-3 font-medium">Laya ms</th>
              <th class="py-1.5 pr-3 font-medium">Total</th>
              <th class="py-1.5 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody id="home-activity">${seedRows(state.decisions, activityRow)}</tbody>
        </table>
        <div id="home-activity-empty">${state.decisions.length ? "" : emptyState("Esperando transacciones procesadas…")}</div>
      </div>
    </section>

    ${renderFlowPanel("hb", { defaultBatch: 32, defaultCount: 100000 })}`;
}

const SEVERITY_META = {
  critical: { dot: "dot-danger", label: "CRITICAL" },
  recoverable: { dot: "dot-warning", label: "ERROR" },
  warning: { dot: "dot-warning", label: "WARNING" },
  unavailable: { dot: "dot-neutral", label: "UNAVAILABLE" },
};

export function errorsList(errors) {
  if (!errors || errors.length === 0) {
    return `<div class="py-6 text-center text-xs text-fg-muted">Sin errores recientes.</div>`;
  }
  return `<div class="divide-y divide-line">${[...errors]
    .reverse()
    .map((event) => {
      const payload = event.payload || {};
      const meta = SEVERITY_META[payload.severity] || SEVERITY_META.recoverable;
      return `<div class="flex items-start gap-2 py-1.5">
        <span class="dot ${meta.dot} mt-1.5"></span>
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between gap-2">
            <span class="font-mono text-[11px] text-fg-secondary">${meta.label} · ${escapeHtml(payload.code || "ERROR")}</span>
            <span class="text-[11px] text-fg-muted truncate">${escapeHtml(payload.operation || "")}</span>
          </div>
          <p class="text-xs text-fg-muted">${escapeHtml(payload.message || "")}</p>
        </div>
      </div>`;
    })
    .join("")}</div>`;
}

export function dataToolbar(prefix) {
  return `<span class="flex items-center gap-2">
    <button id="${prefix}-export" class="btn text-xs"><i data-lucide="download" class="w-3.5 h-3.5"></i>Exportar XLSX</button>
  </span>`;
}

export function filterBar(prefix, { laya = false } = {}) {
  const field = "control";
  return `
    <div class="flex flex-wrap items-center gap-2 mb-3">
      <select id="${prefix}-decision" class="${field}">
        <option value="all">Todas</option>
        <option value="FRAUD">Fraude</option>
        <option value="SUSPICIOUS">Sospechosas</option>
        <option value="LEGITIMATE">Legítimas</option>
      </select>
      ${laya ? `<label class="inline-flex items-center gap-1.5 text-xs text-muted"><input id="${prefix}-laya" type="checkbox" /> Solo con Laya</label>` : ""}
      <input id="${prefix}-search" placeholder="Buscar transaction_id o cuenta" class="${field} w-56" />
    </div>`;
}

export function renderTransactions(state) {
  return `
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs text-muted">Eventos <span class="font-mono">{">"}</span> <span id="tx-counter" class="font-mono">${state.counters?.transactions ?? state.transactions.length}</span></p>
      <span class="flex items-center gap-2">
        <span class="text-xs text-muted hidden sm:inline">Canal: <span class="font-mono">transaction.created</span></span>
        ${dataToolbar("tx")}
      </span>
    </div>
    ${filterBar("tx", { laya: true })}
    <div class="panel overflow-hidden">
      <table class="w-full text-sm">
        <thead class="text-xs text-muted bg-panel">
          <tr class="border-b border-line text-left">
            <th class="py-2 px-3 font-medium">Transacción</th>
            <th class="py-2 px-3 font-medium">Origen</th>
            <th class="py-2 px-3 font-medium">Tipo</th>
            <th class="py-2 px-3 font-medium text-right">Importe</th>
            <th class="py-2 px-3 font-medium">Cuenta origen</th>
            <th class="py-2 px-3 font-medium">Cuenta destino</th>
          </tr>
        </thead>
        <tbody id="tx-body">${seedRows(state.transactions, transactionRow)}</tbody>
      </table>
      <div id="tx-empty">${state.transactions.length ? "" : emptyState("Esperando transacciones…")}</div>
    </div>`;
}

export function renderDecisions(state) {
  return `
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs text-muted">Solo eventos con <span class="font-mono">laya.invoked = true</span></p>
      <span class="flex items-center gap-2">
        <span class="text-xs text-muted">Total: <span id="laya-counter" class="font-mono">${state.counters?.laya ?? state.laya.length}</span></span>
        ${dataToolbar("dec")}
      </span>
    </div>
    <div id="laya-stats" class="mb-3"></div>
    <div id="laya-confidence" class="mb-3"></div>
    ${filterBar("dec")}
    <div class="panel overflow-hidden">
      <table class="w-full text-sm">
        <thead class="text-xs text-muted bg-panel">
          <tr class="border-b border-line text-left">
            <th class="py-2 px-3 font-medium">Transacción</th>
            <th class="py-2 px-3 font-medium">Origen</th>
            <th class="py-2 px-3 font-medium">Primaria</th>
            <th class="py-2 px-3 font-medium">Score</th>
            <th class="py-2 px-3 font-medium">Final</th>
            <th class="py-2 px-3 font-medium">Laya</th>
            <th class="py-2 px-3 font-medium">Laya ms</th>
            <th class="py-2 px-3 font-medium">Total</th>
          </tr>
        </thead>
        <tbody id="laya-body">${seedRows(state.laya, decisionRow)}</tbody>
      </table>
      <div id="laya-empty">${state.laya.length ? "" : emptyState("Aún no hay evaluaciones de Laya.")}</div>
    </div>`;
}

function metricCards(metrics) {
  if (!metrics) {
    return metricCard("Transacciones", "—", "activity") +
      metricCard("Fraude", "—", "shield-alert") +
      metricCard("Latencia p95", "—", "timer") +
      metricCard("Throughput", "—", "gauge");
  }
  return [
    metricCard("Transacciones", fmtNumber(metrics.processed), "activity"),
    metricCard("Fraude", fmtNumber(metrics.fraud), "shield-alert"),
    metricCard("Latencia p95", fmtMs(metrics.latency?.p95), "timer"),
    metricCard("Throughput", `${Number(metrics.throughput_tps || 0).toFixed(0)} tx/s`, "gauge"),
  ].join("");
}

function systemList(system) {
  if (!system || !system.components) {
    return emptyState("Cargando estado…");
  }
  const components = system.components;
  return Object.keys(COMPONENT_LABELS)
    .filter((key) => key in components)
    .map(
      (key) => `
      <div class="flex items-center justify-between py-1.5 border-b border-line last:border-0 text-sm">
        <span class="flex items-center gap-2 text-fg">${statusDot(components[key])} ${escapeHtml(COMPONENT_LABELS[key])}</span>
        <span class="text-xs text-fg-secondary font-mono tabular-nums">${escapeHtml(components[key])}</span>
      </div>`
    )
    .join("");
}

export function renderGraphPage() {
  return `
    <div class="flex flex-wrap items-end gap-3 mb-4">
      <label class="text-sm"><span class="text-muted">ID de transacción</span>
        <input id="graph-tx" class="mt-1 control w-56 font-mono" placeholder="R123 o L0-abc123" />
      </label>
      <button id="graph-tx-load" class="btn btn-primary">
        <i data-lucide="search" class="w-4 h-4"></i> Ver grafo
      </button>
      <button id="graph-global" class="btn">
        <i data-lucide="refresh-cw" class="w-4 h-4"></i> Vista global
      </button>
      <span id="graph-note" class="text-xs text-muted ml-auto"></span>
    </div>
    <div class="flex flex-wrap items-center gap-3 mb-3 text-xs">
      <span class="text-muted">Categorías:</span>
      ${["ACCOUNT", "ORIGIN", "DESTINATION", "RISK"]
        .map(
          (category) =>
            `<label class="inline-flex items-center gap-1"><input type="checkbox" class="graph-cat" value="${category}" checked />${category}</label>`
        )
        .join("")}
      <label class="inline-flex items-center gap-1"><span class="text-muted">Grado ≥</span>
        <input id="graph-min-degree" type="number" min="0" value="0" class="w-16 border border-line-strong rounded px-1.5 py-0.5" /></label>
      <button id="graph-png" class="border border-line-strong rounded px-2 py-0.5">Exportar PNG</button>
      <span class="text-muted">Click en un nodo resalta sus vecinos.</span>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 panel bg-panel overflow-hidden">
        <div id="graph-canvas" class="h-[520px]"></div>
      </div>
      <div class="panel p-3 max-h-[520px] overflow-auto scroll-thin">
        <div id="graph-detail">${emptyState("Busca una transacción o usa la vista global.")}</div>
      </div>
    </div>
    <div id="graph-legend" class="mt-3 flex flex-wrap gap-3"></div>`;
}

function seedRows(items, builder) {
  return items.slice(-50).map((item) => {
    const payload = item.payload || item;
    return builder(payload);
  }).join("");
}

export { metricCards, systemList };
