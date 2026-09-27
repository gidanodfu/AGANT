# AGANT — Flujo interactivo (`/nueva-transaccion`)

Punto de entrada para **crear, enviar y observar** transacciones usando el
pipeline real del backend. No es una simulación visual: cada acción llama a
la API y genera eventos reales.

```
Nueva transacción → Procesar → Resultado inmediato
                              → EventBus → WebSocket
                                 ├── /transacciones
                                 ├── /decisiones (si Laya fue invocado)
                                 ├── /grafo
                                 └── /home (métricas)
```

La ruta `/transacciones` sigue siendo el **monitor** del flujo; el
formulario vive aparte en `/nueva-transaccion`.

## Formulario (transacción individual)

Campos disponibles **antes** de decidir: tipo de operación, importe, cuenta
origen/destino, saldo origen/destino, `step` y la marca del protocolo
`isFlaggedFraud` (señal de reglas, no ground truth).

- **`isFraud` nunca se envía**: es ground truth. El contrato
  `Transaction` usa `extra="forbid"`, de modo que el backend responde
  `400 VALIDATION_ERROR` si se intentara. El backend es la autoridad.
- `transaction_id` se autogenera (`ui-…`) si no se provee.
- Acciones: **Procesar transacción** y **Limpiar**. Estados del botón:
  `idle`, `processing` ("Procesando…"), `success`, `warning`, `error`.

### Resultado inmediato

Muestra `Estado`, `Transacción`, `Evento` (`event_id`),
`Source`, `Primaria`, `Score`, `Laya`, `Final`, `Latencia total` y el
desglose (`rules_ms`, `ml_ms`, `graph_ms`, `laya_ms`, `serialization_ms`).
La latencia procede **del backend**; el navegador no la calcula.

## Flujo de transacciones

Controles: **Fuente** (Live / PaySim Replay), **Cantidad**
(100 / 1000 / 10000 / 100000 / Personalizado), **Bloque** (filas por bloque,
100k por defecto), **Batch size** (1 per-item / 32 / 64), **Modo Laya**
(Deshabilitado / Pretrained / Custom), **Publicación** (muestreada / todas),
**Iniciar**, **Detener**.

El **modo por lotes** (batch 32/64) vectoriza la inferencia ML manteniendo las
mismas decisiones (paridad verificada). El panel está disponible en
`/nueva-transaccion` y, en versión compacta, en `/home`.

- **Todo el dataset**: la Cantidad incluye «Todo el dataset (6,362,620)»,
  **solo para PaySim Replay** (Live exige una cantidad). Procesa en una pasada
  con `count:"all"`, progreso y **ETA** desde el primer estado, y se puede
  **Detener** conservando estadísticas (≈30 min a ~3,400 tx/s). La publicación
  por defecto es **muestreada** (se puede cambiar a «Todas»).
- **Historial**: cada transacción procesada queda en la **ventana del backend**
  (últimas 500, sin muestreo); la ventana del navegador muestra las últimas 100.
- **Custom**: al elegir modo Laya `custom` aparece un selector de checkpoint
  (`AGANT_LAYA_SUBFOLDERS`); la carga se hace sin bloquear el servidor y el
  botón muestra **«Cargando…»** (aviso de VRAM).
- **Modo de decisión** (`decision_mode`): `Híbrido` (Laya solo SOSPECHOSAS) o
  **`Laya decide todo`** (Laya evalúa cada transacción; la decisión primaria se
  conserva). Se muestra un chip en el header (`Híbrido`/`Laya-todo · Laya estado`).
- **UI**: tema claro/oscuro, toasts, `Ctrl+K` (command palette), sparklines de
  throughput/p95, tablas responsive, presets/aleatoria, grafo interactivo
  (filtros por categoría/grado, vecinos, export PNG) y **export XLSX** de las
  transacciones/decisiones filtradas.
- **Filtros**: en `/home`, `/transacciones` y `/decisiones` hay filtros por
  decisión (Todas/Fraude/Sospechosa/Legítima), «solo con Laya» y búsqueda por
  `transaction_id` o cuenta (filtrado en cliente, sin polling).

| Fuente | Semántica | Origen de datos |
|---|---|---|
| Live | `source="live_synthetic"` | transacciones sintéticas generadas server-side |
| PaySim Replay | `source="replay"` | dataset PaySim, orden temporal |

Replay **nunca** se etiqueta como live. El flujo Live es **sintético**
(`live_synthetic`) y no contamina las métricas ni el drift del live real
(`source="live"`, API/import). Live **no** usa PaySim.

- **Modo Laya**: `disabled` no usa Laya; `pretrained` reutiliza el motor ya
  cargado; `custom` exige `AGANT_LAYA_CUSTOM_SUBFOLDER` (si falta, error
  claro `LAYA_ERROR`).
- El progreso llega por eventos `flow.status` (no hay polling para fingir
  tiempo real ni `sleep` en el backend). Si los datos son rápidos, se
  muestran rápido; el render usa `requestAnimationFrame` y el `EventBus`
  aplica backpressure con contadores.
- Al **Detener**, las estadísticas ya obtenidas se conservan
  (`processed`, `fraud`, `suspicious`, `legitimate`, `errors`,
  `throughput_tps`, `latency_p95_ms`).

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/flow/start` | `{source, count, offset?, laya_mode}` |
| POST | `/api/v1/flow/stop` | detiene el flujo |
| GET | `/api/v1/flow/status` | estado y contadores |

Estos endpoints son la entrada de la UI (no administrativos). Los
`/api/v1/replay/*` siguen requiriendo `X-Admin-Token`.

## Errores

Capa global + manejo por operación: API no disponible, WebSocket
desconectado, validación, timeout, ML, grafo, Laya, interno y replay
fallido. Mensajes en español; el detalle técnico es expandible y nunca se
muestra un stack trace como mensaje principal.

## Trazabilidad

`event_id`, `transaction_id` y `source` identifican de forma unívoca cada
evento y permiten relacionar el resultado inmediato, el WebSocket y las
vistas. `event_id = "<source>:<event_type>:<transaction_id>"`.
