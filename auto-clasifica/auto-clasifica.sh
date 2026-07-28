#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# auto-clasifica.sh — complemento OPCIONAL del Gearbox
#
# Resuelve una molestia concreta: la clasificación de marcha (G0-G5) depende de
# que el modelo se acuerde de correr set.sh/log.sh cada vez — y eso falla. Una
# sesión larga real mostró huecos de horas sin ningún registro (4 PRs mergeados
# a producción con cero clasificaciones, ver docs/community para el caso).
#
# Este hook es la "báscula automática": se dispara SOLO (sin que el modelo
# tenga que acordarse) cada vez que se ejecuta Bash/Edit/Write, y clasifica por
# palabras clave. Es más tosco que el juicio del modelo — no reemplaza la
# clasificación manual rica — pero nunca se le olvida hacerlo.
#
# NO ESTÁ ACTIVO POR DEFECTO. Ver auto-clasifica/README.md para instalarlo.
#
# Contrato de seguridad: SOLO LEE/REGISTRA. Nunca emite decision:"block" ni
# impide que la herramienta corra — si algo falla, sale en 0 en silencio.
# ─────────────────────────────────────────────────────────────────────────────

set -u
GB_DIR="$HOME/.claude/gearbox"
SET_SH="$GB_DIR/set.sh"
LOG_SH="$GB_DIR/log.sh"

input=$(cat 2>/dev/null || true)
[ -z "$input" ] && exit 0

event=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('hook_event_name',''))" 2>/dev/null || true)
[ "$event" != "PreToolUse" ] && exit 0

tool=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || true)
case "$tool" in
  Bash|Edit|MultiEdit|Write) ;;
  *) exit 0 ;;
esac

# Señal de texto a clasificar: comando de Bash, o ruta+contenido de Edit/Write
senal=$(printf '%s' "$input" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {}) or {}
tool = d.get('tool_name', '')
if tool == 'Bash':
    s = ti.get('command', '')
else:
    s = ti.get('file_path', '') + ' ' + (ti.get('content', '') or ti.get('new_string', ''))[:200]
print(s.replace(chr(9), ' ').replace(chr(10), ' ')[:400])
" 2>/dev/null)

senal_baja=$(printf '%s' "$senal" | tr '[:upper:]' '[:lower:]')

# Heurística por palabras clave — primer match gana, de más riesgoso a menos.
# Ajusta esta tabla a tu propio stack/vocabulario (ver README §Personalización).
gear=""
effort=""
case "$senal_baja" in
  *"rm -rf"*|*"drop table"*|*"truncate "*|*"reset --hard"*|*"push --force"*|*"delete from"*|*" -c gpgsign=false"*)
    gear="G5"; effort="high" ;;
  *"vercel "*"--prod"*|*"vercel deploy"*|*"railway up"*|*"api.cloudflare.com"*|*"dns_records"*|*"migration"*|*"apply_migration"*|*"stripe"*|*"webhook"*|*".env"*|*"domains add"*|*"domains rm"*)
    gear="G4"; effort="high" ;;
  *"npm run build"*|*"npm install"*|*"npm test"*|*"playwright"*|*"git push"*|*"supabase"*)
    gear="G3"; effort="medium" ;;
  *"git commit"*|*"git add"*|*"mkdir "*|*"mv "*|*"cp "*)
    gear="G2"; effort="medium" ;;
  *"ls "*|*"ls"*|*"cat "*|*"grep "*|*"find "*|*"git log"*|*"git diff"*|*"git status"*|*"head "*|*"tail "*|*"wc "*)
    gear="G0"; effort="low" ;;
  *)
    # Default por tipo de tool cuando ninguna palabra clave hizo match
    case "$tool" in
      Bash) gear="G2"; effort="medium" ;;
      *) gear="G3"; effort="medium" ;;
    esac
    ;;
esac

task="auto:${tool} — $(printf '%s' "$senal" | cut -c1-80)"

if [ -x "$SET_SH" ]; then
  "$SET_SH" "$gear" "$task" "$effort" >/dev/null 2>&1 || true
fi

if [ -x "$LOG_SH" ] || [ -f "$LOG_SH" ]; then
  bash "$LOG_SH" decision "$gear" "$gear" "$task" "" "" "carril-automatico" 2>/dev/null || true
fi

exit 0
