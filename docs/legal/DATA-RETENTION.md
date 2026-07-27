# Política de retención

> ⚠️ **BORRADOR — REQUIERE REVISIÓN LEGAL.** Plantilla técnica redactada por el
> equipo del proyecto, no por abogados. Debe adaptarse y validarse con asesoría
> jurídica según jurisdicción, operación y datos reales antes de publicarse o
> firmarse. Los campos entre `[CORCHETES]` deben completarse.
>
> **Actualizado: 2026-07-26**

## Cliente

| Dato | Retención | Control |
|---|---|---|
| Predicciones y resultados (`gearbox.db`) | mientras el usuario quiera | `uninstall.sh --purge-data` |
| Cola de salida | 14 días; purga automática | `telemetry purge` |
| Comprobantes de consentimiento | indefinida (evidencia del propio usuario) | borrado manual |
| Sal local | mientras exista la instalación | se elimina con `--purge-data` |

## Colector

| Dato | Retención por defecto | Tope duro |
|---|---|---|
| Cápsulas crudas | **7 días** o hasta agregarse (lo que ocurra antes) | **30 días** |
| Agregados | mientras opere el servicio | — |
| Constancias de borrado | mientras opere el servicio | — |
| Métricas operativas (sin PII) | mientras opere el servicio | — |

`GEARBOX_COLLECTOR_RETENTION_DAYS` acepta valores **más cortos**; uno más largo
se recorta a 30 automáticamente. La purga se ejecuta en cada consulta a
`/health`; en producción debe además programarse.

Regla operativa: **la cruda se borra al agregarse**, sin esperar a que expire.
El plazo es el techo, no el objetivo.
