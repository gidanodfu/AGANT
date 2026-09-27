# AGANT — Arquitectura

AGANT es un sistema híbrido de detección de fraude: **reglas + ML + grafo**
producen evidencia, **Laya** toma la decisión central (segunda opinión) y
una **política de fallback** garantiza una decisión aunque falte un
componente. No existe un orquestador monolítico: una composition root
(`app/main.py`) conecta componentes y la lógica vive en cada módulo.

```
Transacción
   │
FeatureBuilder (9 tabulares + 6 de grafo causales)
   ├── RulesEngine        ┐
   ├── MLDecisionProvider ├── Evidence
   └── GraphContextProvider ┘
            │
     DecisionStateBuilder
            │
     LayaDecisionEngine   (solo SUSPICIOUS, opcional, ordinal no calibrado)
            │
       FallbackPolicy
            │
   Decisión + Explicación
            │
   EventBus → WebSocket / SSE → Frontend
            └── MetricsCollector (live/live_synthetic/replay separados)
```

## Capas (`backend/app/`)

| Capa | Responsabilidad |
|---|---|
| `contracts/` | Contratos tipados pydantic, única superficie de tipos |
| `data/` | PaySim: descarga, verificación, DuckDB, splits, memmaps |
| `features/` | Features offline (memmap) y online (causal) |
| `evidence/` | `RulesEngine`, `MLDecisionProvider`, `GraphContextProvider`, `EvidenceEngine` |
| `decision/` | `DecisionStateBuilder`, `LayaDecisionEngine`, `FallbackPolicy`, `DecisionEngine` |
| `events/` | `EventBus` con backpressure y métricas |
| `observability/` | `MetricsCollector`, estado de arranque, drift |
| `replay/` | `ReplayEngine`/`ReplayController` (source=replay) |
| `api/`, `ws/` | HTTP, WebSocket, SSE |
| `service.py` | Capa de aplicación: ejecuta, mide, publica (sin lógica de negocio) |

## Semántica de decisión

Se preserva siempre la separación: `primary_decision`, `primary_score`,
`laya_result`, `final_decision`, `fallback_reason`. Un upgrade/downgrade
de Laya nunca sobrescribe la decisión primaria de forma silenciosa.

## Fallback (por disponibilidad real)

| Nivel | Condición | Decisión |
|---|---|---|
| 0 `GRAPH_ML` | grafo + ML | `Rules + RF online+grafo` |
| 1 `ML_ONLY` | ML sin grafo | `Rules + RF online` |
| 2 `RULES_ONLY` | ML no disponible | `Rules` |

La disponibilidad de Laya **no** cambia el nivel de fallback. AGANT puede
quedar `READY` con Laya `FAILED`.

## Causalidad

Ningún componente online accede a información futura. La ruta online usa
9 features tabulares + 6 de grafo con ventana `RANGE BETWEEN UNBOUNDED
PRECEDING AND 1 PRECEDING` sobre `step`. Prohibidos como feature:
`newbalanceOrg`, `newbalanceDest`, `isFraud` y derivados post-transacción.
