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
21-nov-2026 (el usuario: «100 % gratuito», y que la voz suene lo más humana posible): el oído principal es voz_calidad.py
(local: fonemas wav2vec2 + espeak, Whisper large-v3 desde el 28-nov-2026, ritmo, entonación y uniones entre frases) sobre la locución por tramos tal como sale en el
vídeo. Gemini queda como oído extra cuando tiene cuota; OpenAI (de pago) ya no se usa.
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


def _audio_tramos(texto):
    """21-nov-2026: la locución TAL COMO SALE EN EL VÍDEO (formato presentador: un tramo por cita, con sus pausas medidas).
    Usa la caché de voz, así que el montaje la reutiliza sin volver a sintetizar."""
    import genera_video as V
    import presentador as PR
    tmp = Path(tempfile.mkdtemp(prefix="prevuelo_"))
    tr = PR.tramos_de(texto, "?")                          # toda cita de 5+ palabras, su propio tramo (como en los Shorts)
    PR.locuta_tramos(tr, tmp)
    wav = tmp / "voz.wav"
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
    "ESCÚCHALA y marca SOLO las palabras que suenen CLARAMENTE mal: una palabra atropellada, mal pronunciada, incomprensible o "
    "con las sílabas pegadas de forma que no se entienda. Para cada una propón una ALTERNATIVA parecida en significado que "
    "suene bien. REGLAS IMPORTANTES: (1) NO señales NUNCA el texto que va entre comillas «...»: son citas literales y NO se "
    "pueden cambiar. (2) NO marques cuestiones de ESTILO, entonación leve, ni expresiones coloquiales elegidas a propósito "
    "(«cara de boniato», «menudo percal», «sindiós»…): esas se quedan. (3) Solo lo que un oyente NO entendería o le chirriaría "
    "de verdad. Si todo se entiende bien, devuelve la lista vacía. Responde SOLO en JSON: "
    '{"natural": true/false, "problemas": [{"texto": "la palabra", "motivo": "por qué no se entiende", '
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
                          json={"model": "gpt-audio-mini", "modalities": ["text"],
                                "messages": [{"role": "user", "content": [
                                    {"type": "text", "text": _PROMPT + texto},
                                    {"type": "input_audio", "input_audio": {"data": b64, "format": "mp3"}}]}]})
        if not r.ok:
            print(f"  (OpenAI oído no responde: {r.status_code} {r.text[:80]})", file=sys.stderr)
            return None
        txt = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", txt, re.S)                # el JSON puede venir con texto o ```json alrededor
        return _fmt(json.loads(m.group(0)).get("problemas", []), "openai") if m else []
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


def _paleta():
    """Coletillas/expresiones elegidas a propósito (paleta de NORMAS.md, §4): no se marcan como 'raras'."""
    f = RAIZ / "NORMAS.md"
    try:
        lineas = f.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    out = set()
    dentro = False
    for l in lineas:
        if l.startswith("#"):                          # solo la sección de la paleta, no el resto de la guía
            dentro = "Paleta de coletillas" in l
            continue
        m = re.match(r"\s*-\s+(.+)", l) if dentro else None
        if m:
            out.add(re.sub(r"[.!¡¿?«»]", "", m.group(1)).strip().lower())
    return {e for e in out if 3 <= len(e) <= 60}


def _fuera_de_citas(texto, palabra):
    """True si la palabra/expresión aparece en el guion FUERA de una cita «...» (si solo sale dentro, no se toca)."""
    sin_citas = re.sub(r"«[^»]*»", " ", texto)
    return (palabra or "").strip().lower() in sin_citas.lower()


def _whisper_citas(wf, texto):
    """Pistas de Whisper que caen dentro de una cita literal."""
    return [p for p in wf if p.get("texto") and not _fuera_de_citas(texto, p["texto"])]


def revisa(texto, auto_veta=False):
    """CONTROL DE CALIDAD DE VOZ Y GUION (21-nov-2026): genera la locución como sale en el vídeo y la escucha con el oído
    LOCAL Y GRATUITO de voz_calidad (fonemas, Whisper large-v3, ritmo, entonación y uniones). Gemini, si tiene cuota, es un oído más.
    Devuelve {ok, problemas, en_citas, oido}: «problemas» se arreglan reescribiendo el guion (palabra, pausa o frase);
    «en_citas» no se pueden reescribir (cita literal o nombre propio) y se avisan."""
    import voz_calidad as VC
    wav, mp3 = _audio_tramos(texto)
    r = VC.analiza(wav, texto)
    sub = None
    try:
        sub = _gemini(mp3, texto)                          # oído extra, solo si Gemini responde (gratis)
    except Exception as e:
        print(f"  (Gemini oído falla: {type(e).__name__})", file=sys.stderr)
    oido_extra = "gemini" if sub is not None else "ninguno (Gemini sin cuota)"
    pal = _paleta()                                        # coletillas elegidas a propósito: su palabra NO se cambia
    def protegida(p):
        w = (p["texto"] or "").strip().lower()
        return p.get("tipo") in ("pronunciación", "dudosa", "se oye otra cosa", None) and \
            any(w in expr or expr in w for expr in pal)
    en_citas = list(r["en_citas"]) + [p for p in (sub or []) if not _fuera_de_citas(texto, p["texto"])]
    sub = [p for p in (sub or []) if _fuera_de_citas(texto, p["texto"]) and not protegida(p)]
    problemas = [p for p in r["problemas"] if not protegida(p)] + sub
    if auto_veta:
        for p in problemas:
            if p.get("tipo") in ("pronunciación", "se oye otra cosa"):
                veta(p["texto"], p.get("alternativa", ""), f"la voz no la dice bien ({p['fuente']})")
    return {"ok": not problemas, "problemas": problemas, "en_citas": en_citas, "oido": r["oido"],
            "oido_subjetivo": oido_extra, "medidas": r["medidas"]}


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


def main(fecha, solo=None):
    dia = RAIZ / "dia" / fecha
    (dia / "calidad").mkdir(parents=True, exist_ok=True)
    md = [f"# Control de humanidad de la voz · {fecha}", ""]
    total = 0
    for nombre, txt in _piezas(fecha):
        if solo == "largo" and not nombre.startswith("largo"):
            continue                                       # los Shorts ya se revisaron en su fase
        v = revisa(txt)
        total += len(v["problemas"])
        md.append(f"## {nombre}: {'✅ natural' if v['ok'] else '⚠️ REVISAR'}")
        for p in v["problemas"]:
            md.append(f"- [{p.get('tipo', 'oído')}] «{p['texto']}» — {p['detalle']} → {p.get('alternativa', '')} _({p['fuente']})_")
        for p in v.get("en_citas", []):
            md.append(f"- (aviso, no se reescribe) [{p.get('tipo', 'oído')}] «{p['texto']}» — {p['detalle']}")
        md.append("")
        print(f"{nombre}: {'OK' if v['ok'] else str(len(v['problemas'])) + ' problemas'}", flush=True)
    (dia / "calidad" / "prevuelo_voz.md").write_text("\n".join(md), encoding="utf-8")
    print(f"prevuelo_voz.md listo · {total} cosas a revisar")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
