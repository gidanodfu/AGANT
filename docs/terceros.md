# AGANT — Terceros

Detalle completo en `THIRD_PARTY_NOTICES.md`. Resumen:

## Código propio

- Licencia: **AGPL-3.0-or-later**. Encabezado humano canónico en cada
  archivo (no se usa un identificador SPDX como sustituto del aviso).
- `LICENSE` (texto oficial), `NOTICE` (aviso del proyecto).

## Dependencias principales

| Componente | Licencia |
|---|---|
| PyTorch | BSD-3-Clause |
| Transformers / safetensors / huggingface_hub | Apache-2.0 |
| Laya (`laya`) | Apache-2.0 |
| TileLang | MIT |
| NumPy / pandas / scikit-learn / joblib | BSD-3-Clause |
| DuckDB | MIT |
| FastAPI | MIT |
| Starlette / Uvicorn / websockets | BSD-3-Clause |
| Pydantic | MIT |
| psutil | BSD-3-Clause |
| Lucide | ISC |

## Modelos y datasets

- Checkpoints `convaiinnovations/laya` (`multilingual`, `typed-decisions`),
  Apache-2.0. Se descargan externamente; **no** se redistribuyen.
- PaySim: licencia **UNKNOWN / NEEDS VERIFICATION**; no se redistribuye.
  Si se identifica el origen exacto, actualizar este documento y
  `docs/datasets.md` con fuente, licencia y checksum.

## Reglas

- No aplicar AGPL-3.0 a pesos ni a código de Laya.
- No colocar el aviso AGPL de AGANT en código de terceros.
