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
  API_BASE,
  MAX_LIST,
  MAX_RECENT_TRANSACTIONS,
  METRICS_REFRESH_MS,
  RENDER_PER_FRAME,
} from "./config.js";
import { apiGet, apiPost } from "./api.js";
import { createSocket, CONNECTION_LABELS } from "./ws.js";
import {
  getState,
  ingestEvent,
  setConnection,
  setMetrics,
  setSystem,
  subscribe,
} from "./store.js";
import { installGlobalHandlers, clearError, reportError } from "./errors.js";
import {
  NAV,
  errorsList,
  metricCards,
  renderDecisions,
  renderGraphPage,
  renderHome,
  renderLayaPage,
  renderNewTransaction,
  renderTransactions,
  systemList,
} from "./views.js";
import { activityRow, decisionRow, emptyState, escapeHtml, transactionRow } from "./ui.js";
import {
  clearHighlight,
  currentGraph,
  exportGraphPng,
  filterGraph,
  graphDetail,
  graphLegend,
  renderGraph,
} from "./graph.js";
import { createHistory, sparkline } from "./charts.js";
import { initTheme, toggleTheme } from "./theme.js";
import { setupPalette } from "./palette.js";
import { decisionToRow, exportRows } from "./export.js";
import { parseFile, rowsToTransactions } from "./import.js";
import { toast } from "./toast.js";

const throughputHistory = createHistory(60);
const p95History = createHistory(60);
import {
  buildTransactionPayload,
  flowStatusHtml,
  resultErrorHtml,
  resultHtml,
  statusPill,
} from "./flow.js";

const ROUTES = Object.fromEntries(NAV.map((item) => [item.path, item]));
let dispose = null;
let metricsTimer = null;
let paused = false;
let currentRender = null;

function normalizePath(pathname) {
  return ROUTES[pathname] ? pathname : "/home";
}

function makeQueue(container, builder, limit = MAX_LIST) {
  const pending = [];
  let scheduled = false;

  function flush() {
    scheduled = false;
    for (const payload of pending.splice(0, RENDER_PER_FRAME)) {
      container.insertAdjacentHTML("afterbegin", builder(payload));
    }
    while (container.children.length > limit) container.removeChild(container.lastElementChild);
    if (window.lucide) window.lucide.createIcons();
    if (pending.length) schedule();
  }

  function schedule() {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(flush);
    }
  }

  return {
    enqueue(payload) {
      pending.push(payload);
      schedule();
    },
  };
}

function readFilters(prefix, laya) {
  return {
    decision: document.getElementById(`${prefix}-decision`)?.value || "all",
    layaOnly: laya ? Boolean(document.getElementById(`${prefix}-laya`)?.checked) : false,
    search: (document.getElementById(`${prefix}-search`)?.value || "").trim().toLowerCase(),
  };
}

function matchesDecisionPayload(payload, filters) {
  if (!payload) return false;
  if (filters.layaOnly && !(payload.laya && payload.laya.invoked)) return false;
  if (filters.decision !== "all" && payload.final_decision !== filters.decision) return false;
  if (filters.search && !String(payload.transaction_id || "").toLowerCase().includes(filters.search)) return false;
  return true;
}

function matchesTransactionPayload(payload, filters, state) {
  if (!payload) return false;
  let decision = null;
  for (const source of ["live", "replay"]) {
    const found = state.decisionByKey.get(`${source}:${payload.transaction_id}`);
    if (found) {
      decision = found;
      break;
    }
  }
  if (filters.layaOnly && !(decision && decision.laya && decision.laya.invoked)) return false;
  if (filters.decision !== "all" && (!decision || decision.final_decision !== filters.decision)) return false;
  if (filters.search) {
    const hay = `${payload.transaction_id || ""} ${payload.name_orig || ""} ${payload.name_dest || ""}`.toLowerCase();
    if (!hay.includes(filters.search)) return false;
  }
  return true;
}

function wireFilters(prefix, onChange) {
  const key = `agant-filters-${prefix}`;
  try {
    const saved = JSON.parse(localStorage.getItem(key) || "null");
    if (saved) {
      const decision = document.getElementById(`${prefix}-decision`);
      if (decision && saved.decision) decision.value = saved.decision;
      const laya = document.getElementById(`${prefix}-laya`);
      if (laya) laya.checked = Boolean(saved.layaOnly);
      const search = document.getElementById(`${prefix}-search`);
      if (search && saved.search) search.value = saved.search;
    }
  } catch {
    /* preferencias no disponibles */
  }
  const save = () => {
    try {
      localStorage.setItem(key, JSON.stringify(readFilters(prefix, true)));
    } catch {
      /* ignorar */
    }
  };
  for (const item of ["decision", "laya", "search"]) {
    const element = document.getElementById(`${prefix}-${item}`);
    if (!element) continue;
    element.addEventListener(item === "search" ? "input" : "change", () => {
      save();
      onChange();
    });
  }
}

