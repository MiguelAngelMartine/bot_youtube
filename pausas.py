"""Pausas naturales para la voz: edge-tts deja ~0,75 s de silencio entre frases y la frase termina en seco.
Esto recorta cada silencio largo a una pausa de locutor (con fundido para que no se note el corte), mueve los
tiempos de las palabras en consecuencia (para que escenas y subtitulos sigan sincronizados) y, si se pide,
anade una cola de sala muy ligera para que el final de cada frase se apague de forma natural."""
from __future__ import annotations

import subprocess
import wave

import numpy as np

import genera_video as V1

SALA = "aecho=0.85:0.55:28|46:0.11|0.06"         # cola de sala casi imperceptible


def lee(ruta):
    with wave.open(str(ruta)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32).reshape(-1, ch)
    return x, sr


def escribe(ruta, x, sr):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.clip(x, -32768, 32767).astype(np.int16).tobytes())


def naturaliza(wav, pal, pausa=0.40, coma=0.24, sala=True):
    """Reescribe 'wav' con las pausas acortadas y devuelve las palabras con sus tiempos corregidos.
    pal: [(inicio, fin, texto)] en segundos sobre el audio original."""
    x, sr = lee(wav)
    trozos, nuevos, desplaz, cursor = [], [], 0.0, 0
    fundido = int(0.03 * sr)
    for k, (a, b, w) in enumerate(pal):
        nuevos.append((a - desplaz, b - desplaz, w))
        if k + 1 == len(pal):
            break
        a2 = pal[k + 1][0]
        hueco = a2 - b
        objetivo = pausa if w.rstrip()[-1:] in ".?!:" or hueco > 0.5 else coma
        if hueco <= objetivo + 0.05:
            continue
        # se conservan 0,12 s tras la palabra (la vocal se apaga) y 0,05 s antes de la siguiente; se quita lo de en medio
        quita = hueco - objetivo
        i0 = int((b + 0.12) * sr)
        i1 = min(int((a2 - 0.05) * sr), i0 + int(quita * sr))
        if i1 - i0 < fundido * 2:
            continue
        cola = x[cursor:i0].copy()
        cola[-fundido:] *= np.linspace(1, 0, fundido)[:, None]
        trozos.append(cola)
        cursor = i1
        x[cursor:cursor + fundido] *= np.linspace(0, 1, fundido)[:, None]
        desplaz += (i1 - i0) / sr
    trozos.append(x[cursor:])
    escribe(wav, np.concatenate(trozos), sr)
    if sala:
        tmp = wav.with_name(wav.stem + "_sala.wav")
        subprocess.run([V1.FF, "-y", "-loglevel", "error", "-i", str(wav), "-af", SALA, str(tmp)], check=True)
        tmp.replace(wav)
    with wave.open(str(wav)) as w:
        dur = w.getnframes() / w.getframerate()
    return nuevos, dur
