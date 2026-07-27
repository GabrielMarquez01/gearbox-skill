# Colector de referencia

> **Actualizado: 2026-07-26**
> ⚠️ **NO es un servicio productivo.** Es la implementación de referencia del
> contrato: existe para leerse, probarse y auto-alojarse. Lee
> [Antes de exponerlo a internet](#antes-de-exponerlo-a-internet).

Python estándar, sin dependencias. No requiere desplegarse para que el cliente
funcione: el modo `local` es completo por sí solo.

## Correr

```bash
python3 collector/app.py --host 127.0.0.1 --port 8787 --db collector.db
```

Apuntar un cliente contra él, en desarrollo:

```bash
export GEARBOX_TELEMETRY_DEV=1          # permite http contra localhost
export GEARBOX_TELEMETRY_ENDPOINT=http://127.0.0.1:8787/v1/capsules
gearbox.py telemetry enable self-hosted --endpoint $GEARBOX_TELEMETRY_ENDPOINT
gearbox.py telemetry preview            # revisa antes
gearbox.py telemetry send
```

Sin `GEARBOX_TELEMETRY_DEV=1`, el cliente **rechaza** cualquier destino que no
sea HTTPS.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `POST` | `/v1/capsules` | ingesta. gzip obligatorio, idempotente por `capsule_id` |
| `GET` | `/health` | estado, retención, umbrales, celdas publicadas/suprimidas, métricas sin PII |
| `GET` | `/v1/schema` | contrato publicado |
| `GET` | `/v1/community-priors/latest` | agrega lo pendiente y devuelve el documento agregado |
| `POST` | `/v1/deletion-requests` | borra crudas de un `contributor_id` y deja constancia |

## Arquitectura

```
app.py           enrutador puro: (método, ruta, cabeceras, cuerpo) → (status, cabeceras, cuerpo)
security.py      gzip acotado, auth, rate limit, anti-replay, redacción de logs
schema/          validación INDEPENDIENTE del cliente + JSON Schema publicado
storage.py       crudas efímeras + agregados + constancias + métricas
aggregation.py   agregación, umbrales de cohorte, construcción de priors
```

`Collector.handle` es una función pura: por eso las pruebas cubren zip bombs,
replay, rate limit y campos prohibidos **sin abrir un socket**.

### Por qué el schema del servidor no importa el del cliente

Un colector no debe confiar en la definición que trae quien envía. Si cliente y
servidor divergen, manda el servidor y el cliente recibe un rechazo
estructurado. Por eso `collector/schema/` no importa `gearboxlib`.

## Controles

Límite de cuerpo 512 KiB · descompresión acotada a 4 MiB con detección de ratio
· validación estricta de enums · rechazo de campos no permitidos y de cadenas
largas (texto libre) · idempotencia · anti-replay temporal · rate limit por
contribuyente · autenticación por token opcional con comparación en tiempo
constante · logs sin payload · SQL parametrizado · errores estructurados que
nunca devuelven el token.

## Retención

Crudas: **7 días** por defecto, tope duro **30**, y se borran **al agregarse**
sin esperar. Los agregados no permiten reconstruir una cápsula individual. Una
cápsula individual **nunca** se publica.

```bash
GEARBOX_COLLECTOR_RETENTION_DAYS=1 python3 collector/app.py
```

Un valor más largo que 30 se recorta automáticamente.

## Umbrales de publicación

Una celda se publica sólo si tiene **≥ 20 eventos** y **≥ 5 contribuyentes
distintos**. `/health` reporta cuántas celdas se suprimieron, para que la
supresión sea visible y no silenciosa.

## Configuración

| Variable | Efecto |
|---|---|
| `GEARBOX_COLLECTOR_TOKEN` | exige `Authorization: Bearer`. **Sin esto el colector es abierto** |
| `GEARBOX_COLLECTOR_RETENTION_DAYS` | retención de crudas (tope 30) |
| `GEARBOX_PRIORS_HMAC_KEY` | firma HMAC-SHA256 de los priors publicados |

## Pruebas

```bash
python3 -m unittest tests.test_collector -v
```

## Antes de exponerlo a internet

Esta referencia **no está lista para producción**. Falta, como mínimo:

- **TLS terminado por un proxy real** (aquí no hay HTTPS propio).
- **Rate limiting distribuido**: el de referencia es en memoria y se pierde al
  reiniciar; no sirve con varias réplicas.
- **Autenticación de contribuyentes**. Sin ella, el envenenamiento de priors es
  el riesgo abierto más serio (ver `THREAT-MODEL.md` §3.3).
- **Backups, rotación de logs y monitoreo.**
- **Base de datos apropiada**: SQLite con `isolation_level=None` sirve para la
  referencia, no para concurrencia real.
- **Aviso de privacidad y DPA publicados** — plantillas en `docs/legal/`,
  todas **pendientes de revisión legal**.
- **Auditoría de seguridad externa.**

Quien opere un colector es **responsable/controlador** de ese servicio, con las
obligaciones jurídicas que eso implica. Mantener este software abierto y operar
un servicio de telemetría son papeles distintos.
