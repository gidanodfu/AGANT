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

import { escapeHtml } from "./ui.js";

let container = null;

function ensure() {
  if (container) return container;
  container = document.createElement("div");
  container.className = "fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80 max-w-[90vw]";
  document.body.appendChild(container);
  return container;
}

const STYLES = {
  warning: "border-warning",
  recoverable: "border-danger",
  critical: "border-danger",
  unavailable: "border-line-strong",
  success: "border-success",
};

export function toast({ severity = "recoverable", title, message }) {
  const host = ensure();
  const element = document.createElement("div");
  element.setAttribute("role", "alert");
  element.className = `border-l-4 ${STYLES[severity] || STYLES.recoverable} bg-canvas border border-line rounded-md px-3 py-2 shadow text-sm`;
  element.innerHTML = `<p class="font-medium">${escapeHtml(title || "")}</p>${
    message ? `<p class="text-xs text-muted mt-0.5">${escapeHtml(message)}</p>` : ""
  }`;
  host.appendChild(element);
  setTimeout(() => element.remove(), 6000);
}
