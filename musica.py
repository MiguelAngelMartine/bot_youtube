"""Agente 8, MUSICA: sintonia, fondo musical y efectos COMPUESTOS AQUI, nota a nota, con numpy.
No se usa ninguna grabacion ni muestra ajena: el audio es obra propia, sin derechos de terceros ni reclamaciones de
Content ID. La progresion de acordes (La m - Fa - Do - Sol) es de uso comun y no es protegible.
Uso desde genera_video2: musica.mezcla(voz.wav, salida.wav, intro, outro, cortes)"""
from __future__ import annotations

import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BPM = 96
NEGRA = 60 / BPM
COMPAS = 4 * NEGRA
# acordes en semitonos sobre La 220 Hz: La m, Fa, Do, Sol (y una variante con Re m para no repetir siempre lo mismo)
ACORDES = [[0, 3, 7], [-4, 0, 3], [3, 7, 10], [-2, 2, 5]]
ACORDES_B = [[0, 3, 7], [5, 8, 12], [-4, 0, 3], [-2, 2, 5]]
rng = np.random.default_rng(29)


def hz(semi, base=220.0):
    return base * 2 ** (semi / 12)


def t_(dur):
    return np.arange(int(dur * SR)) / SR


def paso(x, f, tipo="low", orden=2):
    return sosfilt(butter(orden, f, tipo, fs=SR, output="sos"), x)


def sierra_suave(f, dur, armonicos=10):
    t = t_(dur)
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, armonicos + 1))


def pad(semis, dur):
    """Colchon: tres sierras ligeramente desafinadas por nota, filtradas, con entrada y salida lentas."""
    x = sum(sierra_suave(hz(s) * d, dur, 8) for s in semis for d in (0.996, 1.0, 1.004))
    x = paso(x, 900)
    env = np.minimum(1, np.minimum(t_(dur) / 0.5, (dur - t_(dur)) / 0.6).clip(0))
    return x * env / (3 * len(semis))


def pluck(f, dur=0.5):
    t = t_(dur)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return x * np.exp(-t / 0.16) * np.minimum(1, t / 0.004)


def bajo(f, dur):
    t = t_(dur)
    x = np.tanh(1.6 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)))
    return x * np.exp(-t / 0.5) * np.minimum(1, t / 0.01)


def bombo():
    t = t_(0.35)
    f = 45 + 85 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)


def charles():
    t = t_(0.05)
    return paso(rng.standard_normal(len(t)), 7000, "high") * np.exp(-t / 0.012)


def suma(dst, x, t0, gan=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= len(dst):
        return
    x = x[: len(dst) - i]
    dst[i:i + len(x), 0] += x * gan * (1 - pan) ** 0.5
    dst[i:i + len(x), 1] += x * gan * (1 + pan) ** 0.5


def reverb(x, seg=1.6, mezcla=0.18):
    t = t_(seg)
    ir = rng.standard_normal((len(t), 2)) * np.exp(-t / (seg / 5))[:, None]
    ir = paso(ir.T, 5000).T
    h = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], axis=1)
    return x + mezcla * h / np.abs(h).max() * np.abs(x).max()


def fondo(dur):
    """Base continua: colchon + arpegio + bajo + pulso suave. Alterna la progresion A y B cada 4 compases."""
    out = np.zeros((int(dur * SR) + SR, 2))
    n_comp = int(dur / COMPAS) + 1
    for c in range(n_comp):
        t0 = c * COMPAS
        prog = ACORDES if (c // 4) % 2 == 0 else ACORDES_B
        ac = prog[c % 4]
        suma(out, pad(ac, COMPAS + 0.6), t0, 0.55)
        suma(out, bajo(hz(ac[0], 55), COMPAS / 2), t0, 0.5)
        suma(out, bajo(hz(ac[0], 55), COMPAS / 2), t0 + 2 * NEGRA, 0.4)
        notas = [ac[0] + 12, ac[1] + 12, ac[2] + 12, ac[1] + 24, ac[2] + 12, ac[1] + 12, ac[0] + 24, ac[2] + 12]
        for k, s in enumerate(notas):                       # corcheas
            suma(out, pluck(hz(s)), t0 + k * NEGRA / 2, 0.16 if k % 2 == 0 else 0.11, pan=0.35 if k % 2 else -0.35)
        for b in range(4):
            if b in (0, 2):
                suma(out, bombo(), t0 + b * NEGRA, 0.45)
            suma(out, charles(), t0 + b * NEGRA + NEGRA / 2, 0.10, pan=0.2)
    return reverb(out)[: int(dur * SR)]


def sintonia():
    """Firma sonora del canal (unos 2,6 s): arpegio que sube rapido, golpe final y cola."""
    out = np.zeros((int(4.0 * SR), 2))
    sube = t_(0.9)
    ruido = paso(rng.standard_normal(len(sube)), 3000, "high") * (sube / 0.9) ** 3 * 0.25
    suma(out, ruido, 0.0)
    for k, s in enumerate([0, 3, 7, 12, 15, 19]):
        suma(out, pluck(hz(s + 12), 0.7), 0.15 * k, 0.35, pan=-0.4 + 0.16 * k)
    golpe = 0.9
    suma(out, bombo(), golpe, 1.0)
    suma(out, pad([0, 7, 12, 15], 2.6) * np.exp(-t_(2.6) / 1.1), golpe, 1.2)
    suma(out, bajo(hz(0, 55), 1.2), golpe, 0.8)
    for s in (0, 7, 12):
        suma(out, pluck(hz(s + 24), 1.2), golpe, 0.25)
    return reverb(out, 2.2, 0.3)


def barrido(dur=0.6):
    """Efecto de cortinilla: ruido filtrado que sube y baja."""
    t = t_(dur)
    x = rng.standard_normal(len(t))
    trozos = np.array_split(x, 24)
    y = np.concatenate([paso(tr, 400 + 5000 * np.sin(np.pi * (k + 0.5) / 24) ** 2, "low", 1) for k, tr in enumerate(trozos)])
    return y * np.sin(np.pi * t / dur) ** 2 * 0.5


def pop():
    """Efecto corto cuando entra un dato en pantalla: tono que cae rapido, como una burbuja."""
    t = t_(0.09)
    f = 520 + 1300 * np.exp(-t / 0.025)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.028) * np.minimum(1, t / 0.002)


