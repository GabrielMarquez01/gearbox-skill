# Gobierno de datos

> **Actualizado: 2026-07-26**

## Inventario de datos

### En el equipo del usuario (`~/.claude/gearbox/`)

| Archivo | Contiene | Permisos | Se transmite |
|---|---|---|---|
| `gearbox.db` | predicciones, clasificación, resultados, seudónimos locales | 0600 | agregado a bandas |
| `telemetry.db` | cola de salida (metadatos) | 0600 | no |
| `outbox/*.json.gz` | cápsulas pendientes ya minimizadas | 0600 | sí, esas cápsulas |
| `consent.json` | estado del consentimiento y `contributor_id` | 0600 | sólo el id, en cabecera |
| `consent-receipts.jsonl` | comprobantes de otorgar/revocar/rotar | 0600 | no |
| `.local_salt` | sal para seudónimos locales | 0600 | **nunca** |
| `state.json`, `events.jsonl`, `decisions.jsonl` | marcha activa y bitácora V2 | 0600 | no |
| `last_prediction.json` | última predicción (incluye `matched_signals`) | 0600 | no |
| `community-priors.json` | agregados recibidos | 0644 | entrante |
| `policy.json`, `prices.json` | configuración del usuario | 0644 | no |

### En el colector

| Tabla | Contiene | Retención |
|---|---|---|
| `raw_capsules` | cápsula recibida + seudónimo | **borrada al agregar**; tope 30 días |
| `aggregates` | contadores por ruta + set de seudónimos | mientras opere el servicio |
| `deletion_requests` | constancia de solicitudes de borrado | mientras opere el servicio |
| `metrics` | contadores operativos sin PII | mientras opere el servicio |

## Ciclo de vida

```
recolección → minimización → consentimiento → transmisión →
agregación → borrado de la cruda → publicación agregada
```

Cada flecha tiene un control que puede detener el flujo, y el usuario puede
cortarlo en cualquier punto (`disable`, `purge`, `revoke`).

## Bases de tratamiento

| Tratamiento | Base propuesta | Nota |
|---|---|---|
| Procesamiento local | ninguna transmisión; datos bajo control exclusivo del usuario | fuera del alcance del colector |
| Telemetría community | **consentimiento explícito**, revocable | nunca interés legítimo: sería incoherente con "voluntario" |
| Telemetría self-hosted | decisión del propio operador | el operador define su base |

La calificación jurídica final corresponde a quien opere el colector, con
asesoría legal.

## Derechos de los titulares

| Derecho | Cómo se ejerce hoy |
|---|---|
| Acceso | `telemetry preview` y `telemetry export` muestran exactamente lo aportado |
| Rectificación | los agregados no son rectificables por diseño; se puede solicitar borrado y volver a aportar |
| Cancelación / eliminación | `telemetry revoke` local + `POST /v1/deletion-requests` con el `contributor_id` del comprobante |
| Oposición | `telemetry disable` detiene envíos de inmediato |
| Portabilidad | `telemetry export` produce JSON legible |

Procedimiento completo en
[docs/legal/DSAR-ARCO-PROCEDURE.md](docs/legal/DSAR-ARCO-PROCEDURE.md).

### Límite reconocido sobre el borrado

El borrado elimina las **cápsulas crudas** de ese contribuyente. Los
**agregados** no se recalculan, porque no conservan el vínculo
evento→contribuyente: una vez agregada, la aportación ya no es atribuible a una
persona. Esta decisión está documentada aquí a propósito para que un abogado
pueda evaluarla en su jurisdicción, no escondida en el código.

## Quién puede ver qué

- Los **desarrolladores del proyecto no tienen acceso automático** a ninguna
  telemetría. Mantener el software y operar un servicio son papeles distintos.
- El **operador del colector** ve cápsulas crudas durante su breve retención y
  los seudónimos en cabecera.
- La **comunidad** ve únicamente el documento agregado publicado.
