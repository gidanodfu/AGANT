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

const TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"];

export async function parseFile(file) {
  if (!window.XLSX) throw new Error("SheetJS no está disponible.");
  const buffer = await file.arrayBuffer();
  const workbook = window.XLSX.read(buffer, { type: "array" });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  return window.XLSX.utils.sheet_to_json(sheet, { defval: "" });
}

const FIELD_ALIASES = {
  type: ["type", "tipo", "tipo_operacion", "operation"],
  amount: ["amount", "importe", "monto"],
  name_orig: ["nameorig", "name_orig", "cuenta_origen", "origen", "orig"],
  old_balance_org: ["oldbalanceorg", "old_balance_org", "saldo_origen", "old_balance_orig"],
  name_dest: ["namedest", "name_dest", "cuenta_destino", "destino", "dest"],
  old_balance_dest: ["oldbalancedest", "old_balance_dest", "saldo_destino"],
  step: ["step", "paso"],
  transaction_id: ["transaction_id", "id", "txid"],
  is_flagged_fraud: ["isflaggedfraud", "is_flagged_fraud", "marcada"],
};

function pick(row, key) {
  for (const alias of FIELD_ALIASES[key]) {
    const normalized = Object.keys(row).find((k) => k.trim().toLowerCase() === alias);
    if (normalized !== undefined) return row[normalized];
  }
  return undefined;
}

function toNumber(value) {
  if (value === "" || value === undefined || value === null) return NaN;
  return Number(String(value).replace(/,/g, ""));
}

/** Convierte filas (objeto) a transacciones del contrato. Nunca incluye isFraud. */
export function rowsToTransactions(rows) {
  const transactions = [];
  const errors = [];
  rows.forEach((row, index) => {
    if (Object.keys(row).some((k) => k.trim().toLowerCase() === "isfraud")) {
      errors.push({ row: index + 1, error: "isFraud no es una columna válida." });
      return;
    }
    const type = String(pick(row, "type") ?? "").trim().toUpperCase();
    const amount = toNumber(pick(row, "amount"));
    const oldOrg = toNumber(pick(row, "old_balance_org"));
    const oldDest = toNumber(pick(row, "old_balance_dest"));
    const nameOrig = String(pick(row, "name_orig") ?? "").trim();
    const nameDest = String(pick(row, "name_dest") ?? "").trim();
    const step = toNumber(pick(row, "step"));

    if (!TYPES.includes(type)) {
      errors.push({ row: index + 1, error: `Tipo inválido: ${type || "(vacío)"}` });
      return;
    }
    if (!(amount >= 0) || !(oldOrg >= 0) || !(oldDest >= 0)) {
      errors.push({ row: index + 1, error: "Importe/saldos deben ser numéricos ≥ 0." });
      return;
    }
    if (!nameOrig || !nameDest) {
      errors.push({ row: index + 1, error: "Cuenta origen y destino son obligatorias." });
      return;
    }
    const flaggedRaw = pick(row, "is_flagged_fraud");
    transactions.push({
      transaction_id: String(pick(row, "transaction_id") ?? "").trim() || `imp-${index + 1}`,
      step: Number.isFinite(step) && step >= 0 ? Math.trunc(step) : 700,
      type,
      amount,
      name_orig: nameOrig,
      old_balance_org: oldOrg,
      name_dest: nameDest,
      old_balance_dest: oldDest,
      is_flagged_fraud: Boolean(flaggedRaw) && String(flaggedRaw).toLowerCase() !== "false",
    });
  });
  return { transactions, errors };
}
