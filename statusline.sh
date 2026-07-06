#!/usr/bin/env bash
# Gearbox statusline V2 — marcha derivada del modelo real, asterisco si desync
# Input:  JSON de Claude Code por stdin (model.display_name = modelo real)
# State:  ~/.claude/gearbox/state.json (gear/task/effort guardados)
# Prices: ~/.claude/gearbox/prices.json (multiplicadores relativos, opcional)
# Output: línea azul con ⚙ gear · modelo · effort · tarea · ≈Nx [hint en ámbar]

input=$(cat)

# ── 1. Extraer modelo real del payload ─────────────────────────────────────
model=$(printf '%s' "$input" | sed -n 's/.*"display_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
[ -z "$model" ] && model="?"

# ── 2. Leer state.json ─────────────────────────────────────────────────────
state_file="$HOME/.claude/gearbox/state.json"
gear_state="auto"; task_state="auto"; effort_state="auto"
if [ -f "$state_file" ]; then
  s=$(cat "$state_file")
  g=$(printf '%s' "$s" | sed -n 's/.*"gear"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p');   [ -n "$g" ] && gear_state="$g"
  t=$(printf '%s' "$s" | sed -n 's/.*"task"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p');   [ -n "$t" ] && task_state="$t"
  e=$(printf '%s' "$s" | sed -n 's/.*"effort"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'); [ -n "$e" ] && effort_state="$e"
fi

# ── 3. Effort real: runtime > state ────────────────────────────────────────
effort="$effort_state"
re=$(printf '%s' "$input" | sed -n 's/.*"effort"[[:space:]]*:[[:space:]]*{[^}]*"level"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
[ -z "$re" ] && re=$(printf '%s' "$input" | sed -n 's/.*"effort"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
[ -n "$re" ] && effort="$re"
[ "$effort" = "auto" ] && effort="high"

# ── 4. Derivar marcha desde modelo real (fuente de verdad) ─────────────────
case "$model" in
  *[Ff]able*)  gear_derived="G5" ;;
  *[Hh]aiku*)  gear_derived="G0" ;;
  *[Ss]onnet*) gear_derived="G2" ;;
  *[Oo]pus*)
    # Si state ya apunta a algo razonable para Opus, respetarlo
    case "$gear_state" in
      G3|G3.5|G4) gear_derived="$gear_state" ;;
      *)           gear_derived="G4" ;;
    esac ;;
  *)
    # Modelo desconocido: usar state o G2
    if [ "$gear_state" = "auto" ]; then
      gear_derived="G2"
    else
      gear_derived="$gear_state"
    fi ;;
esac

# ── 5. Determinar marcha a mostrar y si hay desync ─────────────────────────
gear_display="$gear_derived"
hint=""
if [ "$gear_state" = "auto" ] || [ "$gear_state" = "$gear_derived" ]; then
  : # sin asterisco
else
  gear_display="${gear_derived}*"
  hint=" · state=${gear_state}"
fi

# ── 6. Task: resolver "auto" a nombre por defecto de la marcha ─────────────
task="$task_state"
if [ "$task" = "auto" ] || [ -z "$task" ]; then
  case "$gear_derived" in
    G0)   task="rutina" ;;
    G1)   task="contenido" ;;
    G2)   task="ejecución" ;;
    G3)   task="planeación" ;;
    G3.5) task="turno-profundo" ;;
    G4)   task="crítico" ;;
    G5)   task="arquitectura" ;;
    *)    task="ejecución" ;;
  esac
fi

# ── 7. Multiplicador desde prices.json ────────────────────────────────────
prices_file="$HOME/.claude/gearbox/prices.json"
mult_str=""
if [ -f "$prices_file" ]; then
  model_key=""
  case "$model" in
    *[Ff]able*)  model_key="fable" ;;
    *[Hh]aiku*)  model_key="haiku" ;;
    *[Ss]onnet*) model_key="sonnet" ;;
    *[Oo]pus*)   model_key="opus" ;;
  esac
  if [ -n "$model_key" ]; then
    rel=$(python3 -c "
import json,sys
try:
  with open(sys.argv[1]) as f:
    d=json.load(f)
  v=float(d['models'][sys.argv[2]]['relative'])
  print(int(v) if v==int(v) else v)
except:
  pass
" "$prices_file" "$model_key" 2>/dev/null)
    [ -n "$rel" ] && mult_str=" · ≈${rel}x"
  fi
fi

# ── 8. Costo real si el payload lo trae (no inventar) ────────────────────
cost_usd=$(printf '%s' "$input" | sed -n 's/.*"cost_usd"[[:space:]]*:[[:space:]]*\([0-9]*\.[0-9]*\).*/\1/p' | head -1)
cost_str=""
[ -n "$cost_usd" ] && [ "$cost_usd" != "0.0" ] && [ "$cost_usd" != "0" ] && cost_str=" · ~\$${cost_usd} est."

# ── 9. Renderizar ─────────────────────────────────────────────────────────
if [ -n "$hint" ]; then
  # Marcha + azul, hint en ámbar
  printf '\033[34m⚙ %s · %s · %s · %s%s%s\033[0m\033[33m%s\033[0m' \
    "$gear_display" "$model" "$effort" "$task" "$mult_str" "$cost_str" "$hint"
else
  printf '\033[34m⚙ %s · %s · %s · %s%s%s\033[0m' \
    "$gear_display" "$model" "$effort" "$task" "$mult_str" "$cost_str"
fi
