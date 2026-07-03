#!/usr/bin/env bash
# ⚙ Gearbox — Instalador de 1 línea
# curl -fsSL https://raw.githubusercontent.com/GabrielMarquez01/gearbox-skill/master/install.sh | bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/GabrielMarquez01/gearbox-skill/master"
CLAUDE_DIR="$HOME/.claude"
GB_DIR="$CLAUDE_DIR/gearbox"
SKILL_DIR="$CLAUDE_DIR/skills/gearbox"

echo "⚙ Instalando Gearbox..."

# 1. Carpetas
mkdir -p "$GB_DIR" "$SKILL_DIR"

# 2. Archivos (desde el repo si corre vía curl; locales si corre desde el clone)
fetch() { # $1=archivo $2=destino
  if [ -f "$(dirname "$0")/$1" ] 2>/dev/null && [ "$0" != "bash" ]; then
    cp "$(dirname "$0")/$1" "$2"
  else
    curl -fsSL "$REPO_RAW/$1" -o "$2"
  fi
}
fetch "SKILL.md"      "$SKILL_DIR/SKILL.md"
fetch "README.md"     "$SKILL_DIR/README.md"
fetch "statusline.sh" "$GB_DIR/statusline.sh"
fetch "reset.sh"      "$GB_DIR/reset.sh"
chmod +x "$GB_DIR/statusline.sh" "$GB_DIR/reset.sh"
bash "$GB_DIR/reset.sh"
echo "  ✅ Skill y scripts instalados"

# 3. Merge de settings.json (backup primero; requiere python3, presente en Mac/Linux/WSL)
SETTINGS="$CLAUDE_DIR/settings.json"
[ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.backup-gearbox"
python3 - "$SETTINGS" <<'PYEOF'
import json, os, sys
path = sys.argv[1]
data = {}
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)

home = os.path.expanduser("~")
data["statusLine"] = {
    "type": "command",
    "command": f"{home}/.claude/gearbox/statusline.sh",
    "padding": 0,
}
hooks = data.setdefault("hooks", {})
ss = hooks.setdefault("SessionStart", [])
cmd = f"{home}/.claude/gearbox/reset.sh"
if not any(cmd in json.dumps(e) for e in ss):
    ss.append({"hooks": [{"type": "command", "command": cmd, "async": True}]})

# opusplan solo si no hay modelo configurado (respeta tu elección previa)
data.setdefault("model", "opusplan")

with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("  ✅ settings.json actualizado (backup en settings.json.backup-gearbox)")
PYEOF

# 4. Directiva en CLAUDE.md global (idempotente)
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
if ! grep -q "skills/gearbox/SKILL.md" "$CLAUDE_MD" 2>/dev/null; then
  cat >> "$CLAUDE_MD" <<'EOF'

## Gearbox — Selector de Modelo y Esfuerzo (SIEMPRE ACTIVO)

En TODA sesión, aplicar el protocolo de `~/.claude/skills/gearbox/SKILL.md`:
clasificar cada tarea en una marcha (G0-G5); si la marcha recomendada difiere de la
configuración actual, PAUSA y emitir el bloque ⚙ GEARBOX con comando exacto, razón
en 1 frase y economía; delegar rutina a Haiku; actualizar ~/.claude/gearbox/state.json
y registrar en log.jsonl. Sesión Fable (G5) siempre con gate de costo.
EOF
  echo "  ✅ Directiva agregada a ~/.claude/CLAUDE.md"
else
  echo "  ✅ Directiva ya existía en CLAUDE.md"
fi

echo ""
echo "⚙ Gearbox instalado. Reinicia Claude Code y verás la marcha en azul bajo la terminal:"
echo "   ⚙ G2 · <tu modelo> · high · ejecución"
echo ""
echo "   Desinstalar: rm -rf ~/.claude/gearbox ~/.claude/skills/gearbox"
echo "                + restaurar ~/.claude/settings.json.backup-gearbox"
