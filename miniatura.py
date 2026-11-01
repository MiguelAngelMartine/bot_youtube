"""Herramienta del DISENADOR GRAFICO: miniatura del episodio (1280x720) y, con --canal, banner (2560x1440) y avatar (800x800).
Todo con la identidad fija del canal: fondo azul con franjas, rojo y amarillo, Urni y el logo. Nunca caras ni fotos ajenas.
Uso: python miniatura.py AAAA-MM-DD --titular "Puente resiste" --destaca "resiste" [--ante "CRISIS FERROVIARIA"] [--sobrio]
     python miniatura.py --canal"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

import genera_video2 as G2
import prototipo_animado as P
from genera_video2 import AMARILLO, BLANCO, ROJO, fuente

MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
RAIZ = Path(__file__).parent


def lineas_ajustadas(d, palabras, ancho, tam_max, tam_min, max_lineas=2):
    """La letra mas grande con la que el titular cabe en max_lineas."""
    for tam in range(tam_max, tam_min - 1, -6):
        f = fuente("Inter-Black.ttf", tam)
        lineas, cur = [], []
        for w in palabras:
            if cur and d.textlength(" ".join(cur + [w]), font=f) > ancho:
                lineas.append(cur)
                cur = [w]
            else:
                cur.append(w)
        lineas.append(cur)
        if len(lineas) <= max_lineas and all(d.textlength(" ".join(l), font=f) <= ancho for l in lineas):
            return tam, lineas
    return tam_min, lineas


def miniatura(dia_txt, titular, destaca="", ante="", sobrio=False):
    dia = RAIZ / "dia" / dia_txt
    W, H = 1920, 1080                                     # se dibuja a 1,5x y se reduce a 1280x720
    im = G2.fondo_marca(2.0)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 14], fill=ROJO + (255,))
    d.rectangle([0, 14, W, 22], fill=AMARILLO + (255,))
    im.alpha_composite(G2.logo(120), (80, 70))
    d.text((222, 130), G2.MARCA, font=fuente("Inter-Black.ttf", 58), fill=AMARILLO + (255,), anchor="lm")
    y, m, dd = (int(x) for x in dia_txt.split("-"))
    etiqueta = f"{dd} {MESES[m - 1]} {y}"
    fe = fuente("Inter-Black.ttf", 50)
    we = int(d.textlength(etiqueta, font=fe)) + 70
    d.rounded_rectangle([W - 80 - we, 92, W - 80, 168], radius=38, fill=ROJO + (255,))
    d.text((W - 80 - we / 2, 130), etiqueta, font=fe, fill=BLANCO + (255,), anchor="mm")
    ancho = 1750 if sobrio else 1120
    yt = 300
    if ante:
        d.text((90, yt), ante.upper(), font=fuente("Inter-Black.ttf", 66), fill=AMARILLO + (255,))
        yt += 110
    tam, lineas = lineas_ajustadas(d, titular.split(), ancho, 230, 120)
    f = fuente("Inter-Black.ttf", tam)
    marca = {w.lower().strip("¿?¡!.,:;") for w in destaca.split()}
    for l in lineas:
        x = 90
        for w in l:
            col = AMARILLO if w.lower().strip("¿?¡!.,:;") in marca else BLANCO
            d.text((x + 6, yt + 8), w, font=f, fill=(0, 0, 0, 140))
            d.text((x, yt), w, font=f, fill=col + (255,))
            x += d.textlength(w + " ", font=f)
        yt += int(tam * 1.08)
    if not sobrio:
        u = P.mascota(0.6, 0.55, False, 0.9)
        u = u.resize((int(u.width * 1.9), int(u.height * 1.9)), Image.LANCZOS)
        im.alpha_composite(u, (W - u.width - 40, H - u.height + 30))
    out = dia / "miniatura.png"
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out)
    print(f"miniatura ({tam}px, {len(lineas)} lineas) -> {out}")


def canal():
    dest = RAIZ / "canal"
    dest.mkdir(exist_ok=True)
    # banner: la zona segura que se ve en todos los dispositivos es el centro, 1546x423
    W, H = 2560, 1440
    im = Image.new("RGBA", (W, H))
    base = G2.fondo_marca(3.0).resize((W, H), Image.LANCZOS)
    im.alpha_composite(base)
    d = ImageDraw.Draw(im)
    x0, y0 = (W - 1546) // 2, (H - 423) // 2
    im.alpha_composite(G2.logo(260), (x0 + 10, y0 + 82))
    d.text((x0 + 300, y0 + 150), G2.MARCA, font=fuente("Inter-Black.ttf", 92), fill=BLANCO + (255,), anchor="lm")
    d.text((x0 + 304, y0 + 250), G2.LEMA, font=fuente("Inter-Regular.ttf", 42), fill=(220, 225, 235, 255), anchor="lm")
    d.text((x0 + 304, y0 + 315), "Cada noche, con datos y fuentes", font=fuente("Inter-SemiBold.ttf", 38), fill=AMARILLO + (255,), anchor="lm")
    u = P.mascota(0.6, 0.0, False, 1.0)
    u = u.resize((int(u.width * 0.74), int(u.height * 0.74)), Image.LANCZOS)
    im.alpha_composite(u, (x0 + 1546 - u.width, y0 + 423 - u.height + 20))
    d.rectangle([0, H - 30, W, H - 18], fill=AMARILLO + (255,))
    d.rectangle([0, H - 18, W, H], fill=ROJO + (255,))
    im.convert("RGB").save(dest / "banner.png")
    # avatar: YouTube lo recorta en circulo; el logo ocupa el centro sobre rojo liso
    av = Image.new("RGBA", (800, 800), ROJO + (255,))
    av.alpha_composite(G2.logo(800))
    av.convert("RGB").save(dest / "avatar.png")
    print(f"banner y avatar -> {dest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dia", nargs="?")
    ap.add_argument("--titular")
    ap.add_argument("--destaca", default="")
    ap.add_argument("--ante", default="")
    ap.add_argument("--sobrio", action="store_true")
    ap.add_argument("--canal", action="store_true")
    a = ap.parse_args()
    if a.canal:
        canal()
    else:
        miniatura(a.dia or date.today().isoformat(), a.titular, a.destaca, a.ante, a.sobrio)
