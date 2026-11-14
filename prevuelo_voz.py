"""CONTROL DE HUMANIDAD DE LA VOZ (14-nov-2026, petición del usuario): antes de montar el vídeo y tras escribir el guion, se
genera la locución y se revisa con DOS oídos, para que suene como leída por una persona de verdad:
  1) Whisper (objetivo): vuelve a transcribir el audio TTS; donde oye algo CLARAMENTE distinto del guion, marca esa palabra
     como poco clara o mal dicha (filtra números y variantes menores para no dar la lata).
  2) Gemini (subjetivo): escucha el audio con el guion delante y señala palabras o expresiones que NO suenan naturales, con
     una ALTERNATIVA parecida que suene bien.
Si hay problemas, el redactor (Opus) reescribe esas palabras por otras naturales y se repite, hasta que suene 100% natural;
solo entonces se monta el vídeo.
Uso:  from prevuelo_voz import revisa;  v = revisa(texto)  -> {"ok": bool, "problemas": [...], "oido": str}
CLI:  python prevuelo_voz.py <fecha>   -> revisa el largo y los Shorts, deja dia/<fecha>/calidad/prevuelo_voz.md
"""
from __future__ import annotations

import base64
import difflib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).parent
_NUM = set("cero un uno una dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciseis "
           "diecisiete dieciocho diecinueve veinte treinta cuarenta cincuenta sesenta setenta ochenta noventa cien ciento "
           "cientos mil millon millones por ciento y".split())


def _norm(s):
    return re.sub(r"[^0-9a-záéíóúñü ]", " ", (s or "").lower()).split()


def _audio(texto):
    """Genera la locución (voz estándar) SIN el alineado Whisper (no hace falta aquí) y devuelve (wav, mp3)."""
    import genera_video as V
    import voz
    tmp = Path(tempfile.mkdtemp(prefix="prevuelo_"))
    crudo = tmp / "crudo.mp3"
    voz._azure_mp3(texto, crudo)                           # síntesis directa (sin alinear), rápido
    wav = tmp / "v.wav"
    subprocess.run([V.FF, "-y", "-loglevel", "error", "-i", str(crudo), "-af", voz.RADIO, "-ar", "48000", str(wav)], check=True)
    mp3 = tmp / "v.mp3"
    subprocess.run([V.FF, "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "96k", str(mp3)], check=True)
    return wav, mp3


def _whisper(wav, texto):
    """Oído objetivo: lo que Whisper NO oye como está escrito (filtrando números y diferencias triviales)."""
    import voz
    segs, _ = voz._modelo().transcribe(str(wav), language="es", beam_size=1, vad_filter=False)
    oido = " ".join(s.text for s in segs).strip()
    a, b = _norm(texto), _norm(oido)
    fallos = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op not in ("replace", "delete"):
            continue
        dicho = [w for w in a[i1:i2] if w not in _NUM and len(w) >= 4 and not w.isdigit()]
        oyo = " ".join(b[j1:j2])
        for w in dicho:
            if w not in oyo and difflib.SequenceMatcher(None, w, oyo).ratio() < 0.6:   # oyó algo claramente distinto
                fallos.append({"texto": w, "detalle": f"Whisper oyó «{oyo[:40] or '(nada)'}»", "fuente": "whisper"})
    # sin repetir, como mucho 8
    vistos, out = set(), []
    for f in fallos:
        if f["texto"] not in vistos:
            vistos.add(f["texto"]); out.append(f)
    return oido, out[:8]


_PROMPT = (
    "Eres un oído experto en locución en español de España. Te doy un GUION y su LOCUCIÓN con una voz sintética (Tristán HD). "
    "ESCÚCHALA y juzga si suena NATURAL, como leída por una persona de verdad y no por una máquina. Señala SOLO las palabras o "
    "expresiones que suenen mal: forzadas, mal pronunciadas, cortadas, con vocales pegadas, acento raro o poco naturales. Para "
    "cada una propón una ALTERNATIVA parecida en significado que suene bien y natural con esta voz. Si todo suena natural, "
    "devuelve la lista vacía. Sé exigente pero no inventes problemas donde no los hay. Responde SOLO en JSON: "
    '{"natural": true/false, "problemas": [{"texto": "la palabra o expresión", "motivo": "por qué suena mal", '
    '"alternativa": "cómo decirlo"}]}.\n\nGUION:\n')


def _fmt(problemas, fuente):
    return [{"texto": p.get("texto", ""), "alternativa": p.get("alternativa", ""),
             "detalle": f"{p.get('motivo', '')} → «{p.get('alternativa', '')}»", "fuente": fuente}
            for p in problemas if isinstance(p, dict) and p.get("texto")]


def _gemini(mp3, texto):
    """Oído subjetivo con Gemini (gratis). Devuelve lista de problemas, o None si Gemini no responde (saturado)."""
    import gem
    b64 = base64.b64encode(Path(mp3).read_bytes()).decode()
    r = gem.pide([{"text": _PROMPT + texto}, {"inline_data": {"mime_type": "audio/mp3", "data": b64}}],
                 como_json=True, limite_s=90, modelos=["gemini-flash-latest", "gemini-2.0-flash"])
    if not isinstance(r, dict):
        return None                                        # no respondió: que lo coja OpenAI
    return _fmt(r.get("problemas", []), "gemini")


def _openai(mp3, texto):
    """Oído subjetivo con OpenAI (de pago, fiable; respaldo de Gemini). Devuelve lista de problemas, o None si falla."""
    import requests
    key = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines()
               if "=" in l and not l.strip().startswith("#")).get("OPENAI_API_KEY", "").strip().strip('"')
    if not key:
        return None
    b64 = base64.b64encode(Path(mp3).read_bytes()).decode()
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", timeout=120,
                          headers={"Authorization": f"Bearer {key}"},
                          json={"model": "gpt-4o-audio-preview", "modalities": ["text"],
                                "response_format": {"type": "json_object"},
                                "messages": [{"role": "user", "content": [
                                    {"type": "text", "text": _PROMPT + texto},
                                    {"type": "input_audio", "input_audio": {"data": b64, "format": "mp3"}}]}]})
        if not r.ok:
            print(f"  (OpenAI oído no responde: {r.status_code} {r.text[:80]})", file=sys.stderr)
            return None
        txt = r.json()["choices"][0]["message"]["content"]
        return _fmt(json.loads(txt).get("problemas", []), "openai")
    except Exception as e:
        print(f"  (OpenAI oído falla: {type(e).__name__})", file=sys.stderr)
        return None


