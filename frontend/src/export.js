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

export function exportRows(rows, filename = "agant-transacciones.xlsx") {
  if (!rows || rows.length === 0) return "empty";
  if (window.XLSX) {
    const sheet = window.XLSX.utils.json_to_sheet(rows);
    const book = window.XLSX.utils.book_new();
    window.XLSX.utils.book_append_sheet(book, sheet, "Transacciones");
    window.XLSX.writeFile(book, filename);
    return "xlsx";
  }
  const header = Object.keys(rows[0]);
  const lines = [
    header.join(","),
    ...rows.map((row) => header.map((key) => JSON.stringify(row[key] ?? "")).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename.replace(/\.xlsx$/, ".csv");
  link.click();
  URL.revokeObjectURL(link.href);
  return "csv";
}

export function decisionToRow(payload) {
  const tx = payload.transaction || {};
  const laya = payload.laya || {};
  const lat = payload.latency || {};
  return {
    transaction_id: payload.transaction_id,
    source: payload.source,
    tipo: tx.type || "",
    importe: tx.amount ?? "",
    cuenta_origen: tx.name_orig || "",
    cuenta_destino: tx.name_dest || "",
    primaria: payload.primary_decision || "",
    score: payload.primary_score ?? "",
    laya_invocado: laya.invoked ? "sí" : "no",
    laya_resultado: laya.decision || "",
    laya_latencia_ms: laya.invoked ? laya.latency_ms ?? "" : "",
    final: payload.final_decision || "",
    total_ms: lat.total_ms ?? "",
    event_id: payload.event_id || "",
    fecha: payload.decided_at || "",
  };
}
