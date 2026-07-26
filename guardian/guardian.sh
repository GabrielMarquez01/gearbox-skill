#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# guardian.sh — complemento OPCIONAL del Gearbox
#
# Resuelve dos molestias de trabajar con sesiones largas de Claude Code:
#
#   1. La sesión se cae (se cierra la terminal, se va el internet, truena algo)
#      → la reabre con su contexto intacto cuando vuelve la conexión.
#
#   2. Se agota el cupo de la ventana de uso
#      → anota dónde quedó, y cuando la ventana se renueva te avisa para que TÚ
#        decidas si continuar. No reanuda solo: reanudar sin supervisión gasta
#        cupo en trabajo que quizá ya no quieres, y obliga a saltarse los
#        permisos. El "play" lo das tú, desde donde estés.
#
# NO ESTÁ ACTIVO POR DEFECTO. Ver guardian/README.md para encenderlo.
#
# Requisitos: bash, curl, cron. Para reabrir ventanas: WSL + Windows Terminal
# (en Linux/macOS el guardián avisa en vez de reabrir — ver README).
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

DIR="${GUARDIAN_DIR:-$HOME/.claude/guardian}"
CONF="$DIR/guardian.conf"
ESTADO="$DIR/estado"
LOG="$DIR/guardian.log"
USAGE="${GUARDIAN_USAGE:-$HOME/.claude/gearbox/usage.json}"
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}"

mkdir -p "$DIR" "$ESTADO"
# shellcheck disable=SC1090
[ -f "$CONF" ] && . "$CONF"

UMBRAL_CUPO="${UMBRAL_CUPO:-95}"   # % de la ventana a partir del cual se pausa
COOLDOWN="${COOLDOWN:-600}"        # segundos mínimos entre intentos de revivir

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG"; }

# ── aviso: se elige UN canal en guardian.conf ───────────────────────────────
avisar() {
  local msg="$1"
  case "${CANAL_AVISO:-escritorio}" in
    telegram)
      curl -s -m 15 -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT}" --data-urlencode "text=$msg" >/dev/null 2>&1 \
        && { log "aviso enviado (telegram)"; return 0; } ;;
    comando)
      # AVISO_COMANDO recibe el mensaje como $1 — webhook, correo, lo que uses
      [ -n "${AVISO_COMANDO:-}" ] && "$AVISO_COMANDO" "$msg" >/dev/null 2>&1 \
        && { log "aviso enviado (comando propio)"; return 0; } ;;
    escritorio)
      command -v notify-send >/dev/null && notify-send "Guardián de sesión" "$msg" 2>/dev/null \
        && { log "aviso en escritorio"; return 0; }
      command -v powershell.exe >/dev/null && powershell.exe -NoProfile -Command \
        "[void][Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');
         [Windows.Forms.MessageBox]::Show('$msg','Guardián de sesión')" >/dev/null 2>&1 & ;;
  esac
  log "AVISO (sin canal): $msg"
}

