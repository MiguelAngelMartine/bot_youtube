"""SHORT VERTICAL DE UNA FRASE (decisión del usuario del 5-nov-2026). 1080x1920, 40-55 s (6-nov: más largo):
  1) gancho (desde el fotograma 0, que es también la miniatura): la persona recortada MUY grande sobre la imagen del
     tema en movimiento, el antetítulo («SÁNCHEZ, A FEIJÓO») y la frase literal enorme;
  2) contexto: el porqué, con las viñetas y fotos del tema pasando a pantalla completa arriba y el texto abajo;
  3) réplica, si la hay: el aludido y su frase escribiéndose;
  4) cierre: «Más información en el vídeo de hoy», «¿Qué opinas?» y botón de suscribirse (sin logo de Urni, 8-nov).
Voz de Tristán, subtítulos grandes, música baja y crédito de las fotos. Fotos siempre a color, contorno suave.
Uso: python short.py AAAA-MM-DD N     -> dia/<fecha>/shorts/short_N.mp4 y short_N_portada.png"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import corto as C
import episodio as E
import genera_video as V1
import genera_video2 as G2
import ia_vinetas as IAV
import miniatura as M
import musica
import voz
from genera_video2 import AMARILLO, BLANCO, ROJO, fuente

RAIZ = Path(__file__).parent
AN, AL, FPS = 1080, 1920, 30
NAVY = (12, 20, 38)


def _fondo_tema(ruta):
    """6-nov-2026 (el usuario: «el fondo siempre azul parece un PowerPoint»): la imagen del tema a pantalla completa,
    desenfocada, con color y la luz de la marca, algo mayor que la pantalla para moverla despacio."""
    if ruta is None or not Path(ruta).exists():
        return _fondo().resize((int(AN * 1.12), int(AL * 1.12)))
    from PIL import ImageEnhance, ImageOps
    import titulares as TIT
    w, h = int(AN * 1.12), int(AL * 1.12)
    im = ImageOps.fit(Image.open(ruta).convert("RGB"), (w // 2, h // 2), Image.LANCZOS, centering=(0.5, 0.35))
    im = im.filter(ImageFilter.GaussianBlur(9))
    im = ImageEnhance.Color(im).enhance(1.35)
    im = ImageEnhance.Brightness(im).enhance(0.55).resize((w, h), Image.BILINEAR).convert("RGBA")
    im.alpha_composite(TIT._tinte((w, h), False))
    g = Image.linear_gradient("L").resize((w, h)).point(lambda v: int(max(0, v - 110) * 1.4))
    sombra = Image.new("RGBA", (w, h), (6, 10, 22, 255))
    sombra.putalpha(g)                                 # abajo, más oscuro: ahí van la frase y los subtítulos
    im.alpha_composite(sombra)
    return im


def _mueve(base, t, total):
    """Ken Burns del fondo: se acerca y se desplaza despacio durante todo el Short."""
    q = min(1.0, t / max(total, 1))
    z = 1.0 + 0.06 * q
    cw, ch = int(base.width / 1.12 / z * 1.0), int(base.height / 1.12 / z * 1.0)
    x0 = int((base.width - cw) * (0.3 + 0.4 * q))
    y0 = int((base.height - ch) * 0.5)
    fr = base.crop((x0, y0, x0 + cw, y0 + ch)).resize((AN, AL), Image.BILINEAR)
    q2 = (t % 7.0) / 7.0                                # 10-nov: un barrido de luz cruza la pantalla cada 7 s
    if q2 < 0.35:
        global _BARRIDO
        if _BARRIDO is None:
            b = Image.new("L", (900, AL))
            ImageDraw.Draw(b).polygon([(300, 0), (520, 0), (420, AL), (200, AL)], fill=70)
            _BARRIDO = b.filter(ImageFilter.GaussianBlur(60))
        x = int(-900 + (AN + 900) * (q2 / 0.35))
        fr = fr.convert("RGBA")
        fr.paste(Image.new("RGBA", _BARRIDO.size, (255, 240, 200, 255)), (x, 0), _BARRIDO)
    return fr


_BARRIDO = None


def _panel(ruta):
    """Viñeta o foto del tema para la parte de arriba durante el contexto (ancho completo, de ZONA[0] a ZONA[1])."""
    from PIL import ImageOps
    alto = ZONA[1] - ZONA[0]
    im = ImageOps.fit(Image.open(ruta).convert("RGB"), (int(AN * 1.1), int(alto * 1.1)), Image.LANCZOS,
                      centering=(0.5, 0.4))
    return im


def _fondo():
    """10-nov-2026 (el usuario: «los fondos quedan muy vacíos»): azul noche con profundidad: foco de luz, franjas
    diagonales de la marca, retícula de mapa, destellos desenfocados y el «EH» enorme en marca de agua."""
    import random
    rnd = random.Random(7)
    w, h = AN, AL
    im = Image.new("RGB", (w, h), (10, 18, 38))
    luz = Image.new("L", (w, h), 0)
    ImageDraw.Draw(luz).ellipse([-300, 150, w + 300, 1350], fill=255)
    im.paste(Image.new("RGB", (w, h), (34, 58, 120)), (0, 0), luz.filter(ImageFilter.GaussianBlur(260)))
    capa = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(capa)
    for x in range(-h, w, 90):                         # retícula fina, como un mapa
        d.line([(x, 0), (x + h * 0.35, h)], fill=(120, 160, 255, 16), width=2)
    for y in range(0, h, 90):
        d.line([(0, y), (w, y)], fill=(120, 160, 255, 12), width=2)
    for x0, col, a in ((-500, ROJO, 70), (-330, AMARILLO, 55), (w - 260, ROJO, 60), (w - 120, AMARILLO, 45)):
        d.polygon([(x0, h), (x0 + 120, h), (x0 + 120 + 0.55 * h, 0), (x0 + 0.55 * h, 0)], fill=col + (a,))
    for _ in range(16):                                # destellos (bokeh)
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(14, 70)
        c = rnd.choice([(255, 210, 90), (120, 170, 255), (255, 120, 110)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=c + (rnd.randint(18, 50),))
    capa = capa.filter(ImageFilter.GaussianBlur(6))
    eh = Image.new("RGBA", (w, h))
    ImageDraw.Draw(eh).text((w // 2, h * 0.47), "EH", font=fuente("Inter-Black.ttf", 760), fill=(255, 255, 255, 8), anchor="mm")
    capa.alpha_composite(eh)
    out = im.convert("RGBA")
    out.alpha_composite(capa)
    g = Image.linear_gradient("L").resize((w, h)).point(lambda v: int(max(0, v - 120) * 1.5))
    sombra = Image.new("RGBA", (w, h), (6, 10, 22, 255))
    sombra.putalpha(g)
    out.alpha_composite(sombra)
    return out



CATEGORIAS = {"ÚLTIMA HORA": (ROJO, BLANCO), "POLÉMICA": (AMARILLO, (16, 28, 52)), "ZASCA": (AMARILLO, (16, 28, 52)),
              "ANÁLISIS": ((30, 64, 140), BLANCO)}          # identidad EH (8-nov-2026)


def _cabecera(fecha, categoria=""):
    cab = Image.new("RGBA", (AN, 150))
    d = ImageDraw.Draw(cab)
    d.rectangle([0, 0, AN, 10], fill=ROJO + (255,))
    d.rectangle([0, 10, AN, 16], fill=AMARILLO + (255,))
    cab.alpha_composite(G2.logo(80), (40, 42))
    f_ = fuente("Inter-Black.ttf", 40)
    d.text((140, 82), "EL HOY ", font=f_, fill=BLANCO + (255,), anchor="lm")
    d.text((140 + f_.getlength("EL HOY "), 82), "FORMATIVO", font=f_, fill=AMARILLO + (255,), anchor="lm")
    y, m, dd = (int(x) for x in fecha[:10].split("-"))
    fe = f"{dd} {['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'][m - 1]}"
    cat = (categoria or "").upper().strip()
    if cat in CATEGORIAS:                                   # etiqueta de formato (identidad EH, 8-nov-2026)
        fondo_c, letra_c = CATEGORIAS[cat]
        fc = fuente("Inter-Black.ttf", 34)
        w = int(fc.getlength(cat)) + 44
        d.polygon([(AN - 40 - w + 14, 50), (AN - 40, 50), (AN - 40 - 14, 104), (AN - 40 - w, 104)], fill=fondo_c + (255,))
        d.text((AN - 40 - w / 2 - 7, 78), cat, font=fc, fill=letra_c + (255,), anchor="mm")
        d.text((AN - 47, 128), fe, font=fuente("Inter-Bold.ttf", 26), fill=BLANCO + (255,), anchor="rm")
    else:
        d.rounded_rectangle([AN - 200, 54, AN - 40, 112], radius=10, fill=ROJO + (255,))
        d.text((AN - 120, 83), fe, font=fuente("Inter-Black.ttf", 36), fill=BLANCO + (255,), anchor="mm")
    return cab


ZONA = (150, 1050)                                    # la persona vive arriba (y de 150 a 1050): 6-nov, más grande


def _busca_foto(dia, nombre):
    """Sin retrato del día: la primera foto de su categoría de Commons en la que se detecta una cara (con crédito)."""
    import fotos as F
    try:
        w = F.retrato_wikidata(nombre)                  # primero, su retrato principal de Wikidata
        cands = ([w] if w else []) + F.commons_categoria(nombre, 14)
        cands.sort(key=lambda c_: 0 if c_["fuente"].startswith("Wikidata") or any(
            x in c_["titulo"].lower() for x in ("retrato", "portrait", "oficial", "official")) else 1)
    except Exception:
        return None
    for k, cd in enumerate(cands):
        im = F.baja(F.original(cd["url"]), 2400) or F.baja(cd["url"], 2400)
        if im is None:
            continue
        import hashlib
        nom = f"short_{F.slug(nombre)}_{hashlib.sha1(cd['url'].encode()).hexdigest()[:8]}.jpg"   # un nombre por foto: sin cachés cruzadas
        (dia / "imagenes").mkdir(exist_ok=True)
        im.save(dia / "imagenes" / nom, quality=92)
        rc = M.recorte(dia / "imagenes" / nom)
        k_ = M.cara(rc)
        # un retrato de verdad: una cara grande dentro del recorte (en las fotos de grupo la cara es pequeña) y nítida
        if k_ and k_[2] >= 0.22 * rc.width and k_[3] >= 140:
            cred_f = dia / "creditos.json"
            cred = json.loads(cred_f.read_text(encoding="utf-8")) if cred_f.exists() else {}
            cred[nom] = {k_: cd[k_] for k_ in ("titulo", "url", "autor", "licencia", "pagina", "fuente")} | {"persona": nombre}
            cred_f.write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
            return dia / "imagenes" / nom
    return None


def _persona(dia, nombre, cargo, centro, alto_cara):
    """(imagen, x, y, credito) de la persona en la mitad de arriba: foto real a color con contorno suave (la del día o,
    si no hay, de su categoría de Commons), o la ilustración de su ámbito."""
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    fotos = C.fotos_personas({nombre}, cred, dia / "imagenes")
    ruta = fotos.get(nombre) if nombre in fotos and fotos[nombre].exists() else _busca_foto(dia, nombre)
    if ruta:
        cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8"))
        c = M.recorte(ruta)
        alto = ZONA[1] - ZONA[0]
        r = M.encuadre_cara(c, AN, alto, (0.5, 0.42), 0.34, suave=True)
        if r is None:
            k = alto / c.height
            cc, pad = M.silueta_suave(c.resize((int(c.width * k), int(c.height * k)), Image.LANCZOS))
            r = (cc, (AN - cc.width) // 2, 0)
        im, x, y = r
        caja2 = Image.new("RGBA", (AN, alto))          # recorte a la zona: el cuerpo no baja a los textos
        caja2.paste(im, (x, y), im)
        cr = cred.get(ruta.name, {})
        autor = re.sub(r"^(Foto:\s*)+", "", cr.get("autor", ""))
        return caja2, 0, ZONA[0], f"Foto: {autor[:40]} · {cr.get('licencia', '')}"
    amb = IAV.ilustracion_ambito(cargo)
    if amb:
        im = Image.open(amb).convert("RGB")
        im.thumbnail((760, ZONA[1] - ZONA[0] - 90), Image.LANCZOS)   # que no tape el crédito (y = 935)
        im = im.convert("RGBA")
        return im, (AN - im.width) // 2, ZONA[0] + 30, "Ilustración IA · sin foto libre"
    return None


# 10-nov-2026 (variedad, camino a la monetización: que los Shorts no parezcan hechos en serie): cada Short con un
# estilo distinto de letra y color (el antetítulo, la franja de la palabra clave y la letra de la cita).
SESTILOS = [
    {"fuente": "Anton-Regular.ttf", "kicker": (229, 37, 33), "acento": (250, 204, 21), "letra": (12, 12, 16)},
    {"fuente": "BarlowCondensed-Bold.ttf", "kicker": (0, 120, 200), "acento": (60, 210, 240), "letra": (8, 20, 40)},
    {"fuente": "Bangers-Regular.ttf", "kicker": (220, 20, 120), "acento": (255, 215, 0), "letra": (20, 10, 30)},
    {"fuente": "Anton-Regular.ttf", "kicker": (15, 110, 70), "acento": (255, 255, 255), "letra": (15, 110, 70)},
    {"fuente": "Inter-Black.ttf", "kicker": (245, 110, 20), "acento": (229, 37, 33), "letra": (255, 255, 255)},
]
SESTILO = dict(SESTILOS[0])


def _kicker(txt, tam=56):
    f = fuente("Inter-Black.ttf", tam)
    w = int(f.getlength(txt)) + 56
    e = Image.new("RGBA", (w + 12, int(tam * 1.5) + 12))
    d = ImageDraw.Draw(e)
    d.rectangle([10, 10, w + 10, int(tam * 1.5) + 10], fill=(0, 0, 0, 150))
    d.rectangle([0, 0, w, int(tam * 1.5)], fill=SESTILO["kicker"] + (255,))
    d.text((28, tam * 0.75 + 2), txt, font=f, fill=BLANCO + (255,), anchor="lm")
    return e


ALTO_CITA = 300                                       # la frase ocupa de 1180 a 1480; el contexto, de 1500 a 1690


def _cita(txt, destaca, ancho=960, max_tam=118):
    """Frase en Anton, blanca, con la palabra clave en franja amarilla (como la miniatura «informativo»)."""
    palabras = ("«" + txt.strip().rstrip(".") + "»").upper().split()
    tam = max_tam
    while tam > 60:
        f = fuente(SESTILO["fuente"], tam)
        lineas, cur = [], []
        for w in palabras:
            if cur and f.getlength(" ".join(cur + [w])) + 40 > ancho:
                lineas.append(cur)
                cur = [w]
            else:
                cur.append(w)
        lineas.append(cur)
        if len(lineas) * tam * 1.05 <= ALTO_CITA:
            break
        tam -= 6
    marca = {w.lower().strip(M.LIMPIA) for w in (destaca or "").split()}
    return M._txt_capa(lineas, fuente(SESTILO["fuente"], tam), marca, acento=SESTILO["acento"], letra_acento=SESTILO["letra"])


def _caja(txt, ancho=940, tam=46):
    f = fuente("ComicNeue-Bold.ttf", tam)
    ls = C.lineas(txt, f, ancho - 50)
    while len(ls) > 5 and tam > 30:                    # 11-nov: si no cabe, letra más pequeña (nunca texto cortado)
        tam -= 3
        f = fuente("ComicNeue-Bold.ttf", tam)
        ls = C.lineas(txt, f, ancho - 50)
    ls = ls[:7]
    h = 40 + int(tam * 1.25) * len(ls)
    im = Image.new("RGBA", (ancho + 14, h + 14))
    d = ImageDraw.Draw(im)
    d.rectangle([12, 12, ancho + 12, h + 12], fill=(0, 0, 0, 255))
    d.rectangle([0, 0, ancho, h], fill=(250, 240, 205, 255), outline=(0, 0, 0, 255), width=5)
    for j, l in enumerate(ls):
        d.text((26, 20 + int(tam * 1.25) * j), l, font=f, fill=(15, 15, 15, 255))
    return im


def _seccion(dia, cita):
    """Bloque del episodio donde sale la frase (para usar sus viñetas y fotos)."""
    import shorts_guion as SG
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    for i, sec in enumerate(G["secciones"]):
        if i and SG._norm(cita)[:40] in SG._norm(json.dumps(sec, ensure_ascii=False)):
            return i, sec
    return None, None


def _imagenes_tema(dia, i, sec, quien):
    """Viñetas y fotos del bloque de la frase (sin la de la persona, que ya sale): el «B-roll» del contexto."""
    out = []
    if i is not None:
        out += sorted((dia / "vinetas").glob(f"s{i}_*.jpg"))
        for p in sec["pasos"]:
            f = (p.get("ve") or {}).get("foto")
            if f and (dia / "imagenes" / f).exists() and _foto_buena(dia / "imagenes" / f):
                out.append(dia / "imagenes" / f)      # 11-nov: «mejor una buena viñeta que una mala imagen»
    return list(dict.fromkeys(out))[:8]


def _foto_buena(ruta, ancho=1600, alto=900):
    """Una foto solo entra en el contexto si tiene calidad: alta resolución y apaisada (si no, mejor una viñeta)."""
    try:
        w, h = Image.open(ruta).size
        return w >= ancho and h >= alto and w >= h
    except OSError:
        return False


def portada_tematica(fondo, titular):
    """11-nov-2026: portada vertical SIN persona, con el estilo de la miniatura de referencia del director: la imagen
    del tema de fondo y el titular gigante en 3 líneas (blanca / negra sobre amarillo de brocha / blanca sobre rojo)."""
    im = fondo.convert("RGB").resize((AN, AL)) if fondo is not None else _fondo().convert("RGB")
    from PIL import ImageEnhance
    im = ImageEnhance.Brightness(im).enhance(0.75).convert("RGBA")
    pal = titular.upper().replace("«", "").replace("»", "").split()
    if len(pal) <= 3:
        lineas = pal
    else:
        import itertools
        mejor = min(([" ".join(pal[:i]), " ".join(pal[i:j]), " ".join(pal[j:])]
                     for i, j in itertools.combinations(range(1, len(pal)), 2)), key=lambda ls: max(map(len, ls)))
        lineas = mejor
    estilos = [((255, 255, 255), None), ((10, 10, 10), AMARILLO), ((255, 255, 255), ROJO)][-len(lineas):]
    tams = []
    for t_ in lineas:
        t = 200
        while t > 70 and fuente("Inter-Black.ttf", t).getlength(t_) > AN * 0.86:
            t -= 6
        tams.append(t)
    y = (AL - sum(int(t * 1.15) for t in tams)) // 2
    for k, (t_, (col, fc)) in enumerate(zip(lineas, estilos)):
        f = fuente("Inter-Black.ttf", tams[k])
        tw, hh = int(f.getlength(t_)), int(tams[k] * 1.12)
        x = (AN - tw) // 2
        if fc:
            fr = M._franja_brocha(tw + 140, int(hh * 1.05), fc, semilla=k)
            im.alpha_composite(fr, (x - 70, y))
        capa = Image.new("RGBA", (AN, hh + 30))
        d = ImageDraw.Draw(capa)
        d.text((x, 4), t_, font=f, fill=col + (255,), stroke_width=8 if col == (255, 255, 255) else 2,
               stroke_fill=(0, 0, 0, 255) if col == (255, 255, 255) else col + (255,))
        im.alpha_composite(M._gastado(capa, semilla=k, fuerza=0.07), (0, y - 4))
        y += int(hh * 1.03)
    im.alpha_composite(_cabecera_logo(), (40, 40)) if "_cabecera_logo" in globals() else None
    return im


def portada(fecha, fondo, foto_persona, kicker, titular, destaca):
    """Miniatura vertical del Short (7-nov-2026: «asegurarse de que los Shorts tienen su miniatura»), con el lenguaje de
    la miniatura del vídeo largo: imagen del tema de fondo, la persona MUY grande y el titular enorme con relieve."""
    im = fondo.crop(((fondo.width - AN) // 2, (fondo.height - AL) // 2, (fondo.width - AN) // 2 + AN,
                     (fondo.height - AL) // 2 + AL)).convert("RGBA")
    if foto_persona:
        c = M.recorte(foto_persona)
        r = M.encuadre_cara(c, AN, 1250, (0.5, 0.36), 0.5, suave=True)
        if r:
            pi, x, y = r
            caja = Image.new("RGBA", (AN, 1250))
            caja.paste(pi, (x, y), pi)
            im.alpha_composite(caja, (0, 120))
    g = Image.linear_gradient("L").resize((AN, 900)).point(lambda v: int(min(255, v * 1.3)))
    sombra = Image.new("RGBA", (AN, 900), (4, 6, 14, 255))
    sombra.putalpha(g)
    im.alpha_composite(sombra, (0, AL - 900))
    tam, lineas = M.ajusta(titular, destaca or "", 1000, False)
    tx = M.texto(lineas, min(tam, 210), False, espacio=0.55)
    if tx.width > 1040:
        k = 1040 / tx.width
        tx = tx.resize((int(tx.width * k), int(tx.height * k)), Image.LANCZOS)
    tx = tx.rotate(3, resample=Image.BICUBIC, expand=True)
    yt = min(AL - tx.height - 170, 1330)
    k_ = _kicker(kicker.upper(), 60)
    im.alpha_composite(k_, (50, yt - k_.height + 10))
    im.alpha_composite(tx, ((AN - tx.width) // 2, yt))
    im.alpha_composite(_cabecera(fecha), (0, 0))
    return im


def _vista_mc(im, ruta, tl, alto, k):
    """10-nov: la imagen del tema como viñeta animada (motion comic con profundidad); si falla, el zoom de siempre."""
    try:
        import motion_comic as MC
        v = MC.anima(im, ruta, tl, AN, alto, semilla=k, dur=5.0).convert("RGBA")
        return MC.ambiente(v, tl, tl + k * 3.1, semilla=k)
    except Exception:
        z = 1.0 + 0.06 * min(tl, 5) / 5
        cw, ch = int(im.width / 1.1 / z), int(im.height / 1.1 / z)
        x0 = int((im.width - cw) * (0.3 + 0.4 * min(tl, 5) / 5))
        y0 = (im.height - ch) // 2
        return im.crop((x0, y0, x0 + cw, y0 + ch)).resize((AN, alto), Image.BILINEAR).convert("RGBA")


def _cierre(fr, tl, pregunta="¿Qué opinas?"):
    """Pantalla final: la pregunta (10-nov: de sí o no, sobre la frase), «Te leo en comentarios» y suscribirse."""
    # 8-nov: sin el logo de Urni; botón de suscribirse
    d = ImageDraw.Draw(fr)
    a_ = G2.suave(min(1.0, tl / 0.25))
    tam_p = 104 if len(pregunta) <= 16 else max(60, int(104 * 16 / len(pregunta)))
    d.text((AN // 2, 560 + int(30 * (1 - a_))), pregunta, font=fuente("Inter-Black.ttf", tam_p),
           fill=AMARILLO + (int(255 * a_),), anchor="mm")
    d.text((AN // 2, 680), "Te leo en comentarios", font=fuente("Inter-Black.ttf", 58), fill=BLANCO + (255,), anchor="mm")
    d.text((AN // 2, 800), "Más información en el vídeo de hoy", font=fuente("Inter-Bold.ttf", 42),
           fill=BLANCO + (220,), anchor="mm")
    e = G2.suave(min(1.0, tl / 0.35)) * (1.0 + 0.05 * math.sin(tl * 6))
    bw, bh = int(400 * e), int(80 * e)
    if bw > 10:
        cy, cx0 = 1000, AN // 2 - 60                         # botón + campana, centrados
        d.rounded_rectangle([cx0 - bw, cy - bh, cx0 + bw, cy + bh], radius=bh, fill=ROJO + (255,))
        f_ = fuente("Inter-Black.ttf", max(10, int(66 * e)))
        tw = f_.getlength("SUSCRÍBETE")
        ix = cx0 - (tw + 90 * e) / 2                       # icono de reproducir + texto, centrados
        r_ = 34 * e
        d.rounded_rectangle([ix, cy - r_, ix + 70 * e, cy + r_], radius=int(16 * e), fill=BLANCO + (255,))
        d.polygon([(ix + 26 * e, cy - 16 * e), (ix + 26 * e, cy + 16 * e), (ix + 52 * e, cy)], fill=ROJO + (255,))
        d.text((ix + 90 * e, cy), "SUSCRÍBETE", font=f_, fill=BLANCO + (255,), anchor="lm")
        if tl > 0.6:                                           # la campana, que se balancea
            bx, by, ang = cx0 + bw + 75, cy, 18 * math.sin(tl * 9)
            cam = Image.new("RGBA", (120, 120))
            dc = ImageDraw.Draw(cam)
            dc.pieslice([20, 14, 100, 94], 180, 360, fill=BLANCO + (255,))
            dc.rectangle([20, 54, 100, 84], fill=BLANCO + (255,))
            dc.rectangle([12, 84, 108, 94], fill=BLANCO + (255,))
            dc.ellipse([50, 96, 70, 114], fill=BLANCO + (255,))
            cam = cam.rotate(ang, resample=Image.BICUBIC, center=(60, 14))
            fr.alpha_composite(cam, (int(bx - 60), int(by - 60)))


def main_segmentos(fecha, n, S):
    """8-nov-2026 (petición del usuario): un Short con VARIOS contenidos, cada uno con su frase gancho, unidos con una
    cortinilla numerada (1/3, 2/3...). S["segmentos"] = [{quien, cargo, kicker, entrada, cita, destaca, contexto,
    imagenes: [rutas dentro de dia/<fecha>/]}]; S["voz"] lleva todo el texto en orden."""
    dia = RAIZ / "dia" / fecha
    tmp = dia / "shorts" / f"tmp_{n}"
    tmp.mkdir(parents=True, exist_ok=True)
    texto = S["voz"]
    pal, dur = voz.locuta([{"di": texto}], "normal", tmp / "voz.wav", cola=0.4)
    T = E.Tiempos(texto, pal, 0.0)
    k_fin = texto.find(S.get("pregunta") or "¿Qué opinas?")
    t_fin = T.en(k_fin) if k_fin >= 0 else dur - 3.0
    total = dur + 1.4
    SEG = []
    for i, g in enumerate(S["segmentos"]):
        k0 = texto.find(g["entrada"][:30])
        k1 = texto.find("». ", k0)
        kq = texto.find("«", k0)
        t0 = 0.0 if i == 0 else T.en(k0)
        tc = T.en(k1 + 3)
        imgs = [dia / x for x in g.get("imagenes", []) if (dia / x).exists()]
        if not g.get("imagenes"):                          # sin imágenes elegidas: las del bloque del vídeo largo
            i_s, sec_s = _seccion(dia, g.get("cita", ""))
            imgs = _imagenes_tema(dia, i_s, sec_s, g["quien"])[:3]
        p_ = _persona(dia, g["quien"], g.get("cargo", ""), (0.5, 0.36), 0.42)
        frases, pos = [], texto.find(g["contexto"].strip()[:30])
        for fr_ in re.split(r"(?<=[.?!])\s+", g["contexto"].strip()):
            k_ = texto.find(fr_[:25], pos)
            if k_ >= 0:
                frases.append((T.en(k_), _caja(fr_, tam=50)))
                pos = k_ + 1
        SEG.append({"g": g, "t0": t0, "tc": tc, "tq": T.en(kq) if kq >= 0 else t0, "p": p_, "k": _kicker(g["kicker"].upper()),
                    "c": _cita(g["cita"], g.get("destaca", ""), max_tam=104), "frases": frases or [(tc, _caja(g["contexto"], tam=44))],
                    "fondo": _fondo_tema(imgs[0] if imgs else None), "imgs": imgs,
                    "paneles": [_panel(x) for x in imgs]})
    for i, sg in enumerate(SEG):
        sg["t1"] = SEG[i + 1]["t0"] if i + 1 < len(SEG) else t_fin
    cab = _cabecera(fecha, S.get("categoria", ""))
    fte = fuente("Inter-SemiBold.ttf", 26)
    caps = C.grupos_palabras(T, set())
    ini = [x[0] for x in caps]
    NSEG = len(SEG)

    def cortinilla(fr, i, q):
        """Entre contenidos: una franja diagonal azul y amarilla barre la pantalla (8-nov: sin numerar, el director)."""
        x = int((2.2 * q - 1.1) * AN)
        capa = Image.new("RGBA", (AN, AL))
        d = ImageDraw.Draw(capa)
        d.polygon([(x - 300, 0), (x + AN, 0), (x + AN - 300, AL), (x - 600, AL)], fill=(16, 28, 52, 255))
        d.polygon([(x + AN, 0), (x + AN + 70, 0), (x + AN - 230, AL), (x + AN - 300, AL)], fill=AMARILLO + (255,))
        fr.alpha_composite(capa)

    def persona_en(fr, p, t0, t):
        if not p:
            return
        im, x, y, credito = p
        tl = t - t0
        s_ = 1.0 + 0.10 * (1 - G2.suave(min(1.0, tl / 0.35))) + 0.03 * min(tl, 8) / 8
        if abs(s_ - 1) > 0.003:
            im = im.resize((int(im.width * s_), int(im.height * s_)), Image.BILINEAR)
        G2.pega(fr, im, x - (im.width - p[0].width) // 2, y - (im.height - p[0].height) // 2, 1.0)
        ImageDraw.Draw(fr).text((AN - 30, ZONA[1] - 16), credito, font=fte, fill=(225, 230, 240, 235), anchor="rd",
                                stroke_width=2, stroke_fill=(0, 0, 0, 160))

    def panel_en(fr, sg, t):
        pans = sg["paneles"]
        cada = max(2.5, (sg["t1"] - sg["tc"]) / max(1, len(pans)))
        k = min(len(pans) - 1, int((t - sg["tc"]) / cada))
        im, tl = pans[k], t - sg["tc"] - k * cada
        alto = ZONA[1] - ZONA[0]
        vista = _vista_mc(im, sg["imgs"][k], tl, alto, k)
        dx = int(AN * (1 - G2.suave(min(1.0, tl / 0.35))))
        fr.alpha_composite(vista, (min(dx, AN - 1), ZONA[0]))
        d = ImageDraw.Draw(fr)
        d.rectangle([0, ZONA[0] - 6, AN, ZONA[0]], fill=AMARILLO + (255,))
        d.rectangle([0, ZONA[1], AN, ZONA[1] + 6], fill=AMARILLO + (255,))
        et = "Ilustración IA" if "vinetas" in str(sg["imgs"][k]) else "Foto del tema"
        d.text((AN - 24, ZONA[1] - 14), et, font=fuente("Inter-SemiBold.ttf", 22), fill=(255, 255, 255, 230), anchor="rd")

    _cc = {}

    def cita_parcial(txt):
        if txt not in _cc:
            _cc[txt] = _cita(txt, "", max_tam=104)
        return _cc[txt]

    def cuadro(t):
        if t >= t_fin:
            fr = _mueve(SEG[-1]["fondo"], t, total).convert("RGBA")
            _cierre(fr, t - t_fin, S.get("pregunta") or "¿Qué opinas?")
        else:
            i = max(j for j, sg in enumerate(SEG) if sg["t0"] <= t + 1e-9)
            sg = SEG[i]
            fr = _mueve(sg["fondo"], t, total).convert("RGBA")
            if t < sg["tc"]:                                       # la frase gancho
                persona_en(fr, sg["p"], sg["t0"], t)
                fr.alpha_composite(sg["k"], (60, 1080))
                tl = t - sg["t0"]
                if i == 0:
                    fr.alpha_composite(sg["c"], (40, 1180))
                else:                                              # se escribe mientras la dice
                    g = sg["g"]
                    tq = t - sg["tq"]                              # empieza cuando la voz abre la cita
                    if tq > 0:
                        n_ = max(1, int(len(g["cita"]) * min(1.0, tq / max(1.0, (sg["tc"] - sg["tq"]) * 0.75))))
                        fr.alpha_composite(sg["c"] if n_ >= len(g["cita"]) else cita_parcial(g["cita"][:n_]), (40, 1180))
            else:                                                  # su contexto, con sus imágenes
                if sg["paneles"]:
                    panel_en(fr, sg, t)
                    y_k, y_c = ZONA[1] + 40, ZONA[1] + 150
                else:
                    persona_en(fr, sg["p"], sg["t0"], t)
                    y_k, y_c = 1080, 1190
                fr.alpha_composite(sg["k"], (60, y_k))
                kf = max([j for j, (tt, _) in enumerate(sg["frases"]) if tt <= t + 0.05] or [0])
                caja, tc = sg["frases"][kf][1], t - sg["frases"][kf][0]
                a = G2.suave(min(1.0, tc / 0.25))
                G2.pega(fr, caja, 60, y_c + int(40 * (1 - a)), a)
            if i > 0 and t - sg["t0"] < 0.75:                       # cortinilla al entrar en un contenido nuevo
                cortinilla(fr, i, (t - sg["t0"]) / 0.75)
        for g in [sg["tc"] for sg in SEG] + [t_fin]:
            if 0 <= t - g < 0.08:
                fr.alpha_composite(Image.new("RGBA", (AN, AL), (255, 255, 255, int(130 * (1 - (t - g) / 0.08)))))
        fr.alpha_composite(cab, (0, 0))
        ImageDraw.Draw(fr).rectangle([0, AL - 12, int(AN * min(1.0, t / dur)), AL], fill=AMARILLO + (255,))
        j = max(0, np.searchsorted(ini, t, side="right") - 1)
        if caps and caps[j][0] <= t < caps[j][1]:
            _, _, ws, clave, _ = caps[j]
            cp = C.capa_cap(ws, clave, 0, 0.9, AN - 120)
            fr.alpha_composite(cp, ((AN - cp.width) // 2, 1760 - cp.height // 2))
        i = max(j for j, sg in enumerate(SEG) if sg["t0"] <= t + 1e-9) if t < t_fin else NSEG - 1
        ImageDraw.Draw(fr).text((AN // 2, AL - 50), f"Fuente: {SEG[i]['g'].get('fuente', S.get('fuente', ''))}"[:70],
                                font=fte, fill=(190, 198, 215, 255), anchor="mm")
        return fr

    cortes = [sg["t0"] for sg in SEG[1:]] + [sg["tc"] for sg in SEG] + [t_fin]
    musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", 0.0, 1.4, [], efectos=[(x, "whoosh") for x in cortes], con_sintonia=False)
    g0 = SEG[0]
    foto_p = None
    if g0["p"] and not g0["p"][3].startswith("Ilustración"):
        cred_ = json.loads((dia / "creditos.json").read_text(encoding="utf-8"))
        foto_p = C.fotos_personas({g0["g"]["quien"]}, cred_, dia / "imagenes").get(g0["g"]["quien"])
    PORT = portada(fecha, g0["fondo"], foto_p, S.get("kicker") or g0["g"]["kicker"], S.get("portada") or g0["g"]["cita"],
                   S.get("destaca") or g0["g"].get("destaca", ""))
    PORT.convert("RGB").save(dia / "shorts" / f"short_{n}_portada.png")
    out = dia / "shorts" / f"short_{n}.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "21", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], stdin=subprocess.PIPE)
    for fi in range(int(math.ceil(total * FPS))):
        t = fi / FPS
        fr = PORT.copy() if t < 0.4 else cuadro(t)
        ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    ff.wait()
    cred_all = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    S["creditos"] = [sg["p"][3] + f" ({sg['g']['quien']})" for sg in SEG if sg["p"]]
    for sg in SEG:
        for f in sg["imgs"]:
            if "vinetas" not in str(f):
                c_ = cred_all.get(Path(f).name, {})
                S["creditos"].append(f"Foto: {c_.get('autor', '')[:40]} · {c_.get('licencia', '')} (tema)")
    if any("vinetas" in str(f) for sg in SEG for f in sg["imgs"]):
        S["creditos"].append("Ilustración IA (viñetas del tema)")
    S["duracion"] = round(total, 1)
    (dia / "shorts" / f"short_{n}.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"SHORT {n} ({len(SEG)} contenidos): {total:.1f} s -> {out}")


def main(fecha, n):
    dia = RAIZ / "dia" / fecha
    S = json.loads((dia / "shorts" / f"short_{n}.json").read_text(encoding="utf-8"))
    global SESTILO
    import zlib
    SESTILO = dict(SESTILOS[(zlib.crc32(fecha[:10].encode()) + int(n)) % len(SESTILOS)])
    if S.get("segmentos"):
        return main_segmentos(fecha, n, S)
    tmp = dia / "shorts" / f"tmp_{n}"
    tmp.mkdir(parents=True, exist_ok=True)
    texto = S["voz"]
    pal, dur = voz.locuta([{"di": texto}], "normal", tmp / "voz.wav", cola=0.4)
    T = E.Tiempos(texto, pal, 0.0)
    t_ctx = T.en(texto.find("». ") + 3) if "». " in texto else dur * 0.3
    if S.get("gancho") and S["gancho"] != S["cita"]:    # 8-nov: gancho, quién lo dice y la cita entera; luego el contexto
        k_c = texto.find("«" + S["cita"][:15])
        if k_c >= 0 and texto.find("». ", k_c) >= 0:
            t_ctx = T.en(texto.find("». ", k_c) + 3)
    med = S.get("medio")                                # 8-nov: una segunda voz entre el gancho y el contexto
    t_med = None
    if med:
        k_med = texto.find(med["entrada"][:30])
        if k_med >= 0 and texto.find("». ", k_med) >= 0:
            t_med = T.en(k_med)
            t_ctx = T.en(texto.find("». ", k_med) + 3)
        else:
            med = None
    rp_ = S.get("replica") or {}
    k_rep = texto.find(rp_.get("entrada") or f"{rp_.get('quien')} le responde") if rp_ else -1
    t_rep = T.en(k_rep) if k_rep >= 0 else None        # (buscar solo el nombre fallaba si el contexto lo nombraba)
    k_fin = next((texto.find(x) for x in (S.get("pregunta") or "@@", "¿Qué opinas?", "Más información", "Todo el cruce")
                  if x in texto), -1)
    t_fin = T.en(k_fin) if k_fin >= 0 else dur - 3.0    # 8-nov: el cierre, solo desde la pregunta (3-4 s)
    total = dur + 1.4

    i_sec, sec = _seccion(dia, S["cita"])
    broll = _imagenes_tema(dia, i_sec, sec, S["quien"])
    # 11-nov (el usuario: «has repetido imágenes en los Shorts»): ninguna imagen se repite entre los Shorts del día;
    # si faltan, dos viñetas nuevas de su propio contexto (las «escenas» que describe Gemini)
    reg_u = dia / "shorts" / "imagenes_usadas.json"
    usadas = set(json.loads(reg_u.read_text(encoding="utf-8"))) if reg_u.exists() else set()
    broll = [b for b in broll if b.name not in usadas]
    if len(broll) < 3:
        try:
            import ia_vinetas as IA
            for k, esc in enumerate((S.get("escenas") or [])[:2]):
                dest = dia / "vinetas" / f"short{n}_{k}.jpg"
                if not dest.exists():
                    dest.parent.mkdir(exist_ok=True)
                    IA.ilustra(esc).save(dest, quality=92)
                broll.append(dest)
        except Exception as e:
            print(f"  (sin viñetas propias para el Short: {type(e).__name__})")
    usadas |= {b.name for b in broll}
    reg_u.write_text(json.dumps(sorted(usadas)), encoding="utf-8")
    cab = _cabecera(fecha, S.get("categoria", ""))
    p1 = _persona(dia, S["quien"], S.get("cargo", ""), (0.5, 0.36), 0.42)
    fondo_img = broll[-1] if len(broll) > 1 else None   # 11-nov: el fondo, distinto de la primera imagen del contexto
    if fondo_img is None and p1 and not p1[3].startswith("Ilustración"):
        fondo_img = next((f for f, c in json.loads((dia / "creditos.json").read_text(encoding="utf-8")).items()
                          if c.get("persona") == S["quien"] and (dia / "imagenes" / f).exists()), None)
        fondo_img = dia / "imagenes" / fondo_img if fondo_img else None
    fondo = _fondo_tema(fondo_img)
    k1 = _kicker(S["kicker"].upper())
    c1 = _cita(S["cita"], S.get("destaca", ""))
    # 6-nov: el contexto, frase a frase y sincronizado con la voz (entero no cabía y se cortaba)
    c_ini = texto.find(S["contexto"].strip()[:30])
    frases_ctx, pos = [], c_ini
    for fr_ in re.split(r"(?<=[.?!])\s+", S["contexto"].strip()):
        k_ = texto.find(fr_[:25], pos)
        if k_ >= 0:
            frases_ctx.append((T.en(k_), _caja(fr_, tam=52)))
            pos = k_ + 1
    if not frases_ctx:
        frases_ctx = [(t_ctx, _caja(S["contexto"], tam=44))]

    def ctx_en(t):
        k_ = max([j for j, (tt, _) in enumerate(frases_ctx) if tt <= t + 0.05] or [0])
        return frases_ctx[k_][1], t - frases_ctx[k_][0]
    p2 = k2 = None
    if S.get("replica"):
        rp = S["replica"]
        p2 = _persona(dia, rp["quien"], rp.get("cargo", ""), (0.5, 0.36), 0.42)
        k2 = _kicker(rp.get("kicker") or f"{rp['quien'].split()[-1].upper()} RESPONDE")
    p3 = k3 = c3 = None
    if med:
        p3 = _persona(dia, med["quien"], med.get("cargo", ""), (0.5, 0.36), 0.42)
        k3 = _kicker(med.get("kicker") or med["quien"].split()[-1].upper())
    fte = fuente("Inter-SemiBold.ttf", 26)
    caps = C.grupos_palabras(T, set())
    ini = [x[0] for x in caps]
    # contexto: un panel del tema cada ~4,5 s (si no hay imágenes del tema, se queda la persona)
    fin_ctx = t_rep if t_rep is not None else t_fin
    paneles = []
    if broll:
        nk = max(1, min(len(broll), int((fin_ctx - t_ctx) / 4.5) or 1))
        paneles = [(t_ctx + k * (fin_ctx - t_ctx) / nk, _panel(broll[k])) for k in range(nk)]
    golpes = [0.0, t_ctx] + ([t_rep] if t_rep is not None else []) + ([t_med] if med else [])

    def persona_en(fr, p, t0, t, a=1.0):
        """La persona, grande, con un golpe de cámara al entrar (se acerca y se asienta)."""
        if not p:
            return
        im, x, y, credito = p
        tl = t - t0
        s_ = 1.0 + 0.10 * (1 - G2.suave(min(1.0, tl / 0.35))) + 0.03 * min(tl, 8) / 8
        if abs(s_ - 1) > 0.003:
            im = im.resize((int(im.width * s_), int(im.height * s_)), Image.BILINEAR)
        G2.pega(fr, im, x - (im.width - p[0].width) // 2, y - (im.height - p[0].height) // 2, a)
        ImageDraw.Draw(fr).text((AN - 30, ZONA[1] - 16), credito, font=fte, fill=(225, 230, 240, int(235 * a)), anchor="rd",
                                stroke_width=2, stroke_fill=(0, 0, 0, int(160 * a)))

    def panel_en(fr, t):
        k = max(j for j, (tp, _) in enumerate(paneles) if tp <= t + 1e-6) if any(tp <= t for tp, _ in paneles) else 0
        tp, im = paneles[k]
        tl = t - tp
        alto = ZONA[1] - ZONA[0]
        vista = _vista_mc(im, broll[k], tl, alto, k)
        entra = G2.suave(min(1.0, tl / 0.35)) if k > 0 else G2.suave(min(1.0, tl / 0.3))
        dx = int(AN * (1 - entra))
        fr.alpha_composite(vista, (dx, ZONA[0]) if dx < AN else (AN - 1, ZONA[0]))
        d = ImageDraw.Draw(fr)
        d.rectangle([0, ZONA[0] - 6, AN, ZONA[0]], fill=AMARILLO + (255,))
        d.rectangle([0, ZONA[1], AN, ZONA[1] + 6], fill=AMARILLO + (255,))
        ff = fuente("Inter-SemiBold.ttf", 22)
        et = "Ilustración IA" if "vinetas" in str(broll[k]) else "Foto del tema"
        d.text((AN - 24, ZONA[1] - 14), et, font=ff, fill=(255, 255, 255, 230), anchor="rd")

    def cuadro(t):
        fr = _mueve(fondo, t, total).convert("RGBA")
        if t_rep is not None and t_rep <= t < t_fin:                  # 3) réplica
            tl = t - t_rep
            persona_en(fr, p2, t_rep, t, G2.suave(min(1.0, tl / 0.3)))
            fr.alpha_composite(k2, (60, 1080))
            n_ = max(1, int(len(S["replica"]["cita"]) * min(1.0, (tl - 0.3) / 1.6)))
            cr = _cita_cache(S["replica"]["cita"][:n_] if tl < 1.9 else S["replica"]["cita"], "")
            fr.alpha_composite(cr, (40, 1180))
        elif t >= t_fin:                                             # 4) cierre
            _cierre(fr, t - t_fin, S.get("pregunta") or "¿Qué opinas?")
        elif med and t_med <= t < t_ctx:                             # 1b) la segunda voz (8-nov)
            tl = t - t_med
            persona_en(fr, p3, t_med, t, G2.suave(min(1.0, tl / 0.3)))
            fr.alpha_composite(k3, (60, 1080))
            n_ = max(1, int(len(med["cita"]) * min(1.0, (tl - 0.3) / 2.2)))
            fr.alpha_composite(_cita_cache(med["cita"][:n_] if tl < 2.5 else med["cita"], ""), (40, 1180))
        elif t >= t_ctx and paneles:                                 # 2) contexto con imágenes del tema
            panel_en(fr, t)
            fr.alpha_composite(k1, (60, ZONA[1] + 40))
            ctx, tc = ctx_en(t)
            a = G2.suave(min(1.0, tc / 0.25))
            G2.pega(fr, ctx, 60, ZONA[1] + 150 + int(40 * (1 - a)), a)
        else:                                                        # 1) gancho (y contexto sin imágenes)
            persona_en(fr, p1, 0.0, t)
            fr.alpha_composite(k1, (60, 1080))
            if t < t_ctx:
                fr.alpha_composite(c1, (40, 1180))
            else:                                                    # el contexto ocupa el sitio de la frase
                ctx, tc = ctx_en(t)
                a = G2.suave(min(1.0, tc / 0.25))
                G2.pega(fr, ctx, 60, 1190 + int(40 * (1 - a)), a)
        for g in golpes:                                             # destello breve en cada cambio de parte
            if 0 <= t - g < 0.08 and g > 0:
                fr.alpha_composite(Image.new("RGBA", (AN, AL), (255, 255, 255, int(150 * (1 - (t - g) / 0.08)))))
        fr.alpha_composite(cab, (0, 0))
        ImageDraw.Draw(fr).rectangle([0, AL - 12, int(AN * min(1.0, t / dur)), AL], fill=AMARILLO + (255,))
        j = max(0, np.searchsorted(ini, t, side="right") - 1)    # subtítulos grandes
        if t < caps[j][1] and t >= caps[j][0]:
            _, _, ws, clave, _ = caps[j]
            cp = C.capa_cap(ws, clave, 0, 0.9, AN - 120)
            fr.alpha_composite(cp, ((AN - cp.width) // 2, 1760 - cp.height // 2))
        ImageDraw.Draw(fr).text((AN // 2, AL - 50), f"Fuente: {S.get('fuente', '')}"[:70], font=fte,
                                fill=(190, 198, 215, 255), anchor="mm")
        return fr

    _cc = {}

    def _cita_cache(txt, dest):
        if txt not in _cc:
            _cc[txt] = _cita(txt, dest, max_tam=104)
        return _cc[txt]

    cortes = [x for x in (t_ctx, t_rep, t_fin) if x] + [tp for tp, _ in paneles[1:]]
    musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", 0.0, 1.4, [], efectos=[(x, "whoosh") for x in cortes], con_sintonia=False)
    foto_p = None                                       # la foto real de la persona (no la ilustración) para la portada
    if p1 and not p1[3].startswith("Ilustración"):
        cred_ = json.loads((dia / "creditos.json").read_text(encoding="utf-8"))
        fp = C.fotos_personas({S["quien"]}, cred_, dia / "imagenes").get(S["quien"])
        foto_p = fp if fp and Path(fp).exists() else None
        if foto_p is None:
            foto_p = next((dia / "imagenes" / f for f, c_ in cred_.items() if c_.get("persona") == S["quien"]
                           and (dia / "imagenes" / f).exists()), None)
    try:
        if S.get("portada_tematica"):                  # 11-nov: sin buena foto de la persona, titular de impacto
            PORT = portada_tematica(Image.open(broll[0]) if broll else None, S["portada_tematica"])
        else:
            PORT = portada(fecha, fondo, foto_p, S["kicker"], S.get("portada") or S["cita"], S.get("destaca", ""))
    except Exception as e:                              # sin portada propia, el fotograma del gancho
        print(f"  AVISO: portada propia no hecha ({type(e).__name__}): se usa el fotograma del gancho")
        PORT = cuadro(0.6)
    PORT.convert("RGB").save(dia / "shorts" / f"short_{n}_portada.png")
    _cuadro_normal = cuadro

    def cuadro(t):                                      # los primeros 0,4 s, la portada (YouTube suele tomarla)
        if t < 0.4:
            fr = PORT.copy()
            ImageDraw.Draw(fr).rectangle([0, AL - 12, int(AN * min(1.0, t / dur)), AL], fill=AMARILLO + (255,))
            return fr
        return _cuadro_normal(t)
    out = dia / "shorts" / f"short_{n}.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "21", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], stdin=subprocess.PIPE)
    for fi in range(int(math.ceil(total * FPS))):
        ff.stdin.write(cuadro(fi / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
    # créditos para la descripción de YouTube (los lee subir.py)
    S["creditos"] = [p[3] + f" ({nom})" for p, nom in ((p1, S["quien"]), (p2, (S.get("replica") or {}).get("quien")), (p3, (med or {}).get("quien")))
                     if p]
    cred_all = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    for f in broll:                                    # las imágenes del tema que salen en el contexto o el fondo
        if "vinetas" in str(f):
            continue
        c_ = cred_all.get(Path(f).name, {})
        S["creditos"].append(f"Foto: {c_.get('autor', '')[:40]} · {c_.get('licencia', '')} (tema)")
    if any("vinetas" in str(f) for f in broll):
        S["creditos"].append("Ilustración IA (viñetas del tema)")
        org = dia / "vinetas" / "origen.json"
        org = json.loads(org.read_text(encoding="utf-8")) if org.exists() else {}
        S["sintetico"] = any(org.get(Path(f).stem, {}).get("persona") for f in broll)   # personas reales dibujadas
    S["duracion"] = round(total, 1)
    (dia / "shorts" / f"short_{n}.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"SHORT {n}: {total:.1f} s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
