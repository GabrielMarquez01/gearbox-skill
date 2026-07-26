#!/usr/bin/env bash
# ⚙ Gearbox V3 Preview — installer (backward-compatible, observe mode by default)
set -euo pipefail

GEARBOX_REF="${GEARBOX_REF:-master}"
REPO_RAW="https://raw.githubusercontent.com/GabrielMarquez01/gearbox-skill/${GEARBOX_REF}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
GB_DIR="$CLAUDE_DIR/gearbox"
SKILL_DIR="$CLAUDE_DIR/skills/gearbox"
BACKUP_DIR="$CLAUDE_DIR/backups/gearbox"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

command -v python3 >/dev/null 2>&1 || {
  echo "❌ Gearbox requiere Python 3.9 o posterior." >&2
  exit 1
}
python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("Gearbox requiere Python 3.9 o posterior")
PY

echo "⚙ Instalando Gearbox V3 Preview (${GEARBOX_REF})..."
mkdir -p "$GB_DIR" "$SKILL_DIR" "$BACKUP_DIR"

fetch() { # $1=source $2=destination
  local src="$1" dest="$2"
  if [ -f "$(dirname "$0")/$src" ] 2>/dev/null && [ "$0" != "bash" ]; then
    cp "$(dirname "$0")/$src" "$dest"
  else
    curl -fsSL "$REPO_RAW/$src" -o "$dest"
  fi
}

# Backup inmutable de la configuración previa + snapshots fechados para upgrades.
SETTINGS="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS" ]; then
  [ -f "$BACKUP_DIR/settings.pre-gearbox.json" ] || cp "$SETTINGS" "$BACKUP_DIR/settings.pre-gearbox.json"
  cp "$SETTINGS" "$BACKUP_DIR/settings.${TIMESTAMP}.json"
fi

# Archivos principales. El núcleo Python se instala antes de los wrappers.
fetch "gearbox.py"    "$GB_DIR/gearbox.py"
fetch "statusline.sh" "$GB_DIR/statusline.sh"
fetch "reset.sh"      "$GB_DIR/reset.sh"
fetch "set.sh"        "$GB_DIR/set.sh"
fetch "log.sh"        "$GB_DIR/log.sh"
fetch "uninstall.sh"  "$GB_DIR/uninstall.sh"
fetch "SKILL.md"      "$SKILL_DIR/SKILL.md"
fetch "README.md"     "$SKILL_DIR/README.md"
fetch "docs/PREDICTIVE-LOOP.md" "$SKILL_DIR/PREDICTIVE-LOOP.md"
chmod +x "$GB_DIR/gearbox.py" "$GB_DIR/statusline.sh" "$GB_DIR/reset.sh" \
  "$GB_DIR/set.sh" "$GB_DIR/log.sh" "$GB_DIR/uninstall.sh"

# No sobrescribir configuración local de precios/política.
if [ ! -f "$GB_DIR/prices.json" ]; then
  fetch "prices.json" "$GB_DIR/prices.json"
  echo "  ✅ prices.json instalado"
else
  echo "  ✅ prices.json conservado"
fi
if [ ! -f "$GB_DIR/policy.json" ]; then
  fetch "policy.json" "$GB_DIR/policy.json"
  echo "  ✅ policy.json instalado en modo observe"
else
  echo "  ✅ policy.json conservado"
fi

# Merge seguro de settings.json. No reemplaza un statusLine ajeno.
python3 - "$SETTINGS" "$GB_DIR" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
gb_dir = Path(sys.argv[2])
data = {}
if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"settings.json no es JSON válido: {exc}")

status_cmd = str(gb_dir / "statusline.sh")
existing_status = data.get("statusLine")
if not existing_status or "gearbox" in json.dumps(existing_status).lower():
    data["statusLine"] = {"type": "command", "command": status_cmd, "padding": 0}
    print("  ✅ statusLine Gearbox configurado")
else:
    print("  ⚠ statusLine existente conservado; Gearbox sigue activo sin reemplazarlo")

hooks = data.setdefault("hooks", {})

def add_hook(event: str, command: str, *, async_mode=None, timeout=None):
    entries = hooks.setdefault(event, [])
    if any(command in json.dumps(entry, ensure_ascii=False) for entry in entries):
        return False
    hook = {"type": "command", "command": command}
    if async_mode is not None:
        hook["async"] = async_mode
    if timeout is not None:
        hook["timeout"] = timeout
    entries.append({"hooks": [hook]})
    return True

reset_cmd = str(gb_dir / "reset.sh")
hook_cmd = f"python3 {gb_dir / 'gearbox.py'} hook"
add_hook("SessionStart", reset_cmd, async_mode=True)
add_hook("UserPromptSubmit", hook_cmd, timeout=5)

# Compatibilidad con la experiencia anterior: sólo define default si el usuario no tiene uno.
data.setdefault("model", "opusplan")

path.parent.mkdir(parents=True, exist_ok=True)
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
os.replace(tmp, path)
print("  ✅ hooks SessionStart + UserPromptSubmit configurados")
PY

# Directiva global versionada. Sustituye el bloque legado conocido y evita duplicados.
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
touch "$CLAUDE_MD"
python3 - "$CLAUDE_MD" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
start = "<!-- GEARBOX:START -->"
end = "<!-- GEARBOX:END -->"
block = f'''{start}
## Gearbox — Gobierno predictivo de modelo y esfuerzo

Aplicar `~/.claude/skills/gearbox/SKILL.md`. Gearbox V3 opera por defecto en modo
`observe`: el hook `UserPromptSubmit` clasifica y registra cada tarea, añade una
predicción explicable y NO cambia automáticamente el modelo. Mantener compatibilidad
con los comandos `set.sh`, `reset.sh` y `log.sh`; las decisiones de calibración viven
en `~/.claude/gearbox/decisions.jsonl` y la telemetría predictiva en `gearbox.db`.
Para seguridad, pagos, producción, datos personales, legal, eliminación o acciones
irreversibles, mantener gate humano. Tratar la probabilidad de éxito como estimación,
nunca como garantía.
{end}'''

# Quitar bloques Gearbox gestionados por versiones anteriores.
text = re.sub(r"\n?<!-- GEARBOX:START -->.*?<!-- GEARBOX:END -->\n?", "\n", text, flags=re.S)
text = re.sub(
    r"\n?## Gearbox — Selector de Modelo y Esfuerzo \(SIEMPRE ACTIVO\).*?(?=\n## |\Z)",
    "\n",
    text,
    flags=re.S,
)
text = text.rstrip() + "\n\n" + block + "\n"
path.write_text(text, encoding="utf-8")
print("  ✅ directiva global Gearbox V3 actualizada")
PY

"$GB_DIR/reset.sh"
"$GB_DIR/gearbox.py" doctor

echo ""
echo "⚙ Gearbox V3 Preview instalado en modo seguro: observe"
echo "   Predice y registra; NO cambia el modelo automáticamente."
echo ""
echo "   Comandos útiles:"
echo "   $GB_DIR/gearbox.py classify --prompt 'Audita este repositorio'"
echo "   $GB_DIR/gearbox.py history --limit 10"
echo "   $GB_DIR/gearbox.py feedback <task_id> accepted"
echo "   $GB_DIR/gearbox.py doctor"
echo "   $GB_DIR/uninstall.sh"
if [ "$GEARBOX_REF" = "master" ]; then
  echo ""
  echo "   ⚠ Instalación desde master. Para producción, fija GEARBOX_REF a una release."
fi