function wireImport(prefix) {
  const button = document.getElementById(`${prefix}-import`);
  const input = document.getElementById(`${prefix}-import-file`);
  if (!button || !input) return;
  button.addEventListener("click", () => input.click());
  input.addEventListener("change", async () => {
    const file = input.files?.[0];
    if (!file) return;
    try {
      const rows = await parseFile(file);
      const { transactions, errors } = rowsToTransactions(rows);
      if (errors.length) {
        toast({
          severity: "warning",
          title: `${errors.length} fila(s) con error`,
          message: errors.slice(0, 3).map((e) => `#${e.row}: ${e.error}`).join(" · "),
        });
      }
      if (!transactions.length) {
        reportError({
          key: "import",
          severity: "warning",
          title: "Sin filas válidas",
          message: "El archivo no contiene transacciones válidas.",
        });
        return;
      }
      const started = await apiPost("/api/v1/transactions/import", {
        transactions,
        batch_size: 32,
      });
      toast({
        severity: "success",
        title: `Import iniciado: ${transactions.length} transacciones`,
        message: started.kind === "import" ? "Procesando en segundo plano" : "",
      });
    } catch (error) {
      reportError({
        key: "import",
        severity: "recoverable",
        title: "No fue posible importar",
        message: error.message,
      });
    } finally {
      input.value = "";
    }
  });
}

function emptyRow(colspan, text) {
  return `<tr><td colspan="${colspan}" class="p-4 text-center text-sm text-muted">${text}</td></tr>`;
}

function renderNav(active) {
  const groups = [];
  for (const item of NAV) {
    const group = groups.find((entry) => entry.name === item.group);
    if (group) group.items.push(item);
    else groups.push({ name: item.group, items: [item] });
  }
  document.getElementById("nav").innerHTML = groups
    .map(
      (group) => `
      <div class="mt-3 first:mt-1">
        <p class="px-2.5 mb-1 text-[10px] font-semibold uppercase tracking-wider text-fg-muted">${group.name}</p>
        ${group.items
          .map((item) => {
            const isActive = item.path === active;
            return `<a href="${item.path}" data-route="${item.path}"
              class="relative flex items-center gap-2 rounded px-2.5 py-1.5 mb-0.5 ${
                isActive
                  ? "bg-hover text-fg font-medium border-l-2 border-fg"
                  : "text-fg-secondary hover:bg-hover hover:text-fg"
              }">
              <i data-lucide="${item.icon}" class="w-4 h-4"></i>
              <span>${item.label}</span>
            </a>`;
          })
          .join("")}
      </div>`
    )
    .join("");
  document.querySelectorAll("[data-route]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      navigate(link.dataset.route);
    });
  });
  if (window.lucide) window.lucide.createIcons();
}

function navigate(path) {
  document.getElementById("sidebar")?.classList.remove("open");
  if (normalizePath(path) === normalizePath(location.pathname)) return;
  history.pushState({}, "", path);
  route();
}

function paintGraph(data) {
  const canvas = document.getElementById("graph-canvas");
  if (canvas) renderGraph(canvas, data.graph || data);
  const legend = document.getElementById("graph-legend");
  if (legend) legend.innerHTML = graphLegend();
  const nodes = (data.graph || data).nodes?.length || 0;
  const edges = (data.graph || data).edges?.length || 0;
  const detail = document.getElementById("graph-detail");
  if (detail) {
    detail.innerHTML = data.graph
      ? graphDetail({ ...data, note: data.note })
      : `<h4 class="text-xs font-semibold uppercase tracking-wide text-muted mb-1">Vista global</h4>
         <p class="text-sm">${nodes} cuentas · ${edges} aristas</p>
         <p class="text-xs text-muted mt-1">Busca un ID de transacción para ver su grafo y contexto.</p>
         ${data.note ? `<p class="text-[11px] text-muted mt-2">${escapeHtml(data.note)}</p>` : ""}`;
  }
  const note = document.getElementById("graph-note");
  if (note) note.textContent = `${nodes} cuentas · ${edges} aristas`;
  if (window.lucide) window.lucide.createIcons();
}

async function loadGraph() {
  try {
    const data = await apiGet("/api/v1/graph?limit=120");
    paintGraph(data);
  } catch (error) {
    reportError({
      key: "graph",
      severity: "recoverable",
      title: "No fue posible cargar el grafo",
      message: error.message,
    });
  }
}

async function loadTransactionGraph(transactionId) {
  if (!transactionId) {
    reportError({
      key: "graph",
      severity: "warning",
      title: "Falta el ID de transacción",
      message: "Escribe un ID (por ejemplo R123 o el de una transacción live).",
    });
    return;
  }
  try {
    const data = await apiGet(`/api/v1/transactions/${encodeURIComponent(transactionId)}/graph?limit=150`);
    paintGraph(data);
    clearError("graph");
  } catch (error) {
    reportError({
      key: "graph",
      severity: "recoverable",
      title: "No se pudo construir el grafo de la transacción",
      message: error.message,
      detail: error.code,
    });
  }
}

