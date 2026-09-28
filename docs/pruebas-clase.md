# AGANT — Guía de pruebas (clase)

Peticiones listas para copiar/pegar y verificar el comportamiento del sistema.
Todos los datos son ficticios. Los resultados exactos pueden variar con el
estado del grafo y con Laya encendido (`hybrid`), por lo que se indican como
"esperado ≈".

## 0. Arranque

```bash
bash scripts/run.sh          # arranca el backend y verifica /health
bash scripts/stop.sh         # detiene
tail -f /tmp/agant_run.log   # logs en vivo (Laya tarda ~11 s en cargar)
```

Comprobar:

```bash
curl -s localhost:8000/health | python3 -m json.tool
curl -s localhost:8000/api/v1/system/status | python3 -m json.tool
```

Esperado: `status: ready` y `config/gpu/dataset/model/laya = ready`.

## 1. Decisión individual

`POST /api/v1/decision` — cuerpo = una `Transaction`.

```bash
post() { curl -s -X POST localhost:8000/api/v1/decision -H 'Content-Type: application/json' -d "$1" | python3 -m json.tool; }

# 1.1 LEGITIMATE
post '{"transaction_id":"c1","step":700,"type":"PAYMENT","amount":50,"name_orig":"C1","old_balance_org":900,"name_dest":"M1","old_balance_dest":0}'

# 1.2 FRAUD por ML
post '{"transaction_id":"c2","step":700,"type":"TRANSFER","amount":120,"name_orig":"C2","old_balance_org":500,"name_dest":"M2","old_balance_dest":0}'

# 1.3 FRAUD por regla R002 (importe alto)
post '{"transaction_id":"c3","step":700,"type":"TRANSFER","amount":250000,"name_orig":"C3","old_balance_org":250000,"name_dest":"M3","old_balance_dest":0}'

# 1.4 R001 forzado (señal del protocolo)
post '{"transaction_id":"c4","step":700,"type":"TRANSFER","amount":10,"name_orig":"C4x","old_balance_org":100,"name_dest":"M4x","old_balance_dest":0,"is_flagged_fraud":true}'
```

| Caso | `primary_decision` | `final_decision` | `explanation` |
|---|---|---|---|
| 1.1 | LEGITIMATE | LEGITIMATE | `score ML≈0.0001` |
| 1.2 | FRAUD | FRAUD | `score ML≈0.99` |
| 1.3 | FRAUD | FRAUD | `Operación de alto riesgo…` (R002) |
| 1.4 | FRAUD | FRAUD | marcada por el protocolo (R001) |

**Clave didáctica:** `primary` es del sistema (ML/reglas); `final` puede
cambiarlo **Laya**.

## 2. Override de Laya (primary ≠ final)

```bash
post '{"transaction_id":"c5","step":700,"type":"CASH_OUT","amount":50000,"name_orig":"C5a","old_balance_org":50000,"name_dest":"C5b","old_balance_dest":0}'
```

Esperado ≈: `primary_decision = SUSPICIOUS` (score ≈0.98) y `final_decision =
LEGITIMATE` porque **Laya bajó** la decisión. Verifícalo en el detalle: `laya:
{invoked:true, status:"succeeded", decision:"LEGITIMATE"}`.

Para ver `final = SUSPICIOUS` **sin** Laya: usa el panel de flujo con
`laya_mode:"disabled"` (sección 6) o desactiva Laya en `/laya`.

## 3. Reglas R001–R004

- **R001 (crítico):** `is_flagged_fraud=true` → FRAUD forzado (caso 1.4).
- **R002:** TRANSFER/CASH_OUT con `amount ≥ 200000` (caso 1.3).
- **R003:** `amount ≥ old_balance_org` ("cuenta vaciada") → evidencia; si el ML
  está disponible, decide el ML.
- **R004 (fan-in):** envía 11 transferencias desde cuentas distintas al mismo
  destino (ver el CSV de la sección 7); en la última la explicación incluye
  "el destino concentra transacciones…".

## 4. Grafo y RISK

```bash
# envía un FRAUD (caso 1.4) y mira el grafo global
curl -s "localhost:8000/api/v1/graph?limit=50" | python3 -m json.tool
```

- Los nodos origen/destino de una decisión **FRAUD** salen con `risk:true` y
  tag `RISK` (color rojo en `/grafo`).
- En `/grafo`, el chip **RISK** filtra los nodos de riesgo.
- Subgrafo por transacción: `GET /api/v1/transactions/<id>/graph` (en el dataset
  `R…`, RISK = solo `isFlaggedFraud`).

