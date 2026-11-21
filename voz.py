"""LOCUCION de Urni. Devuelve el wav y el tiempo de cada palabra (para subtitulos, escenas y pausas).
Voz principal (elegida por el usuario el 2-nov-2026): Tristan HD de Azure Speech (plan gratuito F0, clave en .env),
a velocidad normal. Azure HD no da el tiempo de cada palabra: se saca escuchando el audio con Whisper "tiny" y se casa
con el guion exacto; el recorte de pausas se protege para que no coma sonido.
TODO LO QUE SE SUBE A YOUTUBE TIENE QUE SER MONETIZABLE (norma del usuario, 2-nov-2026): la voz anterior (edge-tts
Alvaro) no tiene licencia comercial, asi que NO es reserva automatica. Si Azure no responde, se reintenta ~10 min y,
si sigue fallando, se para con error (la jornada avisa por Telegram y no sube nada). Solo para pruebas a mano:
VOZ_PRUEBA_EDGE=1 usa Alvaro.
Modos de edge-tts conservados: cada frase puede recibir un registro (gancho, pregunta, dato, matiz, sobrio o normal);
el usuario eligio el modo "plano" (sin entonacion por contexto)."""
from __future__ import annotations

import asyncio
import difflib
import re
import subprocess
import sys
import time
from pathlib import Path

import edge_tts
import numpy as np
import requests

import genera_video as V1
import pausas

RAIZ = Path(__file__).parent
AZURE_VOZ = "es-ES-Tristan:DragonHDLatestNeural"    # muestra D, elegida el 2-nov-2026
AZURE_VEL = "+0%"
AZURE_TEMP = "1.2"                                 # 21-nov-2026: el usuario elige la muestra «A3» (1,2: más regular, menos
#                                                    variación entre lecturas) con el ritmo corregido por trozos y filtro «radio».
#                                                    Antes, 1,6 (14-nov, energética) y 1,0 («A», apagada).
RADIO = ("highpass=f=70,equalizer=f=150:t=q:w=1.0:g=4,equalizer=f=350:t=q:w=1.5:g=1.5,"
         "equalizer=f=5500:t=q:w=2.0:g=-5,lowpass=f=12500,"
         "acompressor=threshold=-16dB:ratio=3:attack=4:release=130,alimiter=limit=0.92")   # 12-nov: filtro «radio»
AZURE_MAX = 2500                                   # caracteres por peticion (el plan F0 admite hasta 3.000)
WHISPER = "tiny"                                   # 4x mas rapido que el audio en el servidor
SESGO = {"tiny": 0.085, "base": 0.0}               # retraso medio medido contra los tiempos exactos de edge-tts (2-nov)
VOZ = "es-ES-AlvaroNeural"                         # solo pruebas a mano (sin licencia comercial)
BASE = (14, 6)                                    # +14 % de velocidad, +6 Hz (la muestra 1 elegida)
REGISTRO = {                                       # (velocidad %, tono Hz)
    "normal": (14, 6),
    "gancho": (19, 10),                           # frase corta de arranque: mas energia
    "pregunta": (14, 11),                         # sube para que suene a pregunta
    "dato": (8, 4),                               # cifras: un pelo mas despacio para que se entiendan
    "matiz": (8, 2),                              # advertencias y contrapesos: pausado
    "sobrio": (6, 1),                             # tragedias: lento y grave
}
# 21-nov-2026 (el usuario: «no quiero que la voz cambie de ritmo con las frases hechas ni coletillas»): cada trozo se mide al
# generarlo y, si va más de un 10 % más rápido o más lento que el ritmo de Tristán, se vuelve a pedir con la velocidad
# corregida (<prosody rate>). Las exclamaciones van en su propio trozo (11-nov, para la entonación) y solas Tristán las
# acelera: «¡Venga, que nos vamos!» salía a 9-10 sílabas por segundo con el resto a 6,7.
RITMO = 6.0                                          # sílabas por segundo de Tristán (temp. 1,6) con los tiempos de alinea(), medido el 21-nov
RITMO_TOL = 0.10
# 21-nov-2026 (el usuario): el CIERRE de los Shorts (la pregunta y «Te leo en comentarios. Y dale a suscribirte…») se locuta
# como en los días anteriores: temperatura 1,6 y sin corregir el ritmo. Ese era su tono y su estilo.
CIERRE = "Te leo en comentarios"
AZURE_TEMP_CIERRE = "1.6"
PAUSA, COMA = 0.40, 0.24                          # opcion B: pausa entre frases y ante comas largas, sin cola de sala
NUMEROS = re.compile(r"\b(cero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|veint\w*|"
                     r"treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien\w*|doscient\w*|trescient\w*|"
                     r"mil|millon\w*|por ciento)\b", re.I)
