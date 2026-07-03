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
| **G4 Crítico** | seguridad/PII, producción caída, debugging multi-sistema | Opus · high | recomendar `/model opus` | +40%/token, se paga si evita retrabajo |
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
3. ACTUALIZAR el estado y la bitácora (ver abajo) — siempre, haya o no cambio
```

### Formato del bloque de recomendación (obligatorio, literal)

```
⚙ GEARBOX → conviene subir a Opus / Alto
   Comando:  /model opus
   Razón:    debugging multi-sistema en producción
   Economía: +40%/token pero evita retrabajo; cambiar AHORA (el caché se reinicia al cambiar)
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

### Estado visible (statusline)
Al cambiar de marcha, actualizar `~/.claude/gearbox/state.json`:

```bash
cat > ~/.claude/gearbox/state.json <<'EOF'
{"gear":"G3","task":"planeación","effort":"high"}
EOF
```

El statusline (`~/.claude/gearbox/statusline.sh`) lo muestra en azul bajo la terminal:
`⚙ G3 · Opus 4.8 · high · planeación`
(El modelo mostrado es el REAL de la sesión — lo inyecta el harness, no el estado.)

### Bitácora de calibración (una línea por clasificación)

```bash
echo '{"ts":"2026-07-02T21:00:00Z","gear":"G2","task":"UI cuidadores","skill":"","retrabajo":false}' >> ~/.claude/gearbox/log.jsonl
```

Campos: `ts` (ISO), `gear`, `task` (3-6 palabras), `skill` (si aplica), `retrabajo` (true si la tarea tuvo que rehacerse — señal de marcha insuficiente).

---

## Calibración Fase 2 (semi-automática, gate humano)

Cuando `log.jsonl` acumule ~2 semanas de datos:
1. Analizar: qué skills corrieron en qué marcha y si hubo retrabajo
2. Proponer al usuario la tabla `skill → effort` para los frontmatter faltantes, CON evidencia
3. Solo con su OK, editar el frontmatter `effort:` de cada skill

Skills ya calibradas por naturaleza obvia (no requieren datos):
`playwright-cli: low` · `primer: low` · `update-sf: low` · `image-generation: low` ·
`prp: high` · `bucle-agentico: high` · `supabase: high` · `compliance: high` · `guardian: high`

---

## Model Watch (revisión mensual)

Una vez al mes (anotar fecha de última revisión en `~/.claude/gearbox/state.json` campo `last_watch`):
1. Consultar https://platform.claude.com/docs/en/about-claude/models/overview
2. Si hay modelo de categoría nueva (no solo versión — los alias cubren versiones):

```
⚙ GEARBOX → modelo nuevo detectado: [nombre]
   Precio: $X/$Y · Capacidades: [resumen 1 línea]
   Propuesta: agregarlo como marcha GX para [tipo de tarea]
   ¿Actualizo la tabla? [requiere OK del usuario]
```

3. Solo con OK, actualizar la Tabla de Marchas de este archivo.

---

## Errores a evitar (heredados del Gearbox Protocol de OpenGravity)

- Usar marcha alta para decidir cosas que se validan barato (10 DMs > multi-LLM)
- Cambiar de modelo a mitad de una tarea larga (caché perdido > ahorro)
- Subir a Fable sin gate de costo explícito
- Clasificar por la IMPORTANCIA del tema en vez de por la TAREA que viene
  (iterar preguntas sobre un plan ya hecho = ejecución ligera, aunque el tema sea estratégico)
- Fijar versiones de modelo en vez de alias