function setupGraph() {
  const input = document.getElementById("graph-tx");
  document.getElementById("graph-tx-load")?.addEventListener("click", () =>
    loadTransactionGraph(input.value.trim())
  );
  input?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") loadTransactionGraph(event.target.value.trim());
  });
  document.getElementById("graph-global")?.addEventListener("click", loadGraph);

  function applyGraphFilters() {
    const categories = new Set(
      Array.from(document.querySelectorAll(".graph-cat"))
        .filter((input) => input.checked)
        .map((input) => input.value)
    );
    const minDegree = Number(document.getElementById("graph-min-degree")?.value || 0);
    filterGraph(currentGraph(), { categories, minDegree });
  }
  document.querySelectorAll(".graph-cat").forEach((input) => input.addEventListener("change", applyGraphFilters));
  document.getElementById("graph-min-degree")?.addEventListener("input", applyGraphFilters);
  document.getElementById("graph-png")?.addEventListener("click", () => exportGraphPng(currentGraph()));

  loadGraph();
  let seen = 0;
  return {
    transactions: () => {
      seen += 1;
      if (seen % 25 === 0) loadGraph();
    },
  };
}

function setupNewTransaction() {
  const form = document.getElementById("tx-form");
  const submit = document.getElementById("tx-submit");
  const label = document.getElementById("tx-submit-label");
  const statusEl = document.getElementById("tx-status");
  const errorsEl = document.getElementById("tx-errors");
  const resultEl = document.getElementById("tx-result");

  function readForm() {
    return {
      type: document.getElementById("f-type").value,
      step: document.getElementById("f-step").value,
      amount: document.getElementById("f-amount").value,
      name_orig: document.getElementById("f-orig").value,
      name_dest: document.getElementById("f-dest").value,
      old_balance_org: document.getElementById("f-bal-orig").value,
      old_balance_dest: document.getElementById("f-bal-dest").value,
      is_flagged_fraud: document.getElementById("f-flagged").checked,
    };
  }

  function setBusy(busy) {
    submit.disabled = busy;
    label.textContent = busy ? "Procesando..." : "Procesar transacción";
    statusEl.innerHTML = busy ? statusPill("processing", "Procesando...") : statusEl.innerHTML;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorsEl.textContent = "";
    const { payload, errors } = buildTransactionPayload(readForm());
    if (errors.length) {
      errorsEl.textContent = errors.join(" ");
      statusEl.innerHTML = statusPill("warning", "Revisa los datos");
      return;
    }
    setBusy(true);
    try {
      const result = await apiPost("/api/v1/decision", payload);
      resultEl.innerHTML = resultHtml(result);
      statusEl.innerHTML = statusPill("success", "Transacción procesada");
      clearError("tx");
    } catch (error) {
      resultEl.innerHTML = resultErrorHtml(error.message, error.code);
      statusEl.innerHTML = statusPill("error", "No se pudo procesar");
      reportError({
        key: "tx",
        severity: error.status === 0 ? "critical" : "recoverable",
        title: "No fue posible procesar la transacción",
        message: error.message,
        detail: error.code,
      });
    } finally {
      submit.disabled = false;
      label.textContent = "Procesar transacción";
    }
  });

  document.getElementById("tx-clear").addEventListener("click", () => {
    form.reset();
    errorsEl.textContent = "";
    statusEl.innerHTML = "";
    resultEl.innerHTML = emptyState("Sin procesar todavía.");
  });

  const PRESETS = {
    "transfer-grande": { type: "TRANSFER", amount: 250000, name_orig: "C123456", name_dest: "C777777", old_balance_org: 250000, old_balance_dest: 0, flagged: false },
    "cashout-vaciado": { type: "CASH_OUT", amount: 5000, name_orig: "C424242", name_dest: "C111111", old_balance_org: 5000, old_balance_dest: 0, flagged: false },
    "payment-normal": { type: "PAYMENT", amount: 120, name_orig: "C555555", name_dest: "M100", old_balance_org: 3000, old_balance_dest: 0, flagged: false },
  };

  function fillForm(data) {
    document.getElementById("f-type").value = data.type;
    document.getElementById("f-amount").value = data.amount;
    document.getElementById("f-orig").value = data.name_orig;
    document.getElementById("f-dest").value = data.name_dest;
    document.getElementById("f-bal-orig").value = data.old_balance_org;
    document.getElementById("f-bal-dest").value = data.old_balance_dest;
    document.getElementById("f-flagged").checked = Boolean(data.flagged);
  }

  document.getElementById("tx-preset").addEventListener("change", (event) => {
    const preset = PRESETS[event.target.value];
    if (preset) fillForm(preset);
  });

  document.getElementById("tx-random").addEventListener("click", () => {
    const types = ["TRANSFER", "CASH_OUT", "CASH_IN", "PAYMENT", "DEBIT"];
    const amount = Math.round(Math.exp(7.4 + (Math.random() - 0.5) * 3) * 100) / 100;
    fillForm({
      type: types[Math.floor(Math.random() * types.length)],
      amount,
      name_orig: `C${Math.floor(Math.random() * 50000)}`,
      name_dest: `C${Math.floor(Math.random() * 50000)}`,
      old_balance_org: Math.round(amount * (1 + Math.random() * 4) * 100) / 100,
      old_balance_dest: 0,
      flagged: false,
    });
  });

  return setupFlowPanel("flow");
}

