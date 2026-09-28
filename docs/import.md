# AGANT — Importar transacciones

La importación se realiza por **API** (no hay botón en el panel): se envían
transacciones y se **procesan de verdad** por el pipeline (reglas + ML + grafo +
Laya), no es una carga decorativa.

## Endpoint

`POST /api/v1/transactions/import` recibe `{transactions, decision_mode?,
batch_size?}` (máx. 20 000 filas) y lanza un **job en segundo plano**
(`kind="import"`, `source="live"`) con el mismo motor de decisiones. El progreso
llega por `flow.status` (procesadas, throughput, p95, ETA) y los eventos reales
aparecen en `/home`, `/transacciones` y `/decisiones` por WebSocket.

- Validación por fila (contrato `Transaction`, `extra="forbid"`).
- Se respeta `decision_mode` (`hybrid` / `laya_all`) y `batch_size` (1/32/64).
- Rate limit compartido con los flujos.
- Si `AGANT_ADMIN_TOKEN` está definido, exige `X-Admin-Token`.

### Ejemplo

```bash
curl -s -X POST localhost:8000/api/v1/transactions/import \
  -H 'Content-Type: application/json' \
  -d '{"transactions":[
        {"transaction_id":"imp-1","step":700,"type":"PAYMENT","amount":20,
         "name_orig":"I1","old_balance_org":500,"name_dest":"I2","old_balance_dest":0}
      ],"batch_size":32}'
```

## Formato de las transacciones

Cada elemento es un `Transaction` (mismo contrato que `/api/v1/decision`):

| Campo | Obligatorio | Notas |
|---|---|---|
| `transaction_id` | sí | único, 1–128 chars |
| `step` | sí | entero ≥ 0 |
| `type` | sí | `CASH_IN`/`CASH_OUT`/`DEBIT`/`PAYMENT`/`TRANSFER` |
| `amount` | sí | ≥ 0, finito |
| `name_orig` / `name_dest` | sí | 1–128 chars |
| `old_balance_org` / `old_balance_dest` | sí | ≥ 0 |
| `is_flagged_fraud` | no | señal del protocolo (no ground truth) |

- **`isFraud` (ground truth) está prohibido**: el contrato lo rechaza
  (`extra="forbid"` → 400).
- Un ejemplo listo para clase: `docs/ejemplos/transacciones-clase.csv` (para
  convertir a JSON) y `docs/pruebas-clase.md`.
