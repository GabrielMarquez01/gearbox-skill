---
name: gearbox
description: >-
  Selector automático de modelo y esfuerzo por tarea. Se aplica en TODA sesión:
  clasifica cada tarea del usuario en una marcha (G0-G5), recomienda el modelo y
  esfuerzo óptimos con el comando exacto y el ahorro estimado, delega subtareas
  rutinarias a Haiku, registra cada decisión en bitácora para calibración, y
  vigila mensualmente si hay modelos nuevos. Triggers: inicio de cualquier tarea,
  gearbox, qué marcha, cambiar modelo, subir marcha, bajar marcha, esfuerzo,
  qué modelo conviene, calibrar gearbox, model watch.
---

# Gearbox — Selector Automático de Modelo y Esfuerzo

> **Regla de oro:** usar la marcha más baja que entregue resultado confiable,
> y subir solo cuando el riesgo, dinero o complejidad lo justifique.
> Evolución del Gearbox Protocol de OpenGravity, enfocada en routing de modelos Claude.

---

## Tabla de Marchas

| Marcha | Tipo de tarea | Modelo · Esfuerzo | Cómo se activa | Economía |
|---|---|---|---|---|
| **G0 Rutina** | búsquedas, lecturas masivas, renombres, formateo, logs | Haiku · low | AUTOMÁTICO — delegar a subagente con `model: haiku` | −67% vs Sonnet |
| **G1 Contenido** | copy, redacción, variantes, assets, SEO | Sonnet · medium | recomendar `/effort medium` | −30-50% tokens de razonamiento |
| **G2 Ejecución** (default) | features con contrato claro, UI, DB, fixes, deploys | Sonnet · high | default de sesión | base $3/$15 por M tokens |
| **G3 Planeación híbrida** | PRPs, features grandes multi-fase | opusplan | recomendar `/model opusplan` (Opus planea → Sonnet ejecuta, cambio automático) | Opus solo al planear |
| **G3.5 Turno profundo** | UNA pregunta difícil aislada | ultrathink | escribir `ultrathink` en el prompt (sin cambiar nada) | $0 de cambio |
| **G4 Crítico** | seguridad/PII, producción caída, debugging multi-sistema | Opus · high | recomendar `/model opus` | ≈1.7× Sonnet estándar (2.5× con intro), se paga si evita retrabajo |
| **G5 Arquitectura** | blueprint de ecosistema, infraestructura, decisiones multi-repo, 1M contexto | Fable (sesión dedicada) | recomendar `/model fable` o `claude --model fable` + GATE de costo | 2x Opus ($10/$50) — siempre con aprobación humana |

Precios de referencia (2026-07): Haiku 4.5 $1/$5 · Sonnet estándar $3/$15 (Sonnet 5 tiene intro $2/$10 hasta 2026-08-31 donde aplique) · Opus 4.8 $5/$25 · Fable 5 $10/$50 (por M tokens in/out).
Usar siempre **alias** (`haiku`, `sonnet`, `opus`, `fable`), nunca versiones fijas — los alias heredan versiones nuevas automáticamente.

---

## Protocolo del Recomendador (cada tarea del usuario)

```
1. LEER     → clasificar el input contra la tabla (costo ≈ $0, es parte de leer el prompt)
2. COMPARAR → ¿marcha recomendada ≠ configuración actual de la sesión?
   ├─ NO → ejecutar directo, sin ruido
   └─ SÍ → 3. PAUSA: emitir bloque de recomendación ANTES de empezar el trabajo
3. REGISTRAR la decisión en la bitácora — siempre, haya o no cambio de marcha, con el
   comando literal (ver "Bitácora de calibración" abajo):
   ~/.claude/gearbox/log.sh decision <gear_actual> <gear_recomendada> "<task>" [skill] [doc]
```

### Formato del bloque de recomendación (obligatorio, literal)

```
⚙ GEARBOX → conviene subir a Opus / Alto
   Comando:  /model opus
   Razón:    debugging multi-sistema en producción
   Economía: ≈1.7× Sonnet estándar pero evita retrabajo; cambiar AHORA (el caché se reinicia al cambiar)
```

