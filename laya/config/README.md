# Laya — configuración

El servicio GPU opcional se controla por variables de entorno:

| Variable | Default | Uso |
|---|---|---|
| `LAYA_MODEL_ID` | `convaiinnovations/laya` | checkpoint de Hugging Face |
| `LAYA_SUBFOLDER` | `typed-decisions` | subcarpeta del checkpoint |
| `LAYA_DEVICE` | `cuda` | `cuda` o `cpu` |
| `LAYA_FAST` | `1` | fast path TileLang |
| `HF_HOME` | `/cache/huggingface` | caché de pesos |

El backend se conecta con `AGANT_LAYA_URL=http://laya:8001`. Si no se
define, AGANT usa Laya in-process (por defecto) o lo deshabilita.
Los checkpoints son Apache-2.0 y no se redistribuyen en el repositorio.
