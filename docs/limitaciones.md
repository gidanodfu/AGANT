# AGANT — Limitaciones

Documento honesto de lo que AGANT **no** garantiza y de los resultados que
deben leerse con cautela. Todo lo aquí citado se apoya en el código, los
tests y los artefactos en `results/`.

## Alcance

- Es un **prototipo académico**, no un sistema de producción. La meta
  `p95 < 50 ms` es una meta de ingeniería medida **offline y sin red**.
- No hay despliegue multi-réplica: `EventBus`, `RateLimit` y `Store` son de
  un solo proceso y sin locks. Las cifras no escalan horizontalmente tal cual.

## Datos y evaluación

- **PaySim es sintético** y la tasa de fraude crece con el `step` (drift
  documentado). El split es temporal; las métricas reflejan ese drift, no un
  entorno productivo.
- La **licencia de PaySim está sin verificar** (`THIRD_PARTY_NOTICES.md`) y no
  se redistribuye.
- Los artefactos (`features.f32`, `online_model.joblib`) están fuera de git y
  deben regenerarse (requiere internet para PaySim y GPU para Laya).

## Reglas y grafo

- Las **reglas deterministas solas son casi inútiles**: F1 ≈ 0.011 con
  positivo = `FRAUD`; al relajar a `SUSPICIOUS` marcan casi todo
  (`results/metrics/baselines.json`). R001 usa `isFlaggedFraud` (señal del
  protocolo, **no** ground truth) y sólo aparece en 16 filas.
- Bajo paridad de features (`online_v2`), el **grafo no mejora** el F1 en la
  ablación (**−0.0117**); sólo se cita como hallazgo, no como aporte.
- `online_v2` **acota la historia** del grafo con LRU (caps 2M/2M). Es
  deliberado para que el servicio coincida con el entrenamiento, pero limita
  el contexto en datasets con más de ~2M cuentas/aristas.

## Modelo

- El modelo servido es un **GBM con pesos balanceados** y umbral alto
  (**0.989**, elegido por F1 en VALIDATION). Los scores **no están
  calibrados**: no deben interpretarse como probabilidad de fraude.
- Las métricas tienen intervalos anchos por la baja prevalencia
  (`docs/modelos.md`); no son garantía de generalización a tráfico real.
- `audit_only` (con `newbalance*`, F1 0.8761) es sólo un techo teórico
  post-transacción; **no** es apto para online.

## Laya

- Laya es un **checkpoint preentrenado** (`convaiinnovations/laya`); **no se
  entrena ni se calibra** aquí. Sus scores se tratan como etiqueta ordinal.
- Está **fuera de la ruta crítica** por su latencia variable (p95 hasta ~93 ms
  bajo carga). Su fallo no cambia el nivel de fallback.
- Si Laya tiene éxito, **reemplaza** la decisión primaria (upgrade o
  downgrade), incluso en modo `hybrid`. No es una mera sugerencia.

## Decisión

- Sólo existen tres decisiones: `FRAUD`, `SUSPICIOUS`, `LEGITIMATE`. **No hay
  estado `REVIEW`** ni decisión de error.
- El "fallback de grafo" sólo se activa ante una excepción del proveedor; no
  hay degradación por saturación de los caps LRU.

## Tiempo real y robustez

- El WebSocket recupera eventos **sólo dentro del historial retenido**
  (`AGANT_EVENT_HISTORY`, por defecto 1000). Caídas más largas pierden eventos.
- El `EventBus` aplica *drop-oldest* por suscriptor; las pérdidas se cuentan,
  pero no se reintentan.
- Los endpoints mutantes (`/flow/*`, `/transactions/import`, `/laya/load`) **no
  exigen token** por defecto; el rate-limit es por proceso y sin respaldo
  distribuido.

## Rendimiento

- Las cifras de `docs/rendimiento.md` son de **batch offline sin red**. El
  modo por lotes vectoriza **sólo el ML**; features, reglas, grafo y Laya
  siguen por ítem.
- El objetivo "100k tps" es una **propiedad de arquitectura** (particionado,
  colas, réplicas), no un resultado medido de este repositorio.

## Decisiones de diseño no implementadas (a propósito)

- **Estado `REVIEW`:** el diseño usa `SUSPICIOUS` como bandeja de revisión
  humana (Laya sólo se invoca ahí). Añadir un cuarto estado sin un flujo de
  revisor real duplicaría `SUSPICIOUS` y ampliaría un contrato que nadie
  consumiría. Se deja como extensión si surge el caso de uso.
- **Calibración de Laya:** sus scores son *uncalibrated* y se tratan como
  etiqueta ordinal; calibrarlos exigiría ejecuciones con GPU y un conjunto
  etiquetado de salidas de Laya, con poco valor para una segunda opinión que
  ya es discreta.

## Metodología del repositorio

- La documentación puede quedar desactualizada; cuando difiere del código, la
  prioridad es **código > tests > configuración > documentación**.
- La comparación RF vs GBM se hizo sobre una única partición temporal; no hay
  validación cruzada ni prueba de significancia entre ambos modelos (sí
  intervalos de confianza dentro de TEST).
