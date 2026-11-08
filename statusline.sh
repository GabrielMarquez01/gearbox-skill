#!/usr/bin/env bash
# Gearbox statusline V2 — marcha derivada del modelo real, asterisco si desync
# Input:  JSON de Claude Code por stdin (model.display_name, effort.level,
#         cost.total_cost_usd, rate_limits.{five_hour,seven_day}.used_percentage)
# State:  ~/.claude/gearbox/state.json (gear/task/effort guardados)
# Prices: ~/.claude/gearbox/prices.json (multiplicadores relativos, opcional)
# Output: ⚙ gear · modelo · effort · tarea · ≈Nx · ~$X est. · barra 7d · % 5h [hints ámbar]

input=$(cat)

# ── 1–3. JSON real: payload y estado; esfuerzo recibido > guardado > ? ────
state_file="$HOME/.claude/gearbox/state.json"
{
  IFS= read -r model
  IFS= read -r gear_state
  IFS= read -r task_state
  IFS= read -r effort
} < <(python3 -c '
import json, sys
try:
    data=json.loads(sys.argv[1])
    if not isinstance(data,dict): data={}
except ValueError: data={}
try:
    state=json.load(open(sys.argv[2]))
    if not isinstance(state,dict): state={}
except (ValueError,OSError): state={}
model=data.get("model") or {}
if not isinstance(model,dict): model={}
effort=data.get("effort")
if isinstance(effort,dict): effort=effort.get("level")
if not isinstance(effort,str) or not effort: effort=state.get("effort", "auto")
if not isinstance(effort,str) or not effort or effort == "auto": effort="?"
for value in (model.get("display_name") or "?", state.get("gear") or "auto", state.get("task") or "auto", effort):
    # Una línea por campo; quitar controles de terminal en la presentación.
    value=str(value).encode("utf-8", "ignore").decode("utf-8")
    print("".join(c if ord(c) >= 32 and ord(c) != 127 else " " for c in value))
' "$input" "$state_file")

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

# ── 7. Catálogo JSON; no atribuir tarifa vigente a otra versión ───────────
prices_file="$HOME/.claude/gearbox/prices.json"
rel=$(python3 -c '
import json, math, sys
try:
    data=json.loads(sys.argv[1]); prices=json.load(open(sys.argv[2]))
    model=data.get("model", {})
    for entry in prices["models"].values():
        if model.get("id") != entry["id"] and (model.get("id") or model.get("display_name", "").lower() not in (entry["_modelo"].lower(), "claude "+entry["_modelo"].lower())):
            continue
        key="relative"
        if "relative_long" in entry:
            n=data.get("context_window", {}).get("total_input_tokens")
            if isinstance(n, bool) or not isinstance(n, (int,float)) or not math.isfinite(n) or n < 0:
                break
            if n > entry["prompt_threshold"]: key="relative_long"
        print(format(entry[key], "g"), end="")
        break
except (ValueError, OSError, KeyError, TypeError, AttributeError):
    pass
' "$input" "$prices_file")
mult_str=""
[ -n "$rel" ] && mult_str=" · ≈${rel}x"

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
# Solo ventanas con porcentaje válido y resets_at futuro. Cada refresco reemplaza
# el snapshot completo: un payload sin límites invalida la lectura anterior.
{
  IFS= read -r five_h
  IFS= read -r seven_d
} < <(python3 -c '
import json, math, os, sys, tempfile, time
now=time.time(); result={"updated_at":now}
try:
    data=json.loads(sys.argv[1])
    if not isinstance(data,dict): data={}
except ValueError:
    data={}
sid=data.get("session_id")
if isinstance(sid,str): result["session_id"]=sid.encode("utf-8", "ignore").decode("utf-8")
limits=data.get("rate_limits") or {}
if not isinstance(limits,dict): limits={}
for name in ("five_hour", "seven_day"):
    window=limits.get(name) or {}
    if not isinstance(window,dict): continue
    pct=window.get("used_percentage"); reset=window.get("resets_at")
    if all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (pct,reset)) and 0 <= pct <= 100 and reset > now:
        result[name]=int(pct)
        result["reset_"+name]=reset
try:
    directory=os.path.dirname(sys.argv[2]); os.makedirs(directory,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",dir=directory,prefix="usage-",delete=False) as f:
        json.dump(result,f); f.write("\n"); temp=f.name
    os.replace(temp,sys.argv[2])  # permisos 600, reemplazo atómico
except OSError:
    pass
print(result.get("five_hour", "")); print(result.get("seven_day", ""))
' "$input" "$HOME/.claude/gearbox/usage.json")

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