Reglas del bloque:
- **Razón**: UNA frase concreta ("planeación estratégica y arquitectura", "copy sin razonamiento profundo")
- **Economía**: ahorro o costo estimado en % o $ siempre que sea calculable
- Si la recomendación es NO cambiar pero el usuario preguntó, decirlo explícito: "mantener Sonnet/high — la planeación difícil ya pasó"
- Recomendar cambios **al inicio de una tarea**, nunca a la mitad (cambiar modelo reinicia el caché de prompt: la siguiente respuesta relee todo el historial sin el descuento del 90%)

### Qué es automático vs qué requiere al humano

| Acción | Quién |
|---|---|
| Delegar subtareas G0 a Haiku (`Agent` con `model: haiku`) | Claude, automático |
| opusplan: Opus al planear → Sonnet al ejecutar | Harness, automático (si `/model opusplan` activo) |
| Cambiar el modelo principal de la sesión | Humano — Claude da el comando exacto |
| Sesión Fable (G5) | Humano — SIEMPRE gate de costo explícito |

---

## Regla G5 — Fable 5 sin humo

Fable 5 es para decisiones grandes, ambiguas o de largo contexto. No recomendarlo por prestigio del tema, sino por la forma de la tarea.

Recomendar G5 cuando la tarea pida:
- Blueprint de arquitectura de producto, plataforma o ecosistema completo
- Infraestructura, seguridad, datos, integraciones o tradeoffs difíciles
- Analizar varios repos/documentos juntos sin perder contexto
- Encontrar causa raíz de bugs complejos o problemas de producción
- Convertir una visión ambigua en un plan ejecutable por fases

No recomendar G5 cuando baste con Sonnet/Haiku:
- Copy, SEO, prompts simples o brainstorming ligero
- Fixes pequeños, formateo, renombres, logs o lectura mecánica
- Implementar una tarea ya definida
- Decisiones que se validan mejor con usuarios reales que con más razonamiento

Ventana temporal (dato de contexto, no promesa permanente): Anthropic anunció Fable 5 disponible globalmente desde 2026-07-01. Para Pro, Max, Team y algunos Enterprise, está incluido hasta 50% de límites semanales hasta 2026-07-07; después requiere usage credits si el plan los permite. Si esta fecha ya pasó, no usarla como argumento de urgencia; mantener solo la regla de buen uso.

Prompt recomendado al sugerir G5:

```text
Estoy usando Fable 5. No implementes todavía.
Analiza el contexto completo y dame:
1. arquitectura recomendada,
2. riesgos y tradeoffs,
3. plan por fases,
4. qué debe ejecutar Sonnet,
5. qué puede delegarse a Haiku,
6. cuándo tendría sentido volver a Fable.
```

Reglas de honestidad:
- Decir que Fable puede rechazar o hacer fallback en áreas sensibles por clasificadores de seguridad.
- No prometer ahorro con Fable: se usa para evitar mala arquitectura o retrabajo caro, no para gastar menos por token.
- Preferir `/model fable` al inicio de la tarea. Evitar cambiar a Fable a mitad de una conversación larga por pérdida de caché.

---

## Estado y Bitácora

### Estado visible (statusline V2)

El statusline V2 **deriva la marcha del modelo real** — no del estado guardado.
El modelo real es la fuente de verdad; `state.json` es una intención que se contrasta.

```
⚙ G5 · Fable 5 · high · arquitectura · ≈5x
```

#### `gear=auto` (por defecto)

`reset.sh` escribe `{"gear":"auto",...}`. Con `auto`, el statusline muestra la marcha
derivada del modelo sin ningún aviso. Recomendado: deja `auto` salvo que quieras anclar
una marcha explícita.

#### `GN*` — qué significa el asterisco

El asterisco aparece cuando `state.json` tiene una marcha distinta al modelo real:

```
⚙ G5* · Fable 5 · high · ejecución · ≈5x  · state=G2
```

