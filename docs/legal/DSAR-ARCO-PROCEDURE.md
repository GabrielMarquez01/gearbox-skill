# Procedimiento de derechos (ARCO / DSAR)

> ⚠️ **BORRADOR — REQUIERE REVISIÓN LEGAL.** Plantilla técnica redactada por el
> equipo del proyecto, no por abogados. Debe adaptarse y validarse con asesoría
> jurídica según jurisdicción, operación y datos reales antes de publicarse o
> firmarse. Los campos entre `[CORCHETES]` deben completarse.
>
> **Actualizado: 2026-07-26**

## Identificación
La única referencia es el **`contributor_id`**, un UUID aleatorio. El operador
no puede vincularlo a una persona por sí solo: quien ejerce el derecho debe
aportarlo desde su comprobante local.

```bash
cat ~/.claude/gearbox/consent-receipts.jsonl
```

**Consecuencia honesta:** si la persona rotó su seudónimo o perdió el
comprobante, no hay forma de localizar sus aportaciones. Es el precio de no
guardar identidad — y debe explicarse en el aviso, no descubrirse al reclamar.

## Flujo

| Derecho | Acción del operador | Plazo |
|---|---|---|
| **Acceso** | El usuario ya lo tiene: `telemetry export`. El operador entrega las crudas vivas de ese `contributor_id` | [PLAZO LEGAL] |
| **Rectificación** | No aplicable a agregados. Se ofrece borrado y nueva aportación | [PLAZO] |
| **Cancelación / eliminación** | `POST /v1/deletion-requests` → borra crudas y deja constancia | [PLAZO] |
| **Oposición** | `telemetry disable` surte efecto inmediato en el cliente | inmediato |
| **Portabilidad** | `telemetry export` produce JSON legible | inmediato |

## Solicitud de eliminación

```bash
curl -X POST https://[COLECTOR]/v1/deletion-requests \
  -H 'Content-Type: application/json' \
  -d '{"contributor_id":"[UUID DEL COMPROBANTE]"}'
```

Respuesta: `request_id`, número de cápsulas crudas eliminadas y estado.

## Límite que debe comunicarse

El borrado elimina las **cápsulas crudas**. Los **agregados no se recalculan**,
porque no conservan el vínculo evento→contribuyente: tras agregarse, la
aportación deja de ser atribuible a una persona identificable.

Esta postura debe ser **validada por un abogado en cada jurisdicción**. Está
escrita aquí, a la vista, precisamente para que pueda discutirse.

## Registro
Toda solicitud queda en `deletion_requests` con fecha, seudónimo y conteo.
