"""PROTOTIPO estilo propio: presentador animado (la urna del canal) + infografias dibujadas por el programa, sin fotos.
Todo lo que se ve es obra propia. Los politicos NO se dibujan: van en tarjetas con iniciales, cargo, color de partido
y la cita textual con su fuente. Un solo bloque (Puente) para valorar el estilo.
Uso: python prototipo_animado.py 2026-10-31"""
from __future__ import annotations

import asyncio
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import genera_video as V1
import genera_video2 as G2
import musica
from genera_video2 import AMARILLO, AN, AL, BLANCO, FPS, ROJO, fuente, pega, suave

S = 2                                  # se dibuja al doble y se reduce: bordes suaves
NAVY = (12, 20, 38)
MIEMBRO = (205, 218, 238)            # brazos y piernas: claros para que se vean sobre el fondo azul
PANEL = (16, 28, 52)
GRIS = (165, 175, 195)
PARTIDO = {"PSOE": (227, 6, 19), "PP": (29, 132, 206), "Vox": (99, 190, 33), "PNV": (0, 135, 63),
           "BNG": (118, 180, 224), "Podemos": (107, 46, 104), "Frente Amplio": (130, 120, 160)}
OUTRO = 5.0


def lienzo(w, h):
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def baja(im):
    # promedio de bloques de SxS con alfa premultiplicado (sin halos oscuros en los bordes): mucho mas rapido que LANCZOS
    return im.convert("RGBa").reduce(S).convert("RGBA")


def f(n, t):
    return fuente(n, int(t * S))


# ------------------------------------------------------------------ presentador: la urna

def mascota(t, boca, parpadeo, gesto):
    im, d = lienzo(400, 500)
    b = 8 * math.sin(2 * math.pi * t / 2.4)
    sx = lambda *v: [x * S / 2 for x in v]           # coordenadas pensadas en un lienzo de 800x1000
    d.ellipse(sx(170, 945, 630, 990), fill=(0, 0, 0, 90))
    for x in (280, 450):
        d.rounded_rectangle(sx(x, 870, x + 70, 950), radius=18, fill=MIEMBRO, outline=NAVY, width=6)
    # brazos
    ola = 25 * math.sin(t * 5) * gesto
    d.line(sx(160, 600 + b, 95, 720 + b), fill=MIEMBRO, width=20)
    d.ellipse(sx(65, 690 + b, 125, 750 + b), fill=BLANCO, outline=NAVY, width=10)
    hx, hy = 735, 690 - 120 * gesto + ola + b
    d.line(sx(640, 600 + b, hx, hy), fill=MIEMBRO, width=20)
    d.ellipse(sx(hx - 30, hy - 30, hx + 30, hy + 30), fill=BLANCO, outline=NAVY, width=10)
    # sobre entrando por la ranura
    e = 10 * math.sin(t * 1.3)
    d.rectangle(sx(330, 140 + b + e, 470, 280 + b), fill=AMARILLO, outline=NAVY, width=8)
    d.line(sx(330, 140 + b + e, 400, 200 + b + e, 470, 140 + b + e), fill=NAVY, width=7)
    # cuerpo de cristal
    d.rounded_rectangle(sx(150, 300 + b, 650, 900 + b), radius=56, fill=(232, 240, 250), outline=NAVY, width=12)
    d.rounded_rectangle(sx(185, 340 + b, 225, 620 + b), radius=20, fill=(255, 255, 255))
    d.polygon(sx(300, 805 + b, 430, 775 + b, 450, 860 + b, 320, 885 + b), fill=BLANCO, outline=(180, 190, 205))
    d.polygon(sx(440, 820 + b, 560, 800 + b, 570, 875 + b, 455, 888 + b), fill=(250, 250, 240), outline=(180, 190, 205))
    d.rectangle(sx(162, 760 + b, 638, 785 + b), fill=ROJO)
    d.rectangle(sx(162, 785 + b, 638, 797 + b), fill=AMARILLO)
    # tapa
    d.rounded_rectangle(sx(120, 232 + b, 680, 318 + b), radius=26, fill=ROJO, outline=NAVY, width=12)
    d.rounded_rectangle(sx(300, 262 + b, 500, 288 + b), radius=12, fill=NAVY)
    # cara
    for cx in (310, 490):
        cy = 520 + b
        if parpadeo:
            d.arc(sx(cx - 55, cy - 30, cx + 55, cy + 30), 20, 160, fill=NAVY, width=12)
        else:
            d.ellipse(sx(cx - 60, cy - 70, cx + 60, cy + 70), fill=BLANCO, outline=NAVY, width=8)
            px, py = cx + 14, cy + 8
            d.ellipse(sx(px - 28, py - 28, px + 28, py + 28), fill=NAVY)
            d.ellipse(sx(px - 2, py - 18, px + 12, py - 4), fill=BLANCO)
        ceja = 18 * boca
        d.line(sx(cx - 55, cy - 105 - ceja, cx + 50, cy - 115 - ceja), fill=NAVY, width=14)
    d.ellipse(sx(205, 600 + b, 265, 635 + b), fill=(255, 150, 170))
    d.ellipse(sx(535, 600 + b, 595, 635 + b), fill=(255, 150, 170))
    my = 665 + b
    if boca < 0.08:
        d.arc(sx(350, my - 40, 450, my + 20), 20, 160, fill=NAVY, width=12)
    else:
        w, h = 50 + 30 * boca, 10 + 55 * boca
        d.ellipse(sx(400 - w, my - h, 400 + w, my + h), fill=(110, 20, 40), outline=NAVY, width=8)
        d.ellipse(sx(400 - w * 0.6, my + h * 0.2, 400 + w * 0.6, my + h), fill=(230, 110, 130))
    return baja(im)


