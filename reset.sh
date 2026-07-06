#!/usr/bin/env bash
# Gearbox reset.sh — restaura marcha a auto (hook SessionStart)
# Default auto permite que statusline.sh derive la marcha del modelo real

GB_DIR="$HOME/.claude/gearbox"
mkdir -p "$GB_DIR"

cat > "$GB_DIR/state.json" <<'EOF'
{"gear":"auto","task":"auto","effort":"auto"}
EOF

# Llamar a log.sh si existe (tolerante a errores)
LOG_SH="$GB_DIR/log.sh"
if [ -x "$LOG_SH" ]; then
  "$LOG_SH" "reset" "auto" "auto" "auto" 2>/dev/null || true
elif [ -f "$LOG_SH" ]; then
  bash "$LOG_SH" "reset" "auto" "auto" "auto" 2>/dev/null || true
fi