function setupFlowPanel(prefix) {
  const start = document.getElementById(`${prefix}-start`);
  if (!start) return {};
  const source = document.getElementById(`${prefix}-source`);
  const countSelect = document.getElementById(`${prefix}-count`);
  const customWrap = document.getElementById(`${prefix}-custom-wrap`);
  const customInput = document.getElementById(`${prefix}-custom`);
  const blockInput = document.getElementById(`${prefix}-block`);
  const batchSelect = document.getElementById(`${prefix}-batch`);
  const layaSelect = document.getElementById(`${prefix}-laya`);
  const subfolderWrap = document.getElementById(`${prefix}-subfolder-wrap`);
  const subfolderSelect = document.getElementById(`${prefix}-subfolder`);
  const publishSelect = document.getElementById(`${prefix}-publish`);
  const decisionModeSelect = document.getElementById(`${prefix}-decision-mode`);
  const modeNote = document.getElementById(`${prefix}-mode-note`);
  const stop = document.getElementById(`${prefix}-stop`);

  countSelect.addEventListener("change", () => {
    customWrap.classList.toggle("hidden", countSelect.value !== "custom");
  });

  const startLabel = document.getElementById(`${prefix}-start-label`);
  const vramNote = document.getElementById(`${prefix}-vram-note`);

  function syncCountOptions() {
    const allOption = Array.from(countSelect.options).find((option) => option.value === "all");
    if (!allOption) return;
    const isLive = source.value === "live";
    allOption.disabled = isLive;
    allOption.textContent = isLive ? "Todo el dataset (solo Replay)" : "Todo el dataset (6,362,620)";
    if (isLive && countSelect.value === "all") countSelect.value = "1000";
  }
  source.addEventListener("change", syncCountOptions);
  syncCountOptions();

  function syncSubfolder() {
    const custom = layaSelect.value === "custom";
    if (subfolderWrap) subfolderWrap.classList.toggle("hidden", !custom);
    if (vramNote) vramNote.classList.toggle("hidden", !custom);
  }
  layaSelect.addEventListener("change", syncSubfolder);
  syncSubfolder();

  function syncModeNote() {
    if (modeNote) modeNote.classList.toggle("hidden", decisionModeSelect.value !== "laya_all");
  }
  decisionModeSelect.addEventListener("change", syncModeNote);
  syncModeNote();

  function updateStartState(state) {
    if (state === "running" || state === "loading") {
      start.disabled = true;
      if (startLabel) startLabel.textContent = "En ejecución";
    } else {
      start.disabled = false;
      if (startLabel) startLabel.textContent = "Iniciar";
    }
  }

  function renderProgress(status) {
    const container = document.getElementById(`${prefix}-progress`);
    if (container) container.innerHTML = flowStatusHtml(status);
    if (status && status.state) updateStartState(status.state);
  }

  function readCount() {
    if (countSelect.value === "custom") return Number(customInput.value);
    if (countSelect.value === "all") return "all";
    return Number(countSelect.value);
  }

  start.addEventListener("click", async () => {
    const count = readCount();
    if (count !== "all" && (!Number.isInteger(count) || count < 1 || count > 100000)) {
      reportError({
        key: `${prefix}-flow`,
        severity: "warning",
        title: "Cantidad inválida",
        message: "Usa una cantidad entre 1 y 100000 o 'Todo el dataset'.",
      });
      return;
    }
    const block = Number(blockInput.value);
    const custom = layaSelect.value === "custom";
    const payload = {
      source: source.value,
      count,
      offset: 0,
      laya_mode: layaSelect.value,
      laya_subfolder: custom ? subfolderSelect?.value || null : null,
      batch_size: Number(batchSelect.value),
      block_size: Number.isFinite(block) && block > 0 ? block : null,
      publish_mode: publishSelect.value,
      decision_mode: decisionModeSelect.value,
    };
    start.disabled = true;
    if (startLabel) startLabel.textContent = custom ? "Cargando…" : "Iniciando…";
    try {
      renderProgress(await apiPost("/api/v1/flow/start", payload));
      clearError(`${prefix}-flow`);
    } catch (error) {
      updateStartState("idle");
      reportError({
        key: `${prefix}-flow`,
        severity: "recoverable",
        title: "No fue posible iniciar el flujo",
        message: error.message,
        detail: error.code,
      });
    }
  });

  stop.addEventListener("click", async () => {
    try {
      renderProgress(await apiPost("/api/v1/flow/stop", {}));
    } catch (error) {
      reportError({
        key: `${prefix}-flow`,
        severity: "recoverable",
        title: "No fue posible detener el flujo",
        message: error.message,
        detail: error.code,
      });
    }
  });

  return {
    "flow.status": (event) => renderProgress(event.payload),
  };
}