MATIZ = re.compile(r"^(es la (lectura|valoración)|habrá que ver|eso sí|por su parte|en cambio|aunque|sin embargo|según)", re.I)


def frases(texto):
    return [f for f in re.split(r"(?<=[.?!])\s+", texto.strip()) if f]


def registro(frase, k, tono_seccion, forzado=None):
    if forzado:
        return forzado
    if tono_seccion == "sobrio":
        return "sobrio"
    if frase.endswith("?"):
        return "pregunta"
    if k == 0 and len(frase.split()) <= 8:
        return "gancho"
    if MATIZ.search(frase):
        return "matiz"
    if len(NUMEROS.findall(frase)) >= 2:
        return "dato"
    return "normal"


async def _sintetiza(texto, reg, mp3):
    v, p = REGISTRO[reg]
    pal = []
    with open(mp3, "wb") as fh:
        async for c in edge_tts.Communicate(texto, VOZ, rate=f"+{v}%", pitch=f"+{p}Hz", boundary="WordBoundary").stream():
            if c["type"] == "audio":
                fh.write(c["data"])
            elif c["type"] == "WordBoundary":
                pal.append((c["offset"] / 1e7, (c["offset"] + c["duration"]) / 1e7, c["text"]))
    return pal


def _credenciales_azure():
    env = RAIZ / ".env"
    if not env.exists():
        return None, None
    kv = dict(l.split("=", 1) for l in env.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
    return kv.get("AZURE_SPEECH_KEY", "").strip().strip("\"'"), kv.get("AZURE_SPEECH_REGION", "").strip().strip("\"'")


_MOTOR = None


def motor():
    """'azure' (siempre en produccion) o 'edge' (solo con VOZ_PRUEBA_EDGE=1). Se decide una vez por proceso."""
    global _MOTOR
    if _MOTOR:
        return _MOTOR
    import os
    if os.environ.get("VOZ_PRUEBA_EDGE") == "1":
        print("  AVISO voz: VOZ_PRUEBA_EDGE=1, voz de pruebas (Alvaro, NO monetizable: no subir)", file=sys.stderr, flush=True)
        _MOTOR = "edge"
        return _MOTOR
    clave, region = _credenciales_azure()
    if not (clave and region):
        raise RuntimeError("Falta la clave de Azure en .env (AZURE_SPEECH_KEY / AZURE_SPEECH_REGION): sin voz con "
                           "licencia comercial no se hace el video. Se guarda con: .venv/bin/python clave_azure.py")
    motivo = ""
    for espera in (0, 30, 60, 120, 180, 240):       # ~10 min en total
        time.sleep(espera)
        try:
            r = requests.post(f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken", timeout=20,
                              headers={"Ocp-Apim-Subscription-Key": clave, "Content-Length": "0"})
            if r.ok:
                _MOTOR = "azure"
                return _MOTOR
            motivo = f"Azure rechaza la clave ({r.status_code})"
            if r.status_code in (401, 403):
                break                               # clave mala: reintentar no sirve
        except requests.RequestException as e:
            motivo = f"Azure no responde ({type(e).__name__})"
        print(f"  AVISO voz: {motivo}; reintento", file=sys.stderr, flush=True)
    raise RuntimeError(f"{motivo}. No se usa voz de reserva porque no seria monetizable: no se sube nada hoy.")


# 10-nov-2026 (el usuario: «cuando lee siglas suena muy raro»): las siglas que Tristán no lee bien se dicen con su nombre
# (<sub alias>: el guion y los subtítulos siguen con la sigla). Solo las que no se leen como palabra o letra a letra natural.
SIGLAS = {"CCOO": "Comisiones Obreras", "CC.OO.": "Comisiones Obreras", "TVE": "Televisión Española",
          "RTVE": "Radiotelevisión Española", "EEUU": "Estados Unidos", "EE.UU.": "Estados Unidos", "UE": "Unión Europea",
          "CGPJ": "Consejo General del Poder Judicial", "IMV": "Ingreso Mínimo Vital", "TC": "Tribunal Constitucional",
          "TS": "Tribunal Supremo", "AN": "Audiencia Nacional", "UCO": "la UCO", "DANA": "dana", "OTAN": "OTAN",
          "PSC": "PSC", "PSPV": "PSPV", "BNG": "Bloque Nacionalista Galego", "CUP": "la CUP", "CEOE": "la CEOE",
          "SMI": "salario mínimo", "IPC": "IPC", "PIB": "PIB", "IRPF": "IRPF", "IVA": "IVA", "EH Bildu": "Bildu"}
SIGLAS = {k: v for k, v in SIGLAS.items() if k != v and not v.startswith("la ")}   # solo las que cambian la lectura


# 21-nov-2026 (el usuario elige «B3»): DICCIONARIO DE PRONUNCIACIÓN. Las palabras que Tristán acentúa o dice mal se le dictan
# con el alfabeto fonético SAPI de Azure (sílaba tónica con «1» tras la vocal). Cada palabra que el usuario oiga mal, aquí.
PRONUNCIA = {
    "mitines": "m i t i 1 n e s",
    "mitin": "m i 1 t i n",
}
# Palabras que basta con escribirle a la voz de otra forma (con tilde, por ejemplo) para que las diga bien. El texto en
# pantalla no cambia. 21-nov-2026: «enterarais» salía «enteraráis» y con SAPI tampoco; con tilde, el usuario la aprueba.
ESCRIBE = {
    "enterarais": "enterárais",
}
# Versión del procesado de la voz: entra en la clave de la caché. Se sube SOLO cuando cambia cómo se genera la voz (no al
# añadir palabras al diccionario: esas entran en la clave de los trozos que las llevan).
VERSION_VOZ = "2026-11-21"


def _pronuncia_ssml(texto):
    import re
    for pal in sorted(PRONUNCIA, key=len, reverse=True):
        texto = re.sub(r"(?<![\wÁÉÍÓÚÑáéíóúñ<'=])(" + re.escape(pal) + r")(?![\wÁÉÍÓÚÑáéíóúñ])",
                       lambda m: f"<phoneme alphabet='sapi' ph='{PRONUNCIA[pal]}'>{m.group(1)}</phoneme>", texto,
                       flags=re.I)
    for pal in sorted(ESCRIBE, key=len, reverse=True):
        texto = re.sub(r"(?<![\wÁÉÍÓÚÑáéíóúñ<'=])(" + re.escape(pal) + r")(?![\wÁÉÍÓÚÑáéíóúñ])",
                       lambda m: f"<sub alias='{ESCRIBE[pal]}'>{m.group(1)}</sub>", texto, flags=re.I)
    return texto


def dicc_de(texto):
    """Entradas del diccionario de pronunciación que afectan a este texto (para la clave de la caché)."""
    t = texto.lower()
    return sorted([k, v] for d in (PRONUNCIA, ESCRIBE) for k, v in d.items() if k.lower() in t)


def _siglas_ssml(texto_escapado):
    import re
    out = _pronuncia_ssml(texto_escapado)
    for sigla in sorted(SIGLAS, key=len, reverse=True):
        out = re.sub(r"(?<![\wÁÉÍÓÚÑáéíóúñ])" + re.escape(sigla) + r"(?![\wÁÉÍÓÚÑáéíóúñ])",
                     f"<sub alias='{SIGLAS[sigla]}'>{sigla}</sub>", out)
    # 29N, 11N... → «29 de noviembre»
    out = re.sub(r"\b(\d{1,2})N\b", lambda m: f"<sub alias='{m.group(1)} de noviembre'>{m.group(0)}</sub>", out)
    return out


def _azure_mp3(texto, mp3, vel=None, temp=None):
    from xml.sax.saxutils import escape
    clave, region = _credenciales_azure()
    ssml = (f"<speak version='1.0' xml:lang='es-ES' xmlns='http://www.w3.org/2001/10/synthesis'>"
            f"<voice name='{AZURE_VOZ}' parameters='temperature={temp or AZURE_TEMP}'><prosody rate='{vel or AZURE_VEL}'>{_siglas_ssml(escape(texto))}</prosody></voice></speak>")
    for intento in range(4):
        try:
            r = requests.post(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1", data=ssml.encode("utf-8"),
                              timeout=180, headers={"Ocp-Apim-Subscription-Key": clave, "User-Agent": "hoyformativo",
                                                    "Content-Type": "application/ssml+xml",
                                                    "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3"})
            if r.ok and len(r.content) > 1000:
                Path(mp3).write_bytes(r.content)
                return
            error = f"{r.status_code} {r.text[:120]}"
        except requests.RequestException as e:
            error = type(e).__name__
        time.sleep((2, 5, 15, 0)[intento])
    raise RuntimeError(f"Azure no ha generado la voz tras 4 intentos: {error}")


_MODELO = None


def _modelo():
    global _MODELO
    if _MODELO is None:
        from faster_whisper import WhisperModel
        _MODELO = WhisperModel(WHISPER, device="cpu", compute_type="int8", cpu_threads=4)
    return _MODELO


def _norm(w):
    return re.sub(r"\W", "", w.lower())


def alinea(wav, texto):
    """Tiempo de cada palabra del guion (con su puntuacion, como la escribe el redactor) escuchando el audio."""
    segs, _ = _modelo().transcribe(str(wav), language="es", word_timestamps=True, beam_size=1, vad_filter=False,
                                   condition_on_previous_text=False)
    s0 = SESGO.get(WHISPER, 0.0)
    oidas = [(max(0.0, w.start - s0), max(0.0, w.end - s0), _norm(w.word)) for s in segs for w in s.words if _norm(w.word)]
    toks = texto.split()
    tt = [None] * len(toks)
    sm = difflib.SequenceMatcher(None, [_norm(t) for t in toks], [o[2] for o in oidas], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                tt[i1 + k] = oidas[j1 + k][:2]
        elif op == "replace":                       # Whisper oyo otra cosa ("vice secretaria"): se reparte su tramo
            _reparte(tt, toks, i1, i2, oidas[j1][0], oidas[j2 - 1][1])
    # palabras que Whisper no oyo: se reparten en el hueco entre sus vecinas
    k = 0
    while k < len(toks):
        if tt[k] is not None:
            k += 1
            continue
        f = k
        while f < len(toks) and tt[f] is None:
            f += 1
        ini = tt[k - 1][1] if k else 0.0
        fin = tt[f][0] if f < len(toks) else (oidas[-1][1] if oidas else ini + 0.3 * (f - k))
        _reparte(tt, toks, k, f, ini, max(fin, ini + 0.05 * (f - k)))
        k = f
    return [(a, b, w) for (a, b), w in zip(tt, toks)]


def _reparte(tt, toks, i1, i2, ini, fin):
    pesos = [max(1, len(_norm(t))) for t in toks[i1:i2]]
    paso, t = (fin - ini) / sum(pesos), ini
    for k, p in zip(range(i1, i2), pesos):
        tt[k] = (t, t + paso * p)
        t += paso * p


def silabas(w):
    return max(1, len(re.findall(r"[aeiouáéíóúü]+", w.lower()))) if re.search(r"\w", w) else 0


def ritmo_de(pal, hueco_max=0.15):
    """Sílabas por segundo de habla (sin contar las pausas de más de hueco_max s). None si es muy corto para medir."""
    pal = [p for p in pal if silabas(p[2])]
    if len(pal) < 3:
        return None
    habla = sum(b - a for a, b, _ in pal) + sum(min(pal[i + 1][0] - pal[i][1], hueco_max) for i in range(len(pal) - 1)
                                              if pal[i + 1][0] - pal[i][1] > 0)
    sil = sum(silabas(p[2]) for p in pal)
    return sil / habla if habla > 0.3 else None


def a_silencios(x, sr, pal, umbral_db=-38):
    """Protege el recorte de pausas (pausas.naturaliza) cuando los tiempos vienen de Whisper: no toca ningun tiempo
    salvo en los huecos que se van a recortar, y ahi solo si el tramo que se quitaria tiene sonido. En ese caso encaja
    el corte en el silencio real mas largo del hueco, o anula el hueco si no hay silencio."""
    mono = np.abs(x).mean(axis=1) if x.ndim > 1 else np.abs(x)
    ven = int(0.01 * sr)
    n = len(mono) // ven
    rms = np.sqrt((mono[:n * ven].reshape(n, ven) ** 2).mean(axis=1) + 1e-9)
    silencio = 20 * np.log10(rms / 32768) < umbral_db
    out = list(pal)
    for k in range(len(out) - 1):
        a, b, w = out[k]
        a2, b2, w2 = out[k + 1]
        objetivo = PAUSA if w.rstrip()[-1:] in ".?!:" or a2 - b > 0.5 else COMA     # la misma regla que naturaliza
        if a2 - b <= objetivo + 0.05:
            continue                                # aqui no se recorta nada
        c0, c1 = int((b + 0.12) * 100), int((a2 - 0.05) * 100)          # lo que naturaliza podria quitar
        if c1 <= c0 or silencio[c0:c1].all():
            continue                                # todo silencio: los tiempos se quedan como estan
        lo, hi = int(b * 100), int(a2 * 100)
        mejor, ini_r = (0, 0), None
        for i, s in enumerate(list(silencio[lo:hi]) + [False]):
            if s and ini_r is None:
                ini_r = i
            elif not s and ini_r is not None:
                if i - ini_r > mejor[1] - mejor[0]:
                    mejor = (ini_r, i)
                ini_r = None
        if mejor[1] - mejor[0] < 10:                # menos de 0,1 s de silencio: sin hueco, no se corta
            m = (b + a2) / 2
            out[k], out[k + 1] = (a, max(a, m), w), (min(b2, m), b2, w2)
            continue
        s0, s1 = (lo + mejor[0]) / 100, (lo + mejor[1]) / 100
        out[k], out[k + 1] = (a, max(a, s0 - 0.12), w), (min(b2, s1 + 0.05), b2, w2)
    return out


CACHE = Path(__file__).parent / "cache" / "voz"


def locuta(pasos, tono_seccion, wav_salida, modo="plano", cola=0.7):
    """Igual que _locuta, pero guarda el resultado: si el texto y los ajustes no cambian (por ejemplo, al volver a
    renderizar tras una correccion de otro bloque), no se vuelve a sintetizar."""
    import hashlib
    import json
    import shutil
    # 21-nov-2026: la clave ya no lleva el código entero (cualquier cambio regrababa TODO, también las tomas aprobadas):
    # lleva la config, VERSION_VOZ y las palabras del diccionario que salen en el texto.
    texto = " ".join(p["di"] for p in pasos)
    cfg = [AZURE_VOZ, AZURE_TEMP, AZURE_VEL, RADIO, AZURE_TEMP_CIERRE, RITMO, RITMO_TOL] if motor() == "azure" else []
    clave = hashlib.sha1(json.dumps([[p["di"], p.get("entona")] for p in pasos] + [tono_seccion, modo, cola, VERSION_VOZ,
                                    motor(), dicc_de(texto)] + cfg, ensure_ascii=False).encode()).hexdigest()[:20]
    wav_c, meta_c = CACHE / f"{clave}.wav", CACHE / f"{clave}.json"
    if wav_c.exists() and meta_c.exists():
        shutil.copyfile(wav_c, wav_salida)
        m = json.loads(meta_c.read_text(encoding="utf-8"))
        return [tuple(x) for x in m["palabras"]], m["dur"]
    palabras, dur = _locuta(pasos, tono_seccion, wav_salida, modo, cola)
    CACHE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(wav_salida, wav_c)
    meta_c.write_text(json.dumps({"palabras": palabras, "dur": dur}, ensure_ascii=False), encoding="utf-8")
    return palabras, dur


def _locuta(pasos, tono_seccion, wav_salida, modo="plano", cola=0.7):
    """pasos: lista de {"di": ..., "entona"?: ...}. Escribe wav_salida (48 kHz estereo) y devuelve (palabras, duracion).
    modo: "plano" (ELEGIDO POR EL USUARIO: voz de la muestra 1 en todo, sin entonacion; solo pausas B), "seccion" (sobrios graves),
    "contexto" (cada frase con su registro) o "plano" (todo normal). cola: silencio al final de la seccion."""
    wav_salida = Path(wav_salida)
    tmp = wav_salida.with_suffix("")
    trozos = []                                    # (texto, registro)
    k = 0
    for p in pasos:
        for f in frases(p["di"]):
            if modo == "contexto":
                r = registro(f, k, tono_seccion, p.get("entona"))
            elif modo == "seccion":
                r = "sobrio" if tono_seccion == "sobrio" else "normal"
            else:
                r = "normal"
            if trozos and trozos[-1][1] == r:
                trozos[-1] = (trozos[-1][0] + " " + f, r)
            else:
                trozos.append((f, r))
            k += 1
    azure = motor() == "azure"
    if azure:                                      # la voz HD no usa registros; trozos largos se parten por frases
        partidos = []
        exclama = re.compile(r"[?!][»\"”']*\.?$")       # 11-nov: preguntas y exclamaciones, en su propio trozo
        for txt, r in trozos:
            cur = ""
            for f in frases(txt):
                aparte = bool(exclama.search(f.strip()))
                if cur and f.strip().startswith(CIERRE):     # el cierre de los Shorts, siempre en su propio trozo
                    partidos.append((cur, r))
                    cur = ""
                if cur and (aparte or len(cur) + len(f) + 1 > AZURE_MAX):
                    partidos.append((cur, r))
                    cur = ""
                if aparte:                         # medido el 11-nov: dentro de un texto largo Tristán no sube el tono
                    partidos.append((f, r))        # al final de la pregunta; sola, sí (de 111 a 174 Hz)
                    continue
                cur = f"{cur} {f}".strip()
            if cur:
                partidos.append((cur, r))
        trozos = partidos
    k_cierre = next((j for j, (txt, _) in enumerate(trozos) if txt.strip().startswith(CIERRE)), None) if azure else None
    if k_cierre and trozos[k_cierre - 1][0].rstrip("»\"' ").endswith("?"):
        k_cierre -= 1                                 # la pregunta del final también es parte del cierre
    audio, palabras, t, sr = [], [], 0.0, 48000
    for j, (txt, r) in enumerate(trozos):
        mp3, wav = Path(f"{tmp}_{j}.mp3"), Path(f"{tmp}_{j}.wav")
        cierre = k_cierre is not None and j >= k_cierre
        if azure:
            _azure_mp3(txt, mp3, temp=AZURE_TEMP_CIERRE if cierre else None)
        else:
            pal = asyncio.run(_sintetiza(txt, r, mp3))
        subprocess.run([V1.FF, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(sr), "-ac", "2", str(wav)], check=True)
        if azure:
            pal = a_silencios(pausas.lee(wav)[0], sr, alinea(wav, txt))
            v = ritmo_de(pal)
            if v and abs(v / RITMO - 1) > RITMO_TOL and not cierre:     # va más rápido o más lento que el resto: se pide otra vez
                pct = int(round(max(-30, min(30, (RITMO / v - 1) * 100))))
                _azure_mp3(txt, mp3, vel=f"{pct:+d}%")
                subprocess.run([V1.FF, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(sr), "-ac", "2", str(wav)], check=True)
                pal2 = a_silencios(pausas.lee(wav)[0], sr, alinea(wav, txt))
                v2 = ritmo_de(pal2)
                print(f"  ritmo: «{txt[:40]}» iba a {v:.1f} síl/s, pedido a {pct:+d}% → {v2 or 0:.1f}", file=sys.stderr)
                if v2 and abs(v2 / RITMO - 1) > abs(v / RITMO - 1):    # salió peor: el primero
                    _azure_mp3(txt, mp3)
                    subprocess.run([V1.FF, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(sr), "-ac", "2", str(wav)], check=True)
                    pal2 = a_silencios(pausas.lee(wav)[0], sr, alinea(wav, txt))
                pal = pal2
        if not azure:                              # 11-nov-2026 (voz 3b): con Azure, las pausas que marca Tristán, sin añadir
            pal, _ = pausas.naturaliza(wav, pal, PAUSA, COMA, sala=False)
        x, _ = pausas.lee(wav)
        # recorta el silencio del principio y del final del trozo y deja la pausa de locutor entre trozos
        ini = max(0.0, pal[0][0] - 0.05) if pal else 0.0
        fin = min(len(x) / sr, pal[-1][1] + 0.18) if pal else len(x) / sr
        x = x[int(ini * sr):int(fin * sr)]
        palabras += [(a - ini + t, b - ini + t, w) for a, b, w in pal]
        hueco = (0.22 if azure else PAUSA) if j + 1 < len(trozos) else cola   # 11-nov: entre trozos, 0,22 s
        audio += [x, np.zeros((int(hueco * sr), 2), dtype=np.float32)]
        t += len(x) / sr + hueco
        mp3.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)
    pausas.escribe(wav_salida, np.concatenate(audio), sr)
    if motor() == "azure":                             # 12-nov: filtro «radio» (quita el metálico, aplasta picos de volumen);
        tmpf = Path(f"{wav_salida}.radio.wav")          # el EQ/compresor/limitador no cambian la duración: los tiempos siguen valiendo
        r = subprocess.run([V1.FF, "-y", "-loglevel", "error", "-i", str(wav_salida), "-af", RADIO, str(tmpf)])
        if r.returncode == 0 and tmpf.exists():
            tmpf.replace(wav_salida)
    return palabras, t
