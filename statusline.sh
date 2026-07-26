#!/usr/bin/env bash
set -euo pipefail
CORE="${GEARBOX_HOME:-$HOME/.claude/gearbox}/gearbox.py"
if [ ! -f "$CORE" ]; then
  printf 'Gearbox: núcleo no encontrado en %s. Ejecuta install.sh de nuevo.\n' "$CORE" >&2
  exit 1
fi
exec python3 "$CORE" statusline "$@"