async function setupLayaPage() {
  const modeSelect = document.getElementById("laya-mode-toggle");
  const subfolderSelect = document.getElementById("laya-subfolder");
  const loadButton = document.getElementById("laya-load");
  const loadLabel = document.getElementById("laya-load-label");
  const loadStatus = document.getElementById("laya-load-status");
  const statusEl = document.getElementById("laya-status");
  const resultEl = document.getElementById("laya-result");

  async function refresh() {
    try {
      const data = await apiGet("/api/v1/laya/status");
      if (subfolderSelect && subfolderSelect.options.length === 0) {
        subfolderSelect.innerHTML = (data.subfolders || [])
          .map((name) => `<option value="${name}">${name}</option>`)
          .join("");
      }
      if (modeSelect && data.mode) modeSelect.value = data.mode;
      const vram = data.vram || {};
      statusEl.innerHTML = `<dl class="space-y-1 text-sm">
        ${[
          ["Modo", data.mode],
          ["Estado", data.status],
          ["Checkpoint", data.subfolder || "—"],
          ["Modo decisión", data.decision_mode],
          ["VRAM asignada", vram.allocated_mb ? `${vram.allocated_mb.toFixed(0)} MB` : "—"],
          ["VRAM reservada", vram.reserved_mb ? `${vram.reserved_mb.toFixed(0)} MB` : "—"],
          ["GPU", vram.device || "—"],
        ]
          .map(
            ([label, value]) =>
              `<div class="flex justify-between gap-3"><dt class="text-muted">${label}</dt><dd class="font-mono text-right">${value}</dd></div>`
          )
          .join("")}
        ${data.load_error ? `<p class="text-danger text-xs mt-1">Error: ${data.load_error}</p>` : ""}
      </dl>`;
    } catch (error) {
      reportError({ key: "laya", severity: "recoverable", title: "No fue posible obtener el estado de Laya", message: error.message });
    }
  }

  loadButton.addEventListener("click", async () => {
    loadButton.disabled = true;
    if (loadLabel) loadLabel.textContent = "Cargando…";
    try {
      const data = await apiPost("/api/v1/laya/load", {
        mode: modeSelect.value,
        subfolder: subfolderSelect.value || null,
        warmup: document.getElementById("laya-warmup").checked,
      });
      if (loadStatus) loadStatus.textContent = `Estado: ${data.status}`;
      await refresh();
      toast({ severity: data.laya_active ? "success" : "warning", title: `Laya: ${data.status}` });
    } catch (error) {
      reportError({ key: "laya", severity: "recoverable", title: "No fue posible cargar Laya", message: error.message });
    } finally {
      loadButton.disabled = false;
      if (loadLabel) loadLabel.textContent = "Cargar";
    }
  });

  document.getElementById("laya-test").addEventListener("click", async () => {
    try {
      const data = await apiPost("/api/v1/laya/test", {});
      resultEl.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
      reportError({ key: "laya", severity: "recoverable", title: "No fue posible probar Laya", message: error.message });
    }
  });

  refresh();
}

function renderMetrics() {
  const container = document.getElementById("home-metrics");
  if (container) container.innerHTML = metricCards(getState().metrics);
  renderSparklines();
  if (window.lucide) window.lucide.createIcons();
}

function renderSparklines() {
  const container = document.getElementById("home-sparklines");
  if (!container) return;
  container.innerHTML = `
    <div class="border border-line rounded-md p-3">
      <p class="text-xs text-muted">Throughput</p>
      ${sparkline(throughputHistory.values(), { color: "#2563eb" })}
    </div>
    <div class="border border-line rounded-md p-3">
      <p class="text-xs text-muted">Latencia p95</p>
      ${sparkline(p95History.values(), { color: "#dc2626" })}
    </div>`;
}

function renderSystem() {
  const container = document.getElementById("home-system");
  if (container) container.innerHTML = systemList(getState().system);
  if (window.lucide) window.lucide.createIcons();
}

