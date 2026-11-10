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

    # Hasta 3 intentos: si se agota el límite de uso del plan de Claude (se comparte con las sesiones del día),
    # espera a que se renueve y retoma (la skill salta las fases ya hechas). Nunca empieza un intento después de las 21:00.
    # Aviso por Telegram de que empieza el vídeo del día (petición del usuario del 4-nov-2026)
    "$PY" notifica.py "$FECHA" --aviso "empieza la jornada: me pongo con el vídeo de hoy. Te aviso cuando esté subido (unas 2 h)." >> "$LOG" 2>&1
    # 10-nov-2026 (petición del usuario): cada fase que se completa (cada línea nueva del parte del día) se avisa por
    # Telegram, para saber que todo sigue adelante. Lo hace este vigía, sin gastar tokens; un mensaje por minuto como mucho.
    PARTE="$DIA/parte_del_dia.md"
    (
        N=$( [ -f "$PARTE" ] && wc -l < "$PARTE" || echo 0 )
        while true; do
            sleep 60
            [ -f "$PARTE" ] || continue
            T=$(wc -l < "$PARTE")
            if [ "$T" -gt "$N" ]; then
                NUEVAS=$(tail -n +"$((N + 1))" "$PARTE" | head -n "$((T - N))" | sed 's/^/✅ /')
                "$PY" notifica.py "$FECHA" --aviso "fase completada:
$NUEVAS" >> "$LOG" 2>&1
                N=$T
            fi
        done
    ) &
    VIGIA=$!
    trap 'kill $VIGIA 2>/dev/null' EXIT
    # 10-nov-2026 (8 % del consumo semanal como máximo): primero el coordinador en Python, con Gemini haciendo cada puesto
    # (jornada.py). Solo si no termina, entra el coordinador de Claude de siempre, que retoma donde se quedó.
    echo "[$(date +%FT%T)] Coordinador en Python (Gemini)" >> "$LOG"
    timeout 4h "$PY" -u jornada.py "$FECHA" >> "$DIA/jornada_py.log" 2>&1
    COD=$?
    echo "[$(date +%FT%T)] jornada.py terminó con código $COD" >> "$LOG"
    for INTENTO in 1 2 3; do
        if [ -f "$DIA/youtube.json" ] && [ -f "$DIA/shorts/youtube.json" ]; then COD=0; break; fi
        echo "[$(date +%FT%T)] Empieza la jornada $FECHA, intento $INTENTO ($(claude --version))" >> "$LOG"
        ANTES=$(wc -l < "$LOG")
        # Tope de 3 h para que una jornada atascada no se quede colgada.
        RES="$DIA/claude_resultado_$INTENTO.json"
        timeout 3h claude -p "/edicion-diaria $FECHA" --model sonnet --permission-mode auto --output-format json > "$RES" 2>> "$LOG"
        COD=$?
        # el texto final al log y el consumo (coste equivalente y tokens por modelo, agentes incluidos) a archivo/consumo.tsv
        "$PY" - "$RES" "$FECHA" "$INTENTO" >> "$LOG" 2>&1 <<'PYEOF'
import json, sys
from pathlib import Path
try:
    d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    print("(sin resultado en json)")
    sys.exit()
print(d.get("result", ""))
u = d.get("modelUsage") or {}
det = "; ".join(f"{m}: {v.get('inputTokens', 0) + v.get('cacheReadInputTokens', 0) + v.get('cacheCreationInputTokens', 0)} entrada "
                f"({v.get('cacheReadInputTokens', 0)} de caché), {v.get('outputTokens', 0)} salida" for m, v in u.items())
linea = f"{d.get('total_cost_usd', 0):.2f} $ equivalentes, {d.get('num_turns', '?')} turnos; {det}"
print("CONSUMO:", linea)
f = Path("archivo/consumo.tsv")
nuevo = not f.exists()
with f.open("a", encoding="utf-8") as fh:
    if nuevo:
        fh.write("fecha\tintento\tcoste_equivalente_usd\tturnos\tdetalle\n")
    fh.write(f"{sys.argv[2]}\t{sys.argv[3]}\t{d.get('total_cost_usd', 0):.2f}\t{d.get('num_turns', '')}\t{det}\n")
PYEOF
        echo "[$(date +%FT%T)] Fin (código $COD)" >> "$LOG"
        if [ "$COD" -eq 0 ]; then
            [ -f "$DIA/youtube.json" ] && break
            # Claude terminó sin subir el vídeo (el 3-nov dejó un montaje corriendo en segundo plano y cerró su turno):
            # se espera a que acabe cualquier montaje en marcha y se retoma la jornada donde se quedó.
            [ "$INTENTO" -eq 3 ] || [ "$(date +%H)" -ge 21 ] && { COD=3; break; }
            echo "[$(date +%FT%T)] Sin vídeo subido: espera a que termine el montaje y retoma" >> "$LOG"
            while pgrep -f "[p]ython.*largo.py $FECHA" > /dev/null; do sleep 30; done
            continue
        fi
        RESET="$(tail -n +"$ANTES" "$LOG" | grep -io 'limit.*resets [0-9:]*[ap]m' | grep -io '[0-9:]*[ap]m' | tail -n 1)"
        [ -z "$RESET" ] && break                              # otro error: aviso normal
        OBJ=$(date -d "$RESET" +%s 2>/dev/null) || break
        AHORA=$(date +%s)
        [ "$OBJ" -le "$AHORA" ] && OBJ=$((AHORA + 60))
        OBJ=$((OBJ + 120))                                      # 2 min de margen tras la renovación
        if [ "$INTENTO" -eq 3 ] || [ "$(date -d "@$OBJ" +%H)" -ge 21 ]; then break; fi
        "$PY" notifica.py "$FECHA" --error "la jornada se ha pausado porque se agotó el límite de uso del plan de Claude. Se reanuda sola a las $(date -d "@$OBJ" +%H:%M), donde se quedó." >> "$LOG" 2>&1
        echo "[$(date +%FT%T)] Límite de uso: espera hasta $(date -d "@$OBJ" +%H:%M)" >> "$LOG"
        sleep $((OBJ - $(date +%s)))
    done
    # 10-nov-2026: si la jornada se cortó (tope de 3 h, límite de uso) con el vídeo subido pero sin Shorts, se hacen aquí,
    # con los programas (sin agentes ni tokens).
    if [ -f "$DIA/youtube.json" ] && [ ! -f "$DIA/shorts/youtube.json" ]; then
        echo "[$(date +%FT%T)] Faltan los Shorts: se hacen sin agente" >> "$LOG"
        "$PY" notifica.py "$FECHA" --aviso "la jornada se cortó tras subir el vídeo: hago los Shorts sin agente" >> "$LOG" 2>&1
        "$PY" -u shorts_dia.py "$FECHA" >> "$DIA/shorts.log" 2>&1 && "$PY" subir.py "$FECHA" shorts >> "$LOG" 2>&1
        echo "$(date +%H:%M) Shorts hechos y subidos por jornada.sh (sin agente)" >> "$PARTE"
    fi
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
