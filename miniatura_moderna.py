"""MINIATURA MODERNA (23-nov-2026, el usuario: «las miniaturas de los vídeos largos siguen quedando poco profesionales;
necesito algo más moderno y llamativo»). Caras GRANDES (de pecho para arriba) con contorno blanco, fondo limpio de
Imagenes/Fondos oscurecido con un degradado (nunca borroso), texto de 2-4 palabras enorme con la palabra clave en un bloque
de color, y una etiqueta pequeña. Solo imágenes de Imagenes/ (NORMAS §6).

Diseños:
  «duelo»       dos caras enfrentadas, una a cada lado, el texto abajo en el centro y un «VS» discreto.
  «protagonista» una cara enorme a la derecha y el texto apilado a la izquierda.
  «cita»        una cara a la derecha y la frase entre comillas grandes a la izquierda.
Uso: python miniatura_moderna.py prueba AAAA-MM-DD"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).parent
W, H = 1280, 720
AMARILLO = (255, 205, 0)
ROJO = (226, 30, 45)
NAVY = (8, 14, 34)
GROSOR = 4                 # contorno de la silueta (23-nov-2026, el usuario: «más fino»)
F = RAIZ / "fuentes"


def fuente(nombre, tam):
    return ImageFont.truetype(str(F / nombre), tam)


def busto(ruta, alto, corte=0.42):
    """De la figura de cuerpo entero, la cabeza y el pecho (corte = fracción de la altura), escalado a `alto`."""
    im = Image.open(ruta).convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox())
    im = im.crop((0, 0, im.width, int(im.height * corte)))
    bb = im.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
    im = im.crop((bb[0], 0, bb[2], im.height))
    k = alto / im.height
    return im.resize((int(im.width * k), alto), Image.LANCZOS)


def contorno(fig, grosor=10, color=(255, 255, 255)):
    """Contorno blanco alrededor de la figura y una sombra suave detrás: la despega del fondo."""
    pad = grosor * 3
    a = Image.new("L", (fig.width + 2 * pad, fig.height + 2 * pad), 0)
    a.paste(fig.getchannel("A"), (pad, pad))
    borde = a.filter(ImageFilter.MaxFilter(grosor * 2 + 1))
    sombra = a.filter(ImageFilter.MaxFilter(grosor * 2 + 1)).filter(ImageFilter.GaussianBlur(22))
    out = Image.new("RGBA", a.size, (0, 0, 0, 0))
    s = Image.new("RGBA", a.size, (0, 0, 0, 255)); s.putalpha(sombra.point(lambda v: int(v * 0.75)))
    out.alpha_composite(s, (8, 12))
    b = Image.new("RGBA", a.size, color + (255,)); b.putalpha(borde)
    out.alpha_composite(b)
    out.alpha_composite(fig, (pad, pad))
    return out, pad


def fondo(ruta, tono=NAVY, lado="izq"):
    """El fondo de Imagenes/Fondos a pantalla completa, oscurecido con un degradado del color de la marca hacia el lado
    del texto (se lee mejor) y un viñeteado. Nítido: nada de desenfoques."""
    ruta = Path(ruta)
    if not ruta.exists():
        ruta = next((f for f in (RAIZ / "Imagenes" / "Fondos").rglob("*") if f.name == ruta.name), ruta)
    im = Image.open(ruta).convert("RGB")
    k = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * k) + 1, int(im.height * k) + 1), Image.LANCZOS)
    im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
    im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), 0.35).convert("RGBA")
    g = Image.linear_gradient("L").rotate(90 if lado == "izq" else -90).resize((W, H))
    capa = Image.new("RGBA", (W, H), tono + (255,)); capa.putalpha(g.point(lambda v: int(70 + v * 0.62)))
    im.alpha_composite(capa)
    abajo = Image.linear_gradient("L").resize((W, H)).point(lambda v: int(max(0, v - 120) * 1.4))
    c2 = Image.new("RGBA", (W, H), tono + (255,)); c2.putalpha(abajo)
    im.alpha_composite(c2)
    return im


def _lineas(palabras, f, ancho_max):
    lineas, cur = [], []
    for w in palabras:
        if cur and f.getlength(" ".join(cur + [w])) > ancho_max:
            lineas.append(cur); cur = [w]
        else:
            cur.append(w)
    return lineas + ([cur] if cur else [])


def alto_bloque(palabras, tam, ancho_max):
    f = fuente("Anton-Regular.ttf", tam)
    return len(_lineas(palabras, f, ancho_max)) * int(tam * 1.08)


def _texto_bloque(d, x, y, palabras, destaca, tam, ancho_max, alinea="izq"):
    """Palabras en líneas (Anton, mayúsculas); la palabra clave sobre un bloque amarillo ajustado a sus letras."""
    f = fuente("Anton-Regular.ttf", tam)
    lineas = _lineas(palabras, f, ancho_max)
    lh = int(tam * 1.08)
    for i, ln in enumerate(lineas):
        total = f.getlength(" ".join(ln))
        cx = x if alinea == "izq" else x - total / 2
        yy = y + i * lh
        for w in ln:
            ww = f.getlength(w)
            clave = re.sub(r"\W", "", w.lower()) == re.sub(r"\W", "", (destaca or "").lower())
            if clave:
                bb = f.getbbox(w)
                d.rectangle((cx + bb[0] - 14, yy + bb[1] - 10, cx + bb[2] + 14, yy + bb[3] + 10), fill=AMARILLO)
                d.text((cx, yy), w, font=f, fill=NAVY)
            else:
                for dx, dy in ((5, 6), (2, 3)):
                    d.text((cx + dx, yy + dy), w, font=f, fill=(0, 0, 0))
                d.text((cx, yy), w, font=f, fill=(255, 255, 255))
            cx += ww + f.getlength(" ")
    return y + len(lineas) * lh


def _chip(d, x, y, txt, color=ROJO, tam=34):
    f = fuente("Inter-Black.ttf", tam)
    w = f.getlength(txt)
    d.rounded_rectangle((x, y, x + w + 36, y + tam + 26), 10, fill=color)
    d.text((x + 18, y + 9), txt, font=f, fill=(255, 255, 255))
    return w + 36


def _marca(im):
    d = ImageDraw.Draw(im)
    f = fuente("Inter-Black.ttf", 26)
    t1, t2 = "EL HOY", "FORMATIVO"
    x, y = W - 40 - f.getlength(t1 + t2) - 30, 28
    d.rounded_rectangle((x - 16, y - 8, W - 34, y + 38), 8, fill=(0, 0, 0, 170))
    d.text((x, y), t1, font=f, fill=(255, 255, 255))
    d.text((x + f.getlength(t1) + 6, y), t2, font=f, fill=AMARILLO)


def duelo(salida, frase, destaca, fig_izq, fig_der, etiqueta, fondo_ruta):
    im = fondo(fondo_ruta, lado="izq")
    # luz de cada lado (rojo / azul neutro de marca) para separar a los dos
    for x0, col in ((0, (200, 30, 45)), (W // 2, (30, 90, 200))):
        g = Image.linear_gradient("L").rotate(90 if x0 == 0 else -90).resize((W // 2, H)).point(lambda v: int(v * 0.35))
        c = Image.new("RGBA", (W // 2, H), col + (255,)); c.putalpha(g)
        im.alpha_composite(c, (x0, 0))
    alto = int(H * 0.78)
    for ruta, lado in ((fig_izq, "izq"), (fig_der, "der")):
        b = busto(ruta, alto)
        if lado == "der":
            b = b.transpose(Image.FLIP_LEFT_RIGHT) if False else b
        c, pad = contorno(b, GROSOR)
        x = -pad + 10 if lado == "izq" else W - c.width + pad - 10
        im.alpha_composite(c, (x, H - c.height + pad + 4))
    d = ImageDraw.Draw(im)
    fv = fuente("Anton-Regular.ttf", 84)
    d.ellipse((W // 2 - 62, 150, W // 2 + 62, 274), fill=ROJO, outline=(255, 255, 255), width=6)
    d.text((W // 2 - fv.getlength("VS") / 2, 160), "VS", font=fv, fill=(255, 255, 255))
    # franja inferior con el texto, centrada
    franja = Image.new("RGBA", (W, 230), (0, 0, 0, 0))
    gf = Image.linear_gradient("L").resize((W, 230)).point(lambda v: int(v * 0.85))
    franja2 = Image.new("RGBA", (W, 230), (0, 0, 0, 255)); franja2.putalpha(gf)
    im.alpha_composite(franja2, (0, H - 230))
    d = ImageDraw.Draw(im)
    pal = frase.upper().split()
    tam = 118
    while alto_bloque(pal, tam, W - 560) > 250 and tam > 70:
        tam -= 6
    _texto_bloque(d, W // 2, H - 40 - alto_bloque(pal, tam, W - 560), pal, destaca.upper(), tam, W - 560, alinea="centro")
    tw = fuente("Inter-Black.ttf", 30).getlength(etiqueta.upper()) + 36
    _chip(d, int(W / 2 - tw / 2), 40, etiqueta.upper(), tam=30)
    _marca(im)
    im.convert("RGB").save(salida, quality=95)


def protagonista(salida, frase, destaca, fig, etiqueta, fondo_ruta):
    im = fondo(fondo_ruta, lado="izq")
    b = busto(fig, int(H * 0.90), corte=0.40)
    c, pad = contorno(b, GROSOR)
    im.alpha_composite(c, (W - c.width + pad + 10, H - c.height + pad + 30))
    d = ImageDraw.Draw(im)
    _chip(d, 56, 60, etiqueta.upper())
    pal, tam = frase.upper().split(), 150                  # el texto se encoge hasta caber entre la etiqueta y el borde
    while 140 + alto_bloque(pal, tam, 640) > H - 40 and tam > 70:
        tam -= 6
    _texto_bloque(d, 60, 140, pal, destaca.upper(), tam, 640)
    _marca(im)
    im.convert("RGB").save(salida, quality=95)


def cita(salida, frase, destaca, fig, etiqueta, quien, fondo_ruta):
    im = fondo(fondo_ruta, lado="izq")
    b = busto(fig, int(H * 0.88), corte=0.40)
    c, pad = contorno(b, GROSOR, color=AMARILLO)
    im.alpha_composite(c, (W - c.width + pad + 20, H - c.height + pad + 30))
    d = ImageDraw.Draw(im)
    fq = fuente("Inter-Black.ttf", 200)
    d.text((52, 92), "“", font=fq, fill=AMARILLO)
    pal, tam = frase.upper().split(), 132
    while 250 + alto_bloque(pal, tam, 620) + 80 > H - 30 and tam > 64:
        tam -= 6
    y = _texto_bloque(d, 70, 250, pal, destaca.upper(), tam, 620)
    fn = fuente("Inter-Black.ttf", 40)
    d.rectangle((70, y + 18, 70 + 8, y + 70), fill=ROJO)
    d.text((92, y + 20), quien.upper(), font=fn, fill=(255, 255, 255))
    _chip(d, 56, 40, etiqueta.upper(), tam=28)
    _marca(im)
    im.convert("RGB").save(salida, quality=95)


def _imagen(nombre):
    import presentador as P
    _, _, pols = P.catalogo()
    return P.figura_de(nombre, pols, {})


def prueba(fecha):
    """Los tres diseños con el gancho del día (para que el usuario elija)."""
    import json
    import presentador as P
    dia = RAIZ / "dia" / fecha
    E = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    items = [it for p in E["secciones"][0]["pasos"] for it in (p.get("ve") or {}).get("items", [])]
    a, b = items[0], items[1] if len(items) > 1 else items[0]
    fondos, _, _ = P.catalogo()
    fnd = fondos[0] if fondos else None
    try:
        fnd = json.loads((dia / "fondos_elegidos.json").read_text(encoding="utf-8"))
        fnd = next(iter(fnd.values())) if isinstance(fnd, dict) else fnd[0]
    except Exception:
        fnd = fondos[0]
    frase_a = a["titular"].strip("«»\"")
    m = re.search(r"\ba\s+(.+)$", a.get("etiqueta", ""))        # «Sánchez a Feijóo»: el rival es el aludido
    rival = m.group(1).strip() if m else b["persona"]
    out = []
    for nombre, fn in (("duelo", lambda s: duelo(s, frase_a, a["destaca"], _imagen(a["persona"]), _imagen(rival),
                                                  a.get("etiqueta", ""), fnd)),
                       ("protagonista", lambda s: protagonista(s, frase_a, a["destaca"], _imagen(a["persona"]),
                                                               a.get("etiqueta", ""), fnd)),
                       ("cita", lambda s: cita(s, frase_a, a["destaca"], _imagen(a["persona"]), a.get("etiqueta", ""),
                                               a["persona"], fnd))):
        s = dia / f"miniatura_{nombre}.png"
        fn(s)
        out.append(s)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["prueba"]:
        print("\n".join(map(str, prueba(sys.argv[2]))))