function renderLayaStats() {
  const container = document.getElementById("laya-stats");
  if (!container) return;
  const snapshot = getState().metrics || {};
  const stages = getState().stages?.live?.laya_ms || {};
  const cards = [
    ["Invocaciones", snapshot.laya_invocations ?? 0],
    ["Fallos", snapshot.laya_failures ?? 0],
    ["p50", `${Number(stages.p50 || 0).toFixed(1)} ms`],
    ["p95", `${Number(stages.p95 || 0).toFixed(1)} ms`],
  ];
  container.innerHTML = cards
    .map(
      ([label, value]) =>
        `<span class="inline-flex items-baseline gap-1.5 mr-4"><span class="text-xs text-muted">${label}</span><span class="font-mono text-sm">${value}</span></span>`
    )
    .join("");
}

function renderConfidence() {
  const container = document.getElementById("laya-confidence");
  if (!container) return;
  const values = getState()
    .laya.map((event) => event.payload?.laya?.confidence)
    .filter((value) => typeof value === "number");
  if (values.length === 0) {
    container.innerHTML = '<p class="text-xs text-muted">Sin confianzas de Laya todavía.</p>';
    return;
  }
  const bins = [0, 0, 0, 0, 0];
  values.forEach((value) => {
    bins[Math.min(4, Math.floor(value * 5))] += 1;
  });
  const total = values.length;
  container.innerHTML = `<p class="text-xs text-muted mb-1">Distribución de confianza de Laya (n=${total})</p>
    <div class="flex items-end gap-1 h-16">
      ${bins
        .map((count, index) => {
          const pct = total ? (count / total) * 100 : 0;
          return `<div class="flex-1 flex flex-col items-center justify-end" title="${(index / 5).toFixed(1)}–${((index + 1) / 5).toFixed(1)}: ${count}">
            <div class="w-full bg-fg" style="height:${Math.max(2, pct)}%"></div>
            <span class="text-[10px] text-muted mt-1">${(index / 5).toFixed(1)}</span>
          </div>`;
        })
        .join("")}
    </div>`;
}

function renderErrors() {
  const container = document.getElementById("home-errors");
  if (container) container.innerHTML = errorsList(getState().errors);
  if (window.lucide) window.lucide.createIcons();
}

function updateChip(system) {
  const chip = document.getElementById("mode-chip");
  if (!chip || !system) return;
  const mode = system.decision_mode === "laya_all" ? "Laya-todo" : "Híbrido";
  chip.textContent = `${mode} · Laya ${system.laya_status || "—"}`;
}

function applyCustomAvailability(system) {
  updateChip(system);
  const available = Boolean(system?.laya_custom_available);
  const subfolders = system?.laya_subfolders || ["typed-decisions", "multilingual"];
  document.querySelectorAll('select[id$="-laya"]').forEach((select) => {
    const option = Array.from(select.options).find((item) => item.value === "custom");
    if (!option) return;
    option.disabled = !available;
    option.textContent = available ? "Custom" : "Custom (no configurado)";
  });
  document.querySelectorAll('select[id$="-subfolder"]').forEach((select) => {
    if (select.options.length === 0) {
      select.innerHTML = subfolders.map((name) => `<option value="${name}">${name}</option>`).join("");
    }
  });
}

