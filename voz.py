"""LOCUCION de Urni: entonacion segun el contexto de cada frase + pausas naturales (opcion B elegida por el usuario).
edge-tts no admite estilos de locutor, pero si velocidad y tono por trozo: cada frase recibe un registro (gancho,
pregunta, dato, matiz, sobrio o normal); las frases seguidas con el mismo registro se generan juntas para no perder
continuidad, y luego se unen con pausas de locutor. Devuelve el wav y el tiempo de cada palabra.
Un paso del guion puede forzar el registro con "entona": "gancho|pregunta|dato|matiz|sobrio|normal"."""
from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts
import numpy as np

import genera_video as V1
import pausas

VOZ = "es-ES-AlvaroNeural"
BASE = (14, 6)                                    # +14 % de velocidad, +6 Hz (la muestra 1 elegida)
REGISTRO = {                                       # (velocidad %, tono Hz)
    "normal": (14, 6),
    "gancho": (19, 10),                           # frase corta de arranque: mas energia
    "pregunta": (14, 11),                         # sube para que suene a pregunta
    "dato": (8, 4),                               # cifras: un pelo mas despacio para que se entiendan
    "matiz": (8, 2),                              # advertencias y contrapesos: pausado
    "sobrio": (6, 1),                             # tragedias: lento y grave
}
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


def locuta(pasos, tono_seccion, wav_salida, modo="plano", cola=0.7):
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
    audio, palabras, t, sr = [], [], 0.0, 48000
    for j, (txt, r) in enumerate(trozos):
        mp3, wav = Path(f"{tmp}_{j}.mp3"), Path(f"{tmp}_{j}.wav")
        pal = asyncio.run(_sintetiza(txt, r, mp3))
        subprocess.run([V1.FF, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(sr), "-ac", "2", str(wav)], check=True)
        pal, _ = pausas.naturaliza(wav, pal, PAUSA, COMA, sala=False)
        x, _ = pausas.lee(wav)
        # recorta el silencio del principio y del final del trozo y deja la pausa de locutor entre trozos
        ini = max(0.0, pal[0][0] - 0.05) if pal else 0.0
        fin = min(len(x) / sr, pal[-1][1] + 0.18) if pal else len(x) / sr
        x = x[int(ini * sr):int(fin * sr)]
        palabras += [(a - ini + t, b - ini + t, w) for a, b, w in pal]
        hueco = PAUSA if j + 1 < len(trozos) else cola
        audio += [x, np.zeros((int(hueco * sr), 2), dtype=np.float32)]
        t += len(x) / sr + hueco
        mp3.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)
    pausas.escribe(wav_salida, np.concatenate(audio), sr)
    return palabras, t
