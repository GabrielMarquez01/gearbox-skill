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

# Azul ANSI (34). Formato: ⚙ G2 · Sonnet 4.6 · high · ejecución
printf '\033[34m⚙ %s · %s · %s · %s\033[0m' "$gear" "$model" "$effort" "$task"
