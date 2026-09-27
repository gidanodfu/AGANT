# AGANT — Importar transacciones

Junto a **Exportar XLSX** en `/home`, `/transacciones` y `/decisiones` hay un
botón **Importar** para cargar transacciones desde un archivo y **procesarlas de
verdad** por el pipeline (no es una carga decorativa).

## Formato

`.xlsx` o `.csv` con columnas equivalentes a PaySim (se aceptan nombres en
español):

| Contrato | Alias aceptados |
|---|---|
| `type` | tipo, tipo_operacion |
| `amount` | importe, monto |
| `name_orig` | cuenta_origen, origen |
| `old_balance_org` | saldo_origen |
| `name_dest` | cuenta_destino, destino |
| `old_balance_dest` | saldo_destino |
| `step` | paso (opcional, default 700) |
| `transaction_id` | id (opcional, se autogenera) |
| `is_flagged_fraud` | marcada (opcional) |

- **`isFraud` está prohibido** (ground truth). Si el archivo lo incluye, esas
  filas se rechazan con un aviso.
- El parseo ocurre **en el navegador** (SheetJS); las filas válidas se envían
  al backend.

## Procesamiento

`POST /api/v1/transactions/import` recibe `{transactions, decision_mode?,
batch_size?}` (máx. 20 000 filas) y lanza un **job en segundo plano**
(`kind="import"`, `source="live"`) con el mismo motor de decisiones. El progreso
llega por `flow.status` (procesadas, throughput, p95, ETA) y los eventos reales
aparecen en `/home`, `/transacciones` y `/decisiones` por WebSocket.

- Validación por fila (contrato `Transaction`, `extra="forbid"`).
- Se respeta `decision_mode` (`hybrid` / `laya_all`) y `batch_size` (1/32/64).
- Rate limit compartido con los flujos.

## UI

El botón cambia el icono (subir/bajar) y la etiqueta para distinguir
rápidamente **Exportar** de **Importar**. Al terminar se muestra un toast con
las procesadas; las filas inválidas se resumen (primeras N).
