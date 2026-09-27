# AGANT — Avisos de terceros

AGANT usa las siguientes dependencias y recursos de terceros. Cada uno
conserva su licencia original; ninguno se relicencia bajo AGPL-3.0.

## Dependencias de ejecución

| Componente | Versión | Licencia | Uso |
|---|---|---|---|
| PyTorch | 2.14.0 | BSD-3-Clause | Tensores / GPU |
| Transformers | 5.17.0 | Apache-2.0 | Encoder de Laya |
| safetensors | 0.8.0 | Apache-2.0 | Pesos |
| huggingface_hub | 1.33.0 | Apache-2.0 | Descarga de checkpoints |
| Laya (`laya`) | 0.3.20 | Apache-2.0 | Motor de decisión (2ª opinión) |
| TileLang | 0.1.14 | MIT | Fast path GPU de Laya |
| NumPy | 2.5.3 | BSD-3-Clause | Álgebra numérica |
| pandas | 3.0.6 | BSD-3-Clause | Procesamiento tabular |
| DuckDB | 1.5.5 | MIT | Consultas analíticas |
| scikit-learn | 1.9.1 | BSD-3-Clause | Random Forest / métricas |
| joblib | 1.6.0 | BSD-3-Clause | Serialización de modelos |
| FastAPI | 0.141.1 | MIT | API HTTP/WS |
| Starlette | 1.7.0 | BSD-3-Clause | Base ASGI |
| Uvicorn | 0.54.0 | BSD-3-Clause | Servidor ASGI |
| Pydantic | 2.13.5 | MIT | Contratos / validación |
| websockets | 17.1 | BSD-3-Clause | WebSocket |
| psutil | 7.2.2 | BSD-3-Clause | Métricas de sistema |
| Lucide | (vendor) | ISC | Iconografía del frontend |
| Cytoscape.js | (vendor) | MIT | Visualización de grafo |
| SheetJS (xlsx) | (vendor) | Apache-2.0 | Exportación XLSX |

## Checkpoints de modelos

- `convaiinnovations/laya` (subcarpetas `multilingual`, `typed-decisions`),
  revisión `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`.
- Licencia: Apache-2.0.
- Se descargan externamente a la caché de Hugging Face; **no** se
  redistribuyen en este repositorio.

## Datasets

- **PaySim** — Synthetic Financial Datasets for Fraud Detection
  (Lopez-Rojas et al.). 6,362,620 transacciones. Licencia: **UNKNOWN /
  NEEDS VERIFICATION**; no se redistribuye (`data/raw/` fuera de git).
  Fuente de descarga reproducible: espejo público en Hugging Face.