def lee_wav(ruta):
    with wave.open(str(ruta)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
        return x.reshape(-1, w.getnchannels()), w.getframerate()


def escribe_wav(ruta, x):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def mezcla(voz_wav, salida, intro, outro, cortes, nivel_fondo=0.16, nivel_hablando=0.055, calma=(), efectos=(), con_sintonia=True,
           sintonia_en=0.0, sintonia_dur=None, sin_fondo=()):
    """voz (que empieza en 'intro') + fondo que baja solo cuando se habla + sintonia + barridos en los 'cortes'."""
    voz, sr = lee_wav(voz_wav)
    assert sr == SR
    total = intro + len(voz) / SR + outro
    v = np.zeros((int(total * SR), 2))
    v[int(intro * SR): int(intro * SR) + len(voz)] = voz
    # envolvente de la voz (ventanas de 20 ms), subida rapida y bajada lenta: el fondo se aparta al hablar
    hop = SR // 50
    rms = np.sqrt(np.mean(v[: len(v) // hop * hop, 0].reshape(-1, hop) ** 2, axis=1))
    activo = (rms > 0.01).astype(float)
    g = np.zeros_like(activo)
    for k in range(len(activo)):
        prev = g[k - 1] if k else 0
        g[k] = prev + (activo[k] - prev) * (0.5 if activo[k] > prev else 0.03)
    gan = nivel_fondo + (nivel_hablando - nivel_fondo) * g
    gan = np.repeat(gan, hop)
    gan = np.pad(gan, (0, len(v) - len(gan)), mode="edge")
    m = fondo(total - intro + 0.1)
    fondo_tot = np.zeros_like(v)
    i0 = max(0, int((intro - 0.4) * SR))
    n_m = min(len(m), len(v) - i0)
    fondo_tot[i0:i0 + n_m] = m[:n_m]
    entra = np.clip((np.arange(len(v)) / SR - (intro - 0.4)) / 1.5, 0, 1)
    sale = np.clip((total - np.arange(len(v)) / SR) / 3.0, 0, 1)
    fondo_tot *= (gan * entra * sale)[:, None] / max(np.abs(m).max(), 1e-9)
    tt = np.arange(len(v)) / SR
    for c0, c1 in calma:                        # bloques sobrios (tragedias): el fondo baja a menos de la mitad
        dentro = np.clip(np.minimum(tt - c0, c1 - tt) / 1.0, 0, 1)
        fondo_tot *= (1 - 0.6 * dentro)[:, None]
    for c0, c1 in sin_fondo:                    # el fondo se retira (golpe de marca: la sintonia suena sola)
        fuera = np.clip(np.minimum(tt - c0, c1 - tt) / 0.35, 0, 1)
        fondo_tot *= (1 - fuera)[:, None]
    ef = np.zeros_like(v)
    s = sintonia()
    s /= np.abs(s).max()
    def estereo(x, t0, gan):
        i = int(t0 * SR)
        x = x[: len(ef) - i]
        ef[i:i + len(x)] += x * gan
    if con_sintonia:                            # en los cortos verticales se entra directo con el gancho
        if sintonia_dur:                        # recortada con fundido (golpe de marca del largo, tras el sumario)
            s = s[: int(sintonia_dur * SR)] * np.clip((sintonia_dur - np.arange(int(sintonia_dur * SR)) / SR) / 0.6, 0, 1)[:, None]
        estereo(s, sintonia_en, 0.7)
        estereo(s[: int(3.2 * SR)], total - outro + 0.3, 0.6)
    b = barrido()
    for c in cortes:
        suma(ef, b, c - 0.1, 0.35)
    bp, bw = pop(), barrido(0.38)
    for te, tipo in efectos:                    # ritmo de video corto: "pop" por dato, "whoosh" por cambio de escena
        if tipo == "pop":
            suma(ef, bp, te, 0.13, pan=float(rng.uniform(-0.3, 0.3)))
        else:
            suma(ef, bw, te - 0.12, 0.2)
    x = v + fondo_tot + ef
    escribe_wav(salida, x * min(1.0, 0.95 / np.abs(x).max()))
    return total
