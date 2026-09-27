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

import { decisionBadge, escapeHtml, fmtNumber, fmtScore, sourceBadge } from "./ui.js";

export const GRAPH_CATEGORY_LABELS = {
  ACCOUNT: "Cuenta (origen y destino)",
  ORIGIN: "Origen",
  DESTINATION: "Destino",
  EDGE: "Arista",
  HISTORY: "Con historial",
  RISK: "Riesgo",
};

function token(name, fallback) {
  if (typeof document === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export function categoryColors() {
  return {
    ACCOUNT: token("--text-primary", "#111827"),
    ORIGIN: token("--status-info", "#2563eb"),
    DESTINATION: token("--status-success", "#059669"),
    RISK: token("--status-danger", "#dc2626"),
  };
}

function cyStyle() {
  const line = token("--border-strong", "#d4d4d4");
  const label = token("--text-secondary", "#374151");
  const panel = token("--bg-panel", "#ffffff");
  const fg = token("--text-primary", "#111827");
  return [
    {
      selector: "node",
      style: {
        "background-color": "data(color)",
        label: "data(label)",
        "font-size": 9,
        color: label,
        "text-valign": "bottom",
        "text-margin-y": 3,
        width: "mapData(degree, 0, 20, 14, 42)",
        height: "mapData(degree, 0, 20, 14, 42)",
        "border-width": 1,
        "border-color": panel,
      },
    },
    { selector: "node[?center]", style: { "border-width": 3, "border-color": fg } },
    { selector: ".dim", style: { opacity: 0.12 } },
    { selector: ".hidden-el", style: { display: "none" } },
    {
      selector: "edge",
      style: {
        width: "mapData(weight, 0, 10, 1, 4)",
        "line-color": line,
        "curve-style": "bezier",
        "target-arrow-shape": "triangle",
        "target-arrow-color": line,
        "arrow-scale": 0.6,
      },
    },
  ];
}

export function graphElements(data) {
  const nodes = (data.nodes || []).map((node) => ({
    data: {
      id: node.id,
      label: node.id,
      category: node.category,
      degree: node.degree || 0,
      risk: Boolean(node.risk),
      center: Boolean(node.center),
      color: node.risk
        ? categoryColors().RISK
        : categoryColors()[node.category] || "#6b7280",
    },
  }));
  const edges = (data.edges || []).map((edge, index) => ({
    data: {
      id: `e${index}`,
      source: edge.source,
      target: edge.target,
      weight: edge.count || 1,
    },
  }));
  return [...nodes, ...edges];
}

export function graphLegend() {
  return Object.entries(categoryColors())
    .map(
      ([key, color]) =>
        `<span class="inline-flex items-center gap-1.5 text-xs text-muted"><span class="w-2.5 h-2.5 rounded-full" style="background:${color}"></span>${escapeHtml(key)}</span>`
    )
    .join("");
}

let instance = null;

export function renderGraph(container, data, options = {}) {
  if (!container) return null;
  if (!window.cytoscape) {
    container.innerHTML = '<p class="text-sm text-muted p-4">Cytoscape no está disponible.</p>';
    return null;
  }
  if (!data || !data.nodes || data.nodes.length === 0) {
    container.innerHTML = '<p class="text-sm text-muted p-4">Sin datos de grafo.</p>';
    return null;
  }
  if (instance) {
    instance.destroy();
    instance = null;
  }
  instance = window.cytoscape({
    container,
    elements: graphElements(data),
    style: cyStyle(),
    layout: { name: "cose", animate: false, nodeRepulsion: 9000, idealEdgeLength: 90 },
    wheelSensitivity: 0.2,
  });
  instance.on("tap", "node", (event) => {
    highlightNeighbors(instance, event.target.id());
    if (options.onSelect) options.onSelect(event.target.id());
  });
  instance.on("tap", (event) => {
    if (event.target === instance) clearHighlight(instance);
  });
  return instance;
}

export function currentGraph() {
  return instance;
}

export function highlightNeighbors(cy, id) {
  cy.elements().addClass("dim");
  const node = cy.getElementById(id);
  node.removeClass("dim");
  const edges = node.connectedEdges();
  edges.removeClass("dim");
  edges.connectedNodes().removeClass("dim");
}

export function clearHighlight(cy) {
  cy?.elements().removeClass("dim");
}

export function filterGraph(cy, { categories = null, minDegree = 0 } = {}) {
  if (!cy) return;
  cy.nodes().forEach((node) => {
    const okCategory = !categories || categories.has(node.data("category"));
    const okDegree = (node.data("degree") || 0) >= minDegree;
    node.toggleClass("hidden-el", !(okCategory && okDegree));
  });
  cy.edges().forEach((edge) => {
    const hidden = edge.source().hasClass("hidden-el") || edge.target().hasClass("hidden-el");
    edge.toggleClass("hidden-el", hidden);
  });
}

export function exportGraphPng(cy, filename = "agant-grafo.png") {
  if (!cy) return;
  const url = cy.png({ full: true, scale: 2, bg: "#ffffff" });
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
}

function row(label, value) {
  return `<div class="flex justify-between gap-3 py-0.5"><dt class="text-muted">${escapeHtml(label)}</dt><dd class="text-right">${value}</dd></div>`;
}

export function graphDetail(data) {
  if (!data) return '<p class="text-sm text-muted">Busca una transacción o usa la vista global.</p>';
  const tx = data.transaction || {};
  const context = data.context || {};
  const decision = data.decision;
  const info = [
    row("ID", `<span class="font-mono text-xs">${escapeHtml(tx.transaction_id || "—")}</span>`),
    row("Source", tx.source ? sourceBadge(tx.source) : "—"),
    row("Tipo", escapeHtml(tx.type || "—")),
    row("Importe", fmtNumber(tx.amount)),
    row("Origen", `<span class="font-mono text-xs">${escapeHtml(tx.name_orig || "—")}</span>`),
    row("Destino", `<span class="font-mono text-xs">${escapeHtml(tx.name_dest || "—")}</span>`),
  ].join("");

  const contextRows = Object.entries(context)
    .map(
      ([name, item]) =>
        `<div class="py-1 border-b border-line last:border-0">
           <div class="flex justify-between gap-3"><span class="font-mono text-[11px]">${escapeHtml(name)}</span><span class="font-mono text-xs">${item.value ?? "—"}</span></div>
           <p class="text-[11px] text-muted">${escapeHtml(item.description || "")}</p>
         </div>`
    )
    .join("");

  const decisionBlock = decision
    ? `<div class="mt-3 pt-3 border-t border-line">
         ${row("Primaria", decisionBadge(decision.primary_decision))}
         ${row("Score", fmtScore(decision.primary_score))}
         ${row("Final", decisionBadge(decision.final_decision))}
         ${row("Laya", decision.laya?.invoked ? escapeHtml(String(decision.laya.decision || "—")) : `Omitida`)}
       </div>`
    : "";

  return `
    <h4 class="text-xs font-semibold uppercase tracking-wide text-muted mb-1">Transacción</h4>
    <dl class="text-sm">${info}</dl>
    ${decisionBlock}
    <h4 class="text-xs font-semibold uppercase tracking-wide text-muted mt-4 mb-1">Contexto de grafo</h4>
    ${contextRows || '<p class="text-xs text-muted">Sin contexto disponible.</p>'}
    ${data.note ? `<p class="text-[11px] text-muted mt-3">${escapeHtml(data.note)}</p>` : ""}`;
}
