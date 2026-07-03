#!/usr/bin/env bash
# Gearbox reset — restaura la marcha default al iniciar sesión (hook SessionStart)
mkdir -p "$HOME/.claude/gearbox"
cat > "$HOME/.claude/gearbox/state.json" <<'EOF'
{"gear":"G2","task":"ejecución","effort":"high"}
EOF