# ── lectura del cupo (lo escribe el statusline del Gearbox) ─────────────────
usage_num() { [ -s "$USAGE" ] || return 1; sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p" "$USAGE" | head -1; }
usage_sid() { [ -s "$USAGE" ] || return 1; sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$USAGE" | head -1; }

hay_internet() { curl -sf -m 8 -o /dev/null https://api.anthropic.com/ 2>/dev/null; }

sesion_viva() {
  pgrep -x claude >/dev/null 2>&1 && return 0
  # -f también hace match con el propio guardián y con la ventana que acabamos
  # de lanzar (llevan la ruta de claude en su línea de comandos): se descartan.
  local p cmd
  for p in $(pgrep -f "$CLAUDE_BIN" 2>/dev/null); do
    [ "$p" = "$$" ] && continue
    cmd=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
    case "$cmd" in
      *wt.exe*|*wsl.exe*|*guardian.sh*) continue ;;
      *) return 0 ;;
    esac
  done
  return 1
}

# ── abrir una ventana nueva ─────────────────────────────────────────────────
# cron corre con un PATH mínimo y sin las variables de WSL: no encuentra wt.exe
# ni tiene el socket de interoperabilidad. Se resuelven a mano en vez de confiar
# en el entorno heredado (era la causa de "no se pudo abrir la ventana").

buscar_wt() {
  command -v wt.exe 2>/dev/null && return 0
  local ruta
  for ruta in /mnt/c/Users/*/AppData/Local/Microsoft/WindowsApps/wt.exe; do
    [ -x "$ruta" ] && { printf '%s' "$ruta"; return 0; }
  done
  return 1
}

asegurar_interop() {
  # Sin WSL_INTEROP los .exe pueden negarse a arrancar. Los sockets viven en
  # /run/WSL; se prueba cada uno con un comando barato hasta dar con el vivo.
  [ -n "${WSL_INTEROP:-}" ] && [ -e "${WSL_INTEROP}" ] && return 0
  [ -d /run/WSL ] || return 1
  local sock
  for sock in $(ls -t /run/WSL/*_interop 2>/dev/null); do
    if WSL_INTEROP="$sock" /mnt/c/Windows/System32/cmd.exe /c exit >/dev/null 2>&1; then
      export WSL_INTEROP="$sock"; return 0
    fi
  done
  return 1
}

abrir_sesion() { # $1 = session_id, $2 = título de la ventana
  local sid="$1" titulo="${2:-Claude — sesión recuperada}" wt i
  asegurar_interop
  wt=$(buscar_wt) || { log "sin Windows Terminal: no puedo abrir la ventana"; return 1; }
  # Desde una ruta UNC (\\wsl.localhost\...) los .exe arrancan con advertencia y
  # a veces fallan; se lanza parado en una ruta de Windows.
  # OJO: Windows Terminal usa ';' como separador de comandos. El comando que se
  # le pase NO puede llevar punto y coma o lo parte en dos.
  ( cd /mnt/c 2>/dev/null || cd /
    "$wt" -w 0 nt --title "$titulo" \
      wsl.exe -- bash -lc "cd ~ && '$CLAUDE_BIN' --resume '$sid'" ) >/dev/null 2>&1 &
  # Windows Terminal + WSL + claude en frío tardan bastante más de 4 s.
  for i in 1 2 3 4 5 6; do sleep 3; sesion_viva && return 0; done
  return 1
}

# ── 1. la sesión murió ──────────────────────────────────────────────────────
vigilar_sesion() {
  sesion_viva && return 0
  hay_internet || { log "sesión caída, sin internet — espero"; return 0; }

  local sid ahora previo
  sid=$(cat "$ESTADO/session_id" 2>/dev/null || usage_sid)
  [ -z "$sid" ] && return 0

  ahora=$(date +%s); previo=$(cat "$ESTADO/ultimo_intento" 2>/dev/null || echo 0)
  [ $((ahora - previo)) -lt "$COOLDOWN" ] && return 0
  echo "$ahora" > "$ESTADO/ultimo_intento"

  log "sesión caída + internet OK -> reabriendo $sid"
  if abrir_sesion "$sid" "Claude — sesión recuperada"; then
    avisar "🔄 Se cayó la sesión y ya la reabrí con todo su contexto. Puedes seguir donde te quedaste."
  else
    avisar "⚠️ Tu sesión se cayó y no pude reabrirla sola. En la terminal:  claude --resume $sid"
  fi
}

# ── 2. se agotó el cupo ─────────────────────────────────────────────────────
vigilar_cupo() {
  local pct reset ahora restante
  pct=$(usage_num five_hour) || return 0
  [ -z "$pct" ] && return 0
  reset=$(usage_num reset_five_hour); ahora=$(date +%s)

  if [ "$pct" -ge "$UMBRAL_CUPO" ] && [ ! -f "$ESTADO/pausa_cupo" ]; then
    { echo "SID='$(usage_sid)'"; echo "RESET='${reset:-0}'"; echo "DESDE='$(date '+%H:%M')'"; } > "$ESTADO/pausa_cupo"
    restante=$(( (${reset:-0} - ahora) / 60 ))
    log "cupo agotado ($pct%)"
    avisar "⏸️ Se agotó el cupo de esta ventana ($pct%). Tu tarea queda en pausa. Se renueva en ~${restante} min y te aviso."
    return 0
  fi

  if [ -f "$ESTADO/pausa_cupo" ]; then
    # shellcheck disable=SC1090
    . "$ESTADO/pausa_cupo"
    if [ "$ahora" -ge "${RESET:-0}" ] || [ "$pct" -lt 50 ]; then
      rm -f "$ESTADO/pausa_cupo"
      echo "${SID:-}" > "$ESTADO/pendiente"
      log "cupo renovado — esperando tu visto bueno"
      avisar "▶️ Ya se renovó tu cupo (al $pct%). La tarea quedó pausada desde las ${DESDE:-?}. Para retomarla:  guardian.sh continuar"
    fi
  fi
}

continuar() {
  local sid="${1:-$(cat "$ESTADO/pendiente" 2>/dev/null || usage_sid)}"
  [ -z "$sid" ] && { echo "✗ no hay tarea pausada que retomar"; return 1; }
  log "retomando $sid por orden del usuario"
  if abrir_sesion "$sid" "Claude — tarea reanudada"; then
    rm -f "$ESTADO/pendiente"; echo "✓ tarea retomada"; avisar "▶️ Retomé la tarea donde se quedó."
  else
    echo "✗ no pude abrirla — en la terminal:  claude --resume $sid"
  fi
}

case "${1:-check}" in
  registrar) echo "${2:-$(usage_sid)}" > "$ESTADO/session_id"; echo "✓ vigilando $(cat "$ESTADO/session_id")" ;;
  check)     [ -f "$ESTADO/pausado" ] && exit 0; vigilar_cupo; vigilar_sesion ;;
  continuar) continuar "${2:-}" ;;
  cupo)
    echo "  cupo 5 h usado : $(usage_num five_hour)%"
    r=$(usage_num reset_five_hour)
    [ -n "$r" ] && [ "$r" != "null" ] && echo "  se renueva     : $(date -d "@$r" '+%H:%M' 2>/dev/null) (en $(( (r - $(date +%s)) / 60 )) min)"
    echo "  cupo 7 días    : $(usage_num seven_day)%"
    echo -n "  estado         : "; [ -f "$ESTADO/pausa_cupo" ] && echo "EN PAUSA por cupo" || echo "operando" ;;
  estado)
    echo "  sesión vigilada : $(cat "$ESTADO/session_id" 2>/dev/null || echo '—')"
    echo -n "  sesión ahora    : "; sesion_viva && echo "viva" || echo "caída"
    echo -n "  internet        : "; hay_internet && echo "ok" || echo "sin conexión"
    echo "  canal de aviso  : ${CANAL_AVISO:-escritorio}"
    echo -n "  cron            : "; crontab -l 2>/dev/null | grep -q guardian.sh && echo "instalado" || echo "no instalado"
    [ -f "$LOG" ] && { echo "  --- log ---"; tail -5 "$LOG" | sed 's/^/  /'; } ;;
  off) touch "$ESTADO/pausado"; echo "✓ guardián pausado" ;;
  on)  rm -f "$ESTADO/pausado"; echo "✓ guardián activo" ;;
  *)   sed -n '3,20p' "$0" ;;
esac
