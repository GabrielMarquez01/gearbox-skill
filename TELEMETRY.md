# Telemetría de Gearbox

> **Actualizado: 2026-07-26**
> Estado: implementado y probado en local. El colector productivo **no existe
> todavía** — ver [Lo que aún no existe](#lo-que-aún-no-existe).

Gearbox es software gratuito bajo licencia MIT. **Funciona completo sin enviar
nada.** La telemetría es un extra voluntario que sirve para una sola cosa:
mejorar las recomendaciones de routing con evidencia de muchas personas en vez
de la intuición de una.

## Las tres modalidades

| Modo | Qué hace | Coste | Red |
|---|---|---|---|
| **local** *(por defecto)* | Todo se queda en tu equipo. Aprendizaje sólo con tu historia. | Gratis | **Cero conexiones** |
| **community** | Aportas métricas agregadas y recibes priors de la comunidad. | Gratis | Sólo al enviar, y sólo con tu consentimiento |
| **self-hosted** | Igual que community pero contra **tu** colector. Nada llega a OpenGravity. | Gratis | Sólo hacia tu endpoint |

La licencia **no** está condicionada a enviar datos. El modo local es un
ciudadano de primera: no hay funciones capadas, banners ni recordatorios
insistentes.

## Qué se envía exactamente

Sólo esto, y sólo si consentiste:

```json
{
  "schema_version": "1.0",
  "client_version": "3.0",
  "capsule_id": "UUID aleatorio",
  "generated_period": "2026-W30",
  "contribution_mode": "community",
  "events": [
    {
      "task_type": "implementation",
      "predicted_gear": "G2",
      "model_family": "sonnet",
      "effort": "high",
      "risk_band": "low",
      "complexity_band": "medium",
      "ambiguity_band": "low",
      "routing_confidence_band": "0.7-0.8",
      "predicted_success_band": "0.8-0.9",
      "outcome": "accepted",
      "rework": false,
      "cost_band": "unknown",
      "latency_band": "unknown",
      "human_override": false,
      "feedback_reason": "none"
    }
  ],
  "aggregate": { "event_count": 1 }
}
```

Todo son **enums cerrados o rangos**. No hay un solo campo de texto libre. Las
cifras exactas se generalizan a bandas antes de salir para que un número no
funcione como cuasi-identificador.

## Lo que Gearbox nunca recopila

Ni en community ni en self-hosted, por diseño y verificado por pruebas:

prompts · respuestas · código · archivos · fragmentos de documentos ·
`prompt_hash` · task_id locales · session_id · project_id · `cwd` · nombre de
repositorio · rama · commit · nombres de archivo · rutas Unix o Windows · URLs ·
IP · correo · teléfono · hostname · usuario · tokens · llaves API · secretos ·
cookies · texto libre de cualquier tipo · stack traces · `matched_signals` ·
marcas de tiempo exactas · geografía.

El campo `feedback_reason` sólo admite nueve valores predefinidos. El motivo
`other_local_only` **nunca se transmite**: se degrada a `none` al construir la
cápsula.

### El contributor_id no va en el cuerpo

El seudónimo viaja en la cabecera `X-Gearbox-Contributor`, no dentro de la
cápsula. Así el cuerpo que el colector almacena no contiene ningún
identificador, ni siquiera seudónimo. Es una decisión de diseño documentada: la
lista de campos permitidos de la cápsula es cerrada y el `contributor_id` no
está en ella.

El `contributor_id` es un UUID aleatorio. No deriva de tu equipo, tu correo, tu
IP ni tus rutas. Puedes rotarlo cuando quieras (`telemetry rotate-id`) y se
regenera al revocar.

## Cómo verificarlo tú mismo

No hace falta creernos. Estos comandos son reproducibles:

```bash
# 1. Ver el texto exacto que saldría de tu equipo, antes de enviar nada
~/.claude/gearbox/gearbox.py telemetry preview

# 2. Guardarlo a disco y revisarlo con tus herramientas
~/.claude/gearbox/gearbox.py telemetry export --out /tmp/capsula.json
grep -iE 'prompt|path|home|token|@|http' /tmp/capsula.json    # no debe salir nada

# 3. Escanear cualquier JSON con el mismo escáner que usa el envío
~/.claude/gearbox/gearbox.py privacy scan /tmp/capsula.json

# 4. Comprobar el estado y la cola
~/.claude/gearbox/gearbox.py telemetry status

# 5. Comprobar que el modo local no abre conexiones
python3 -m unittest tests.test_compat_transport.LocalModeIsOfflineTests -v
```

La prueba `test_preview_matches_exactly_what_would_be_sent` comprueba que lo que
muestra `preview` es byte por byte lo que se comprime y encola. No es una
maqueta.

## El camino completo de un dato

```
tu tarea
  └─ clasificación local (sin red)
      └─ tú registras el resultado:  gearbox.py feedback last accepted
          └─ SQLite local
              └─ selección de elegibles (sólo con resultado registrado)
                  └─ eliminación de identificadores
                      └─ generalización a bandas
                          └─ ESCÁNER DE SECRETOS  ── si detecta algo → SE DETIENE
                              └─ validación contra allowlist ── campo desconocido → SE DETIENE
                                  └─ vista previa (la ves tú)
                                      └─ ¿consentimiento vigente? ── no → SE DETIENE
                                          └─ JSON canónico → gzip → SHA-256
                                              └─ cola transaccional en disco
                                                  └─ HTTPS con TLS validado
                                                      └─ confirmación del colector
                                                          └─ marcado como enviado
```

El hook `UserPromptSubmit` **nunca** entra en este camino: no toca la red ni la
cola. La telemetría se procesa al cerrar sesión o cuando tú lo pides.

## Comandos

```bash
gearbox.py telemetry status         # modo, consentimiento, cola, priors
gearbox.py telemetry explain        # qué se envía y qué no, en llano
gearbox.py telemetry enable community
gearbox.py telemetry enable self-hosted --endpoint https://mi-colector/v1/capsules
gearbox.py telemetry consent        # confirmar el consentimiento
gearbox.py telemetry preview        # ver el paquete exacto
gearbox.py telemetry export --out archivo.json
gearbox.py telemetry send           # construir, encolar y enviar
gearbox.py telemetry flush          # sólo enviar lo pendiente
gearbox.py telemetry disable        # detener envíos futuros
gearbox.py telemetry purge          # vaciar la cola local
gearbox.py telemetry revoke         # revocar: invalida, vacía la cola, rota el seudónimo
gearbox.py telemetry rotate-id      # nuevo seudónimo
```

### Diferencia entre `disable`, `purge` y `revoke`

| Comando | Detiene envíos | Borra la cola | Invalida el consentimiento | Rota el seudónimo |
|---|---|---|---|---|
| `disable` | ✅ | ❌ | ❌ | ❌ |
| `purge` | ❌ | ✅ | ❌ | ❌ |
| `revoke` | ✅ | ✅ | ✅ | ✅ |

`revoke` además deja un **comprobante local** en `consent-receipts.jsonl` con el
`contributor_id` anterior, para que puedas pedirle al colector que borre lo ya
recibido (`POST /v1/deletion-requests`).

## Instalación desatendida

El instalador **no** activa telemetría. Para activarla sin interacción hacen
falta **las dos** variables — declarar el modo no equivale a consentir:

```bash
GEARBOX_TELEMETRY_MODE=community GEARBOX_TELEMETRY_CONSENT=yes bash install.sh
```

Con una sola, la instalación se queda en local. Hay pruebas para ambos casos.

## Configuración

| Variable | Para qué |
|---|---|
| `GEARBOX_TELEMETRY_ENDPOINT` | URL HTTPS del colector |
| `GEARBOX_TELEMETRY_TOKEN` | Token de ingesta. Se lee del entorno y **nunca** se escribe en logs ni en disco |
| `GEARBOX_TELEMETRY_DEV=1` | Permite `http://localhost` para desarrollo. Sin esto, sólo HTTPS |
| `GEARBOX_PRIORS_URL` | Documento de priors comunitarios |
| `GEARBOX_PRIORS_HMAC_KEY` | Clave para verificar la firma de los priors |

## Transporte

HTTPS obligatorio con validación TLS completa; un certificado inválido aborta el
envío. `http://` sólo se acepta contra `localhost` y sólo con
`GEARBOX_TELEMETRY_DEV=1`. Cuerpo gzip, tope de 512 KiB, timeout de 10 s,
`Idempotency-Key` = `capsule_id`, SHA-256 del cuerpo en cabecera, User-Agent sin
información del dispositivo, y códigos de error estructurados.

Reintentos con backoff exponencial y jitter determinista, máximo 6 intentos,
retención de cola de 14 días y purga automática de lo expirado.

## Lo que aún no existe

Honestidad por delante:

- **No hay colector productivo.** No hay dominio, ni endpoint público, ni
  certificado, ni token de ingesta. Lo que existe es una **implementación de
  referencia** (`collector/`) para leer, probar y auto-alojar.
- **No hay firma asimétrica de priors.** Se soporta HMAC-SHA256 con clave
  compartida; la firma de producción requiere infraestructura de llaves que aún
  no existe. No se simula.
- **No hay privacidad diferencial.** Se documenta como trabajo futuro en
  [COMMUNITY-LEARNING.md](COMMUNITY-LEARNING.md). Fingirla sería peor que no
  tenerla.
- **No hay revisión legal.** Los documentos de `docs/legal/` son borradores que
  requieren abogado según jurisdicción y operación reales.

Mientras eso no exista, `community` no tiene a dónde enviar: en la práctica hoy
las opciones reales son **local** y **self-hosted**.
