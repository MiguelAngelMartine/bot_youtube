#!/bin/bash
# Jornada diaria automática de El Hoyformativo (servidor Linux).
#
#   jornada.sh lanza [AAAA-MM-DD]   -> lanza /edicion-diaria con Claude Code, sin nadie delante
#   jornada.sh vigila [AAAA-MM-DD]  -> a la hora de entrega, avisa por Telegram si el vídeo no está subido
#
# El cron corre en UTC; con --si-hora HH solo actúa si en Madrid son las HH
# (así se respeta el cambio de hora sin tocar el crontab).

set -u
RAIZ="$(cd "$(dirname "$0")" && pwd)"
cd "$RAIZ" || exit 1
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export TZ=Europe/Madrid

ACCION="${1:-lanza}"; shift || true
SI_HORA=""
if [ "${1:-}" = "--si-hora" ]; then SI_HORA="$2"; shift 2; fi
if [ -n "$SI_HORA" ] && [ "$(date +%H)" != "$SI_HORA" ]; then exit 0; fi

FECHA="${1:-$(date +%F)}"
DIA="dia/$FECHA"
PY="$RAIZ/.venv/bin/python"
mkdir -p "$DIA"
LOG="$DIA/jornada.log"

case "$ACCION" in
lanza)
    # Un solo lanzamiento a la vez.
    exec 9>"$RAIZ/.jornada.lock"
    if ! flock -n 9; then echo "[$(date +%FT%T)] Ya hay una jornada en marcha" >> "$LOG"; exit 0; fi
    if [ -f "$DIA/youtube.json" ]; then echo "[$(date +%FT%T)] $FECHA ya está subido; no se repite" >> "$LOG"; exit 0; fi

    echo "[$(date +%FT%T)] Empieza la jornada $FECHA ($(claude --version))" >> "$LOG"
    # Tope de 3 h para que una jornada atascada no se quede colgada.
    timeout 3h claude -p "/edicion-diaria $FECHA" --permission-mode auto --output-format text >> "$LOG" 2>&1
    COD=$?
    echo "[$(date +%FT%T)] Fin (código $COD)" >> "$LOG"
    if [ "$COD" -ne 0 ]; then
        if [ "$COD" -eq 124 ]; then MSG="la jornada pasó de 3 horas y se ha cortado"; else MSG="la jornada terminó con un error (código $COD)"; fi
        "$PY" notifica.py "$FECHA" --error "$MSG. Detalles en $LOG" >> "$LOG" 2>&1
    fi
    ;;
vigila)
    if [ ! -f "$DIA/youtube.json" ]; then
        ULTIMA="$(tail -n 1 "$DIA/parte_del_dia.md" 2>/dev/null | cut -c1-200)"
        "$PY" notifica.py "$FECHA" --error "son las $(date +%H:%M) y el vídeo de hoy aún no está subido. Última línea del parte: ${ULTIMA:-sin parte todavía}" >> "$LOG" 2>&1
    fi
    ;;
*)
    echo "Uso: $0 lanza|vigila [--si-hora HH] [AAAA-MM-DD]"; exit 2 ;;
esac