# ------------------------------------------------------------------ piezas de infografia

def iniciales(n):
    return "".join(p[0] for p in n.replace("Ó", "O").split()[:2]).upper()


def tarjeta_compacta(nombre, cargo, partido, ancho, cita, medio, tc=30):
    """Nombre y cargo en una fila y la cita al lado del circulo: caben tres en pantalla."""
    col = PARTIDO[partido]
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lc = G2.texto_lineas(d0, cita, fuente("Inter-Italic.ttf", tc), ancho - 170)
    alto = 70 + len(lc) * int(tc * 1.35) + 38
    im, d = lienzo(ancho, alto)
    d.rounded_rectangle([0, 0, ancho * S, alto * S], radius=22 * S, fill=PANEL + (240,))
    d.rounded_rectangle([0, 0, 12 * S, alto * S], radius=6 * S, fill=col)
    d.ellipse([32 * S, 22 * S, 116 * S, 106 * S], fill=col, outline=BLANCO, width=4 * S)
    d.text((74 * S, 64 * S), iniciales(nombre), font=f("Inter-Black.ttf", 32), fill=BLANCO, anchor="mm")
    d.text((140 * S, 18 * S), nombre, font=f("Inter-Black.ttf", 34), fill=BLANCO)
    w = d0.textlength(nombre, font=fuente("Inter-Black.ttf", 34))
    d.text(((150 + w) * S, 26 * S), "·  " + cargo, font=f("Inter-Regular.ttf", 26), fill=GRIS)
    y = 66
    for l in lc:
        d.text((140 * S, y * S), l, font=f("Inter-Italic.ttf", tc), fill=BLANCO)
        y += int(tc * 1.35)
    d.text((140 * S, (y + 4) * S), "Fuente: " + medio, font=f("Inter-Regular.ttf", 22), fill=GRIS)
    return baja(im)


def tarjeta(nombre, cargo, partido, ancho=600, cita=None, medio=None, ini=None, tc=34):
    col = PARTIDO[partido]
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lc = G2.texto_lineas(d0, cita, fuente("Inter-Italic.ttf", tc), ancho - 70) if cita else []
    alto = 150 + (len(lc) * int(tc * 1.35) + 40 if cita else 0)
    im, d = lienzo(ancho, alto)
    d.rounded_rectangle([0, 0, ancho * S, alto * S], radius=24 * S, fill=PANEL + (240,))
    d.rounded_rectangle([0, 0, 12 * S, alto * S], radius=6 * S, fill=col)
    d.ellipse([34 * S, 27 * S, 130 * S, 123 * S], fill=col, outline=BLANCO, width=4 * S)
    d.text((82 * S, 75 * S), ini or iniciales(nombre), font=f("Inter-Black.ttf", 36), fill=BLANCO, anchor="mm")
    d.text((154 * S, 32 * S), nombre, font=f("Inter-Black.ttf", 40), fill=BLANCO)
    d.text((154 * S, 86 * S), cargo, font=f("Inter-Regular.ttf", 28), fill=GRIS)
    y = 150
    for l in lc:
        d.text((40 * S, y * S), l, font=f("Inter-Italic.ttf", tc), fill=BLANCO)
        y += int(tc * 1.35)
    if medio:
        d.text((40 * S, (y + 8) * S), "Fuente: " + medio, font=f("Inter-Regular.ttf", 22), fill=GRIS)
    return baja(im)


