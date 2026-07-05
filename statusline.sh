#!/usr/bin/env bash
# Gearbox statusline — muestra marcha activa, modelo real y esfuerzo en azul
# Input: JSON de Claude Code por stdin (model.display_name = modelo REAL de la sesión)
# Estado: ~/.claude/gearbox/state.json (lo mantiene la skill gearbox)
# Sin dependencias: solo bash + sed (portable, no requiere jq)

input=$(cat)

# Extraer display_name del JSON de entrada
model=$(printf '%s' "$input" | sed -n 's/.*"display_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -z "$model" ] && model="?"

# Leer estado del gearbox (defaults si no existe)
state_file="$HOME/.claude/gearbox/state.json"
gear="G2"; task="ejecución"; effort="high"
if [ -f "$state_file" ]; then
  s=$(cat "$state_file")
  g=$(printf '%s' "$s" | sed -n 's/.*"gear"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p');   [ -n "$g" ] && gear="$g"
  t=$(printf '%s' "$s" | sed -n 's/.*"task"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p');   [ -n "$t" ] && task="$t"
  e=$(printf '%s' "$s" | sed -n 's/.*"effort"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'); [ -n "$e" ] && effort="$e"
fi

# Si Claude Code expone effort real en el payload, preferirlo sobre state.json.
# Soporta {"effort":{"level":"high"}} y {"effort":"high"}.
runtime_effort=$(printf '%s' "$input" | sed -n 's/.*"effort"[[:space:]]*:[[:space:]]*{[^}]*"level"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -z "$runtime_effort" ] && runtime_effort=$(printf '%s' "$input" | sed -n 's/.*"effort"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -n "$runtime_effort" ] && effort="$runtime_effort"

# Detección de desincronización: el modelo REAL (harness, fuente de verdad) vs la marcha
# guardada en state.json. Evita que el statusline mienta — p.ej. mostrar G2 (Sonnet) mientras
# la sesión corre en Opus, ocultando que se paga de más. Marca " ⚠ desync" cuando no cuadran.
desync=""
case "$model" in
  *Fable*)  [ "$gear" != "G5" ] && desync=" ⚠ desync" ;;
  *Opus*)   case "$gear" in G3|G3.5|G4) ;; *) desync=" ⚠ desync" ;; esac ;;
  *Haiku*)  [ "$gear" != "G0" ] && desync=" ⚠ desync" ;;
esac

# Azul ANSI (34); el aviso de desync en amarillo (33) para que salte a la vista.
if [ -n "$desync" ]; then
  printf '\033[34m⚙ %s · %s · %s · %s\033[0m\033[33m%s\033[0m' "$gear" "$model" "$effort" "$task" "$desync"
else
  printf '\033[34m⚙ %s · %s · %s · %s\033[0m' "$gear" "$model" "$effort" "$task"
fi
