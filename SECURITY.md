# Seguridad

> **Actualizado: 2026-07-26**

## Reportar una vulnerabilidad

Abre un issue **sin incluir secretos, datos personales ni exploits completos**,
describiendo impacto y reproducción mínima. Si el hallazgo expone datos de
terceros, sigue [INCIDENT-RESPONSE.md](INCIDENT-RESPONSE.md) antes de publicar.

No hay programa de recompensas ni SLA de respuesta: es un proyecto pequeño y
decirlo por adelantado es más útil que prometer lo que no se puede cumplir.

## Controles implementados

### Cliente

| Control | Dónde |
|---|---|
| Permisos `0600` en archivos sensibles, `0700` en directorios | `gearboxlib/paths.py` |
| Escrituras atómicas (`tmp` + `os.replace` + `fsync`) | `gearboxlib/paths.py` |
| Consultas SQLite **parametrizadas** en todo el código | `gearbox.py`, `gearboxlib/*`, `collector/*` |
| Sin `shell=True`; `subprocess` con lista de argumentos | `audit/providers/base.py` |
| Prompt por **stdin**, nunca por `argv` (no aparece en `ps`) | `audit/providers/base.py` |
| Timeouts y salida acotada en todo subproceso | `audit/providers/base.py` |
| Entorno filtrado hacia CLIs de terceros (sin `TOKEN`/`KEY`) | `audit/providers/base.py` |
| Redacción de tokens en logs y mensajes de error | `gearboxlib/transport.py` |
| Allowlist estricta de campos + enums | `gearboxlib/privacy.py` |
| Sin deserialización insegura (`json` únicamente, nunca `pickle`/`eval`) | todo el proyecto |
| Sin descarga ni ejecución de código recibido | todo el proyecto |
| TLS validado; HTTP sólo contra localhost en modo desarrollo | `gearboxlib/transport.py` |
| Cero dependencias externas (sólo biblioteca estándar) | todo el proyecto |

### Colector de referencia

| Control | Dónde |
|---|---|
| Límite de cuerpo (512 KiB) | `collector/security.py` |
| Descompresión acotada + detección de ratio (anti zip-bomb) | `collector/security.py` |
| Validación de schema **independiente del cliente** | `collector/schema/` |
| Rechazo de campos no permitidos y de texto libre | `collector/schema/` |
| Idempotencia por `capsule_id` | `collector/app.py` |
| Anti-replay temporal (periodo demasiado viejo o futuro) | `collector/security.py` |
| Rate limiting por contribuyente | `collector/security.py` |
| Autenticación configurable con comparación en tiempo constante | `collector/security.py` |
| Logs sin payload y sin PII | `collector/app.py` |
| Separación ingestión / agregación / publicación | `collector/{app,aggregation}.py` |
| Borrado de crudas tras agregar; retención tope 30 días | `collector/storage.py` |

## Manejo de secretos

- Los tokens se leen **del entorno**, nunca del repositorio ni de la base local.
- `GEARBOX_TELEMETRY_TOKEN` no se escribe en logs, ni en errores, ni en disco.
  `transport._redact()` es la última barrera si algo se cuela en un mensaje.
- El escáner de privacidad bloquea el envío si detecta cualquier credencial.
- No hay credenciales en el repositorio. Los secretos de las pruebas son
  ficticios y están marcados como tales en `tests/support.py`.

## CI

`.github/workflows/test.yml` corre con `permissions: contents: read`, matriz de
Ubuntu y macOS con Python 3.9, 3.11 y 3.12, y fija las actions a versiones
mayores publicadas. Ejecuta la suite completa, valida sintaxis shell y corre un
chequeo de compilación de todos los módulos.

## Lo que NO está resuelto

Honestidad por delante — el detalle está en [THREAT-MODEL.md](THREAT-MODEL.md):

- **Sin firma asimétrica** de priors ni de releases. Hoy sólo HMAC opcional.
- **Sin fijación por SHA** de las GitHub Actions (se usan versiones mayores).
- **Sin análisis estático ni escaneo de dependencias automatizados** en CI (el
  proyecto no tiene dependencias externas, lo que reduce pero no elimina el
  riesgo de cadena de suministro).
- **Sin autenticación fuerte de contribuyentes**: un actor decidido con muchos
  seudónimos podría intentar sesgar los priors.
- **Sin auditoría de seguridad externa.**
