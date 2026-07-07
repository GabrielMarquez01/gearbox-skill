#!/usr/bin/env bash
# Gearbox statusline V2 — marcha derivada del modelo real, asterisco si desync
# Input:  JSON de Claude Code por stdin (model.display_name, effort.level,
#         cost.total_cost_usd, rate_limits.{five_hour,seven_day}.used_percentage)
# State:  ~/.claude/gearbox/state.json (gear/task/effort guardados)
# Prices: ~/.claude/gearbox/prices.json (multiplicadores relativos, opcional)
# Output: ⚙ gear · modelo · effort · tarea · ≈Nx · ~$X est. · barra 7d · % 5h [hints ámbar]

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

# ── 4. Derivar marcha desde modelo real + effort (fuente de verdad) ───────
case "$model" in
  *[Ff]able*)  gear_derived="G5" ;;
  *[Hh]aiku*)  gear_derived="G0" ;;
  *[Ss]onnet*)
    case "$effort" in
      medium|low) gear_derived="G1" ;;
      *)          gear_derived="G2" ;;
    esac ;;
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

# ── 7. Multiplicador desde prices.json (sed puro, sin python3) ────────────
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
    rel=$(sed -n "s/.*\"${model_key}\"[[:space:]]*:[[:space:]]*{[^}]*\"relative\"[[:space:]]*:[[:space:]]*\([0-9.]*\).*/\1/p" "$prices_file" | head -1)
    [ -n "$rel" ] && mult_str=" · ≈${rel}x"
  fi
fi

# ── 8. Costo real: cost.total_cost_usd (anidado — "cost_usd" plano no existe) ─
cost_usd=$(printf '%s' "$input" | sed -n 's/.*"total_cost_usd"[[:space:]]*:[[:space:]]*\([0-9]*\.\?[0-9]*\).*/\1/p' | head -1)
cost_str=""
if [ -n "$cost_usd" ] && [ "$cost_usd" != "0" ] && [ "$cost_usd" != "0.0" ]; then
  cost_display=$(printf '%.2f' "$cost_usd" 2>/dev/null)
  [ -z "$cost_display" ] && cost_display="$cost_usd"
  cost_str=" · ~\$${cost_display} est."
fi

# ── 9. Barra de /usage real — rate_limits.{five_hour,seven_day}.used_percentage
#      7d: barra de 5 bloques + %. 5h: solo número (cambia rápido, la barra marearía).
#      Si rate_limits no viene, no mostrar nada — nunca inventar. Cada ventana es
#      independiente: puede faltar una sin la otra.
usage_str=""
usage_hint=""
five_h=$(printf '%s' "$input" | sed -n 's/.*"five_hour"[[:space:]]*:[[:space:]]*{[^}]*"used_percentage"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)
seven_d=$(printf '%s' "$input" | sed -n 's/.*"seven_day"[[:space:]]*:[[:space:]]*{[^}]*"used_percentage"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' | head -1)

color_for() { # $1 = porcentaje entero → código ANSI: <50 verde · 50-79 ámbar · ≥80 rojo
  if [ "$1" -ge 80 ]; then printf '31'
  elif [ "$1" -ge 50 ]; then printf '33'
  else printf '32'
  fi
}

bar_for() { # $1 = porcentaje entero → 5 bloques ▓/░, redondeado al bloque más cercano (20%/bloque)
  pct="$1"
  filled=$(( (pct + 10) / 20 ))
  [ "$filled" -gt 5 ] && filled=5
  [ "$filled" -lt 0 ] && filled=0
  bar=""
  i=1
  while [ "$i" -le 5 ]; do
    if [ "$i" -le "$filled" ]; then bar="${bar}▓"; else bar="${bar}░"; fi
    i=$((i + 1))
  done
  printf '%s' "$bar"
}

ESC=$'\033'
if [ -n "$seven_d" ]; then
  bar7=$(bar_for "$seven_d")
  c7=$(color_for "$seven_d")
  usage_str="${usage_str} · ${ESC}[${c7}m${bar7} ${seven_d}% 7d${ESC}[34m"
fi
if [ -n "$five_h" ]; then
  c5=$(color_for "$five_h")
  usage_str="${usage_str} · ${ESC}[${c5}m${five_h}% 5h${ESC}[34m"
fi

# Pieza gearbox-nativa: cruzar el % con la marcha activa
if [ -n "$seven_d" ] && [ "$seven_d" -ge 80 ]; then
  case "$gear_derived" in
    G4|G5) usage_hint=" · ⚠ 7d al ${seven_d}% en marcha cara — considera bajar" ;;
  esac
fi

# ── 10. Renderizar ─────────────────────────────────────────────────────────
line="⚙ ${gear_display} · ${model} · ${effort} · ${task}${mult_str}${cost_str}${usage_str}"
amber_suffix="${hint}${usage_hint}"

if [ -n "$amber_suffix" ]; then
  printf '\033[34m%s\033[0m\033[33m%s\033[0m' "$line" "$amber_suffix"
else
  printf '\033[34m%s\033[0m' "$line"
fi