function route() {
  const path = normalizePath(location.pathname);
  const meta = ROUTES[path];
  const state = getState();

  document.getElementById("view-title").textContent = meta.title;
  document.getElementById("view-subtitle").textContent = meta.subtitle;
  renderNav(path);

  const view = document.getElementById("view");
  if (path === "/home") view.innerHTML = renderHome(state);
  else if (path === "/nueva-transaccion") view.innerHTML = renderNewTransaction();
  else if (path === "/transacciones") view.innerHTML = renderTransactions(state);
  else if (path === "/grafo") view.innerHTML = renderGraphPage();
  else if (path === "/laya") view.innerHTML = renderLayaPage();
  else view.innerHTML = renderDecisions(state);
  if (window.lucide) window.lucide.createIcons();

  if (dispose) dispose();
  currentRender = null;

  const handlers = {};
  if (path === "/nueva-transaccion") {
    Object.assign(handlers, setupNewTransaction());
  } else if (path === "/transacciones") {
    const body = document.getElementById("tx-body");
    const render = () => {
      const filters = readFilters("tx", true);
      const items = state.transactions
        .slice(-MAX_LIST)
        .filter((event) => matchesTransactionPayload(event.payload, filters, state));
      body.innerHTML = items.length
        ? items.map((event) => transactionRow({ ...event.payload, source: event.source })).join("")
        : emptyRow(6, "Sin transacciones que coincidan.");
    };
    wireFilters("tx", render);
    wireImport("tx");
    render();
    document.getElementById("tx-export")?.addEventListener("click", () => {
      const filters = readFilters("tx", true);
      const rows = state.transactions
        .map((event) => ({ ...event.payload, source: event.source }))
        .filter((payload) => matchesTransactionPayload(payload, filters, state))
        .map((row) => ({
          transaction_id: row.transaction_id,
          source: row.source,
          tipo: row.type,
          importe: row.amount,
          cuenta_origen: row.name_orig,
          cuenta_destino: row.name_dest,
        }));
      exportRows(rows, "agant-transacciones.xlsx");
    });
    currentRender = render;
    const queue = makeQueue(body, (payload) => transactionRow(payload));
    handlers.transactions = (event) => {
      if (!paused && matchesTransactionPayload(event.payload, readFilters("tx", true), state)) {
        queue.enqueue({ ...event.payload, source: event.source });
      }
      const counter = document.getElementById("tx-counter");
      if (counter) counter.textContent = state.counters.transactions;
    };
  } else if (path === "/decisiones") {
    const body = document.getElementById("laya-body");
    const render = () => {
      const filters = readFilters("dec", false);
      const items = state.laya
        .slice(-MAX_LIST)
        .filter((event) => matchesDecisionPayload(event.payload, filters));
      body.innerHTML = items.length
        ? items.map((event) => decisionRow(event.payload)).join("")
        : emptyRow(8, "Sin decisiones de Laya que coincidan.");
    };
    wireFilters("dec", render);
    wireImport("dec");
    render();
    renderLayaStats();
    renderConfidence();
    document.getElementById("dec-export")?.addEventListener("click", () => {
      const filters = readFilters("dec", false);
      const rows = state.laya
        .map((event) => event.payload)
        .filter((payload) => matchesDecisionPayload(payload, filters))
        .map(decisionToRow);
      exportRows(rows, "agant-laya.xlsx");
    });
    currentRender = render;
    const queue = makeQueue(body, (payload) => decisionRow(payload));
    handlers.laya = (event) => {
      if (!paused && matchesDecisionPayload(event.payload, readFilters("dec", false))) queue.enqueue(event.payload);
      const counter = document.getElementById("laya-counter");
      if (counter) counter.textContent = state.counters.laya;
      renderConfidence();
    };
    handlers.metrics = () => {
      renderLayaStats();
      renderConfidence();
    };
  } else if (path === "/grafo") {
    Object.assign(handlers, setupGraph());
  } else if (path === "/laya") {
    setupLayaPage();
  } else {
    const body = document.getElementById("home-activity");
    const renderActivity = () => {
      const filters = readFilters("act", true);
      const items = state.decisions
        .slice(-MAX_RECENT_TRANSACTIONS)
        .filter((event) => matchesDecisionPayload(event.payload, filters));
      body.innerHTML = items.length
        ? items.map((event) => activityRow(event.payload)).join("")
        : emptyRow(13, "Sin transacciones que coincidan.");
      if (window.lucide) window.lucide.createIcons();
    };
    wireFilters("act", renderActivity);
    wireImport("act");
    renderActivity();
    document.getElementById("act-export")?.addEventListener("click", () => {
      const filters = readFilters("act", true);
      const rows = state.decisions
        .map((event) => event.payload)
        .filter((payload) => matchesDecisionPayload(payload, filters))
        .map(decisionToRow);
      exportRows(rows, "agant-actividad.xlsx");
    });
    body.addEventListener("click", (event) => {
      const button = event.target.closest("[data-detail]");
      if (!button) return;
      document.getElementById(button.dataset.detail)?.classList.toggle("hidden");
    });
    currentRender = renderActivity;
    const queue = makeQueue(body, (payload) => activityRow(payload), MAX_RECENT_TRANSACTIONS * 2);
    handlers.decisions = (event) => {
      if (!paused && matchesDecisionPayload(event.payload, readFilters("act", true))) queue.enqueue(event.payload);
    };
    handlers.errors = renderErrors;
    handlers.metrics = renderMetrics;
    handlers.system = renderSystem;
    Object.assign(handlers, setupFlowPanel("hb"));
  }

  dispose = subscribe((channel, item) => {
    const handler = handlers[channel];
    if (handler) handler(item);
  });

  updateConnection(state.connection);
  applyCustomAvailability(state.system);
}

function updateConnection(connection) {
  const labels = CONNECTION_LABELS;
  const dot = document.getElementById("connection-dot");
  const label = document.getElementById("connection-label");
  if (label) label.textContent = labels[connection] || connection;
  const home = document.getElementById("home-connection");
  if (home) {
    home.textContent = `${connection === "connected" ? "●" : "○"} ${labels[connection] || connection}`;
    home.className = `text-xs ${connection === "connected" ? "text-success" : "text-warning"}`;
  }
  if (dot) {
    const colors = {
      connected: "dot-success",
      connecting: "dot-warning animate-pulse",
      reconnecting: "dot-warning animate-pulse",
      disconnected: "dot-danger",
      error: "dot-danger",
    };
    dot.className = `dot ${colors[connection] || "dot-neutral"}`;
  }
}

