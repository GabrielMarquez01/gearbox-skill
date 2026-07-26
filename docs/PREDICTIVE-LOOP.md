# Gearbox V3 Preview — Predictive Loop

Gearbox V3 añade una capa predictiva **sin retirar la funcionalidad V2**. Los
scripts `set.sh`, `reset.sh`, `log.sh` y `statusline.sh` siguen disponibles, pero
usan un núcleo Python común para procesar JSON de forma segura.

## Bucle operativo

```text
observar → clasificar → predecir → recomendar → ejecutar → verificar → aprender
```

La instalación inicia en `mode: observe`:

- clasifica cada prompt mediante el hook `UserPromptSubmit`;
- registra únicamente hash y métricas del prompt, no el texto completo;
- estima marcha, modelo, esfuerzo, riesgo y confianza;
- guarda las predicciones en SQLite;
- no cambia automáticamente el modelo;
- conserva gates humanos para acciones críticas.

## Contrato predictivo

Cada tarea produce una predicción con:

- `task_type`;
- `gear`, `model`, `effort`;
- `routing_confidence`;
- `predicted_success`;
- `risk` y `human_gate`;
- razón y fallback.

`predicted_success` es un prior conservador. Cuando se registra feedback, Gearbox
actualiza la estimación mediante un posterior Beta-Bernoulli por tipo de tarea y
ruta. No es una garantía.

## Feedback y aprendizaje

```bash
~/.claude/gearbox/gearbox.py history --limit 10
~/.claude/gearbox/gearbox.py feedback <task_id> accepted
~/.claude/gearbox/gearbox.py feedback <task_id> rejected
~/.claude/gearbox/gearbox.py feedback <task_id> rework
```

La autonomía futura sólo debe habilitarse después de recopilar evidencia local.
La política por defecto exige al menos 100 muestras y 90% de confianza, y sólo
considera G0–G2. G4/G5 mantienen gate humano.

## Privacidad

Por defecto no se almacena el prompt. Se guarda:

- SHA-256 del prompt;
- número de caracteres;
- proyecto/cwd;
- clasificación y predicción;
- feedback posterior.

## Compatibilidad

Los comandos históricos siguen funcionando:

```bash
~/.claude/gearbox/set.sh G2 ejecución high
~/.claude/gearbox/reset.sh
~/.claude/gearbox/log.sh decision G2 G2 "fix checkout" supabase
```

## Siguiente iteración

1. Shadow Mode con evaluación de precisión.
2. Verificación objetiva mediante tests/builds.
3. Agentes especializados G0–G5.
4. Exportación opcional a Graphos/MCP.
5. Autonomía gobernada sólo para tareas reversibles y con evidencia suficiente.