Aquí: el modelo real es Fable (→ G5) pero `state.json` dice G2. El `*` lo advierte en azul;
`state=G2` en ámbar dice exactamente qué está almacenado. Para resolverlo:

```bash
~/.claude/gearbox/set.sh G5 arquitectura high   # anclar a G5
~/.claude/gearbox/set.sh auto                   # o volver a auto (sin asterisco nunca)
```

No rompe nada — solo informa. El asterisco nunca bloquea trabajo.

#### `≈Nx` — el multiplicador

Brújula de costo relativo vs Sonnet base, leída de `~/.claude/gearbox/prices.json`.
**No es una factura** — usa `/usage` como fuente final. Si el payload de Claude Code trae
un costo real de sesión, el statusline lo muestra como `~$X est.`.

#### Barra de `/usage` — cuánto llevas quemado de tus límites

Desde Claude Code v2.1.80 el payload de statusline trae `rate_limits.{five_hour,seven_day}.used_percentage`
— el mismo dato que `/usage`, sin API externa ni polling. El statusline lo muestra así:

```
⚙ G2 · Sonnet 5 · high · ejecución · ≈1x · ▓▓▓░░ 61% 7d · 24% 5h
```

- **7d** (el recurso escaso en plan Pro): barra de 5 bloques `▓`/`░` + porcentaje.
- **5h**: solo el número, sin barra (cambia rápido, la barra marearía).
- Colores: <50% verde · 50–79% ámbar · ≥80% rojo.
- Si el payload no trae `rate_limits` (API, plan free, primer turno de la sesión), no se
  muestra nada — cada ventana puede faltar por separado, nunca se inventa.
- Pieza gearbox-nativa: si 7d≥80% y la marcha activa es G4/G5, aparece un hint ámbar:
  `⚠ 7d al NN% en marcha cara — considera bajar`. El `≈Nx` dice qué tan rápido quemas;
  la barra dice cuánto llevas quemado; el hint conecta ambos con la decisión de marcha.

### Actualizar la marcha con `set.sh`

```bash
~/.claude/gearbox/set.sh G5 arquitectura high   # fijar a G5
~/.claude/gearbox/set.sh G2 ejecución high      # volver a Sonnet/ejecución
~/.claude/gearbox/set.sh auto                   # modo auto (recomendado al cerrar sesión especial)
```

Marchas válidas: `auto G0 G1 G2 G3 G3.5 G4 G5`.
El segundo y tercer argumento son opcionales (defaults por marcha: tarea y effort=high).

### Bitácora de calibración: dos ríos separados

`log.sh` escribe en dos archivos distintos según el tipo de dato — un evento de `set`/`reset`
no tiene valor de calibración (solo dice "abrí sesión" o "cambié estado"); una decisión
clasificada sí lo tiene. Mezclarlos hacía la Calibración Fase 2 imposible de analizar.

**`events.jsonl`** — automático, `set.sh`/`reset.sh` escriben aquí en cada llamada:

```json
{"ts":"2026-07-06T22:44:32Z","gear":"G5","task":"arquitectura","effort":"high","action":"set","model":"Fable 5"}
```

**`decisions.jsonl`** — el dato que calibra. Se escribe con el comando literal del paso 3
del protocolo, SIEMPRE que se clasifique una tarea (haya o no cambio de marcha):

```bash
~/.claude/gearbox/log.sh decision <gear_actual> <gear_recomendada> "<task>" [skill] [doc]
```

Ejemplo real:

```bash
~/.claude/gearbox/log.sh decision G2 G2 "fix de bug en checkout" supabase
```

Esquema canónico que produce (una línea JSONL):

```json
{"ts":"...","model":"Sonnet 5","gear_actual":"G2","gear_recomendada":"G2",
 "task":"fix de bug en checkout","skill":"supabase","accion":"ejecutar",
 "doc":"","retrabajo":false}
```

