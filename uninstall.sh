#!/usr/bin/env bash
# Desinstalador seguro: retira integración y archiva datos salvo --purge-data.
set -euo pipefail
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
GB_DIR="$CLAUDE_DIR/gearbox"
SKILL_DIR="$CLAUDE_DIR/skills/gearbox"
BACKUP_DIR="$CLAUDE_DIR/backups/gearbox"
PURGE=false
[ "${1:-}" = "--purge-data" ] && PURGE=true

SETTINGS="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS" ]; then
python3 - "$SETTINGS" "$GB_DIR" <<'PY'
import json, os, sys
from pathlib import Path
path = Path(sys.argv[1]); gb = str(Path(sys.argv[2]))
data = json.loads(path.read_text(encoding="utf-8"))
status = data.get("statusLine")
if status and "gearbox" in json.dumps(status).lower():
    data.pop("statusLine", None)
hooks = data.get("hooks", {})
for event in ("SessionStart", "UserPromptSubmit"):
    entries = hooks.get(event, [])
    kept = [e for e in entries if gb not in json.dumps(e, ensure_ascii=False)]
    if kept:
        hooks[event] = kept
    else:
        hooks.pop(event, None)
if not hooks:
    data.pop("hooks", None)
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
os.replace(tmp, path)
PY
fi

CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
python3 - "$CLAUDE_MD" <<'PY'
import re, sys
from pathlib import Path
path = Path(sys.argv[1]); text = path.read_text(encoding="utf-8")
text = re.sub(r"\n?<!-- GEARBOX:START -->.*?<!-- GEARBOX:END -->\n?", "\n", text, flags=re.S)
path.write_text(text.rstrip() + "\n", encoding="utf-8")
PY
fi

rm -rf "$SKILL_DIR"
if $PURGE; then
  rm -rf "$GB_DIR"
  echo "⚙ Gearbox desinstalado y datos eliminados."
else
  mkdir -p "$BACKUP_DIR"
  if [ -d "$GB_DIR" ]; then
    archive="$BACKUP_DIR/uninstalled-$(date -u +%Y%m%dT%H%M%SZ)"
    mv "$GB_DIR" "$archive"
    echo "⚙ Gearbox desinstalado. Datos archivados en: $archive"
  else
    echo "⚙ Gearbox desinstalado."
  fi
fi
