"""Herramienta del DISENADOR GRAFICO: miniatura del episodio (1280x720) y, con --canal, banner (2560x1440) y avatar (800x800).

Estilo de las miniaturas (elegido por el usuario el 1-nov-2026, referencia en canal/miniatura_referencia.png):
- de fondo, una foto real del tema (tren, edificio, lugar), oscurecida y algo desenfocada;
- el protagonista recortado a la derecha, con un filo blanco fino y una sombra suave (sin halo de color);
- un titular corto y enorme abajo a la izquierda: letras con degradado (blanco y una palabra en amarillo-oro),
  contorno negro grueso, filo claro, relieve 3D y algo inclinado;
- una etiqueta roja encima con el hecho (por ejemplo «PUENTE NO DIMITE»), el logo arriba a la izquierda y marco amarillo.
--sobrio (tragedias): foto en grises, letra blanca lisa sin relieve ni inclinacion, sin marco ni color de gancho.

Uso: python miniatura.py AAAA-MM-DD --titular "«Me espera un calvario»" --destaca "calvario" \
         [--etiqueta "Puente no dimite"] [--persona miniatura_puente.jpg] [--fondo s1_2.jpg] [--sobrio]
     (--persona y --fondo son ficheros de dia/<fecha>/imagenes/, elegidos con fotos.py para que quede su credito)
     python miniatura.py --canal"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

import genera_video2 as G2
import prototipo_animado as P
from genera_video2 import AMARILLO, BLANCO, ROJO, fuente

RAIZ = Path(__file__).parent
W, H = 1920, 1080                                   # se dibuja a 1,5x y se reduce a 1280x720
GRAD = {"blanco": ((255, 255, 255), (245, 246, 250), (196, 202, 214)),
        "amarillo": ((255, 240, 120), (250, 200, 10), (226, 128, 0))}
LISO = {"blanco": (BLANCO,) * 3, "amarillo": (AMARILLO,) * 3}
LIMPIA = "¿?¡!.,:;«»\"'"


# ---------- piezas ----------
def recorte(foto: Path) -> Image.Image:
    """Persona sin fondo (rembg). Se guarda junto a la foto para no repetirlo."""
    cache = foto.with_name(foto.stem + "_recorte.png")
    if cache.exists():
        return Image.open(cache).convert("RGBA")
    from rembg import new_session, remove             # pesado: solo se importa si hace falta
    im = Image.open(foto).convert("RGB")
    c = remove(im, session=new_session("u2net_human_seg"))
    a = c.getchannel("A").point(lambda v: 255 if v > 100 else 0)
    f = a.copy()
    ImageDraw.floodfill(f, (0, 0), 128)               # huecos interiores (entre brazo y corbata...) son persona
    a = np.array(f.point(lambda v: 0 if v == 128 else 255))
    filas = np.nonzero(a.any(axis=1))[0]
    for y in range(int(filas[0] + 0.7 * (filas[-1] - filas[0])), filas[-1] + 1):   # parte baja: sin muescas
        xs = np.nonzero(a[y])[0]                       # (un cartel o una mesa delante dejan un hueco que el
        if len(xs):                                    # filo blanco convertiria en un recuadro)
            a[y, xs[0]:xs[-1] + 1] = 255
    anchos = (a > 0).sum(axis=1)                       # si lo de abajo se estrecha (mesa, cartel), se corta ahi
    mitad = len(anchos) // 2
    llenas = np.nonzero(anchos[mitad:] >= 0.85 * anchos[mitad:].max())[0]
    a[mitad + llenas[-1] + 1:] = 0
    c.putalpha(Image.fromarray(a))
    c = c.crop(c.getchannel("A").getbbox())
    c.save(cache)
    return c


def silueta(c, borde=7):
    """Filo blanco fino y sombra oscura suave: separa a la persona del fondo sin efecto de foco detras."""
    pad = 60
    base = Image.new("RGBA", (c.width + pad * 2, c.height + pad * 2))
    a = Image.new("L", base.size)
    a.paste(c.getchannel("A"), (pad, pad))
    linea = a.filter(ImageFilter.MaxFilter(borde * 2 + 1)).filter(ImageFilter.GaussianBlur(1.2))
    sombra = linea.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.75))
    base.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", base.size).split(), sombra)), (-18, 14))
    base.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", base.size, (255, 255, 255)).split(), linea)))
    base.alpha_composite(c, (pad, pad))
    return base, pad


def fondo(foto: Path | None, sobrio: bool, con_persona: bool):
    if foto is None:
        return G2.fondo_marca(2.0).resize((W, H)).convert("RGBA")
    f = ImageOps.fit(Image.open(foto).convert("RGB"), (W, H), Image.LANCZOS)
    if sobrio:
        f = ImageOps.grayscale(f).convert("RGB")
    f = f.filter(ImageFilter.GaussianBlur(4 if con_persona else 1))
    f = ImageEnhance.Brightness(f).enhance(0.6 if sobrio else 0.72 if con_persona else 0.85)
    im = ImageEnhance.Contrast(f).enhance(1.15).convert("RGBA")
    vi = Image.new("L", (W, H), 0)                    # vineta: bordes mas oscuros
    ImageDraw.Draw(vi).ellipse([-300, -500, W + 500, H + 300], fill=255)
    vi = ImageOps.invert(vi.filter(ImageFilter.GaussianBlur(200))).point(lambda v: int(v * .8))
    im.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H)).split(), vi)))
    return im


def oscurece_abajo(im, alto=560, alfa=210):
    g = Image.linear_gradient("L").resize((1, alto)).point(lambda v: int(alfa * (v / 255) ** 1.4))
    capa = Image.new("RGBA", (W, alto), (0, 0, 0, 255))
    capa.putalpha(g.resize((W, alto)))
    im.alpha_composite(capa, (0, H - alto))


def degradado(tam, arriba, medio, abajo):
    w, h = tam
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        a, b, u = (arriba, medio, t / 0.55) if t < 0.55 else (medio, abajo, (t - 0.55) / 0.45)
        g.putpixel((0, y), tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3)))
    return g.resize((w, h))


def texto(lineas, tam, sobrio=False, interlinea=0.96):
    """Letra de miniatura: relleno en degradado, brillo arriba, contorno negro grueso, filo exterior claro
    y relieve 3D hacia abajo-derecha. En sobrio, letra lisa con contorno fino y sombra."""
    negro, exterior, relieve = (6, 0, 0) if sobrio else (18, 7, 16)
    colores = LISO if sobrio else GRAD
    f = fuente("Inter-Black.ttf", tam)
    m = negro + exterior + relieve + 30
    medir = ImageDraw.Draw(Image.new("L", (1, 1)))
    hueco = int(1.2 * (negro + exterior))              # el contorno se come el espacio entre palabras
    ancho = int(max(medir.textlength(" ".join(p for p, _ in l), font=f) + hueco * (len(l) - 1) for l in lineas)) + 2 * m
    alto = int(tam * interlinea * len(lineas) + tam * 0.35) + 2 * m
    relleno = Image.new("RGBA", (ancho, alto))
    M, S, E = (Image.new("L", (ancho, alto)) for _ in range(3))
    yy = m
    for l in lineas:
        xx = m
        for pal, col in l:
            mk = Image.new("L", (ancho, alto))
            ImageDraw.Draw(mk).text((xx, yy), pal, font=f, fill=255)
            bb = mk.getbbox()
            capa = Image.new("RGB", (ancho, alto))
            capa.paste(degradado((ancho, bb[3] - bb[1]), *colores[col]), (0, bb[1]))
            relleno.paste(capa, (0, 0), mk)
            M.paste(255, (0, 0), mk)
            ImageDraw.Draw(S).text((xx, yy), pal, font=f, fill=255, stroke_width=negro, stroke_fill=255)
            ImageDraw.Draw(E).text((xx, yy), pal, font=f, fill=255, stroke_width=negro + exterior, stroke_fill=255)
            xx += medir.textlength(pal + " ", font=f) + hueco
        yy += int(tam * interlinea)
    out = Image.new("RGBA", (ancho, alto))
    negra = lambda mascara, col=(0, 0, 0): Image.merge("RGBA", (*Image.new("RGB", (ancho, alto), col).split(), mascara))
    out.alpha_composite(negra(E.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .8))), (relieve + 10, relieve + 14))
    for i in range(relieve, 0, -1):
        tono = int(20 + 25 * (1 - i / relieve))
        out.alpha_composite(negra(E, (tono, tono, tono + 6)), (i, i))
    if exterior:
        out.alpha_composite(negra(E, (255, 255, 255)))
    out.alpha_composite(negra(S, (8, 8, 12)))
    out.alpha_composite(relleno)
    if not sobrio:                                     # brillo en el filo superior de cada letra
        filo = ImageChops.subtract(M, ImageChops.offset(M, 0, 5)).filter(ImageFilter.GaussianBlur(1))
        out.alpha_composite(negra(filo.point(lambda v: int(v * .7)), (255, 255, 255)))
    return out.crop(out.getbbox())


def ajusta(titular, destaca, ancho, sobrio):
    """La letra mas grande con la que el titular cabe en 2 lineas (3 si no hay otra)."""
    marca = {w.lower().strip(LIMPIA) for w in destaca.split()}
    palabras = [(w.upper(), "amarillo" if w.lower().strip(LIMPIA) in marca else "blanco") for w in titular.split()]
    medir = ImageDraw.Draw(Image.new("L", (1, 1)))
    for max_lineas in (2, 3):
        for tam in range(210, 109, -6):
            f = fuente("Inter-Black.ttf", tam)
            extra = 2 * (6 if sobrio else 25)
            lineas, cur = [], []
            for p in palabras:
                if cur and medir.textlength(" ".join(x for x, _ in cur + [p]), font=f) + extra + 30 * len(cur) > ancho:
                    lineas.append(cur)
                    cur = [p]
                else:
                    cur.append(p)
            lineas.append(cur)
            if len(lineas) <= max_lineas and all(medir.textlength(" ".join(x for x, _ in l), font=f) + extra + 30 * (len(l) - 1) <= ancho
                                                 for l in lineas):
                return tam, lineas
    return 110, lineas


def etiqueta(txt, sobrio=False, tam=58):
    f = fuente("Inter-Black.ttf", tam)
    w = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(txt, font=f)) + 60
    h = int(tam * 1.45)
    e = Image.new("RGBA", (w + 16, h + 16))
    d = ImageDraw.Draw(e)
    if sobrio:
        d.rectangle([0, 0, 10, h], fill=AMARILLO + (255,))
        d.text((34, h / 2 + 2), txt, font=f, fill=AMARILLO + (255,), anchor="lm")
        return e
    d.rounded_rectangle([10, 10, w + 10, h + 10], radius=12, fill=(0, 0, 0, 160))
    d.rounded_rectangle([0, 0, w, h], radius=12, fill=ROJO + (255,), outline=(255, 255, 255, 255), width=4)
    d.text((w / 2, h / 2 + 2), txt, font=f, fill=BLANCO + (255,), anchor="mm")
    return e


def marco(im, col=AMARILLO, grosor=22, radio=46):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=radio, fill=255)
    d.rounded_rectangle([grosor, grosor, W - 1 - grosor, H - 1 - grosor], radius=radio - 8, fill=0)
    capa = Image.new("RGBA", (W, H), col + (255,))
    capa.putalpha(m)
    im.alpha_composite(capa)
    fuera = Image.new("L", (W, H), 255)
    ImageDraw.Draw(fuera).rounded_rectangle([0, 0, W - 1, H - 1], radius=radio, fill=0)
    n = Image.new("RGBA", (W, H), (15, 15, 15, 255))
    n.putalpha(fuera)
    im.alpha_composite(n)


# ---------- miniatura ----------
def miniatura(dia_txt, titular, destaca="", etiqueta_txt="", persona="", foto_fondo="", sobrio=False, salida="miniatura.png"):
    dia = RAIZ / "dia" / dia_txt
    img = dia / "imagenes"
    for nombre in (persona, foto_fondo):
        if nombre and not (img / nombre).exists():
            raise SystemExit(f"no existe {img / nombre}: guardala antes con fotos.py elegir")
    im = fondo(img / foto_fondo if foto_fondo else None, sobrio, bool(persona))
    oscurece_abajo(im, 560 if persona else 700, 210 if persona else 240)
    ancho_texto = 1750
    if persona:
        c = recorte(img / persona)
        if sobrio:
            c = Image.merge("RGBA", (*ImageOps.grayscale(c.convert("RGB")).convert("RGB").split(), c.getchannel("A")))
        k = min(1000 / c.height, 1000 / c.width)
        c, pad = silueta(c.resize((int(c.width * k), int(c.height * k)), Image.LANCZOS))
        x = W - c.width + 150
        im.alpha_composite(c, (x, H - c.height + pad + 30))     # el borde de abajo, fuera de cuadro
        ancho_texto = min(1750, x + pad + 120 - 50)        # el texto puede montar un poco sobre el hombro
    tam, lineas = ajusta(titular, destaca, ancho_texto, sobrio)
    t = texto(lineas, tam, sobrio)
    inclina = 0 if sobrio else 4
    if inclina:
        t = t.rotate(inclina, resample=Image.BICUBIC, expand=True)
    y = H - t.height - 40
    im.alpha_composite(t, (30 if not sobrio else 70, y))
    if etiqueta_txt:
        e = etiqueta(etiqueta_txt.upper(), sobrio)
        if inclina:
            e = e.rotate(inclina, resample=Image.BICUBIC, expand=True)
        im.alpha_composite(e, (80, max(190, y - e.height + 30)))
    im.alpha_composite(G2.logo(110), (60, 50))
    if not sobrio:
        marco(im)
    out = dia / salida
    im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out)
    print(f"miniatura ({tam}px, {len(lineas)} lineas{', sobria' if sobrio else ''}) -> {out}")


# ---------- banner y avatar del canal ----------
def canal():
    dest = RAIZ / "canal"
    dest.mkdir(exist_ok=True)
    # banner: la zona segura que se ve en todos los dispositivos es el centro, 1546x423
    W2, H2 = 2560, 1440
    im = Image.new("RGBA", (W2, H2))
    base = G2.fondo_marca(3.0).resize((W2, H2), Image.LANCZOS)
    im.alpha_composite(base)
    d = ImageDraw.Draw(im)
    x0, y0 = (W2 - 1546) // 2, (H2 - 423) // 2
    im.alpha_composite(G2.logo(260), (x0 + 10, y0 + 82))
    d.text((x0 + 300, y0 + 150), G2.MARCA, font=fuente("Inter-Black.ttf", 92), fill=BLANCO + (255,), anchor="lm")
    d.text((x0 + 304, y0 + 250), G2.LEMA, font=fuente("Inter-Regular.ttf", 42), fill=(220, 225, 235, 255), anchor="lm")
    d.text((x0 + 304, y0 + 315), "Cada noche, con datos y fuentes", font=fuente("Inter-SemiBold.ttf", 38), fill=AMARILLO + (255,), anchor="lm")
    u = P.mascota(0.6, 0.0, False, 1.0)
    u = u.resize((int(u.width * 0.74), int(u.height * 0.74)), Image.LANCZOS)
    im.alpha_composite(u, (x0 + 1546 - u.width, y0 + 423 - u.height + 20))
    d.rectangle([0, H2 - 30, W2, H2 - 18], fill=AMARILLO + (255,))
    d.rectangle([0, H2 - 18, W2, H2], fill=ROJO + (255,))
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
    ap.add_argument("--etiqueta", default="")
    ap.add_argument("--persona", default="")
    ap.add_argument("--fondo", default="")
    ap.add_argument("--sobrio", action="store_true")
    ap.add_argument("--salida", default="miniatura.png")
    ap.add_argument("--canal", action="store_true")
    a = ap.parse_args()
    if a.canal:
        canal()
    else:
        miniatura(a.dia or date.today().isoformat(), a.titular, a.destaca, a.etiqueta, a.persona, a.fondo, a.sobrio, a.salida)
