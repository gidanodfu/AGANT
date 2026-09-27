# AGANT — Grafo

El contexto de grafo son **6 features causales** por transacción
(`origin_degree_before`, `destination_degree_before`,
`origin_unique_destinations_before`, `destination_unique_origins_before`,
`edge_count_before`, `edge_seen_before`). La vista no inventa señales: usa
cuentas y aristas observadas y esas features.

## Categorías

| Categoría | Significado |
|---|---|
| `ACCOUNT` | Cuenta que aparece como origen y destino |
| `ORIGIN` | Sólo como cuenta origen |
| `DESTINATION` | Sólo como cuenta destino |
| `EDGE` | Arista (origen→destino) |
| `HISTORY` | Nodo con grado > 1 (repetición) |
| `RISK` | Involucrado en transacción marcada por el protocolo |

## Vistas

- **Global** (`GET /api/v1/graph?limit=`): subgrafo de las últimas
  transacciones de la ventana en memoria.
- **Por transacción** (`GET /api/v1/transactions/{transaction_id}/graph`):
  - Si el id es de PaySim (`R{row_id}`) → subgrafo del **dataset completo**
    por cuenta (DuckDB, acotado por `LIMIT`), con las 6 features precalculadas.
  - Si es live (`L…`/`ui-…`) → decisión en memoria + vecindario reciente.
  - Devuelve la transacción, la decisión (primaria/final/Laya) y cada feature
    con una **descripción legible**.

```bash
curl -s 'localhost:8000/api/v1/transactions/R100000/graph?limit=150' | python3 -m json.tool
```

## Frontend

`frontend/src/graph.js` renderiza con **Cytoscape.js** (vendor UMD): layout
force-directed (`cose`), tamaño por grado, color por categoría/riesgo, grosor
de arista por conteo y panel lateral con descripciones. En `/grafo` hay un
buscador por **ID de transacción** y botón *Vista global*.
