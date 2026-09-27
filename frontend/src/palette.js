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

export function setupPalette(actions) {
  let overlay = null;

  function close() {
    overlay?.remove();
    overlay = null;
  }

  function open() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.className = "fixed inset-0 z-50 bg-black/40 flex items-start justify-center pt-24";
    overlay.innerHTML = `<div class="w-full max-w-lg bg-panel border border-line-strong rounded-md shadow overflow-hidden">
      <input id="palette-input" class="control w-full rounded-none border-0 border-b border-line" placeholder="Ir a… o acción (Ctrl+K)" />
      <ul id="palette-list" class="max-h-80 overflow-auto text-sm"></ul>
    </div>`;
    document.body.appendChild(overlay);
    const input = overlay.querySelector("#palette-input");
    const list = overlay.querySelector("#palette-list");
    input.focus();

    const render = () => {
      const query = input.value.trim().toLowerCase();
      const matches = actions.filter((action) => action.label.toLowerCase().includes(query));
      list.innerHTML = matches.length
        ? matches
            .map(
              (action, index) =>
                `<li><button data-index="${index}" class="w-full text-left px-3 py-2 hover:bg-hover">${action.label}</button></li>`
            )
            .join("")
        : '<li class="px-3 py-2 text-muted">Sin resultados</li>';
      list.querySelectorAll("[data-index]").forEach((button) => {
        button.addEventListener("click", () => {
          close();
          matches[Number(button.dataset.index)].run();
        });
      });
    };

    input.addEventListener("input", render);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
      if (event.key === "Enter") {
        const matches = actions.filter((action) =>
          action.label.toLowerCase().includes(input.value.trim().toLowerCase())
        );
        if (matches[0]) {
          close();
          matches[0].run();
        }
      }
    });
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) close();
    });
    render();
  }

  window.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      open();
    }
  });

  return { open, close };
}
