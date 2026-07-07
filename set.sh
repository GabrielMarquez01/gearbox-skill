#!/usr/bin/env bash
# Gearbox set.sh — establece marcha, tarea y esfuerzo en state.json
# Uso: set.sh <gear> [task] [effort] [model]
#      set.sh G5 arquitectura high "Fable 5"
#      set.sh G2 ejecución high
#      set.sh auto
# [model] también puede llegar por env var GEARBOX_MODEL, si no se pasa como argumento.

GB_DIR="$HOME/.claude/gearbox"
LOG_SH="$GB_DIR/log.sh"

# Marchas válidas
valid_gears="auto G0 G1 G2 G3 G3.5 G4 G5"
gear="${1:-auto}"

# Validar marcha
found=0
for g in $valid_gears; do
  [ "$g" = "$gear" ] && found=1 && break
done

if [ "$found" -eq 0 ]; then
  printf 'Gearbox set.sh — marcha inválida: "%s"\n' "$gear" >&2
  printf 'Marchas válidas: %s\n' "$valid_gears" >&2
  printf 'Ejemplos:\n  set.sh G5 arquitectura high\n  set.sh G2 ejecución high\n  set.sh auto\n' >&2
  exit 1
fi

# Default de tarea por marcha
default_task() {
  case "$1" in
    auto) echo "auto" ;;
    G0)   echo "rutina" ;;
    G1)   echo "contenido" ;;
    G2)   echo "ejecución" ;;
    G3)   echo "planeación" ;;
    G3.5) echo "turno-profundo" ;;
    G4)   echo "crítico" ;;
    G5)   echo "arquitectura" ;;
    *)    echo "auto" ;;
  esac
}

task="${2:-$(default_task "$gear")}"
effort="${3:-high}"
model="${4:-${GEARBOX_MODEL:-}}"

# Crear directorio si no existe
mkdir -p "$GB_DIR"

# Escribir state.json (sin jq, usando printf para seguridad)
clean() { printf '%s' "$1" | tr -d '"\\' ; }
cat > "$GB_DIR/state.json" <<STATEOF
{"gear":"$(clean "$gear")","task":"$(clean "$task")","effort":"$(clean "$effort")"}
STATEOF

printf '⚙ Gearbox: %s · %s · %s\n' "$gear" "$task" "$effort"

# Llamar a log.sh si existe (tolerante a errores)
if [ -x "$LOG_SH" ]; then
  "$LOG_SH" "set" "$gear" "$task" "$effort" "$model" 2>/dev/null || true
elif [ -f "$LOG_SH" ]; then
  bash "$LOG_SH" "set" "$gear" "$task" "$effort" "$model" 2>/dev/null || true
fi
