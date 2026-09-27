# AGANT — Replay

El replay procesa PaySim respetando su semántica temporal y marcando todo
con `source="replay"`. Nunca se confunde con tráfico live y no contamina
las métricas LIVE.

## Modos

- **sin Laya**: ruta `Rules + ML + graph`.
- **con Laya**: `with_laya` se propaga hasta el motor; toda transacción
  elegible en banda `SUSPICIOUS` se intenta. No hay límite artificial de
  llamadas.

El replay usa un **estado de grafo propio**, de modo que no altera el
estado online. Las decisiones se ejecutan en orden de `row_id`/`step`
(micro-batching de 5000 para reducir cambios de hilo sin romper causalidad).

## API

```bash
# iniciar (requiere X-Admin-Token si AGANT_ADMIN_TOKEN está definido)
curl -X POST localhost:8000/api/v1/replay/start \
  -H "X-Admin-Token: $AGANT_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"with_laya": false, "max_records": 5000}'

curl localhost:8000/api/v1/replay/status
curl -X POST localhost:8000/api/v1/replay/stop -H "X-Admin-Token: $AGANT_ADMIN_TOKEN"
```

`status`: `idle | running | finished | stopped`, con `processed`, `total`,
`with_laya`, `laya_active`, `elapsed_s`, `throughput_tps`.

## Sin servidor

```bash
.venv/bin/python scripts/replay.py --max-records 3000
.venv/bin/python scripts/replay.py --with-laya --max-records 2000
```

## Semántica en el dashboard

Los eventos de replay llevan badge **REPLAY** y métricas separadas
(`snapshots.replay`). El frontend no inventa tiempo real: la animación
refleja el flujo real de eventos (sin `sleep` artificial).

> Nota: un replay completo de 6.36M transacciones por la ruta online puede
> tardar horas a ~560 items/s. Para evaluación masiva usar el pipeline de
> memoria (inferencia vectorizada por lote), no el replay online.
