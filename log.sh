#!/usr/bin/env bash
# Gearbox log.sh — bitácora dual v3: eventos operativos vs decisiones de calibración
#
# Eventos (set/reset — sin valor de calibración, solo "abrí sesión/cambié estado"):
#   log.sh <action> <gear> <task> <effort> [model]        → ~/.claude/gearbox/events.jsonl
#
# Decisiones (el dato que calibra — una por clasificación de tarea):
#   log.sh decision <gear_actual> <gear_recomendada> "<task>" [skill] [doc] [accion] → decisions.jsonl
#   log.sh retrabajo "<task>"                                                         → decisions.jsonl
#
# Modelo: exportar GEARBOX_MODEL="Sonnet 5" antes de llamar (o pasarlo como último
# argumento en modo evento). Si no está disponible, se registra vacío — nunca se inventa.
# Tolerante a errores: falla silencioso para no romper set.sh/reset.sh

GB_DIR="$HOME/.claude/gearbox"
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$GB_DIR" 2>/dev/null || exit 0

ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

# Sanear valores para JSON manual (quitar comillas y backslashes)
clean() { printf '%s' "$1" | tr -d '"\\' ; }

# Skills globales de Claude Code sin carpeta local en .claude/skills/ (no listables por filesystem)
GLOBAL_SKILLS="deep-research artifact-design update-config keybindings-help verify code-review simplify fewer-permission-prompts loop schedule claude-api run init review security-review"

skill_valida() {
  s="$1"
  [ -z "$s" ] && return 1
  [ "$s" = "ninguno" ] && return 0
  [ -d "$SKILLS_DIR/$s" ] && return 0
  for g in $GLOBAL_SKILLS; do
    [ "$g" = "$s" ] && return 0
  done
  return 1
}

# model desde state.json (fallback cuando no llega por arg/GEARBOX_MODEL)
model_de_state() {
  [ -f "$GB_DIR/state.json" ] || return 0
  grep -o '"model":"[^"]*"' "$GB_DIR/state.json" 2>/dev/null | head -1 | sed 's/"model":"//;s/"$//'
}

mode="${1:-set}"

case "$mode" in
  decision)
    gear_actual="$(clean "${2:-}")"
    gear_recomendada="$(clean "${3:-}")"
    task="$(clean "${4:-}")"
    skill="$(clean "${5:-}")"
    doc="$(clean "${6:-}")"
    accion="$(clean "${7:-}")"
    if [ -z "$accion" ]; then
      if [ -n "$gear_actual" ] && [ "$gear_actual" = "$gear_recomendada" ]; then
        accion="ejecutar"
      else
        accion="recomendar-cambio"
      fi
    fi
    skill_valida "$skill" || skill="ninguno"
    model="$(clean "${GEARBOX_MODEL:-}")"
    [ -z "$model" ] && model="$(clean "$(model_de_state)")"
    line="{\"ts\":\"$ts\",\"model\":\"$model\",\"gear_actual\":\"$gear_actual\",\"gear_recomendada\":\"$gear_recomendada\",\"task\":\"$task\",\"skill\":\"$skill\",\"accion\":\"$accion\",\"doc\":\"$doc\",\"retrabajo\":false}"
    printf '%s\n' "$line" >> "$GB_DIR/decisions.jsonl" 2>/dev/null || true
    ;;

  retrabajo)
    task="$(clean "${2:-}")"
    model="$(clean "${GEARBOX_MODEL:-}")"
    line="{\"ts\":\"$ts\",\"model\":\"$model\",\"gear_actual\":\"\",\"gear_recomendada\":\"\",\"task\":\"$task\",\"skill\":\"\",\"accion\":\"retrabajo\",\"doc\":\"\",\"retrabajo\":true}"
    printf '%s\n' "$line" >> "$GB_DIR/decisions.jsonl" 2>/dev/null || true
    ;;

  *)
    action="$mode"
    gear="$(clean "${2:-auto}")"
    task="$(clean "${3:-auto}")"
    effort="$(clean "${4:-auto}")"
    model="$(clean "${5:-${GEARBOX_MODEL:-}}")"
    model_field=""
    [ -n "$model" ] && model_field=",\"model\":\"$model\""
    line="{\"ts\":\"$ts\",\"gear\":\"$gear\",\"task\":\"$task\",\"effort\":\"$effort\",\"action\":\"$action\"${model_field}}"
    printf '%s\n' "$line" >> "$GB_DIR/events.jsonl" 2>/dev/null || true
    ;;
esac
