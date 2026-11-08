# Guardián de sesión — complemento opcional

Actualizado: 2026-11-08 09:27 (America/Mexico_City).

> **No se instala con el Gearbox y no está activo por defecto.** Es un extra para quien
> trabaja con sesiones largas o deja tareas corriendo mientras no está frente a la PC.

> **Vigencia del cupo:** solo actúa con lecturas de hasta 300 segundos, no futuras,
> y renovación futura de cada ventana. Sin ellas espera; no deduce cupo disponible del reloj.
> El aviso de recuperación exige un porcentaje <50 en una lectura posterior de la misma sesión.

Funciones:

| Problema | Qué hace el guardián |
|---|---|
| **La sesión se cae** — se cierra la terminal, se va el internet, truena algo | La reabre con su contexto intacto **en cuanto vuelve la conexión** |
| **Se agota el cupo de la ventana de uso** | Anota dónde quedó y, cuando la ventana se renueva, **te avisa para que tú decidas** si continuar |

---

## Por qué NO reanuda solo

Es la pregunta obvia: *si ya sabe cuándo se renueva el cupo, ¿por qué no sigue trabajando solo?*

Se decidió deliberadamente que no, por dos razones:

1. **Para no atorarse en las confirmaciones tendría que saltarse los permisos.** Un agente
   continuando sin supervisión, con permisos abiertos, sobre código real, es exactamente el
   escenario que cualquier política sensata evita.
2. **Puede quemarte el cupo nuevo en algo que ya no quieres.** Despiertas y la ventana entera
   se fue en una tarea que ibas a replantear.

El aviso te llega donde estés; el "play" lo das tú y toma un segundo. Ganas lo mismo —no tener
que estar pendiente— sin ceder el control.

---

## Requisitos

- `bash`, `python3` (biblioteca estándar), `curl`, `cron`
- Para vigilar **cupo**, el statusline incluido escribe `~/.claude/gearbox/usage.json`.
  Las ventanas ausentes o vencidas se omiten. Sin lectura vigente solo vigila caídas.
  Con sesión registrada, descarta lecturas de otras sesiones. El archivo es un único snapshot:
  sesiones simultáneas pueden reemplazarlo; si falta la sesión registrada, espera nuevos datos.
- Para **reabrir ventanas**: WSL + Windows Terminal. En Linux/macOS el guardián detecta y avisa,
  pero no abre la ventana solo — te manda el comando listo para pegar

---

## Instalación

```bash
mkdir -p ~/.claude/guardian
cp guardian/guardian.sh ~/.claude/guardian/
chmod +x ~/.claude/guardian/guardian.sh
cp guardian/guardian.conf.ejemplo ~/.claude/guardian/guardian.conf
```

Edita `~/.claude/guardian/guardian.conf` para elegir **cómo quieres que te avise** (ver abajo),
registra la sesión y activa el ciclo:

```bash
~/.claude/guardian/guardian.sh registrar "ID_DE_TU_SESION"  # reemplaza el ID; sin él lee usage.json
( crontab -l 2>/dev/null; echo "*/3 * * * * $HOME/.claude/guardian/guardian.sh check >/dev/null 2>&1" ) | crontab -
~/.claude/guardian/guardian.sh estado             # verifica que quedó bien
```

---

## Elegir el canal de aviso

En `guardian.conf`, `CANAL_AVISO` acepta tres valores:

| Valor | Qué hace | Cuándo conviene |
|---|---|---|
| `escritorio` *(por defecto)* | Notificación en la propia PC | Trabajas frente a la máquina |
| `telegram` | Mensaje a tu chat | **Estás lejos de la PC** — el caso que motivó esto |
| `comando` | Ejecuta un programa tuyo con el mensaje como argumento | Webhook, correo, tu propio bot |

Para Telegram necesitas un bot propio (se crea gratis hablando con `@BotFather`) y tu `chat_id`.

> ⚠️ **Sobre guardar el token:** si usas `telegram`, el token queda en `guardian.conf` en tu
> disco. Déjalo con permisos `600` (sólo tu usuario). Si prefieres no tener credenciales en la
> máquina, usa `comando` y delega el envío a un servicio que ya tengas autenticado.

---

## Uso diario

```bash
guardian.sh cupo        # cuánto llevas y a qué hora se renueva
guardian.sh continuar   # retomar la tarea que quedó pausada
guardian.sh estado      # diagnóstico completo
guardian.sh off / on    # pausar o reanudar la vigilancia
```

---

## Lo que NO puede hacer

Se dice de frente para que nadie se lleve una sorpresa:

- **Si la PC está apagada o suspendida, nada la enciende.** Tu máquina está detrás de tu router,
  sin dirección pública — eso es tu seguridad, no un defecto. El guardián cubre caídas de sesión
  y de internet, no cortes de energía.
- **No reconecta el enlace con el celular por sí solo.** Ese comando sólo existe dentro de la
  sesión interactiva.
- **No adivina si la tarea que quedó a medias sigue teniendo sentido.** Por eso pregunta.

---

## Cómo sabe cuánto cupo queda

Claude Code entrega al statusline, en cada refresco, un bloque `rate_limits` con el porcentaje
usado y la **hora exacta de renovación** de cada ventana, según la consulta del 2026-10-30.
El guardián lee una vez por ejecución `~/.claude/gearbox/usage.json` (o `GUARDIAN_USAGE`).
El statusline guarda `updated_at`, `session_id`, porcentajes y `reset_five_hour` /
`reset_seven_day`; escribe atómicamente con permisos 600. La falta de límites en el
siguiente payload reemplaza el snapshot anterior sin conservar porcentajes.
El margen de 300 segundos es una decisión de este parche para el ciclo cron de tres minutos,
no un límite del proveedor. No se envía aviso de renovación sin una nueva lectura <50%.
Si no llegan datos nuevos tras el reset, comprueba `/usage`. Una pausa heredada sin `LECTURA`
no se renueva automáticamente: requiere revisión manual. La pausa resuelta se archiva como
`estado/pausa_cupo.anterior`.

Es una lectura local y barata: **no consulta la red ni gasta cupo para saber cuánto cupo queda.**