VETADAS = RAIZ / "archivo" / "palabras_vetadas.json"


def vetadas():
    """Lista negra de palabras/expresiones que la voz no dice bien (para que el redactor NO las use)."""
    try:
        return json.loads(VETADAS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def veta(palabra, alternativa="", motivo=""):
    """Añade una palabra/expresión descartada a la lista negra (sin repetir)."""
    lista = vetadas()
    pl = (palabra or "").strip().lower()
    if not pl or any((e.get("palabra", "").lower() == pl) for e in lista):
        return
    import time as _t
    lista.append({"palabra": palabra.strip(), "alternativa": alternativa.strip(), "motivo": motivo.strip(),
                  "fecha": _t.strftime("%Y-%m-%d")})
    VETADAS.parent.mkdir(parents=True, exist_ok=True)
    VETADAS.write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")


def revisa(texto, auto_veta=False):
    """Genera la locución y la revisa. Oído subjetivo: Gemini (gratis) y, si no responde, OpenAI (fiable). Oído objetivo:
    Whisper. Devuelve {ok, problemas, oido}. Con auto_veta, añade a la lista negra lo que marque el oído subjetivo."""
    wav, mp3 = _audio(texto)
    sub = None
    try:
        sub = _gemini(mp3, texto)                          # 1º Gemini (gratis)
    except Exception as e:
        print(f"  (Gemini oído falla: {type(e).__name__})", file=sys.stderr)
    oido_usado = "gemini"
    if sub is None:                                        # 2º OpenAI (saturó Gemini)
        sub = _openai(mp3, texto)
        oido_usado = "openai"
    sub = sub or []
    oido, wf = _whisper(wav, texto)                        # 3º Whisper (objetivo), siempre
    if auto_veta:
        for p in sub:
            veta(p["texto"], p.get("alternativa", ""), f"no suena natural ({p['fuente']})")
    return {"ok": not (sub + wf), "problemas": sub + wf, "oido_subjetivo": oido_usado, "oido": oido}


def _piezas(fecha):
    dia = RAIZ / "dia" / fecha
    piezas = []
    ep = dia / "episodio.json"
    if ep.exists():
        G = json.loads(ep.read_text(encoding="utf-8"))
        for s in G.get("secciones", []):
            txt = " ".join(p.get("di", "") for p in s.get("pasos", []))
            if txt.strip():
                piezas.append((f"largo · {s.get('titulo', '')[:40]}", txt))
    for f in sorted((dia / "shorts").glob("short_*.json")) if (dia / "shorts").exists() else []:
        try:
            S = json.loads(f.read_text(encoding="utf-8"))
            if S.get("voz"):
                piezas.append((f"Short {re.sub(chr(92)+'D', '', f.stem)}", S["voz"]))
        except (OSError, ValueError):
            pass
    return piezas


def main(fecha):
    dia = RAIZ / "dia" / fecha
    (dia / "calidad").mkdir(parents=True, exist_ok=True)
    md = [f"# Control de humanidad de la voz · {fecha}", ""]
    total = 0
    for nombre, txt in _piezas(fecha):
        v = revisa(txt)
        total += len(v["problemas"])
        md.append(f"## {nombre}: {'✅ natural' if v['ok'] else '⚠️ REVISAR'}")
        for p in v["problemas"]:
            md.append(f"- «{p['texto']}» — {p['detalle']} _({p['fuente']})_")
        md.append("")
        print(f"{nombre}: {'OK' if v['ok'] else str(len(v['problemas'])) + ' problemas'}", flush=True)
    (dia / "calidad" / "prevuelo_voz.md").write_text("\n".join(md), encoding="utf-8")
    print(f"prevuelo_voz.md listo · {total} cosas a revisar")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