def sello(txt, ang=-7):
    ft = fuente("Inter-Black.ttf", 46)
    w = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(txt, font=ft)) + 60
    im, d = lienzo(w, 90)
    d.rounded_rectangle([4 * S, 4 * S, (w - 4) * S, 86 * S], radius=14 * S, fill=(12, 20, 38, 220), outline=AMARILLO, width=6 * S)
    d.text((w * S // 2, 45 * S), txt, font=f("Inter-Black.ttf", 46), fill=AMARILLO, anchor="mm")
    return baja(im).rotate(ang, expand=True, resample=Image.BICUBIC)


def chip(txt, partido, ancho=440, apagado=False):
    col = PARTIDO[partido]
    im, d = lienzo(ancho, 78)
    if apagado:
        d.rounded_rectangle([3 * S, 3 * S, (ancho - 3) * S, 75 * S], radius=39 * S, fill=PANEL + (230,), outline=col, width=5 * S)
    else:
        d.rounded_rectangle([0, 0, ancho * S, 78 * S], radius=39 * S, fill=col)
    d.text((ancho * S // 2, 39 * S), txt, font=f("Inter-Black.ttf", 36), fill=BLANCO, anchor="mm")
    return baja(im)


def rotulo(txt):
    im, d = lienzo(900, 50)
    d.text((0, 25 * S), txt, font=f("Inter-Black.ttf", 32), fill=AMARILLO, anchor="lm")
    return baja(im)


def texto(txt, tam=34, color=BLANCO, n="Inter-Regular.ttf", ancho=1100):
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ls = G2.texto_lineas(d0, txt, fuente(n, tam), ancho)
    im, d = lienzo(ancho, int(len(ls) * tam * 1.35) + 10)
    for j, l in enumerate(ls):
        d.text((0, j * tam * 1.35 * S), l, font=f(n, tam), fill=color)
    return baja(im)


def flecha(d, a, b, p, color=AMARILLO, ancho=8):
    """Flecha de a a b dibujada hasta la fraccion p."""
    if p <= 0:
        return
    x = a[0] + (b[0] - a[0]) * p
    y = a[1] + (b[1] - a[1]) * p
    d.line([a, (x, y)], fill=color, width=ancho)
    if p > 0.9:
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        pts = [(x, y), (x - 26 * math.cos(ang - 0.45), y - 26 * math.sin(ang - 0.45)),
               (x - 26 * math.cos(ang + 0.45), y - 26 * math.sin(ang + 0.45))]
        d.polygon(pts, fill=color)


# mapa de Espana (contorno simplificado, lon/lat)
ESPANA = [(-9.3, 43.1), (-8.3, 43.6), (-7.0, 43.55), (-5.8, 43.6), (-4.5, 43.4), (-3.4, 43.45), (-2.0, 43.3), (-1.8, 43.4),
          (-1.4, 43.05), (0.0, 42.7), (0.7, 42.85), (1.7, 42.5), (3.2, 42.4), (3.2, 41.9), (2.2, 41.3), (1.0, 41.05),
          (0.6, 40.6), (0.0, 40.0), (-0.3, 39.5), (0.2, 38.8), (-0.5, 38.3), (-0.8, 37.6), (-1.6, 37.0), (-2.2, 36.7),
          (-3.2, 36.75), (-4.4, 36.7), (-5.0, 36.45), (-5.6, 36.0), (-6.3, 36.5), (-6.4, 36.8), (-7.4, 37.2), (-7.5, 37.5),
          (-7.3, 38.2), (-7.0, 38.9), (-7.5, 39.7), (-6.9, 40.3), (-6.8, 41.0), (-6.2, 41.6), (-6.6, 41.95), (-8.1, 41.8),
          (-8.9, 41.9), (-9.0, 42.5), (-9.3, 42.9)]
MAPA_X, MAPA_Y, MAPA_K = 640, 250, 76


def proy(lon, lat):
    return MAPA_X + (lon + 9.6) * math.cos(math.radians(40)) * MAPA_K, MAPA_Y + (44 - lat) * MAPA_K


def capa_mapa():
    im, d = lienzo(AN, AL)
    pts = [(x * S, y * S) for x, y in (proy(*p) for p in ESPANA)]
    d.polygon(pts, fill=(28, 46, 80), outline=(80, 110, 160))
    d.line(pts + [pts[0]], fill=(80, 110, 160), width=4 * S)
    cx, cy = proy(3.0, 39.6)
    d.ellipse([(cx - 32) * S, (cy - 16) * S, (cx + 32) * S, (cy + 16) * S], fill=(28, 46, 80), outline=(80, 110, 160), width=3 * S)
    for nombre, lon, lat, dx in (("Madrid", -3.7, 40.4, -150), ("Barcelona", 2.17, 41.39, -120)):
        x, y = proy(lon, lat)
        d.ellipse([(x - 13) * S, (y - 13) * S, (x + 13) * S, (y + 13) * S], fill=BLANCO, outline=NAVY, width=4 * S)
        d.text(((x + dx) * S, (y + 22) * S), nombre, font=f("Inter-SemiBold.ttf", 32), fill=BLANCO)
    return baja(im)


def tren(ang):
    im, d = lienzo(110, 44)
    d.rounded_rectangle([0, 0, 110 * S, 44 * S], radius=20 * S, fill=BLANCO, outline=NAVY, width=4 * S)
    d.rectangle([0, 30 * S, 110 * S, 37 * S], fill=ROJO)
    for k in range(3):
        d.rounded_rectangle([(14 + k * 26) * S, 9 * S, (32 + k * 26) * S, 23 * S], radius=4 * S, fill=NAVY)
    return baja(im).rotate(-math.degrees(ang), expand=True, resample=Image.BICUBIC)


def aviso():
    im, d = lienzo(120, 110)
    d.polygon([(60 * S, 4 * S), (116 * S, 104 * S), (4 * S, 104 * S)], fill=AMARILLO, outline=NAVY)
    d.text((60 * S, 70 * S), "!", font=f("Inter-Black.ttf", 60), fill=NAVY, anchor="mm")
    return baja(im)


def capa_sub(txt):
    ft = fuente("Inter-SemiBold.ttf", 40)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ls = G2.texto_lineas(d0, txt, ft, 1180)
    w = int(max(d0.textlength(l, font=ft) for l in ls)) + 50
    h = 54 * len(ls) + 22
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w, h], radius=14, fill=(0, 0, 0, 170))
    for j, l in enumerate(ls):
        d.text((w // 2, 11 + 54 * j + 27), l, font=ft, fill=BLANCO, anchor="mm")
    return im


def capa_bloque(titulo, etiqueta):
    im, d = lienzo(1800, 80)
    d.rounded_rectangle([0, 10 * S, 170 * S, 64 * S], radius=27 * S, fill=ROJO)
    d.text((85 * S, 37 * S), etiqueta, font=f("Inter-Black.ttf", 28), fill=BLANCO, anchor="mm")
    d.text((196 * S, 37 * S), titulo, font=f("Inter-Black.ttf", 48), fill=BLANCO, anchor="lm")
    return baja(im)


# ------------------------------------------------------------------ montaje

def main(dia_txt):
    dia = Path(__file__).parent / "dia" / dia_txt
    G = json.loads((dia / "guion.json").read_text(encoding="utf-8"))
    sec = G["secciones"][2]
    tmp = dia / "tmp_anim"
    tmp.mkdir(exist_ok=True)
    frases = asyncio.run(V1.voz(sec["texto"], tmp / "voz.mp3", *G2.VOZ))
    dur = V1.a_wav(tmp / "voz.mp3", tmp / "voz.wav")
    I0 = G2.INTRO
    def empieza(trozo):
        return I0 + next(a for a, b, t in frases if trozo in t)
    tA, tB, tC, tD = I0, empieza("abre otro frente"), empieza("oposición aprieta"), empieza("presión llega")
    tBravo, tAbascal = empieza("Juan Bravo"), empieza("Santiago Abascal")
    tGarriga = tAbascal + 0.55 * (empieza("presión llega") - tAbascal)
    tSan = empieza("descarta dimitir")
    tPod = empieza("Podemos")
    fin = I0 + dur
    total = musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", I0, OUTRO, [tA, tB, tC, tD, fin])

    # labios: volumen de la voz en cada fotograma
    v, sr = musica.lee_wav(tmp / "voz.wav")
    hop = sr // FPS
    rms = np.sqrt(np.mean(v[: len(v) // hop * hop, 0].reshape(-1, hop) ** 2, axis=1))
    boca = np.clip(rms / np.percentile(rms[rms > 0.01], 90), 0, 1) ** 0.8
    gesto = np.convolve(boca, np.ones(25) / 25, mode="same")

    subs = [(I0 + a, I0 + b, capa_sub(t)) for a, b, t in V1.trocea(frases, 9)]
    cab = G2.capa_cabecera(G["fecha"])
    blq = capa_bloque("Óscar Puente: no dimite y crece la presión", "02 / 05")
    # escena A
    puente = tarjeta("Óscar Puente", "Ministro de Transportes · PSOE", "PSOE", 620, "«Me espera un calvario»", "La Vanguardia")
    sello_a = sello("NO DIMITE")
    sanchez = tarjeta("Pedro Sánchez", "Presidente del Gobierno · PSOE", "PSOE", 620,
                      "Consideró «injusto» cesarle", "La Vanguardia")
    txt_a = texto("Puso su cargo a disposición del presidente", 30, GRIS, ancho=520)
    # escena B
    mapa, av = capa_mapa(), aviso()
    xm, ym = proy(-3.7, 40.4)
    xb, yb = proy(2.17, 41.39)
    tr = tren(math.atan2(yb - ym, xb - xm))
    txt_b1 = texto("¿Cierre del AVE Madrid–Barcelona?", 44, BLANCO, "Inter-Black.ttf", 440)
    txt_b2 = texto("Lo plantea Óscar Puente por motivos de seguridad", 30, GRIS, ancho=440)
    txt_b3 = texto("Fuente: Europa Press", 22, GRIS)
    # escena C
    rot_c = rotulo("LA OPOSICIÓN")
    bravo = tarjeta_compacta("Juan Bravo", "Vicesecretario del PP", "PP", 1180,
                    "«Esto no se puede despachar diciendo que es una fatalidad o buscando una cabeza de turco»", "20minutos", tc=30)
    abascal = tarjeta_compacta("Santiago Abascal", "Presidente de Vox", "Vox", 1180,
                      "El posible cierre del AVE demuestra que el Gobierno es «responsable»", "Europa Press", tc=30)
    garriga = tarjeta_compacta("Ignacio Garriga", "Vox", "Vox", 1180, "Denuncia la «tercermundización» de la red ferroviaria", "20minutos", tc=30)
    # escena D
    rot_d = rotulo("LOS SOCIOS DEL GOBIERNO")
    puente_d = tarjeta("Óscar Puente", "Ministro de Transportes", "PSOE", 520)
    chips = [chip("Frente Amplio", "Frente Amplio"), chip("PNV", "PNV"), chip("BNG", "BNG")]
    pod = chip("Podemos", "Podemos", apagado=True)
    txt_d1 = texto("Piden que se asuman responsabilidades", 30, BLANCO, "Inter-SemiBold.ttf", 470)
    txt_d2 = texto("Evita pedir expresamente la dimisión", 30, GRIS, ancho=470)
    txt_d3 = texto("Fuentes: elDiario.es · Europa Press", 22, GRIS)

    out = dia / "prototipo_animado.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], stdin=subprocess.PIPE)
    def vis(t, a, b):
        """opacidad de una escena que dura de a a b"""
        return min(suave((t - a) / 0.45), 1 - suave((t - (b - 0.35)) / 0.35))
    nf = int(math.ceil(total * FPS))
    for fi in range(nf):
        t = fi / FPS
        if t < I0 or t >= fin:
            fr = G2.cuadro_intro(t, G["fecha"]) if t < I0 else G2.cuadro_cierre(t - fin, G["fecha"])
            ff.stdin.write(fr.convert("RGB").tobytes())
            continue
        fr = G2.fondo_marca(t)
        fr.alpha_composite(cab)
        pega(fr, blq, 100, 108)
        d = ImageDraw.Draw(fr)
        # A: Puente sigue / no dimite / se lo ofrecio a Sanchez
        o = vis(t, tA, tB)
        if o > 0:
            a = suave((t - tA - 0.2) / 0.5)
            pega(fr, puente, 640 + 60 * (1 - a), 250, o * a)
            s = suave((t - tA - 1.2) / 0.35)
            if s > 0:
                st = sello_a.resize((int(sello_a.width * (1.5 - 0.5 * s)), int(sello_a.height * (1.5 - 0.5 * s))))
                pega(fr, st, 1130 - st.width / 2 + 120, 255 - st.height / 2, o * s)
            q = suave((t - tSan - 1.0) / 0.8)
            flecha(d, (950, 250 + puente.height + 10), (1180, 560), q * o)
            pega(fr, txt_a, 660, 250 + puente.height + 60, o * suave((t - tSan - 1.2) / 0.5))
            b = suave((t - tSan - 2.4) / 0.5)
            pega(fr, sanchez, 1180 + 60 * (1 - b), 560, o * b)
        # B: mapa y posible cierre
        o = vis(t, tB, tC)
        if o > 0:
            pega(fr, mapa, 0, 0, o)
            p = suave((t - tB - 0.6) / 2.0)
            if p > 0:
                d.line([(xm, ym), (xm + (xb - xm) * p, ym + (yb - ym) * p)], fill=AMARILLO + (int(255 * o),), width=10)
                pos = min(p, 0.62)
                pega(fr, tr, xm + (xb - xm) * pos - tr.width / 2, ym + (yb - ym) * pos - tr.height / 2 - 30, o)
            s = suave((t - tB - 2.8) / 0.4)
            if s > 0:
                ax, ay = xm + (xb - xm) * 0.78, ym + (yb - ym) * 0.78
                pega(fr, av, ax - 60, ay - 130 - 20 * (1 - s), o * s)
            pega(fr, txt_b1, 1420, 470, o * suave((t - tB - 3.0) / 0.5))
            pega(fr, txt_b2, 1420, 470 + txt_b1.height + 10, o * suave((t - tB - 3.4) / 0.5))
            pega(fr, txt_b3, 1420, 470 + txt_b1.height + txt_b2.height + 30, o * suave((t - tB - 3.6) / 0.5))
        # C: la oposicion
        o = vis(t, tC, tD)
        if o > 0:
            pega(fr, rot_c, 640, 215, o)
            y = 262
            for tarj, t1 in ((bravo, tBravo), (abascal, tAbascal), (garriga, tGarriga)):
                a = suave((t - t1) / 0.5)
                pega(fr, tarj, 640 + 80 * (1 - a), y, o * a)
                y += tarj.height + 12
        # D: los socios
        o = vis(t, tD, fin + 0.4)
        if o > 0:
            pega(fr, rot_d, 640, 215, o)
            a = suave((t - tD - 0.1) / 0.5)
            pega(fr, puente_d, 640, 420, o * a)
            for k, c in enumerate(chips):
                a = suave((t - tD - 1.6 - 0.35 * k) / 0.5)
                yc = 290 + k * 110
                pega(fr, c, 1340 + 120 * (1 - a), yc, o * a)
                flecha(d, (1330, yc + 39), (1170, 480 + 20 * (k - 1)), suave((t - tD - 2.4 - 0.35 * k) / 0.5) * o,
                       AMARILLO + (int(255 * o),), 6)
            pega(fr, txt_d1, 1340, 630, o * suave((t - tD - 3.0) / 0.5))
            a = suave((t - tPod) / 0.5)
            pega(fr, pod, 1340, 730, o * a)
            pega(fr, txt_d2, 1340, 820, o * a)
            pega(fr, txt_d3, 640, 870, o * a)
        # presentador
        k = min(fi - int(I0 * FPS), len(boca) - 1)
        bo = float(boca[k]) if k >= 0 else 0.0
        par = (t % 3.7) < 0.12 or (t % 5.3) < 0.1
        ent = suave((t - I0) / 0.6)
        m = mascota(t, bo, par, float(gesto[max(k, 0)]))
        pega(fr, m, 90, 520 + 200 * (1 - ent), ent)
        for a0, b0, cs in subs:
            if a0 <= t < b0:
                pega(fr, cs, 1210 - cs.width / 2, AL - cs.height - 40)
                break
        d.rectangle([0, AL - 8, int(AN * (t - I0) / dur), AL], fill=AMARILLO + (255,))
        if t - I0 < G2.CORTINILLA:                                   # cortinilla de entrada
            q = (t - I0) / G2.CORTINILLA
            x0 = int(AN * (2.2 * q - 1.2))
            d.rectangle([x0, 0, x0 + AN, AL], fill=ROJO + (255,))
            d.rectangle([x0 + AN, 0, x0 + AN + 40, AL], fill=AMARILLO + (255,))
        ff.stdin.write(fr.convert("RGB").tobytes())
        if fi % (FPS * 10) == 0:
            print(f"  fotograma {fi}/{nf}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"PROTOTIPO {total:.1f} s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
