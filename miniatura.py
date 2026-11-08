"""Herramienta del DISENADOR GRAFICO: miniatura del episodio (1280x720) y, con --canal, banner (2560x1440) y avatar (800x800).

Estilo de las miniaturas (elegido por el usuario el 1-nov-2026, referencia en canal/miniatura_referencia.png):
- de fondo, una foto real del tema (tren, edificio, lugar), oscurecida y algo desenfocada;
- el protagonista recortado a la derecha, con un filo blanco fino y una sombra suave (sin halo de color);
- un titular corto y enorme abajo a la izquierda: letras con degradado (blanco y una palabra en amarillo-oro),
  contorno negro grueso, filo claro, relieve 3D y algo inclinado;
- una etiqueta roja encima con el hecho (por ejemplo «PUENTE NO DIMITE»), el logo arriba a la izquierda y marco amarillo.
--sobrio (tragedias): foto a color (nunca en grises, 4-nov-2026), letra blanca lisa sin relieve ni inclinacion, sin marco ni color de gancho.

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
    for xy in ((0, 0), (f.width - 1, 0), (0, f.height - 1), (f.width - 1, f.height - 1)):   # 7-nov: desde las 4 esquinas
        if f.getpixel(xy) == 0:                       # (si el pelo toca el borde, un fondo oscuro quedaba como «hueco»)
            ImageDraw.floodfill(f, xy, 128)           # huecos interiores (entre brazo y corbata...) son persona
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


def silueta_suave(c):
    """Contorno fino y suave (decision del usuario del 4-nov-2026): linea clara tenue, luz de borde difusa y sombra
    blanda. Resalta a la persona sin el filo blanco grueso de pegatina."""
    pad = 40
    a = Image.new("L", (c.width + 2 * pad, c.height + 2 * pad))
    a.paste(c.getchannel("A"), (pad, pad))
    base = Image.new("RGBA", a.size)
    sombra = a.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.6))
    base.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", a.size).split(), sombra)), (-10, 12))
    luz = a.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.28))
    base.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", a.size, (235, 240, 255)).split(), luz)))
    linea = a.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1)).point(lambda v: int(v * 0.6))
    base.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", a.size, (255, 255, 255)).split(), linea)))
    base.alpha_composite(c, (pad, pad))
    return base, pad


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
    if con_persona:                                    # fondo: a color (4-nov-2026), apagado y desenfocado; manda la cara
        f = ImageEnhance.Color(f.filter(ImageFilter.GaussianBlur(13))).enhance(0.7)
    f = f.filter(ImageFilter.GaussianBlur(4 if con_persona else 1))
    f = ImageEnhance.Brightness(f).enhance(0.6 if sobrio else 0.6 if con_persona else 0.85)
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


def texto(lineas, tam, sobrio=False, interlinea=0.96, espacio=1.0):
    """Letra de miniatura: relleno en degradado, brillo arriba, contorno negro grueso, filo exterior claro
    y relieve 3D hacia abajo-derecha. En sobrio, letra lisa con contorno fino y sombra."""
    negro, exterior, relieve = (6, 0, 0) if sobrio else (18, 7, 16)
    colores = LISO if sobrio else GRAD
    f = fuente("Inter-Black.ttf", tam)
    m = negro + exterior + relieve + 30
    medir = ImageDraw.Draw(Image.new("L", (1, 1)))
    hueco = int(0.7 * (negro + exterior))              # el contorno se come el espacio entre palabras
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
            xx += medir.textlength(pal, font=f) + espacio * medir.textlength(" ", font=f) + hueco
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
        for tam in range(300 if len(palabras) == 1 else 210, 109, -6):   # una sola palabra («DIMITE»), aun mas grande
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


YUNET = RAIZ / "cache" / "modelos" / "yunet.onnx"      # detector de caras de OpenCV (YuNet, licencia MIT)
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"


def cara(c):
    """Caja de la cara (x, y, ancho, alto) en un recorte, o None. Sirve para encuadrar igual que un fotografo."""
    import cv2
    if not YUNET.exists():
        import requests
        YUNET.parent.mkdir(parents=True, exist_ok=True)
        YUNET.write_bytes(requests.get(YUNET_URL, timeout=60).content)
    rgb = np.array(c.convert("RGB"))[:, :, ::-1].copy()
    k = min(1.0, 900 / max(rgb.shape[:2]))            # el detector va mejor con imagenes medianas
    if k < 1:
        rgb = cv2.resize(rgb, (int(rgb.shape[1] * k), int(rgb.shape[0] * k)))
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (rgb.shape[1], rgb.shape[0]), 0.7)
    _, caras = det.detect(rgb)
    if caras is None or not len(caras):
        return None
    x, y, w, h = max(caras, key=lambda f: f[2] * f[3])[:4]
    return tuple(int(v / k) for v in (x, y, w, h))


def encuadre_cara(c, ancho, alto, centro=(0.72, 0.37), alto_cara=0.30, suave=False):
    """Encuadre profesional por la cara para un lienzo ancho x alto: la cara grande (alto_cara del alto) y centrada en
    'centro'; el cuerpo sale por abajo y se disuelve sin cortes rectos. Devuelve (imagen, x, y) o None si no hay cara."""
    k = cara(c)
    if not k:
        return None
    fx, fy, fw, fh = k
    s = alto_cara * alto / fh
    if s > 2.4:
        print(f"  AVISO: la foto se amplia x{s:.1f}; busca una de mas resolucion (fotos.py la baja original)")
    c = realza(c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS))
    visible = alto - (centro[1] * alto - (fy + fh / 2) * s)
    ini = int(min(c.height, visible) * 0.5)
    g = np.ones(c.height, dtype=np.float32)
    g[ini:] = np.clip(1 - (np.arange(c.height - ini) / max(1, min(c.height, visible) - ini)) ** 1.6, 0, 1)
    a = np.asarray(c.getchannel("A"), dtype=np.float32) * g[:, None]
    ancho_f = max(1, int(c.width * 0.2))
    rampa = np.linspace(0, 1, ancho_f) ** 0.8
    for lado in (0, -1):                               # lados cortados del recorte: tambien se disuelven
        if (a[:, lado] > 128).mean() > 0.12:
            if lado == 0:
                a[:, :ancho_f] *= rampa[None, :]
            else:
                a[:, -ancho_f:] *= rampa[::-1][None, :]
    c.putalpha(Image.fromarray(a.astype(np.uint8)))
    cc, pad = silueta_suave(c) if suave else silueta(c, borde=6)
    x = int(centro[0] * ancho - (fx + fw / 2) * s) - pad
    y = int(centro[1] * alto - (fy + fh / 2) * s) - pad
    if y + cc.height - pad < alto:                     # el cuerpo siempre sale por abajo
        y = alto - cc.height + pad + 10
    return cc, x, y


def protagonista(im, c, centro=(0.72, 0.37), alto_cara=0.30):
    """Miniatura: protagonista encuadrado por la cara. Devuelve su x izquierda o None si no hay cara."""
    r = encuadre_cara(c, W, H, centro, alto_cara)
    if not r:
        return None
    cc, x, y = r
    im.alpha_composite(cc, (x, y))
    return x + 40


def rayos(im, desde=(0.95, -0.15), color=(255, 214, 140), fuerza=46):
    """Luz que entra en diagonal por el fondo (no es un halo alrededor de la persona): da profundidad y dramatismo."""
    capa = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(capa)
    ox, oy = desde[0] * W, desde[1] * H
    import math as _m
    for k in range(7):
        a = _m.radians(118 + k * 7.5)
        ancho = _m.radians(1.6 + (k % 3) * 0.9)
        largo = 2.6 * W
        d.polygon([(ox, oy), (ox + largo * _m.cos(a - ancho), oy + largo * _m.sin(a - ancho)),
                   (ox + largo * _m.cos(a + ancho), oy + largo * _m.sin(a + ancho))], fill=fuerza + 10 * (k % 2))
    capa = capa.filter(ImageFilter.GaussianBlur(28))
    im.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), color).split(), capa)))


def grano(im, fuerza=7):
    """Grano fino de pelicula: quita el aspecto plano de imagen generada."""
    a = np.asarray(im).astype(np.int16)
    ruido = np.random.default_rng(7).integers(-fuerza, fuerza + 1, a.shape[:2])[..., None]
    a[..., :3] = np.clip(a[..., :3] + ruido, 0, 255)
    return Image.fromarray(a.astype(np.uint8), im.mode)


def insignia(im, txt):
    """Distintivo arriba a la derecha («ESPECIAL», «ÚLTIMA HORA» solo si lo es)."""
    f = fuente("Inter-Black.ttf", 54)
    w = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(txt, font=f)) + 70
    e = Image.new("RGBA", (w + 20, 110))
    d = ImageDraw.Draw(e)
    d.rounded_rectangle([12, 14, w + 12, 96], radius=14, fill=(0, 0, 0, 150))
    d.rounded_rectangle([0, 0, w, 82], radius=14, fill=AMARILLO + (255,))
    d.text((w / 2, 43), txt, font=f, fill=(15, 15, 20, 255), anchor="mm")
    e = e.rotate(-4, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(e, (W - e.width - 70, 54))


def realza(c):
    """Persona con mas presencia: algo mas de contraste, color y nitidez (sin cambiar sus rasgos)."""
    rgb = c.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.08)     # sin subir el color: exagera las luces de escenario
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
    return Image.merge("RGBA", (*rgb.split(), c.getchannel("A")))


def encuadre(c, alto):
    """Plano mas cerrado: de la cabeza al pecho (el 72 % de arriba del recorte), escalado a 'alto' px."""
    c = c.crop((0, 0, c.width, int(c.height * 0.72)))
    k = alto / c.height
    return c.resize((int(c.width * k), alto), Image.LANCZOS)


def gradua(im, vs=False):
    """Acabado dramatico del fondo: azul noche desde el lado del texto y, en enfrentamiento, cada mitad con su tono."""
    capa = Image.new("RGBA", (W, H))
    g = Image.linear_gradient("L").rotate(90, expand=True).resize((W, H))      # izquierda opaca -> derecha clara
    if vs:
        izq = Image.new("RGBA", (W, H), (120, 10, 25, 255))
        der = Image.new("RGBA", (W, H), (10, 25, 70, 255))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([(0, 0), (W * 0.56, 0), (W * 0.44, H), (0, H)], fill=150)
        capa.alpha_composite(Image.merge("RGBA", (*izq.convert("RGB").split(), m)))
        m2 = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m2).polygon([(W * 0.56, 0), (W, 0), (W, H), (W * 0.44, H)], fill=150)
        capa.alpha_composite(Image.merge("RGBA", (*der.convert("RGB").split(), m2)))
    else:
        azul = Image.new("RGB", (W, H), (8, 18, 48))
        capa = Image.merge("RGBA", (*azul.split(), g.point(lambda v: int(v * 0.62))))
    im.alpha_composite(capa)


def diagonal(im):
    """Rayo amarillo del enfrentamiento, con sombra."""
    for desp, col, ancho in ((10, (0, 0, 0, 150), 30), (0, AMARILLO + (255,), 22)):
        ImageDraw.Draw(im).line([(W * 0.56 + desp, -20), (W * 0.44 + desp, H + 20)], fill=col, width=ancho)


def polaroid_mini(foto: Path, ancho=440, giro=-6):
    """Foto secundaria en polaroid inclinada, con sombra (contexto de la noticia)."""
    f = ImageOps.fit(Image.open(foto).convert("RGB"), (ancho, int(ancho * 0.66)), Image.LANCZOS)
    f = ImageEnhance.Contrast(f).enhance(1.1)
    b = 18
    p = Image.new("RGBA", (f.width + 2 * b, f.height + 2 * b + 26), (250, 248, 242, 255))
    p.paste(f, (b, b))
    s = Image.new("RGBA", (p.width + 60, p.height + 60))
    m = Image.new("L", s.size, 0)
    ImageDraw.Draw(m).rectangle([30, 34, 30 + p.width, 34 + p.height], fill=170)
    s.putalpha(m.filter(ImageFilter.GaussianBlur(14)))
    s.alpha_composite(p, (24, 24))
    return s.rotate(giro, resample=Image.BICUBIC, expand=True)


# ---------- miniatura ----------
def miniatura(dia_txt, titular, destaca="", etiqueta_txt="", persona="", foto_fondo="", sobrio=False, salida="miniatura.png",
              rival="", inserto="", insignia_txt="", caricatura=False, gestos=("", "")):
    dia = RAIZ / "dia" / dia_txt
    img = dia / "imagenes"
    for nombre in (persona, foto_fondo, rival, inserto):
        if nombre and not (img / nombre).exists():
            raise SystemExit(f"no existe {img / nombre}: guardala antes con fotos.py elegir")
    im = fondo(img / foto_fondo if foto_fondo else None, sobrio, bool(persona))
    vs = bool(rival and persona and not sobrio)
    if not sobrio:
        gradua(im, vs)
    oscurece_abajo(im, 560 if persona else 700, 210 if persona else 240)
    ancho_texto = 1750
    if vs:                                             # enfrentamiento: una persona a cada lado, cara a cara
        diagonal(im)
        for (nombre, lado), gesto in zip(((rival, "izq"), (persona, "der")), gestos):
            r = recorte(img / nombre if not caricatura else _caricatura(dia, nombre, lado, gesto))
            k = min(1000 / r.height, 760 / r.width)
            cc, pad = silueta(realza(r.resize((int(r.width * k), int(r.height * k)), Image.LANCZOS)))
            x = -pad + 10 if lado == "izq" else W - cc.width + pad - 10
            im.alpha_composite(cc, (x, H - cc.height + pad - 10))     # hasta el borde de abajo; el titular, sobre los pechos
        oscurece_abajo(im, 380, 200)                   # el titular, legible sobre los dos
        ancho_texto = 1250                             # mas contenido: no puede tapar las caras
    elif persona:
        c = recorte(img / persona)                     # siempre a color (4-nov-2026)
        if sobrio:
            k = min(1000 / c.height, 1000 / c.width)
            c = c.resize((int(c.width * k), int(c.height * k)), Image.LANCZOS)
        x = None
        if not sobrio:
            rayos(im)
            x = protagonista(im, c)                    # encuadre por la cara, como un fotografo
            if x is not None:
                ancho_texto = min(1750, x + 170)       # el texto puede montar un poco sobre el hombro
        if x is None:                                  # sin cara detectable (o sobria): como antes
            if not sobrio:
                c = realza(encuadre(c, 960))
            c, pad = silueta(c)
            x = W - c.width + 150
            im.alpha_composite(c, (x, H - c.height + pad + 30))     # el borde de abajo, fuera de cuadro
            ancho_texto = min(1750, x + pad + 120 - 50)        # el texto puede montar un poco sobre el hombro
    tam, lineas = ajusta(titular, destaca, ancho_texto, sobrio)
    t = texto(lineas, tam, sobrio)
    if vs:                                             # 7-nov: franja roja de brocha detras del titular (referencia)
        t = brocha(t)
    inclina = 0 if sobrio else 4
    if inclina:
        t = t.rotate(inclina, resample=Image.BICUBIC, expand=True)
    y = H - t.height - (10 if vs else 40)
    if inserto and not sobrio and not vs:              # foto secundaria del lugar u objeto de la noticia
        pm = polaroid_mini(img / inserto)
        im.alpha_composite(pm, (150, max(40, y - pm.height - 40)))
    tx = (W - t.width) // 2 if vs else (30 if not sobrio else 70)
    im.alpha_composite(t, (tx, y))
    if etiqueta_txt:
        e = etiqueta(etiqueta_txt.upper(), sobrio)
        if inclina:
            e = e.rotate(inclina, resample=Image.BICUBIC, expand=True)
        ex = (W - e.width) // 2 if vs else 80
        im.alpha_composite(e, (ex, max(190, y - e.height + 30)))
    im.alpha_composite(G2.logo(110), (60, 50))
    if insignia_txt and not sobrio:
        insignia(im, insignia_txt.upper())
    if not sobrio:
        im = grano(im)
        marco(im)
    out = dia / salida
    fin = im.convert("RGB").resize((1280, 720), Image.LANCZOS)
    fin.filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=2)).save(out)     # nitidez final
    print(f"miniatura ({tam}px, {len(lineas)} lineas{', sobria' if sobrio else ''}) -> {out}")


def _caricatura(dia, nombre, lado, gesto=""):
    """Caricatura de la foto libre (decision del usuario del 7-nov-2026: miniaturas con caricaturas IA de los dos
    protagonistas enfrentados). Solo desde fotos CC0, dominio publico o CC BY (como las viñetas). Cada uno mira al otro."""
    import json
    import ia_vinetas as IA
    img = dia / "imagenes"
    cr = json.loads((dia / "creditos.json").read_text(encoding="utf-8")).get(nombre, {})
    if not IA.licencia_dibujable(cr.get("licencia", "")):
        raise SystemExit(f"{nombre}: licencia {cr.get('licencia') or 'desconocida'}; para caricaturizar hace falta "
                         f"CC0, dominio publico o CC BY (elige otra con fotos.py mejores)")
    dest = img / f"{Path(nombre).stem}_caricatura.jpg"
    if not dest.exists():
        IA.caricatura(img / nombre, "right" if lado == "izq" else "left",
                      gesto or "serious determined expression").save(dest, quality=94)
        creds = json.loads((dia / "creditos.json").read_text(encoding="utf-8"))
        creds[dest.name] = dict(cr, ilustracion_ia=True, nota="Caricatura IA a partir de la foto")
        (dia / "creditos.json").write_text(json.dumps(creds, ensure_ascii=False, indent=1), encoding="utf-8")
    return dest


def brocha(t):
    """Pone el titular sobre una franja roja de trazo de brocha (bordes irregulares), como en la referencia del usuario."""
    rng = np.random.default_rng(7)
    pad_x, pad_y = 30, 4
    w, h = t.width + 2 * pad_x, t.height + 2 * pad_y
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    arriba = [(x, pad_y * 0.5 + rng.uniform(-14, 14)) for x in range(0, w + 1, 24)]
    abajo = [(x, h - pad_y * 0.5 + rng.uniform(-14, 14)) for x in range(w, -1, -24)]
    d.polygon([(rng.uniform(0, 30), h / 2)] + arriba + [(w - rng.uniform(0, 30), h / 2)] + abajo, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2))
    capa = Image.new("RGBA", (w, h))
    sombra = Image.new("RGBA", (w, h), (0, 0, 0, 150))
    capa.paste(sombra, (10, 12), m)
    capa = capa.filter(ImageFilter.GaussianBlur(8))
    capa.paste(Image.new("RGBA", (w, h), ROJO + (255,)), (0, 0), m)
    capa.alpha_composite(t, (pad_x, pad_y))
    return capa


# ---------- plantillas profesionales (4-nov-2026) ----------
ANTON = "Anton-Regular.ttf"                            # tipografia condensada de impacto (OFL)


def _txt_capa(lineas, f, destaca, interlinea=0.98):
    """Titular en Anton: blanco con contorno fino y sombra; la palabra clave, en negro sobre franja amarilla."""
    medir = ImageDraw.Draw(Image.new("L", (1, 1)))
    alto_l = int(f.size * interlinea) + 14
    ancho = max(int(medir.textlength(" ".join(l), font=f)) for l in lineas) + 60
    capa = Image.new("RGBA", (ancho + 40, alto_l * len(lineas) + 60))
    sombra = Image.new("RGBA", capa.size)
    d, ds = ImageDraw.Draw(capa), ImageDraw.Draw(sombra)
    esp = medir.textlength(" ", font=f)
    for i, l in enumerate(lineas):
        x, y = 10, 10 + i * alto_l
        for w in l:
            tw = medir.textlength(w, font=f)
            clave = w.lower().strip(LIMPIA) in destaca
            if clave:                                   # franja amarilla ajustada a la caja real de las letras
                nucleo = w.strip(LIMPIA) or w           # la puntuación («, », comas, puntos) queda fuera de la franja
                ini = w.find(nucleo)
                pre, post = w[:ini], w[ini + len(nucleo):]
                xn = x + (medir.textlength(pre, font=f) + 16 if pre else 0)
                bx0, _, bx1, _ = d.textbbox((xn, y), nucleo, font=f)
                _, by0, _, by1 = d.textbbox((xn, y), "HQ", font=f)   # alto de la letra, sin tildes ni diéresis
                caja = [bx0 - (12 if pre else 18), by0 - 14, bx1 + (12 if post else 18), by1 + 14]
                ds.rectangle([c + 10 for c in caja], fill=(0, 0, 0, 170))
                d.rectangle(caja, fill=AMARILLO + (255,))
                d.text((xn, y), nucleo, font=f, fill=(12, 12, 16, 255))
                xp = caja[2] + 2
                for trozo, xt in ((pre, x), (post, xp)):
                    if trozo:
                        ds.text((xt + 8, y + 10), trozo, font=f, fill=(0, 0, 0, 200))
                        d.text((xt, y), trozo, font=f, fill=(255, 255, 255, 255), stroke_width=3,
                               stroke_fill=(10, 10, 14, 255))
                tw = (xp + medir.textlength(post, font=f) if post else caja[2] - 18) - x
            else:
                ds.text((x + 8, y + 10), w, font=f, fill=(0, 0, 0, 200))
                d.text((x, y), w, font=f, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(10, 10, 14, 255))
            x += tw + esp + (12 if clave else 0)
    sombra = sombra.filter(ImageFilter.GaussianBlur(9))
    sombra.alpha_composite(capa)
    return sombra


def _kicker(txt, tam=50):
    """Antetitulo: caja roja recta con texto blanco (quien lo dice o de que va)."""
    f = fuente("Inter-Black.ttf", tam)
    w = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(txt, font=f)) + 56
    h = int(tam * 1.5)
    e = Image.new("RGBA", (w + 12, h + 12))
    d = ImageDraw.Draw(e)
    d.rectangle([8, 8, w + 8, h + 8], fill=(0, 0, 0, 140))
    d.rectangle([0, 0, w, h], fill=ROJO + (255,))
    d.text((28, h / 2 + 1), txt, font=f, fill=BLANCO + (255,), anchor="lm")
    return e


def miniatura_pro(dia_txt, titular, destaca="", etiqueta_txt="", persona="", foto_fondo="", insignia_txt="",
                  plantilla="informativo", salida="miniatura.png"):
    """informativo: titular Anton a la izquierda con la palabra clave en franja amarilla, cara grande a la derecha.
    impacto: la palabra clave gigante DETRAS de la persona (efecto de profundidad) y el resto, en el antetitulo."""
    dia = RAIZ / "dia" / dia_txt
    img = dia / "imagenes"
    marca_d = {w.lower().strip(LIMPIA) for w in destaca.split()}
    im = fondo(img / foto_fondo if foto_fondo else None, False, bool(persona))
    gradua(im)
    rayos(im)
    c = recorte(img / persona) if persona else None
    if plantilla == "impacto":
        palabra = (destaca or titular).upper()
        tam = 600
        while tam > 120 and fuente(ANTON, tam).getlength(palabra) > W * 0.70:
            tam -= 10
        f = fuente(ANTON, tam)
        capa = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(capa)
        y = int(H * 0.16)                              # por debajo del logo y del distintivo
        cx = W * 0.40                                  # algo a la izquierda: la persona tapa solo el final
        d.text((cx + 12, y + 16), palabra, font=f, fill=(0, 0, 0, 170), anchor="mt")
        capa = capa.filter(ImageFilter.GaussianBlur(10))
        ImageDraw.Draw(capa).text((cx, y), palabra, font=f, fill=AMARILLO + (255,), anchor="mt",
                                  stroke_width=5, stroke_fill=(10, 10, 14, 255))
        im.alpha_composite(capa)                       # primero el texto...
        if c is not None:                              # ...y la persona delante
            protagonista(im, c, centro=(0.80, 0.60), alto_cara=0.34)
        oscurece_abajo(im, 300, 170)
        if etiqueta_txt:
            k = _kicker(etiqueta_txt.upper(), 84)        # legible en el movil (director de arte, 4-nov)
            im.alpha_composite(k, (90, H - k.height - 80))
    else:
        oscurece_abajo(im, 620, 200)
        x_p = protagonista(im, c, centro=(0.73, 0.37), alto_cara=0.31) if c is not None else None
        ancho = (x_p + 120 - 90) if x_p else 1700
        lineas, tam = [], 210
        palabras = titular.upper().split()
        while tam > 90:
            f = fuente(ANTON, tam)
            lineas, cur = [], []
            for w in palabras:
                if cur and f.getlength(" ".join(cur + [w])) + 60 > ancho:
                    lineas.append(cur)
                    cur = [w]
                else:
                    cur.append(w)
            lineas.append(cur)
            if len(lineas) <= 3 and all(f.getlength(" ".join(l)) + 60 <= ancho for l in lineas):
                break
            tam -= 8
        tc = _txt_capa(lineas, fuente(ANTON, tam), marca_d)
        y = H - tc.height - 50
        if etiqueta_txt:                               # el antetitulo nunca sube hasta el logo
            k = _kicker(etiqueta_txt.upper())
            y = max(y, 190 + k.height)
            im.alpha_composite(k, (90, y - k.height - 4))
        im.alpha_composite(tc, (80, y))
    im.alpha_composite(G2.logo(110), (60, 50))
    if insignia_txt:
        insignia(im, insignia_txt.upper())
    im = grano(im)
    marco(im)
    out = dia / salida
    fin = im.convert("RGB").resize((1280, 720), Image.LANCZOS)
    fin.filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=2)).save(out)
    print(f"miniatura {plantilla} -> {out}")


# ---------- banner y avatar del canal ----------
def partes_marca():
    """El nombre del canal en trozos con su color: «HOY» en amarillo dentro de «EL HOYFORMATIVO»."""
    m = G2.MARCA
    i = m.find("HOY")
    if i < 0:
        return [(m, BLANCO)]
    return [(m[:i], BLANCO), ("HOY", AMARILLO), (m[i + 3:], BLANCO)]

def canal():
    """Banner (2560x1440) y logo del canal con la identidad EH (8-nov-2026; sin Urni). La zona segura del banner, la que
    se ve en todos los dispositivos, es el centro: 1546x423. El logo sirve de foto de perfil en YouTube y TikTok."""
    dest = RAIZ / "canal"
    dest.mkdir(exist_ok=True)
    W2, H2 = 2560, 1440
    fondo_b = G2.fondo_marca(3.0).resize((W2, H2), Image.LANCZOS).convert("RGBA")
    capa = Image.new("RGBA", (W2, H2))                  # luz suave detrás del conjunto
    ImageDraw.Draw(capa).ellipse([W2 // 2 - 900, H2 // 2 - 380, W2 // 2 + 900, H2 // 2 + 380], fill=(60, 90, 160, 70))
    fondo_b.alpha_composite(capa.filter(ImageFilter.GaussianBlur(160)))
    im = Image.new("RGBA", (W2, H2))                    # el contenido, aparte: luego se encoge con margen
    d = ImageDraw.Draw(im)
    f1, f3 = fuente("Inter-Black.ttf", 112), fuente("Inter-SemiBold.ttf", 36)
    tl = 330
    ancho_txt = max(d.textlength("FORMATIVO", font=f1), d.textlength(G2.SUBLEMA, font=f3), d.textlength(G2.LEMA, font=fuente("Inter-Black.ttf", 54)) + 100)
    lema = Image.new("RGBA", (900, 120))                # lema en cursiva sobre trazo amarillo
    fl = fuente("Inter-Black.ttf", 54)
    dl = ImageDraw.Draw(lema)
    wl = int(dl.textlength(G2.LEMA, font=fl))
    lema = Image.new("RGBA", (wl + 80, 100))
    dl = ImageDraw.Draw(lema)
    dl.polygon([(18, 22), (wl + 70, 12), (wl + 60, 86), (6, 92)], fill=AMARILLO + (255,))
    dl.text((40, 52), G2.LEMA, font=fl, fill=(16, 28, 52, 255), anchor="lm")
    lema = lema.transform(lema.size, Image.AFFINE, (1, 0.22, -26, 0, 1, 0), resample=Image.BICUBIC)
    total = tl + 70 + 6 + 70 + ancho_txt
    x0 = int((W2 - total) / 2)
    yc = H2 // 2
    im.alpha_composite(G2.logo(tl), (x0, yc - tl // 2))
    xl = x0 + tl + 70
    d.rectangle([xl, yc - 190, xl + 6, yc + 190], fill=(255, 255, 255, 200))
    xt = xl + 76
    d.text((xt, yc - 140), "EL HOY", font=f1, fill=BLANCO + (255,), anchor="lm")
    d.text((xt, yc - 30), "FORMATIVO", font=f1, fill=AMARILLO + (255,), anchor="lm")
    d.text((xt + 4, yc + 58), G2.SUBLEMA, font=f3, fill=(225, 230, 240, 255), anchor="lm")
    im.alpha_composite(lema, (xt - 20, yc + 92))
    # 8-nov: con margen dentro de la zona segura (1546x423): el contenido, al 80 %, centrado
    K = 0.80
    caja = im.getbbox()
    cont = im.crop(caja)
    cont = cont.resize((int(cont.width * K), int(cont.height * K)), Image.LANCZOS)
    fondo_b.alpha_composite(cont, ((W2 - cont.width) // 2, (H2 - cont.height) // 2))
    db = ImageDraw.Draw(fondo_b)
    db.rectangle([0, H2 - 30, W2, H2 - 18], fill=AMARILLO + (255,))
    db.rectangle([0, H2 - 18, W2, H2], fill=ROJO + (255,))
    fondo_b.convert("RGB").save(dest / "banner.png")
    fondo_b.convert("RGB").resize((2048, 1152), Image.LANCZOS).save(dest / "banner_2048.jpg", quality=92)
    print(f"contenido del banner: {cont.width}x{cont.height} (zona segura 1546x423)")
    # logo / foto de perfil: YouTube y TikTok lo recortan en círculo; fuera, el mismo azul noche
    for lado_ in (800, 1080):
        av = Image.new("RGBA", (lado_, lado_), G2.NOCHE + (255,))
        av.alpha_composite(G2.logo(lado_))
        av.convert("RGB").save(dest / ("avatar.png" if lado_ == 800 else "avatar_tiktok.png"))
    G2.logo(1600).save(dest / "logo_EH.png")            # con fondo transparente, para otros usos
    print(f"banner, avatar y logo -> {dest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dia", nargs="?")
    ap.add_argument("--titular")
    ap.add_argument("--destaca", default="")
    ap.add_argument("--etiqueta", default="")
    ap.add_argument("--persona", default="")
    ap.add_argument("--fondo", default="")
    ap.add_argument("--sobrio", action="store_true")
    ap.add_argument("--rival", default="", help="segunda persona: enfrentamiento cara a cara (foto de imagenes/)")
    ap.add_argument("--inserto", default="", help="foto secundaria en polaroid (lugar u objeto de la noticia)")
    ap.add_argument("--insignia", default="", help="distintivo arriba a la derecha («ESPECIAL»)")
    ap.add_argument("--plantilla", default="", help="informativo | impacto (diseño profesional, 4-nov-2026)")
    ap.add_argument("--caricatura", action="store_true",
                    help="con --rival: los dos como caricaturas IA desde su foto libre CC BY (7-nov-2026)")
    ap.add_argument("--gestos", default="", help="gesto en ingles de rival|persona, p. ej. 'smiling|angry frown'")
    ap.add_argument("--salida", default="miniatura.png")
    ap.add_argument("--canal", action="store_true")
    a = ap.parse_args()
    if a.canal:
        canal()
    else:
        if a.plantilla and not a.sobrio and not a.rival:
            miniatura_pro(a.dia or date.today().isoformat(), a.titular, a.destaca, a.etiqueta, a.persona, a.fondo,
                          a.insignia, a.plantilla, a.salida)
        else:
          miniatura(a.dia or date.today().isoformat(), a.titular, a.destaca, a.etiqueta, a.persona, a.fondo, a.sobrio, a.salida,
                  a.rival, a.inserto, a.insignia, a.caricatura, tuple((a.gestos.split("|") + ["", ""])[:2]))
