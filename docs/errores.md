# AGANT — Errores

Estrategia formal: **capturar → clasificar → registrar contexto → medir →
propagar → responder**. Sin `except: pass` ni errores silenciosos.

## Taxonomía (`ErrorCode`)

`VALIDATION_ERROR, FEATURE_ERROR, GRAPH_ERROR, ML_ERROR, LAYA_ERROR,
MODEL_LOAD_ERROR, CONFIG_ERROR, DATABASE_ERROR, EVENT_BUS_ERROR,
WEBSOCKET_ERROR, SSE_ERROR, REPLAY_ERROR, TIMEOUT_ERROR, INTERNAL_ERROR`.

Cada error tiene `code`, `status` (HTTP), `severity`, `source`,
`operation`, `details` seguros y `request_id` (correlación).

## Seguridad de la respuesta

Al cliente se le devuelve un **mensaje seguro** por código; nunca trazas,
rutas internas, credenciales ni `repr` de excepciones. El detalle técnico
queda sólo en logs. Ejemplo:

| Código | HTTP | Mensaje |
|---|---|---|
| `VALIDATION_ERROR` | 400 | La transacción enviada no es válida. |
| `ML_ERROR` | 503 | El modelo de Machine Learning no está disponible. |
| `LAYA_ERROR` | 503 | No fue posible completar la evaluación de Laya. |
| `TIMEOUT_ERROR` | 504 | La operación excedió el tiempo máximo permitido. |
| `INTERNAL_ERROR` | 500 | Ocurrió un error interno controlado. |

## En el frontend

Capa global captura `window.onerror`, `unhandledrejection`, errores de
`fetch` y de WebSocket. Se muestran en español y distinguen severidad:
`warning`, `recoverable`, `critical`, `unavailable`. El usuario entiende
qué ocurrió, qué componente se afectó y si puede continuar. El mensaje
principal es comprensible; el detalle técnico es opcional/expandible.

## Degradación controlada

Si Laya falla, AGANT sigue `READY` con `fallback_level=0`. Si ML falta,
cae a `RULES_ONLY`. Si el grafo falta, a `ML_ONLY`. La caída de un
componente opcional no detiene el sistema.
