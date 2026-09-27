# AGANT — WebSocket y SSE

## Transporte

- **WebSocket** para datos dinámicos (transacciones, decisiones, Laya).
- **SSE** para métricas agregadas.
- **HTTP** para bootstrap, configuración, estáticos y administración.

WebSocket es sólo el transporte: **no** convierte un replay en tráfico real.

## Eventos

```json
{
  "event_id": "live:decision.created:T1",
  "event_type": "decision.created",
  "source": "live",
  "timestamp": "2026-09-26T16:00:00Z",
  "sequence": 42,
  "payload": { }
}
```

| `event_type` | Cuándo |
|---|---|
| `transaction.created` | transacción aceptada |
| `transaction.updated` | reservado |
| `decision.created` | decisión final |
| `laya.decision` | sólo cuando `laya.invoked=true` |
| `system.status` / `system.error` | estado/errores |
| `flow.status` | avance de un flujo Live/Replay (contadores, p95, `batch_mode`, `batch_size`, `block_size`, `publish_mode`) |
| `replay.status` | avance de replay (CLI) |
| `metrics.updated` | SSE de métricas agregadas (1 s) |

## Payload de decisión autosuficiente

`decision.created` y `laya.decision` transportan el `DecisionResult` **más**
el contexto de la operación, para que una sola fila/burbuja se pueda
renderizar sin joins:

```json
{
  "transaction_id": "L23143",
  "source": "live",
  "event_id": "live:decision.created:L23143",
  "primary_decision": "SUSPICIOUS",
  "primary_score": 0.3742,
  "final_decision": "FRAUD",
  "laya": { "invoked": true, "status": "succeeded", "decision": "FRAUD", "latency_ms": 12.3 },
  "latency": { "rules_ms": 0.02, "ml_ms": 1.5, "graph_ms": 0.02, "laya_ms": 12.3, "total_ms": 14.1 },
  "transaction": { "type": "TRANSFER", "amount": 1250.5, "name_orig": "C123", "name_dest": "C987", "step": 700 },
  "state": { "features": {}, "evidence": { "rules": [], "ml": {}, "graph": { "status": "ready", "context": {} } } }
}
```

`transaction` y `state` son aditivos y reutilizan los contratos existentes
(`Transaction`, `DecisionState`).

## Errores del backend

En fallos relevantes el backend publica `system.error` con
`code`, `message` (seguro), `severity`, `operation` y `request_id`.
`/home` los muestra en «Errores recientes» sin exponer trazas.

## Reconexión y recuperación

El `EventBus` retiene un **historial acotado** de los últimos eventos
(`AGANT_EVENT_HISTORY`, por defecto 1000). Al reconectarse, el cliente pasa
`?last_sequence=<n>` con su última `sequence` vista y el servidor reenvía los
eventos retenidos posteriores antes de continuar con el vivo. El cliente
deduplica por `event_id`+`sequence`, de modo que cualquier solapamiento se
descarta. Si la caída supera el historial retenido, esos eventos no se
recuperan (se documenta, no se oculta).

## Identidad y orden

`event_id = "<source>:<event_type>:<transaction_id>"` distingue
`live` de `replay` para un mismo `transaction_id`. El frontend **no**
deduplica sólo por `transaction_id`: usa `event_id` (+ `sequence`).

`source` nunca se falsifica: `live` sólo desde la API online;
`replay` desde el motor de replay.

## Backpressure

El `EventBus` usa colas acotadas por suscriptor con política *drop-oldest*.
Las pérdidas se **cuentan** (`events_dropped`) y se exponen en
`/api/v1/metrics`; nunca se ocultan.

## Conexión en el frontend

Estados: `Conectando…`, `Conectado`, `Reconectando…`, `Sin conexión`,
`Error`. Reconexión con backoff exponencial (máx. 15 s); la desconexión
no se oculta. El bootstrap HTTP carga estado inicial y el WebSocket
reconcilia con actualizaciones. En cada reconexión el cliente adjunta
`last_sequence` para recuperar los eventos perdidos dentro del historial.
