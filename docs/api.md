# AGANT — API

Base: `http://<host>:8000`. Todas las respuestas usan el sobre uniforme:

```json
{ "success": true, "data": {}, "error": null, "request_id": "..." }
```

Error:

```json
{
  "success": false,
  "data": null,
  "error": { "code": "LAYA_ERROR", "message": "No fue posible completar la evaluación de Laya." },
  "request_id": "..."
}
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado básico (`ready`/`degraded`) |
| GET | `/api/v1/system/status` | Estado por componente (config, gpu, dataset, model, laya) |
| POST | `/api/v1/decision` | Decide una transacción (`source=live`) |
| POST | `/api/v1/decision/batch` | Hasta 1000 transacciones; ML vectorizado por lote, misma semántica que `/decision` |
| GET | `/api/v1/transactions` | Transacciones recientes (`limit`, `source`) |
| GET | `/api/v1/decisions` | Decisiones recientes (`limit`, `source`) |
| GET | `/api/v1/laya-decisions` | Decisiones con `laya.invoked=true` |
| GET | `/api/v1/metrics` | Snapshots live/live_synthetic/replay, etapas y EventBus |
| GET | `/api/v1/metrics/stream` | SSE `metrics.updated` |
| GET | `/api/v1/drift` | Drift de features/etiqueta (offline) |
| GET | `/api/v1/graph` | Contexto de grafo acotado |
| GET | `/api/v1/transactions/{id}/graph` | Subgrafo por transacción (dataset o live) con descripciones |
| POST | `/api/v1/flow/start` | Inicia flujo UI: `source`, `count` (entero o `"all"`), `laya_mode`, `laya_subfolder`, `batch_size` (1/32/64), `block_size`, `publish_mode` |
| POST | `/api/v1/flow/stop` | Detiene el flujo UI |
| POST | `/api/v1/transactions/import` | Importa y procesa transacciones (`source=live`) |
| GET | `/api/v1/laya/status` | Estado, checkpoint y VRAM de Laya |
| POST | `/api/v1/laya/load` | Carga un checkpoint (UI, no bloquea el loop) |
| POST | `/api/v1/laya/test` | Prueba Laya con una transacción de ejemplo |
| GET | `/api/v1/flow/status` | Estado y contadores del flujo |
| POST | `/api/v1/replay/start` | Inicia replay (admin) |
| POST | `/api/v1/replay/stop` | Detiene replay (admin) |
| GET | `/api/v1/replay/status` | Estado del replay |
| WS | `/api/v1/ws/events` | Todos los eventos |
| WS | `/api/v1/ws/transactions` | Eventos de transacción/decisión/Laya |

## Ejemplo de decisión

```bash
curl -s -X POST localhost:8000/api/v1/decision \
  -H 'Content-Type: application/json' \
  -d '{"transaction_id":"T1","step":700,"type":"TRANSFER","amount":181000,
       "name_orig":"C1","old_balance_org":181000,"name_dest":"C2","old_balance_dest":0}'
```

La respuesta incluye `event_id`, `primary_decision`, `primary_score`, `laya`,
`final_decision`, `fallback_level`, `fallback_reason`, `explanation` y
`latency` por etapa (`rules_ms`, `ml_ms`, `graph_ms`, `laya_ms`,
`serialization_ms`, `event_ms`, `fallback_ms`, `total_ms`). Además incluye
`transaction` (datos de la operación) y `state` (features + evidencia:
rules/ML/grafo), de modo que el evento realtime es autosuficiente. El campo
`isFraud` no se acepta (`extra="forbid"` → `400`).

## Administración

`/api/v1/replay/*` requiere `X-Admin-Token` igual a `AGANT_ADMIN_TOKEN`.
Si no hay token configurado, los endpoints administrativos responden `403`
y **no** se exponen.

Los endpoints **mutantes** (`/flow/start`, `/flow/stop`,
`/transactions/import`, `/laya/load`, `/laya/test`) exigen el token **sólo si**
`AGANT_ADMIN_TOKEN` está definido; con el token vacío quedan abiertos para no
romper el panel en desarrollo. El panel no envía el token: en despliegue,
protege estos endpoints con un proxy de autenticación o usa la API con la
cabecera.

## Seguridad

Validación de entrada, límite de lote (1000), CORS explícito, validación de
origen WebSocket, timeouts y errores seguros (sin trazas, rutas ni secretos).
