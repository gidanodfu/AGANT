# AGANT — Laya (motor de decisión)

Laya es un motor de decisión **no autoregresivo** (paquete `laya`, Apache-2.0)
usado como **segunda opinión** para decisiones primarias `SUSPICIOUS`. Es
**opcional**: su fallo no cambia el nivel de fallback ni impide `READY`.

## Modos de decisión (eje separado)

`AGANT_DECISION_MODE` (o el selector por flujo `decision_mode`):

| Modo | Comportamiento |
|---|---|
| `hybrid` (default) | Laya es segunda opinión **solo** en `SUSPICIOUS` |
| `laya_all` | Laya **decide todas** las transacciones; `final_decision` = Laya; `primary_decision` (ML/reglas) se conserva para trazabilidad |

En `laya_all` se usa **micro-batching** (`Agent.predict_batch` con
`questions_from_json_schema` + `answers_to_json`) para agrupar estados y ganar
throughput. Si Laya no está `ready`, hay fallback explícito. Aviso: es más lento
y usa GPU.

## Modos de checkpoint

| Modo | Checkpoint | Comportamiento |
|---|---|---|
| `disabled` | ninguno | Laya no se usa |
| `pretrained` | `AGANT_LAYA_MODEL_ID` + `AGANT_LAYA_SUBFOLDER` (`typed-decisions`) | reutiliza el motor cargado en startup |
| `custom` | `AGANT_LAYA_CUSTOM_SUBFOLDER` | carga **otro checkpoint** (especializado) on-demand |

- `custom` **no entrena** nada: solo selecciona pesos distintos. Pensado para un
  checkpoint especializado en fraude.
- **Desde la UI** (`/nueva-transaccion` y `/home`): al elegir `custom` aparece
  un selector de checkpoint con `AGANT_LAYA_SUBFOLDERS` (por defecto
  `typed-decisions,multilingual`); la subcarpeta viaja en `flow/start`
  (`laya_subfolder`) y se carga on-demand. Así no falta el dato.
- Si no hay ninguna subcarpeta disponible, AGANT responde **400** con mensaje
  accionable (no 503).
- La carga del checkpoint custom se ejecuta **fuera del event loop**
  (`asyncio.to_thread`); la UI muestra **«Cargando…»** y avisa del consumo de
  VRAM. La latencia de Laya solo se registra cuando `laya.invoked=true`.
- Cargar `custom` junto al `pretrained` ya cargado suma VRAM; usa
  `AGANT_LAYA_MODE=custom` en el arranque para tener un solo modelo.

## Carga y fast path

- Carga en el `lifespan` (síncrona, idempotente) + warm-up; `fast=True`.
- El fast path requiere TileLang + el toolkit CUDA del paquete
  `nvidia-cuda-nvcc` (incluido en `requirements.txt`). Sin él, Laya cae al
  forward stock (más lento) y lo advierte por log.
- Los scores del checkpoint son **uncalibrated**: se tratan como etiqueta
  ordinal, nunca como probabilidad de fraude.

## Integración

- **In-process** (por defecto): `LayaDecisionEngine` en el backend.
- **Servicio GPU aislado** (opcional): `AGANT_LAYA_URL=http://laya:8001`
  apunta al servicio de `laya/service/app.py` (perfil `gpu` de compose). El
  navegador **nunca** contacta a Laya directamente.
- Solo se invoca cuando `primary_decision == SUSPICIOUS`; `LayaStatus` puede ser
  `disabled`, `skipped`, `unavailable`, `invoked`, `succeeded`, `failed`.
- La latencia de Laya solo cuenta cuando `laya.invoked=true`.

## Panel visual (`/laya`)

Pestaña dedicada para configurar y probar Laya:

- **Modo** (disabled/pretrained/custom) y **Checkpoint** (catálogo
  `AGANT_LAYA_SUBFOLDERS`), **warm-up**, botones **Cargar** (muestra
  “Cargando…”, no bloquea el servidor) y **Probar**.
- **Estado**: modo, estado, checkpoint, modo de decisión, **VRAM** asignada/
  reservada y GPU.
- **Preview** del resultado de prueba (JSON).
- Endpoints: `GET /api/v1/laya/status`, `POST /api/v1/laya/load`,
  `POST /api/v1/laya/test`. Cargar reemplaza el motor usado por `/decision` y
  los flujos (una carga a la vez; aviso de VRAM).

## Rendimiento medido

Fast path activo: carga ≈11 s, régimen ≈14 ms, VRAM in-process ≈4 GB. En un
replay con 36 invocaciones: 36/36 `succeeded`, latencia min 14.4 ms · p50 55.5 ·
p95 92.8 ms. Por eso Laya **no** está en la ruta crítica.
