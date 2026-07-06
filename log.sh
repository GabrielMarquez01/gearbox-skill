#!/usr/bin/env bash
# Gearbox log.sh — agrega línea JSONL a ~/.claude/gearbox/log.jsonl
# Uso: log.sh <action> <gear> <task> <effort> [model]
# Tolerante a errores: falla silencioso para no romper set.sh/reset.sh

action="${1:-set}"
gear="${2:-auto}"
task="${3:-auto}"
effort="${4:-auto}"
model="${5:-}"

log_file="$HOME/.claude/gearbox/log.jsonl"
mkdir -p "$(dirname "$log_file")" 2>/dev/null || exit 0

ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

# Sanear valores para JSON manual (quitar comillas y backslashes)
clean() { printf '%s' "$1" | tr -d '"\\' ; }

model_field=""
[ -n "$model" ] && model_field=",\"model\":\"$(clean "$model")\""

line="{\"ts\":\"$(clean "$ts")\",\"gear\":\"$(clean "$gear")\",\"task\":\"$(clean "$task")\",\"effort\":\"$(clean "$effort")\",\"action\":\"$(clean "$action")\"${model_field}}"

printf '%s\n' "$line" >> "$log_file" 2>/dev/null || true