`accion` se auto-deriva (`ejecutar` si `gear_actual`==`gear_recomendada`, si no
`recomendar-cambio`) o se pasa explícito como 6º argumento — usar `delegar-haiku` cuando
la tarea se delega a un subagente Haiku (G0), para que la delegación deje rastro:

```bash
~/.claude/gearbox/log.sh decision G2 G0 "buscar todas las referencias a X" "" "" delegar-haiku
```

**Retrabajo** — LA señal de marcha insuficiente. Si una tarea tuvo que rehacerse, registrar
una línea nueva (JSONL es append-only, no se edita la anterior):

```bash
~/.claude/gearbox/log.sh retrabajo "<task>"
```

**Modelo:** ambos comandos registran el modelo si está disponible — vía `GEARBOX_MODEL`
(variable de entorno) o como último argumento en modo evento
(`set.sh <gear> [task] [effort] [model]`). Nunca se inventa: si no está disponible, el
campo queda vacío.

El historial previo a este esquema vive en `~/.claude/gearbox/log.jsonl.v1` (archivado,
nunca borrado — 3 esquemas incompatibles convivían ahí; ver auditoría 2026-07-06).
El análisis de `decisions.jsonl` alimenta la Calibración Fase 2.

---

## Calibración Fase 2 (semi-automática, gate humano)

Umbral mínimo utilizable: **≥10 decisiones por skill** en `decisions.jsonl` antes de proponer
un frontmatter `effort:` — menos que eso no es evidencia, es ruido.

Cuando un skill alcance el umbral:
1. Analizar: en qué marcha corrió y si hubo `retrabajo:true`
2. Proponer al usuario la tabla `skill → effort` para los frontmatter faltantes, CON evidencia
3. Solo con su OK, editar el frontmatter `effort:` de cada skill

Skills ya calibradas por naturaleza obvia (no requieren datos):
`playwright-cli: low` · `primer: low` · `update-sf: low` · `image-generation: low` ·
`prp: high` · `bucle-agentico: high` · `supabase: high` · `compliance: high` · `guardian: high`

---

## Model Watch (revisión mensual)

La fecha de última revisión vive en `~/.claude/gearbox/watch.json` (`{"last_watch":"YYYY-MM-DD"}`)
— un archivo propio que ningún `reset.sh` toca (a diferencia de `state.json`, que se reescribe
completo en cada SessionStart). Si tu proyecto ya tiene un hook `SessionStart` propio (no lo
instala `install.sh`; es infraestructura opcional que cada quien conecta a su gusto), puede leer
este archivo y agregar un aviso pasivo al contexto (`⚙ Model Watch pendiente`) si pasaron más de
30 días desde la última revisión, o si nunca se ha registrado una. Sin ese hook, revisar
`watch.json` a mano una vez al mes cumple lo mismo.

Cuando el aviso aparezca (o una vez al mes por iniciativa propia):
1. Consultar https://platform.claude.com/docs/en/about-claude/models/overview
2. Si hay modelo de categoría nueva (no solo versión — los alias cubren versiones):

```
⚙ GEARBOX → modelo nuevo detectado: [nombre]
   Precio: $X/$Y · Capacidades: [resumen 1 línea]
   Propuesta: agregarlo como marcha GX para [tipo de tarea]
   ¿Actualizo la tabla? [requiere OK del usuario]
```

3. Solo con OK, actualizar la Tabla de Marchas de este archivo.
4. Actualizar `~/.claude/gearbox/watch.json` con la fecha de hoy — haya o no modelo nuevo,
   la revisión en sí misma resetea el conteo de 30 días.

---

## Errores a evitar (heredados del Gearbox Protocol de OpenGravity)

- Usar marcha alta para decidir cosas que se validan barato (10 DMs > multi-LLM)
- Cambiar de modelo a mitad de una tarea larga (caché perdido > ahorro)
- Subir a Fable sin gate de costo explícito
- Clasificar por la IMPORTANCIA del tema en vez de por la TAREA que viene
  (iterar preguntas sobre un plan ya hecho = ejecución ligera, aunque el tema sea estratégico)
- Fijar versiones de modelo en vez de alias