## 5. Laya (`/laya`)

- **Estado:** modo, checkpoint, VRAM y GPU.
- `POST /api/v1/laya/load` `{"mode":"pretrained"|"custom"|"disabled"}` y
  `POST /api/v1/laya/test`.
- En `/decisiones` se ven las filas con `laya.invoked=true`, su decisión y
  `latency_ms` (Laya está **fuera** de la ruta crítica).

## 6. Flujos Live / Replay

```bash
curl -s -X POST localhost:8000/api/v1/flow/start -H 'Content-Type: application/json' \
  -d '{"source":"live","count":100,"laya_mode":"disabled","batch_size":32}' | python3 -m json.tool
curl -s localhost:8000/api/v1/flow/status | python3 -m json.tool
curl -s -X POST localhost:8000/api/v1/flow/stop | python3 -m json.tool
```

- `source:"live"` → tráfico **sintético** (`live_synthetic`); `source:"replay"`
  → PaySim (`replay`).
- Prueba `batch_size` 1/32/64 y `laya_mode` disabled/pretrained.

## 7. Lote e Import

```bash
# lote (ML vectorizado), misma semántica que /decision
curl -s -X POST localhost:8000/api/v1/decision/batch -H 'Content-Type: application/json' -d '[
 {"transaction_id":"b1","step":700,"type":"PAYMENT","amount":20,"name_orig":"C1","old_balance_org":500,"name_dest":"M1","old_balance_dest":0}
]' | python3 -m json.tool
```

Import desde el CSV de ejemplo (`docs/ejemplos/transacciones-clase.csv`):

```bash
python3 - <<'PY'
import csv, json, urllib.request
rows = list(csv.DictReader(open("docs/ejemplos/transacciones-clase.csv")))
txs = [{
  "transaction_id": f"cls-{i+1}", "step": int(r["step"]), "type": r["type"],
  "amount": float(r["amount"]), "name_orig": r["nameOrig"],
  "old_balance_org": float(r["oldBalanceOrg"]), "name_dest": r["nameDest"],
  "old_balance_dest": float(r["oldBalanceDest"]),
} for i, r in enumerate(rows)]
req = urllib.request.Request("http://localhost:8000/api/v1/transactions/import",
  data=json.dumps({"transactions": txs, "batch_size": 32}).encode(), method="POST",
  headers={"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req))["data"]["state"])
PY
```

> El botón **Importar** del panel ya no existe; la importación es por API.

## 8. Tiempo real y métricas

```bash
curl -s localhost:8000/api/v1/metrics | python3 -m json.tool   # snapshots live/live_synthetic/replay
curl -sN localhost:8000/api/v1/metrics/stream                  # SSE (Ctrl-C para salir)
```

- En `/home`, la tabla "Actividad en tiempo real" se alimenta por WebSocket.
- **Reconexión:** con el panel abierto, `stop.sh` y luego `run.sh`; el cliente
  reconecta y recupera eventos con `?last_sequence` (dentro del historial).

## 9. Drift

```bash
curl -s "localhost:8000/api/v1/drift?sample=5000" | python3 -m json.tool
```

## 10. Auth opcional (endpoints mutantes)

```bash
AGANT_ADMIN_TOKEN=secreto bash scripts/run.sh
# sin cabecera → 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/api/v1/flow/start \
  -H 'Content-Type: application/json' -d '{"source":"live","count":5}'
# con cabecera → 200
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/api/v1/flow/start \
  -H 'Content-Type: application/json' -H 'X-Admin-Token: secreto' -d '{"source":"live","count":5}'
```

## 11. Suites y benchmark

```bash
.venv/bin/python -m pytest        # 144
cd frontend && npm test           # 26
.venv/bin/python scripts/benchmark_e2e.py --records 3000 --batch 32
```

## Notas didácticas

- **`primary` vs `final`:** el sistema produce la primaria; Laya puede
  reemplazarla (upgrade/downgrade) cuando su estado es `succeeded`.
- **Umbral del ML:** se elige en VALIDATION y viaja en el artefacto (**0.989**);
  `state.thresholds` muestra los valores de configuración (0.2/0.5), no el del
  modelo. ≥0.989 = FRAUD, ≥0.2 = SUSPICIOUS.
- **Fuentes:** `live` (API/import), `live_synthetic` (flujo Live del panel),
  `replay` (PaySim). No se mezclan.
- **Reglas:** casi todo el trabajo lo hace el ML; las reglas solas tienen F1≈0.01.
