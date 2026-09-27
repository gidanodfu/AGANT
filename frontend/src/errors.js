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

import { toast } from "./toast.js";

const active = new Map();

const STYLES = {
  warning: { box: "border-warning bg-panel text-warning", icon: "alert-triangle" },
  recoverable: { box: "border-danger bg-panel text-danger", icon: "alert-circle" },
  critical: { box: "border-danger bg-panel text-danger", icon: "shield-alert" },
  unavailable: { box: "border-line-strong bg-panel text-fg-secondary", icon: "cloud-off" },
};

function region() {
  return document.getElementById("error-region");
}

export function reportError({ key = null, severity = "recoverable", title, message, detail = null }) {
  const id = key || `${severity}:${title}:${message}`;
  active.set(id, { severity, title, message, detail });
  render();
  toast({ severity, title, message });
}

export function clearError(key) {
  if (active.delete(key)) render();
}

function render() {
  const container = region();
  if (!container) return;
  if (active.size === 0) {
    container.innerHTML = "";
    return;
  }
  const blocks = [];
  for (const [id, item] of active) {
    const style = STYLES[item.severity] || STYLES.recoverable;
    const detail = item.detail
      ? `<details class="mt-1"><summary class="cursor-pointer text-xs opacity-80">Detalle técnico</summary><pre class="mt-1 max-h-40 overflow-auto whitespace-pre-wrap text-[11px] opacity-90">${escapeHtml(item.detail)}</pre></details>`
      : "";
    blocks.push(`
      <div class="mb-2 flex items-start gap-3 rounded-md border ${style.box} px-3 py-2 text-sm" data-error="${escapeHtml(id)}">
        <i data-lucide="${style.icon}" class="w-4 h-4 mt-0.5 shrink-0"></i>
        <div class="min-w-0 flex-1">
          <p class="font-medium">${escapeHtml(item.title)}</p>
          <p class="text-xs opacity-90">${escapeHtml(item.message)}</p>
          ${detail}
        </div>
        <button class="text-xs underline opacity-70 hover:opacity-100" data-dismiss="${escapeHtml(id)}">Cerrar</button>
      </div>`);
  }
  container.innerHTML = blocks.join("");
  container.querySelectorAll("[data-dismiss]").forEach((button) => {
    button.addEventListener("click", () => clearError(button.dataset.dismiss));
  });
  if (window.lucide) window.lucide.createIcons();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function installGlobalHandlers() {
  window.addEventListener("error", (event) => {
    reportError({
      key: "runtime",
      severity: "recoverable",
      title: "Ocurrió un error inesperado en la interfaz",
      message: "Puedes continuar; si persiste, recarga la página.",
      detail: event.error?.stack || event.message,
    });
  });
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    reportError({
      key: "promise",
      severity: "recoverable",
      title: "Una operación de la interfaz no se completó",
      message: reason?.message || "Se reintentará automáticamente.",
      detail: reason?.stack || String(reason),
    });
  });
}