function startMetricsStream() {
  let sseFailed = false;
  try {
    const source = new EventSource(API_BASE + "/api/v1/metrics/stream");
    source.addEventListener("metrics.updated", (event) => {
      try {
        setMetrics(JSON.parse(event.data));
        clearError("sse");
      } catch {
        /* snapshot no interpretable */
      }
    });
    source.onerror = () => {
      if (sseFailed) return;
      sseFailed = true;
      startMetricsPolling();
      reportError({
        key: "sse",
        severity: "warning",
        title: "Métricas en vivo con interrupción",
        message: "Se usarán métricas por sondeo mientras se restablece la conexión.",
      });
    };
  } catch {
    startMetricsPolling();
  }
}

function startMetricsPolling() {
  if (metricsTimer) return;
  metricsTimer = setInterval(async () => {
    try {
      setMetrics(await apiGet("/api/v1/metrics"));
    } catch {
      /* se reporta en el bootstrap */
    }
  }, METRICS_REFRESH_MS);
}

async function bootstrap() {
  try {
    const [health, system] = await Promise.all([
      apiGet("/health"),
      apiGet("/api/v1/system/status"),
    ]);
    setSystem(system, health);
  } catch (error) {
    reportError({
      key: "server",
      severity: "critical",
      title: "Servidor no disponible",
      message: "No fue posible obtener el estado del sistema.",
      detail: error.message,
    });
  }

  try {
    setMetrics(await apiGet("/api/v1/metrics"));
  } catch {
    /* opcional */
  }

  try {
    const transactions = await apiGet("/api/v1/transactions?limit=200");
    for (const item of transactions || []) {
      const { event_id, source, ...payload } = item;
      ingestEvent({ event_id, event_type: "transaction.created", source, payload });
    }
  } catch {
    /* opcional */
  }

  try {
    const decisions = await apiGet("/api/v1/decisions?limit=200");
    for (const item of decisions || []) {
      ingestEvent({
        event_id: `${item.source}:decision.created:${item.transaction_id}`,
        event_type: "decision.created",
        source: item.source,
        payload: item,
      });
    }
  } catch {
    /* opcional */
  }

  try {
    const laya = await apiGet("/api/v1/laya-decisions?limit=200");
    for (const item of laya || []) {
      ingestEvent({
        event_id: `${item.source}:laya.decision:${item.transaction_id}`,
        event_type: "laya.decision",
        source: item.source,
        payload: item,
      });
    }
  } catch {
    /* opcional */
  }

  startMetricsStream();
}

function main() {
  installGlobalHandlers();
  initTheme();
  document.getElementById("theme-toggle")?.addEventListener("click", () => {
    const dark = toggleTheme();
    const icon = document.querySelector("#theme-toggle i");
    if (icon) icon.setAttribute("data-lucide", dark ? "sun" : "moon");
    if (window.lucide) window.lucide.createIcons();
    if (document.getElementById("graph-canvas")) loadGraph();
  });

  const feedToggle = document.getElementById("feed-toggle");
  feedToggle?.addEventListener("click", () => {
    paused = !paused;
    const icon = feedToggle.querySelector("i");
    if (icon) icon.setAttribute("data-lucide", paused ? "play" : "pause");
    if (window.lucide) window.lucide.createIcons();
    toast({ severity: "warning", title: paused ? "Feed en pausa" : "Feed reanudado" });
    if (!paused && currentRender) currentRender();
  });
  setupPalette([
    ...NAV.map((item) => ({ label: `Ir a ${item.label}`, run: () => navigate(item.path) })),
    {
      label: "Cambiar tema",
      run: () => {
        toggleTheme();
        if (window.lucide) window.lucide.createIcons();
      },
    },
  ]);
  bootstrap();

  if (!window.EventSource) startMetricsPolling();

  subscribe((channel, value) => {
    if (channel === "connection") updateConnection(value);
    if (channel === "system") {
      const status = document.getElementById("sidebar-status");
      if (status && value) status.textContent = value.summary || "";
      applyCustomAvailability(value);
    }
    if (channel === "metrics" && value) {
      throughputHistory.push(value.throughput_tps);
      p95History.push(value.latency?.p95);
      renderSparklines();
    }
    if (channel === "flow.status") {
      const payload = value?.payload || value || {};
      if (payload.kind === "import" && ["finished", "error"].includes(payload.state)) {
        toast({
          severity: payload.state === "finished" ? "success" : "critical",
          title: payload.state === "finished" ? `Import completado: ${payload.processed}` : "Import falló",
          message: payload.error || "",
        });
      }
    }
  });

  document.getElementById("nav-toggle")?.addEventListener("click", () => {
    document.getElementById("sidebar")?.classList.toggle("open");
  });

  const socket = createSocket({
    onEvent: (event) => ingestEvent(event),
    onState: (connection) => setConnection(connection),
  });
  window.addEventListener("beforeunload", () => socket.close());

  window.addEventListener("popstate", route);
  route();
  updateConnection(getState().connection);
  applyCustomAvailability(getState().system);
}

main();
