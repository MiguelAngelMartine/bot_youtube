"""LARGO HORIZONTAL (16:9) para YouTube con el estilo tablero del corto vertical: polaroids con fotos reales, notas,
pegatinas, sellos y flechas que se van pegando en un tablero; la camara viaja a cada pieza cuando la voz la nombra y Urni
narra abajo a la izquierda. Es el episodio completo (todas las secciones de episodio.json) con la cabecera, la sintonia,
las cortinillas y el cierre del canal. Los bloques "sobrio" van sin Urni, sin "pop" y con la musica mas baja.
Escribe lo mismo que episodio.py (episodio.mp4, episodio.srt, escenas.json, episodio_descripcion.txt), asi que el control
de calidad y la publicacion no cambian.
El arranque es el sumario a pantalla completa de titulares.py, sin presentacion, y un golpe de marca (logo y sintonia).
Uso: python largo.py AAAA-MM-DD [--fotogramas] [--hasta S]   (--fotogramas: sin video, un PNG del final de cada escena en tmp_largo/)"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import multiprocessing as mp
import os
import subprocess
import time
import traceback
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

import corto as C
import episodio as E
import genera_video as V1
import genera_video2 as G2
import musica
import voz
import prototipo_animado as P
import cierre as CI
import marca
import titulares as TIT
import vinetas as VIN
import ia_vinetas as IAV
from corto import estrecha, nota, pegatina, polaroid, sello
from genera_video2 import AMARILLO, AN, AL, BLANCO, FPS, ROJO, fuente, pega, suave

INTRO = 0.4        # el video entra directo con los titulares (sin cabecera ni presentacion; decision del 1-nov-2026)
GOLPE = marca.DUR  # golpe de marca (logo y sintonia, marca.py) entre el sumario y el primer bloque
CALIENTA = 40      # fotogramas que cada trozo dibuja sin grabar antes de empezar (la camara suaviza con ~0,2 s)
CON_URNI = False                         # decision del usuario (2-nov-2026): Urni ya no sale en los videos (el logo sigue)
BX, BY, BW, BH = 40, 178, 1840, 762      # ventana del escenario: de lado a lado (6-nov: más grande, sin columna lateral)
LW = 1510                                 # ancho con el que se colocan las piezas del tablero (luego se amplían)
AMARILLA = (255, 238, 150)               # nota amarilla (etiquetas y datos de contexto)
CREMA = (255, 246, 196)


def foto_suelta(ruta, credito, ancho=360):
    """Foto de archivo de la escena, impresa y pegada en el tablero, con su credito al pie."""
    f = Image.open(ruta).convert("RGB")
    alto_f = int(ancho * 0.72)
    im = Image.new("RGBA", (ancho + 30, alto_f + 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([15, 20, ancho + 15, alto_f + 80], fill=(0, 0, 0, 70))
    d.rectangle([8, 12, ancho + 8, alto_f + 72], fill=BLANCO + (255,))
    r = max((ancho - 30) / f.width, (alto_f - 30) / f.height)
    f = f.resize((math.ceil(f.width * r), math.ceil(f.height * r)), Image.LANCZOS)
    x0, y0 = (f.width - (ancho - 30)) // 2, (f.height - (alto_f - 30)) // 3
    im.paste(f.crop((x0, y0, x0 + ancho - 30, y0 + alto_f - 30)), (23, 27))
    d.text((ancho / 2 + 8, alto_f + 24), f"Foto de archivo: {credito['autor'][:34]} · {credito['licencia']}",
           font=fuente("Inter-Regular.ttf", 17), fill=(130, 135, 145), anchor="mt")
    C.celo(im, ancho / 2 - 50, -3)
    return im.rotate(-2, expand=True, resample=Image.BICUBIC)


def rejilla(notas, x0, y0, ancho, t_de):
    """Notas en dos columnas, con la segunda fila algo desplazada para que no parezca una tabla."""
    out, y, fila = [], y0, []
    for k, nt in enumerate(notas):
        x = x0 + (ancho + 30) * (k % 2) + (40 if (k // 2) % 2 else 0)
        out.append((nt, x, y, t_de(k)))
        fila.append(nt.height)
        if k % 2 == 1:
            y += max(fila) - 10
            fila = []
    return out


def rejilla_vinetas(vins, t_de, y0=130):
    """Viñetas grandes y con aire (3-nov-2026): 1 centrada; 2 lado a lado; 3, dos arriba y una centrada; 4, de dos en
    dos. Marcadas como 'foco' para que la camara vaya de una a otra como quien lee un comic."""
    out, gap = [], 70
    w = vins[0].width
    for k, v in enumerate(vins):
        v.info["foco"] = True
        fila, col = divmod(k, 2)
        solo = len(vins) % 2 == 1 and k == len(vins) - 1
        x = 40 + (w + gap) // 2 if solo and len(vins) > 1 else 40 + col * (w + gap)
        alto_fila = max(vv.height for vv in vins[fila * 2:fila * 2 + 2])
        y = y0 + fila * (alto_fila + gap)
        out.append((v, x, y, t_de(k)))
    return out


# ------------------------------------------------------------------ de la escena del guion a piezas en el tablero

VARIANTES, USOS = {}, {}                              # retratos de cada persona en este video y cuantas veces ha salido


def piezas_h(ve, T, c0, t0, fotos, cred, foto, usadas):
    """Lista de (pieza, x, y, t_aparece) sobre un tablero de BW de ancho. foto: (ruta, credito) de la escena o None."""
    def foto_de(nombre, cargo=""):
        f = fotos.get(nombre)
        if not f:                                         # sin foto libre: ilustracion de su ambito, nunca su cara (4-nov)
            amb = IAV.ilustracion_ambito(cargo, ve.get("_sobrio", False))
            return (amb, {"ia": True, "autor": "Ilustración IA", "licencia": "sin foto libre"}) if amb else (None, None)
        otras = VARIANTES.get(nombre) or [f]              # 3-nov: si hay varias fotos de la persona, se van turnando
        f = otras[USOS.get(nombre, 0) % len(otras)]
        USOS[nombre] = USOS.get(nombre, 0) + 1
        usadas[f.name] = cred[f.name]
        return f, cred[f.name]

    def cuando(tr, defecto):
        return T.cuando(tr, c0, defecto) if tr else defecto
    lado = foto_suelta(*foto) if foto else None
    out, tipo = [], ve["tipo"]
    if tipo == "persona":
        p = ve["persona"]
        f, c = foto_de(p["nombre"], p.get("cargo", ""))
        out.append((polaroid(f, p["nombre"], p["cargo"], p["partido"], c, 340), 40, 30, t0 + 0.1))
        y_sello = 60
        if p.get("cita"):
            nc = nota(p["cita"], 480, 42, "Fuente: " + p.get("medio", ""))
            out.append((nc, 440, 50, cuando(p.get("cita_cuando"), t0 + 2)))
            y_sello = 50 + nc.height + 30
        if ve.get("sello"):                            # junto a la cita, nunca sobre la cara ni el nombre (2-nov)
            out.append((sello(ve["sello"]), 460, y_sello, cuando(ve.get("sello_cuando"), t0 + 1.2)))
        fl = ve.get("flujo")
        if fl:
            a = fl["a"]
            f2, c2 = foto_de(a["nombre"], a.get("cargo", ""))
            ta = cuando(fl.get("a_cuando"), t0 + 4)
            tf = cuando(fl.get("cuando"), ta - 1)
            out.append((nota(fl["etiqueta"], 380, 32, color=AMARILLA), 450, 440, tf))
            out.append((("flecha", (860, 540), (1090, 330)), 0, 0, tf + 0.2))
            out.append((polaroid(f2, a["nombre"], a["cargo"], a["partido"], c2, 300), 1120, 30, ta))
            if a.get("cita"):
                out.append((nota(a["cita"], 470, 34, "Fuente: " + a.get("medio", "")), 980, 520, ta + 1.2))
        elif lado:
            out.append((lado, 1060, 90, t0 + 0.6))
    elif tipo == "mapa":
        out.append((C.mapa(ve["puntos"], ve.get("ruta", []), 620), 40, 40, t0 + 0.1))
        out.append((pegatina(ve["titular"].upper(), tam=44), 760, 60, t0 + 1.2))
        out.append((nota(ve.get("sub", ""), 640, 38, "Fuente: " + ve.get("fuente", "")), 760, 180, t0 + 2.0))
    elif tipo == "citas":
        out.append((pegatina(ve["titulo"], tam=46), 40, 20, t0 + 0.1))
        n = len(ve["items"])
        col = (LW - 60) // n
        ap = min(340, int(col * 0.52))                    # 6-nov: polaroids más grandes (con dos, mucho más)
        for k, it in enumerate(ve["items"]):
            f, c = foto_de(it["nombre"], it.get("cargo", ""))
            ti = cuando(it.get("cuando"), t0 + 1 + 3 * k)
            x = 30 + col * k
            out.append((polaroid(f, it["nombre"], it["cargo"], it["partido"], c, ap), x + (col - ap - 30) // 2, 100, ti))
            out.append((nota(it["cita"], col - 40, 36 if n < 3 else 32, "Fuente: " + it["medio"]), x, 100 + ap + 150,
                        ti + 0.6))
    elif tipo == "posturas":
        out.append((pegatina(ve["titulo"], tam=46), 40, 20, t0 + 0.1))
        cc = ve["centro"]
        f, c = foto_de(cc["nombre"], cc.get("cargo", ""))
        out.append((polaroid(f, cc["nombre"], cc["cargo"], cc["partido"], c, 300), 40, 100, t0 + 0.3))
        y = 100
        for k, it in enumerate(ve["presionan"]):
            col = P.PARTIDO.get(it["partido"], (90, 100, 120))
            ti = cuando(it.get("cuando"), t0 + 1 + 0.5 * k)
            out.append((pegatina(it["nombre"].upper(), col, BLANCO, 44), 720, y, ti))
            out.append((("flecha", (710, y + 40), (400, 250 + 40 * k)), 0, 0, ti + 0.25))
            y += 100
        wmax = max([o[0].width for o in out if isinstance(o[0], Image.Image) and o[1] == 720] + [0])
        te = cuando(ve.get("etiqueta_cuando"), t0 + 3)
        if 720 + wmax + 20 <= 1080:
            out.append((nota(ve["etiqueta"], 400, 38, color=AMARILLA), 1080, 100, te))
        else:                                          # nombres largos: la nota va debajo, sin pisarlos
            ne = nota(ve["etiqueta"], 700, 38, color=AMARILLA)
            out.append((ne, 720, y + 10, te))
            y += ne.height + 10
        ap = ve["aparte"]
        ta = cuando(ap.get("cuando"), t0 + 6)
        out.append((pegatina(ap["nombre"].upper(), (150, 150, 160), BLANCO, 44), 720, y + 30, ta))
        out.append((nota(ap["texto"], 760, 34, "Fuentes: " + ve.get("fuente", "")), 720, y + 120, ta + 0.5))
    elif tipo in ("claves", "cronologia", "sumario"):
        titulo = "HOY EN EL RESUMEN" if tipo == "sumario" else ve["titulo"]
        out.append((pegatina(titulo, tam=46), 40, 56, t0 + 0.1))
        ancho = 520 if lado else 680
        txts = [(f"{k + 1:02d} · " if tipo == "sumario" else (it["hora"] + " · " if it.get("hora") else "")) + it["texto"]
                for k, it in enumerate(ve["items"])]
        vin = ve.get("_vin", {})
        if vin and tipo != "sumario":                  # viñetas de novela grafica en vez de notas manuscritas
            ancho = 700                                # grandes: la camara se acerca a cada una (3-nov)
            txts = [(it["hora"] + " · " if it.get("hora") else "") + it["texto"] for it in ve["items"]]
        notas = [VIN.vineta(None, tx, ancho, sobrio=ve.get("_sobrio", False), imagen=Image.open(vin[k]),
                            proporcion=0.50, letra=1.3, giro=(-0.8, 0.7, 0.6, -0.6)[k % 4],
                            fuente_txt=ve.get("_vin_txt", {}).get(k, "Ilustración IA")) if k in vin
                 else nota(tx, ancho, 38, color=CREMA if k % 2 else C.PAPEL) for k, tx in enumerate(txts)]
        if vin and tipo != "sumario" and len(vin) == len(notas):
            # la primera entra con la escena (el locutor ya habla de ella); las demas, cuando la voz las nombra
            out += rejilla_vinetas(notas, lambda k: t0 + 0.4 if k == 0 else cuando(ve["items"][k].get("cuando"), t0 + 1 + k))
        else:
            out += rejilla(notas, 40, 130, ancho, lambda k: cuando(ve["items"][k].get("cuando"), t0 + 1 + k))
        if lado and not (vin and tipo != "sumario"):   # con viñetas, la foto sobra y quedaba tapada (2-nov)
            out.append((lado, 1140, 110, t0 + 0.6))
    elif tipo == "cifra":
        out.append((pegatina(ve["numero"], ROJO, BLANCO, 200), 60, 40, t0 + 0.1))
        out.append((pegatina(ve["etiqueta"].upper(), tam=50), 60, 300, t0 + 0.6))
        out.append((nota(ve.get("sub", ""), 620, 38, "Fuente: " + ve.get("fuente", "")), 60, 400, t0 + 1.2))
        if lado:
            out.append((lado, 1060, 40, t0 + 0.9))
        if ve.get("nota"):
            out.append((nota(ve["nota"], 560, 36, color=AMARILLA), 760, 420 if lado else 120,
                        cuando(ve.get("cuando_nota"), t0 + 3)))
    elif tipo == "calendario":
        out.append((E.hoja_calendario(ve["dia"], ve["mes"], ve["pie"]), 60, 60, t0 + 0.1))
        y = 30
        for k, it in enumerate(ve["items"]):
            ti = cuando(it.get("cuando"), t0 + 1 + k)
            nt = nota(it["texto"], 820, 36)
            out.append((pegatina(it["hora"].upper(), tam=40), 480, y, ti))
            out.append((nt, 480, y + 66, ti + 0.2))
            y += 66 + nt.height - 6
    elif tipo == "breve":
        out.append((pegatina(ve["lugar"], ROJO, BLANCO, 44), 40, 30, t0 + 0.1))
        if 0 in ve.get("_vin", {}):
            out.append((VIN.vineta(None, ve["titular"], 700, sobrio=ve.get("_sobrio", False),
                                   imagen=Image.open(ve["_vin"][0]), letra=1.2,
                                   fuente_txt=ve.get("_vin_txt", {}).get(0, "Ilustración IA")), 40, 110, t0 + 0.3))
            out.append((nota(ve["sub"], 560, 34, "Fuente: " + ve["fuente"], color=AMARILLA), 800, 160, t0 + 1.2))
        else:
            out.append((nota(ve["titular"], 760, 48), 40, 130, t0 + 0.3))
            out.append((nota(ve["sub"], 640, 34, "Fuente: " + ve["fuente"], color=AMARILLA), 120, 470, t0 + 1.2))
            out.append((lado, 900, 70, t0 + 0.6) if lado else (E.icono(ve["icono"], 200), 1000, 140, t0 + 0.6))
    elif tipo == "despedida":
        out.append((nota("Gracias por vernos.", 720, 64), 380, 110, t0 + 0.1))
        out.append((pegatina("MAÑANA, MÁS.", tam=64), 560, 400, t0 + 0.9))
    else:
        raise ValueError(f"escena sin version de tablero: {tipo}")
    if lado and any(pc is lado for pc, *_ in out):     # en la descripcion solo se acredita la foto que sale
        usadas[foto[0].name] = foto[1]
    return out


# ------------------------------------------------------------------ capas fijas

_cache_fte = {}


def tarjeta_fuente(txt):
    """Columna izquierda: de donde sale lo que se esta contando."""
    if txt not in _cache_fte:
        fnt = fuente("Inter-Regular.ttf", 24)
        ls = C.lineas(txt, fnt, 256)[:6]
        alto = 66 + len(ls) * 32 + 14
        im = Image.new("RGBA", (300, alto), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, 299, alto - 1], radius=14, fill=(10, 18, 34, 235), outline=(44, 62, 100, 255), width=2)
        d.text((22, 18), "FUENTES" if any(s in txt for s in "·,") else "FUENTE", font=estrecha(32), fill=AMARILLO + (255,))
        for j, l in enumerate(ls):
            d.text((22, 64 + 32 * j), l, font=fnt, fill=(220, 225, 235, 255))
        _cache_fte[txt] = im
    return _cache_fte[txt]


_fondos = {}


def fondo_vivo(ruta, w, h, sobrio=False):
    """6-nov-2026 (el usuario: «parece un PowerPoint»): detrás de las piezas, la imagen del tema a pantalla completa,
    desenfocada, oscurecida y con la luz de la marca, en vez del azul liso. Sin imagen, el tablero de siempre."""
    k = (str(ruta), w, h, sobrio)
    if k not in _fondos:
        if ruta is None or not Path(ruta).exists():
            _fondos[k] = C.tablero_base(h, w)
        else:
            im = ImageOps.fit(Image.open(ruta).convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.35))
            im = im.filter(ImageFilter.GaussianBlur(max(6, w // 110)))
            im = ImageEnhance.Color(im).enhance(0.9 if sobrio else 1.3)
            im = ImageEnhance.Brightness(im).enhance(0.42 if sobrio else 0.5).convert("RGBA")
            import titulares as TIT
            im.alpha_composite(TIT._tinte((w, h), sobrio))
            _fondos[k] = im
    return _fondos[k]


def fondo_de(ve, foto, vin, fotos, bloque_img):
    """La imagen del tema de una escena: su foto, su viñeta, la foto de alguien que sale en ella o la del bloque."""
    if foto:
        return foto[0]
    if vin:
        return vin[min(vin)]
    txt = json.dumps(ve, ensure_ascii=False, default=str)
    for n, f in fotos.items():
        if n and n in txt and Path(f).exists():
            return f
    return bloque_img


def linea_fuente(txt):
    k = ("linea", txt)
    if k not in _cache_fte:
        f1, f2 = estrecha(28), fuente("Inter-Regular.ttf", 22)
        et = "FUENTES" if any(c_ in txt for c_ in "·,") else "FUENTE"
        md = ImageDraw.Draw(Image.new("L", (1, 1)))
        w1 = int(md.textlength(et, font=f1))
        ls = C.lineas(txt, f2, 560 - w1)[:2]
        im = Image.new("RGBA", (600, 64))
        d = ImageDraw.Draw(im)
        d.text((0, 4), et, font=f1, fill=AMARILLO + (255,))
        for j, l in enumerate(ls):
            d.text((w1 + 14, 6 + 27 * j), l, font=f2, fill=(215, 222, 235, 255))
        _cache_fte[k] = im
    return _cache_fte[k]


def encaja(piezas, fondo=None, sobrio=False):
    """Tablero de la escena con la proporcion de la ventana y las piezas centradas en el, para que se vea entero.
    6-nov: la cámara se acerca para que las piezas llenen la pantalla (hasta x1,35) y detrás va el fondo vivo."""
    def caja(pc, x, y):
        if isinstance(pc, tuple):
            return max(pc[1][0], pc[2][0]) + 40, max(pc[1][1], pc[2][1]) + 40
        return x + pc.width, y + pc.height
    ancho = max(caja(pc, x, y)[0] for pc, x, y, _ in piezas) + 40
    alto = max(caja(pc, x, y)[1] for pc, x, y, _ in piezas) + 40
    wb = max(int(BW / 1.35), ancho, math.ceil(alto * BW / BH))
    hb = math.ceil(wb * BH / BW)
    dx, dy = (wb - ancho) // 2, (hb - alto) // 2
    mueve = lambda pc, x, y: ((("flecha", (pc[1][0] + dx, pc[1][1] + dy), (pc[2][0] + dx, pc[2][1] + dy)), 0, 0)
                              if isinstance(pc, tuple) else (pc, x + dx, y + dy))
    return [(*mueve(pc, x, y), ta) for pc, x, y, ta in piezas], fondo_vivo(fondo, wb, hb, sobrio).copy()


# ------------------------------------------------------------------ comic a pantalla completa (opcion A, 4-nov-2026)
_comic_cache = {}


def silueta_suave(c):
    import miniatura as MN
    return MN.silueta_suave(c)


def _trama(sobrio):
    k = ("trama", sobrio)
    if k not in _comic_cache:
        im = Image.new("RGB", (BW, BH), (14, 18, 26) if sobrio else (12, 20, 38))
        d = ImageDraw.Draw(im)
        col = (40, 44, 52) if sobrio else (28, 44, 86)
        for y in range(0, BH, 18):
            for x in range((y // 18) % 2 * 9, BW, 18):
                d.ellipse([x, y, x + 6, y + 6], fill=col)
        _comic_cache[k] = im
    return _comic_cache[k]


def _caja_narr(txt, ancho=820):
    k = ("caja", txt, ancho)
    if k not in _comic_cache:
        f = fuente("ComicNeue-Bold.ttf", 38)
        ls = C.lineas(txt.upper(), f, ancho - 44)[:5]
        h = 32 + 46 * len(ls)
        im = Image.new("RGBA", (ancho + 12, h + 12))
        d = ImageDraw.Draw(im)
        d.rectangle([10, 10, ancho + 10, h + 10], fill=(0, 0, 0, 255))
        d.rectangle([0, 0, ancho, h], fill=(250, 240, 205, 255), outline=(0, 0, 0, 255), width=4)
        for j, l in enumerate(ls):
            d.text((22, 16 + 46 * j), l, font=f, fill=(15, 15, 15, 255))
        _comic_cache[k] = im
    return _comic_cache[k]


def _panel(pn, tl, sobrio):
    """Un panel del comic en el instante tl (segundos desde que entra)."""
    if pn["clase"] == "vineta":
        k = ("ilus", pn["ruta"], sobrio)
        if k not in _comic_cache:
            im = ImageOps.fit(Image.open(pn["ruta"]).convert("RGB"), (int(BW * 1.12), int(BH * 1.12)), Image.LANCZOS,
                              centering=(0.5, 0.4))
            if sobrio:
                im = ImageEnhance.Color(im).enhance(0.35)
            _comic_cache[k] = im
        base = _comic_cache[k]
        z = 1.0 + 0.07 * min(tl, 12) / 12               # zoom y desplazamiento lentos (Ken Burns)
        cw, ch = int(base.width / z), int(base.height / z)
        x0 = int((base.width - cw) * (0.3 + 0.4 * min(tl, 12) / 12))
        y0 = int((base.height - ch) * 0.45)
        im = base.crop((x0, y0, x0 + cw, y0 + ch)).resize((BW, BH), Image.BILINEAR).convert("RGBA")
        if pn.get("credito"):
            ff = fuente("Inter-SemiBold.ttf", 22)
            d = ImageDraw.Draw(im)
            tw = d.textlength(pn["credito"], font=ff)
            d.rectangle([BW - tw - 34, BH - 46, BW - 10, BH - 12], fill=(255, 255, 255, 220))
            d.text((BW - 22, BH - 16), pn["credito"], font=ff, fill=(60, 60, 70, 255), anchor="rb")
    else:
        fondo = pn.get("foto") or pn.get("fondo")       # 6-nov: la foto (o la imagen del tema) desenfocada, no la trama
        im = fondo_vivo(fondo, BW, BH, sobrio).copy() if fondo else _trama(sobrio).copy().convert("RGBA")
        if pn["clase"] == "persona":
            k = ("persona", pn["foto"], sobrio)
            if k not in _comic_cache:
                import miniatura as MN
                cc = MN.recorte(pn["foto"])
                kk = (BH * 0.96) / cc.height
                cc = cc.resize((int(cc.width * kk), int(cc.height * kk)), Image.LANCZOS)
                _comic_cache[k] = silueta_suave(cc)
            s, pad = _comic_cache[k]
            im.alpha_composite(s, (BW - s.width + pad + 10, BH - s.height + pad + 20))
            ancho_txt = int(BW * 0.55)
        else:
            ancho_txt = BW - 160
        cita = pn["cita"]
        n = len(cita) if pn["clase"] != "persona" else max(0, int(len(cita) * min(1.0, (tl - 0.5) / 3.0)))
        if n:                                            # la cita se va escribiendo (persona) o sale entera (texto)
            f = fuente("Anton-Regular.ttf", 72 if len(cita) < 90 else 60)
            d = ImageDraw.Draw(im)
            for j, l in enumerate(C.lineas(cita[:n], f, ancho_txt)[:6]):
                d.text((64, 200 + 84 * j), l, font=f, fill=(0, 0, 0, 200))
                d.text((58, 194 + 84 * j), l, font=f, fill=(255, 255, 255, 255))
    if pn.get("narr"):
        im.alpha_composite(_caja_narr(pn["narr"], 760 if pn["clase"] == "persona" else 900), (40, 30))
    if pn.get("sub") and tl > 1.0:                     # breves: la explicacion entra despues, abajo a la izquierda
        sb = _caja_narr(pn["sub"], 860)
        im.alpha_composite(sb, (40, BH - sb.height - 30))
    if pn.get("lugar"):                                # breves: el lugar, en etiqueta roja arriba a la derecha
        k = ("lugar", pn["lugar"])
        if k not in _comic_cache:
            f = fuente("Inter-Black.ttf", 40)
            w = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(pn["lugar"].upper(), font=f)) + 50
            e = Image.new("RGBA", (w + 10, 74))
            d = ImageDraw.Draw(e)
            d.rectangle([8, 8, w + 8, 72], fill=(0, 0, 0, 160))
            d.rectangle([0, 0, w, 64], fill=ROJO + (255,))
            d.text((25, 32), pn["lugar"].upper(), font=f, fill=BLANCO + (255,), anchor="lm")
            _comic_cache[k] = e
        e = _comic_cache[k]
        im.alpha_composite(e, (BW - e.width - 30, 30))
    return im


def vista_comic(pt, t):
    """Opcion A: un panel tras otro a pantalla completa; el nuevo entra empujando (o fundido en los bloques sobrios)."""
    pns, sobrio = pt["comic"], pt.get("sobrio", False)
    k = max([j for j, pn in enumerate(pns) if pn["t"] <= t] or [0])
    tl = t - pns[k]["t"]
    cur = _panel(pns[k], max(0.0, tl), sobrio)
    dur = 0.6 if sobrio else 0.42
    if k > 0 and tl < dur:
        prev = _panel(pns[k - 1], t - pns[k - 1]["t"], sobrio)
        x = suave(tl / dur)
        if sobrio:
            return Image.blend(prev, cur, x)
        fr = Image.new("RGBA", (BW, BH), (0, 0, 0, 255))
        fr.paste(prev, (int(-BW * x), 0))
        fr.paste(cur, (int(BW * (1 - x)), 0))
        ImageDraw.Draw(fr).rectangle([int(BW * (1 - x)) - 14, 0, int(BW * (1 - x)), BH], fill=(0, 0, 0, 255))
        return fr
    return cur


def paneles_comic(ve, T, c0, t0, fotos):
    """Paneles de una escena claves/cronologia: viñeta, persona (foto real + cita) o texto. Cada uno entra cuando
    empieza la frase que habla de el (no al llegar a la palabra clave); el primero, con la escena."""
    vin, txt_ia = ve.get("_vin", {}), ve.get("_vin_txt", {})
    pns, ult = [], t0
    for k, it in enumerate(ve.get("items", [])):
        texto = ((it.get("hora") + " · ") if it.get("hora") else "") + it.get("texto", "")
        quien = it.get("persona_vineta")
        foto = (VARIANTES.get(quien) or [fotos.get(quien)])[0] if quien else None
        if k in vin:
            pn = {"clase": "vineta", "ruta": vin[k], "narr": texto, "credito": txt_ia.get(k, "Ilustración IA")}
        elif foto:
            narr, _, cita = texto.partition(":")
            pn = {"clase": "persona", "foto": foto, "narr": narr if cita else quien, "cita": (cita or texto).strip()}
        else:
            pn = {"clase": "texto", "narr": "", "cita": texto}
        if k == 0:
            tk = t0 + 0.3
        else:
            cw = it.get("cuando") or ""
            ci = T.texto.find(cw, c0) if cw else -1
            if ci >= 0:                                   # inicio de la frase que contiene el «cuando»
                ini = max(T.texto.rfind(s, c0, ci) for s in (". ", "? ", "! ", ": "))
                tk = T.en(ini + 2 if ini >= c0 else ci)
            else:
                tk = ult + 4.0
            tk = max(tk, ult + 2.2)                       # cada panel, al menos 2,2 s
        pn["t"] = tk
        ult = tk
        pns.append(pn)
        if k:
            T.eventos.append(tk)                          # golpe de sonido en cada cambio de panel
    return pns


def vista_tablero(pt, t, cam):
    """Lo que ve la camara del tablero en el instante t (BW x BH). cam: [cx, cy, z] suavizado, se actualiza aqui.
    Se ve el tablero entero; cuando entra una pieza, la camara se acerca un poco hacia ella y vuelve despacio."""
    base = pt["base"]
    visibles = [(pc, x, y, ta) for pc, x, y, ta in pt["piezas"] if ta <= t]
    cx, cy, z = base.width / 2, base.height / 2, 1.0
    if visibles:
        pc, x, y, ta = visibles[-1]
        if isinstance(pc, tuple):
            (x0, y0), (x1, y1) = pc[1], pc[2]
            px, py = (x0 + x1) / 2, (y0 + y1) / 2
        else:
            px, py = x + pc.width / 2, y + pc.height / 2
        foco = not isinstance(pc, tuple) and pc.info.get("foco")
        if foco and pt["t1"] - t > 1.3:              # viñeta: la camara se acerca y se queda en ella, con zoom lento
            zf = min(2.2, max(1.0, min(base.width / (pc.width * 1.25), base.height / (pc.height * 1.25))))
            z = zf * (1 + 0.025 * min(t - ta, 4.0))
            cx, cy = px, py
        elif not foco:                                # el resto de piezas: golpe de camara breve, como hasta ahora
            golpe = math.exp(-(t - ta) / 0.7)
            z = 1.0 + 0.12 * golpe
            cx, cy = cx + (px - cx) * golpe, cy + (py - cy) * golpe
        # (viñeta en el ultimo segundo y pico de la escena: la camara se aleja y se ven todas juntas)
    if not cam or t - pt["t0"] < 1 / FPS:
        cam[:] = [cx, cy, z]
    else:
        a = 1 - math.exp(-(1 / FPS) / 0.22)
        cam[:] = [c0 + (c1 - c0) * a for c0, c1 in zip(cam, (cx, cy, z))]
    ccx, ccy, cz = cam
    # capa fija: el tablero con las piezas que ya terminaron de entrar (se amplia a medida que llegan; no se recompone)
    quietas = 0
    while quietas < len(visibles) and t - visibles[quietas][3] >= 0.3:
        quietas += 1
    fijo = pt.get("_fijo")
    if fijo is None or fijo[0] > quietas:
        fijo = (0, base.copy())
    if fijo[0] < quietas:
        img = fijo[1] if fijo[0] else fijo[1].copy()
        dfi = ImageDraw.Draw(img)
        for pc, x, y, ta in visibles[fijo[0]:quietas]:
            if isinstance(pc, tuple):
                (x0, y0), (x1, y1) = pc[1], pc[2]
                dfi.line([(x0, y0), (x1, y1)], fill=AMARILLO + (255,), width=12)
                ang = math.atan2(y1 - y0, x1 - x0)
                dfi.polygon([(x1, y1), (x1 - 40 * math.cos(ang - 0.5), y1 - 40 * math.sin(ang - 0.5)),
                             (x1 - 40 * math.cos(ang + 0.5), y1 - 40 * math.sin(ang + 0.5))], fill=AMARILLO + (255,))
            else:
                img.alpha_composite(pc, (int(x), int(y)))
        fijo = (quietas, img)
    pt["_fijo"] = fijo
    sin_zoom = abs(cz - 1) < 1e-3 and base.size == (BW, BH)
    if sin_zoom:                                       # el caso mas comun: ni recorte ni reescalado
        bx = by = 0
        vw, vh = BW, BH
        vista = fijo[1].copy()
    else:
        vw, vh = base.width / cz, base.height / cz
        bx = min(max(ccx - vw / 2, 0), base.width - vw)
        by = min(max(ccy - vh / 2, 0), base.height - vh)
        vista = fijo[1].crop((int(bx), int(by), int(bx + vw) + 1, int(by + vh) + 1))
    dv = ImageDraw.Draw(vista)
    for pc, x, y, ta in visibles[quietas:]:
        e = (t - ta) / 0.3
        if isinstance(pc, tuple):                      # flecha que se dibuja
            (x0, y0), (x1, y1) = pc[1], pc[2]
            q = min(1.0, e)
            xe, ye = x0 + (x1 - x0) * q, y0 + (y1 - y0) * q
            dv.line([(x0 - bx, y0 - by), (xe - bx, ye - by)], fill=AMARILLO + (255,), width=12)
            if q >= 1:
                ang = math.atan2(y1 - y0, x1 - x0)
                tri = [(x1, y1), (x1 - 40 * math.cos(ang - 0.5), y1 - 40 * math.sin(ang - 0.5)),
                       (x1 - 40 * math.cos(ang + 0.5), y1 - 40 * math.sin(ang + 0.5))]
                dv.polygon([(a_ - bx, b_ - by) for a_, b_ in tri], fill=AMARILLO + (255,))
            continue
        if x - bx > vw or y - by > vh or x + pc.width - bx < 0 or y + pc.height - by < 0:
            continue
        if e < 1:
            s = 0.6 + 0.4 * E.rebote(e)
            im = pc.resize((max(1, int(pc.width * s)), max(1, int(pc.height * s))), Image.BILINEAR)
            pega(vista, im, x - bx + (pc.width - im.width) / 2, y - by + (pc.height - im.height) / 2, min(1.0, e * 3))
        else:
            vista.alpha_composite(pc, (int(x - bx), int(y - by)))
    if not sin_zoom:
        vista = G2.escala(vista, (BW, BH))
    # barrido con desenfoque al cambiar de escena dentro del bloque
    for borde, sentido in ((pt["t0"], 1), (pt["t1"], -1)):
        dt = (t - borde) if sentido == 1 else (borde - t)
        if 0 <= dt < 0.22 and ((sentido == -1 and not pt.get("sin_salida")) or (sentido == 1 and pt["k"] > 0)):
            off = int((1 - dt / 0.22) ** 2 * 900) * sentido
            capas = [vista.transform(vista.size, Image.AFFINE, (1, 0, -(off + j * 50 * sentido), 0, 1, 0),
                                     fillcolor=(22, 36, 64, 255)) for j in range(5)]   # lo que entra: color del tablero
            acc = np.mean([np.asarray(cc, dtype=np.float32) for cc in capas], axis=0)
            vista = Image.fromarray(acc.astype(np.uint8), "RGBA")
    return vista


# ------------------------------------------------------------------ montaje

def trabajadores(nf):
    """Cuantos procesos dibujan a la vez: uno por hilo del procesador (variable RENDER_PROCESOS para cambiarlo).
    En Windows no hay fork, asi que alli se dibuja en un solo proceso."""
    if "fork" not in mp.get_all_start_methods():
        return 1
    n = int(os.environ.get("RENDER_PROCESOS", os.cpu_count() or 1))
    return max(1, min(n, nf // (FPS * 10)))           # trozos de al menos 10 s

def main(dia_txt, solo_fotogramas=False, hasta=None, desde=0.0):
    dia = Path(__file__).parent / "dia" / dia_txt
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    secs = G["secciones"]
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    nombres = {n for s in secs for p in s["pasos"] if p.get("ve") for n in C.personas_de(p["ve"])}
    nombres |= {it["persona"] for s in secs[:1] for p in s["pasos"] if p.get("ve", {}).get("tipo") == "sumario"
                for it in p["ve"]["items"] if it.get("persona")}
    fotos = C.fotos_personas(nombres, cred, dia / "imagenes")
    # variedad (decision del usuario del 3-nov-2026): todas las fotos marcadas con la misma persona se turnan en el video
    VARIANTES.clear()
    USOS.clear()
    for nombre, principal in fotos.items():
        extra = sorted(dia / "imagenes" / f for f, cc in cred.items()
                       if cc.get("persona") == nombre and (dia / "imagenes" / f).exists() and f != principal.name)
        VARIANTES[nombre] = [principal] + extra
    origen = (json.loads((dia / "vinetas" / "origen.json").read_text(encoding="utf-8"))
              if (dia / "vinetas" / "origen.json").exists() else {})
    tmp = dia / "tmp_largo"
    tmp.mkdir(exist_ok=True)
    t = INTRO
    golpe0 = desp = None
    plan, wavs, subs, caps, calma, usadas = [], [], [], [], [], {}
    for i, s in enumerate(secs):
        texto = " ".join(p["di"] for p in s["pasos"])
        pal, dur = voz.locuta(s["pasos"], s["tono"], tmp / f"s{i}.wav")      # voz elegida: plana, con pausas naturales
        wavs.append(tmp / f"s{i}.wav")
        T = E.Tiempos(texto, pal, t)
        print(f"  bloque {i}: {dur:5.1f} s, {T.casadas}/{len(T.toks)} palabras con tiempo", flush=True)
        partes, c = [], 0
        vins_blq = sorted((dia / "vinetas").glob(f"s{i}_*.jpg"))
        fot_blq = [dia / "imagenes" / p["ve"]["foto"] for p in s["pasos"] if (p.get("ve") or {}).get("foto")
                   and (dia / "imagenes" / p["ve"]["foto"]).exists()]
        img_blq = (fot_blq or vins_blq or [None])[0]       # imagen del bloque para el fondo vivo (6-nov)
        for jp, p in enumerate(s["pasos"]):
            ve = p.get("ve")
            if ve:
                ve = dict(ve)                          # viñetas ya aceptadas de este paso (dia/<fecha>/vinetas/)
                ve["_vin"] = {k: f for k in range(len(ve.get("items", [])) or 1)
                              if (f := dia / "vinetas" / f"s{i}_{jp}_{k}.jpg").exists()}
                ve["_vin_txt"] = {k: IAV.credito_vineta(origen, f"s{i}_{jp}_{k}") for k in ve["_vin"]}   # «Ilustración IA»
                ve["_sobrio"] = s["tono"] == "sobrio"
                t0 = T.en(c) if partes else t
                foto, fn = None, ve.get("foto")
                if fn and ve["tipo"] in E.CON_FOTO:
                    if fn in cred and (dia / "imagenes" / fn).exists():
                        foto = (dia / "imagenes" / fn, cred[fn])
                    else:
                        print(f"  AVISO: la foto {fn} no esta en imagenes/ o no tiene credito; la escena va sin foto")
                pz = sorted(piezas_h(ve, T, c, t0, fotos, cred, foto, usadas), key=lambda z: z[3])
                parte = {"k": len(partes), "t0": t0, "tipo": ve["tipo"], "piezas": pz,
                         "fondo": fondo_de(ve, foto, ve["_vin"], fotos, img_blq), "sobrio_f": ve["_sobrio"],
                         "fuente": ve.get("fuente") or " · ".join(s.get("fuentes", [])[:3])}
                if ve["tipo"] in ("claves", "cronologia") and (ve["_vin"] or any(it.get("persona_vineta") in fotos
                                                                                  for it in ve.get("items", []))):
                    parte["comic"] = paneles_comic(ve, T, c, t0, fotos)      # opcion A (4-nov-2026)
                    parte["sobrio"] = ve["_sobrio"]
                    for pn_ in parte["comic"]:
                        pn_.setdefault("fondo", parte["fondo"])
                elif ve["tipo"] == "breve":                     # breves, tambien en comic a pantalla completa (4-nov)
                    sub = ve.get("sub", "")                       # la fuente ya va en el recuadro FUENTES
                    if 0 in ve["_vin"]:
                        pn = {"clase": "vineta", "ruta": ve["_vin"][0], "narr": ve["titular"], "sub": sub,
                              "lugar": ve.get("lugar", ""), "credito": ve["_vin_txt"].get(0, "Ilustración IA")}
                    else:
                        pn = {"clase": "texto", "narr": "", "cita": ve["titular"], "sub": sub, "lugar": ve.get("lugar", ""),
                              "fondo": parte["fondo"]}
                    pn["t"] = t0
                    parte["comic"] = [pn]
                    parte["sobrio"] = ve["_sobrio"]
                partes.append(parte)
            c += len(p["di"]) + 1
        if not partes:
            raise ValueError(f"el bloque {i} no tiene ninguna escena")
        for pt in partes:                              # despedida a pantalla completa (cierre.py), sincronizada con la voz
            if pt["tipo"] == "despedida":
                ev = {k: T.cuando(w, 0, None) for k, w in (("suscribete", "suscríbete"), ("campanita", "campanita"),
                                                           ("gracias", "Gracias por vernos"))}
                desp = {"t0": pt["t0"], "ev": {k: (v - pt["t0"] if v is not None else None) for k, v in ev.items()}}
        for a, b in zip(partes, partes[1:]):
            a["t1"] = b["t0"]
            a["sin_salida"] = b["tipo"] == "despedida"     # el cierre ya trae su barrida: sin dos transiciones seguidas
        partes[-1]["t1"] = t + dur
        for pt in partes:
            pt["piezas"], pt["base"] = encaja(pt["piezas"], pt.get("fondo"), pt.get("sobrio_f", False))
        tit = None
        vs = next((p["ve"] for p in s["pasos"] if p.get("ve", {}).get("tipo") == "sumario"), None) if i == 0 else None
        if vs:                                         # sumario a pantalla completa: una tarjeta por titular
            fotos_tit = {n: (VARIANTES.get(n) or [f])[-1] for n, f in fotos.items()}   # el sumario, con otra foto si la hay
            tit = TIT.prepara(vs, secs, dia / "imagenes", fotos_tit, cred, usadas)
            for k, tj in enumerate(tit):
                tj["t0"] = t if k == 0 else T.cuando(tj["cuando"], 0, t + 2.0 * k) if tj["cuando"] else t + 2.0 * k
        else:
            caps += C.grupos_palabras(T, set())
        subs += T.subtitulos()
        plan.append({"t0": t, "dur": dur, "sec": s, "partes": partes, "pops": [] if tit else sorted(T.eventos), "tit": tit,
                     "blq": P.capa_bloque(s["titulo"], "HOY" if i == 0 else f"{i:02d} / {len(secs) - 1:02d}")})
        if s["tono"] == "sobrio":
            calma.append((t, t + dur))
        t += dur
        if tit:                                        # silencio para el golpe de marca, que entra al acabar la frase
            v0, _ = musica.lee_wav(tmp / f"s{i}.wav")
            sonido = np.nonzero(np.abs(v0[:, 0]) > 0.01)[0]
            cola = len(v0) / musica.SR - (sonido[-1] / musica.SR if len(sonido) else 0)
            adelanta = min(max(0.0, cola - 0.15), GOLPE - 0.5)
            golpe0 = t - adelanta
            musica.escribe_wav(tmp / "golpe.wav", np.zeros((int((GOLPE - adelanta) * musica.SR), 2)))
            wavs.append(tmp / "golpe.wav")
            t = golpe0 + GOLPE
    fin_voz = t
    lista = tmp / "voz.txt"
    lista.write_text("".join(f"file '{w.name}'\n" for w in wavs), encoding="utf-8")
    subprocess.run([V1.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(tmp / "voz.wav")], check=True)
    # ritmo: "pop" con cada pieza que entra y barrido con cada cambio de escena; en los bloques sobrios no hay "pop"
    pops = sorted(x for p in plan if p["sec"]["tono"] != "sobrio" for x in p["pops"])
    cambios = sorted(pt["t0"] for p in plan if not p["tit"] for pt in p["partes"][1:])
    tarj = [tj for p in plan if p["tit"] for tj in p["tit"]]
    efectos = [(x, "pop") for x in pops] + [(x, "whoosh") for x in cambios]
    efectos += [(tj["t0"] - 0.05, "whoosh") for tj in tarj] + [(tj["t0"] + TIT.ENTRA, "pop") for tj in tarj if not tj["sobrio"]]
    cortes = [p["t0"] for p in plan if not p["tit"]] + [fin_voz]
    sin_fondo = []
    if desp:
        efectos.append((desp["t0"], "whoosh"))
        es, ec = desp["ev"]["suscribete"], desp["ev"]["campanita"]
        if es is not None:
            efectos.append((desp["t0"] + es, "clic"))
        if ec is not None:
            efectos += [(desp["t0"] + ec, "clic"), (desp["t0"] + ec + 0.02, "campana")]
        cortes = [c for c in cortes if abs(c - fin_voz) > 0.01]
    if golpe0 is not None:                             # el golpe de marca suena solo: sintonia y sus dos barridos
        efectos += [(golpe0, "whoosh"), (golpe0 + 2.05, "whoosh")]
        cortes = [c for c in cortes if abs(c - (golpe0 + GOLPE)) > 0.01]
        sin_fondo = [(golpe0 - 0.1, golpe0 + GOLPE - 0.1)]
    total = musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", INTRO, G2.OUTRO, cortes, calma=calma, efectos=efectos,
                          sintonia_en=golpe0 if golpe0 is not None else 0.0, sintonia_dur=GOLPE + 0.5 if golpe0 else None,
                          sin_fondo=sin_fondo)
    v, sr = musica.lee_wav(tmp / "voz.wav")
    hop = sr // FPS
    rms = np.sqrt(np.mean(v[: len(v) // hop * hop, 0].reshape(-1, hop) ** 2, axis=1))
    boca = np.clip(rms / np.percentile(rms[rms > 0.01], 90), 0, 1) ** 0.8
    gesto = np.convolve(boca, np.ones(25) / 25, mode="same")

    cab = G2.capa_cabecera(G["fecha"])
    ini_caps = [x[0] for x in caps]
    for j, p in enumerate(plan[:-1]):
        p["teaser"] = E.capa_teaser(plan[j + 1]["sec"]["titulo"])
    cam = []

    def presente(t, i):
        """1 si Urni esta en pantalla (bloques normales), con entrada y salida suaves."""
        if not CON_URNI:
            return 0.0
        dentro = plan[i]["sec"]["tono"] != "sobrio"
        antes = plan[i - 1]["sec"]["tono"] != "sobrio" and not plan[i - 1]["tit"] if i > 0 else False
        x = suave((t - plan[i]["t0"] - 0.3) / 0.6)
        return (antes + (dentro - antes) * x) if i > 0 else float(dentro) * suave((t - plan[0]["t0"]) / 0.6)

    gm, sin_marca, cie = [], [], []
    cab_sin = G2.capa_cabecera(G["fecha"], con_marca=False)

    def barra(fr, t):
        ImageDraw.Draw(fr).rectangle([0, AL - 8, int(AN * max(0.0, t - INTRO) / (fin_voz - INTRO)), AL], fill=AMARILLO + (255,))
        return fr

    def cuadro(t):
        if plan[0]["tit"] and t < (golpe0 if golpe0 is not None else plan[0]["t0"] + plan[0]["dur"]):   # sumario
            tj = [x for x in plan[0]["tit"] if x["t0"] <= t + 1e-9] or plan[0]["tit"][:1]
            return barra(TIT.cuadro(tj[-1], max(0.0, t - tj[-1]["t0"]), t), t)
        if desp and t >= desp["t0"]:                  # despedida y pantalla final
            if not cie:
                cie.append(CI.Cierre(G["fecha"]))
                cie.append(cuadro(desp["t0"] - 1e-3).convert("RGBA"))
            urni = None
            if CON_URNI and t < fin_voz + 0.9:
                k = min(int((t - INTRO) * FPS), len(boca) - 1)
                m = P.mascota(t, float(boca[k]) if t < fin_voz else 0.0, (t % 3.7) < 0.12, 1.0)
                urni = m.resize((int(m.width * 1.05), int(m.height * 1.05)), Image.BILINEAR)
            fr = cie[0].cuadro(t - desp["t0"], cie[1], desp["ev"], urni, fin_voz - desp["t0"])
            if t < fin_voz:
                fr = barra(fr, t)
            fundido = (t - (total - 0.6)) / 0.6
            if fundido > 0:                            # fundido a negro en el ultimo medio segundo
                fr.alpha_composite(Image.new("RGBA", (AN, AL), (0, 0, 0, int(255 * min(1.0, fundido)))))
            return fr
        if golpe0 is not None and golpe0 <= t < golpe0 + GOLPE:
            if not gm:                                 # se preparan una vez: la pieza, el ultimo titular y el tablero
                ult = plan[0]["tit"][-1]
                gm.append(marca.Golpe(G["fecha"]))
                gm.append(TIT.cuadro(ult, golpe0 - ult["t0"], golpe0))
                sin_marca.append(1)                    # el tablero sin logo, nombre ni titulo: los trae el vuelo
                gm.append(cuadro(golpe0 + GOLPE + 1e-4).convert("RGBA"))
                sin_marca.clear()
            return barra(gm[0].cuadro(t - golpe0, gm[1], gm[2]), t)
        if t < INTRO or t >= fin_voz:
            fr = G2.cuadro_intro(t, G["fecha"]) if t < INTRO else G2.cuadro_cierre(t - fin_voz, G["fecha"])
            q = (t - fin_voz) / G2.CORTINILLA
            if 0 <= q < 1:
                d = ImageDraw.Draw(fr)
                x0 = int(AN * (2.2 * q - 1.2))
                d.rectangle([x0, 0, x0 + AN, AL], fill=ROJO + (255,))
                d.rectangle([x0 + AN, 0, x0 + AN + 40, AL], fill=AMARILLO + (255,))
            return fr
        i = max(j for j, p in enumerate(plan) if p["t0"] <= t + 1e-9)
        p = plan[i]
        pt = p["partes"][max(j for j, x in enumerate(p["partes"]) if x["t0"] <= t + 1e-9 or j == 0)]
        fr = G2.fondo_marca(t)
        fr.paste((vista_comic(pt, t) if pt.get("comic") else vista_tablero(pt, t, cam)).convert("RGBA"), (BX, BY))  # el tablero es opaco: pegar es mucho mas rapido que componer
        d = ImageDraw.Draw(fr)
        d.rectangle([BX, BY - 4, BX + BW, BY], fill=AMARILLO + (255,))
        d.rectangle([BX, BY + BH, BX + BW, BY + BH + 4], fill=AMARILLO + (255,))
        fr.alpha_composite(cab_sin if sin_marca else cab)
        tras_golpe = golpe0 is not None and abs(p["t0"] - golpe0 - GOLPE) < 0.01
        if not sin_marca:
            pega(fr, p["blq"], 100 - 30 * (1 - suave((t - p["t0"]) / 0.35)) * tras_golpe,
                 108, suave((t - p["t0"]) / 0.35) if tras_golpe else 1.0)
        if 0 < i < len(plan) - 1:                      # "A continuacion": anuncia el bloque siguiente (retencion)
            falta = plan[i + 1]["t0"] - t
            if falta < 4.5:
                tz = p["teaser"]
                pega(fr, tz, BX + BW - 16 - tz.width, BY + BH + 12, min(1.0, (4.5 - falta) * 3))
        if pt["fuente"]:                               # 6-nov: una línea discreta bajo el escenario, a la izquierda
            fr.alpha_composite(linea_fuente(pt["fuente"]), (BX, BY + BH + 10))
        pm = presente(t, i)
        if pm > 0.001:                                 # Urni narra abajo a la izquierda y da un saltito con cada pieza
            k = min(int((t - INTRO) * FPS), len(boca) - 1)
            ge = 1.0 if pt["tipo"] == "despedida" else float(gesto[k])
            par = (t % 3.7) < 0.12 or (t % 5.3) < 0.1
            kp = bisect.bisect_right(pops, t)
            salto = max([math.sin(math.pi * (t - x) / 0.34) for x in pops[max(0, kp - 4):kp] if t - x < 0.34] + [0])
            m = P.mascota(t, float(boca[k]), par, ge)
            m = m.resize((int(m.width * 0.7), int(m.height * 0.7)), Image.BILINEAR)
            pega(fr, m, 50, AL - m.height - 24 - 30 * salto + 300 * (1 - pm), pm)
        j = bisect.bisect_right(ini_caps, t) - 1       # subtitulo de 1-2 palabras con la clave en amarillo
        if j >= 0 and t < caps[j][1]:
            a, _, ws, clave, _ = caps[j]
            cp = C.capa_cap(ws, clave, 0, 0.72, BW - 60)
            s = 0.8 + 0.2 * E.rebote((t - a) / 0.12)
            cp = cp.resize((int(cp.width * s), int(cp.height * s)), Image.BILINEAR)
            pega(fr, cp, BX + BW / 2 - cp.width / 2, 985 - cp.height / 2)
        d = ImageDraw.Draw(fr)
        d.rectangle([0, AL - 8, int(AN * (t - INTRO) / (fin_voz - INTRO)), AL], fill=AMARILLO + (255,))
        tl = t - p["t0"]
        if tl < G2.CORTINILLA and not tras_golpe:
            # cortinilla roja y amarilla al cambiar de bloque (tras el golpe de marca no: ya trae su transicion)
            x0 = int(AN * (2.2 * tl / G2.CORTINILLA - 1.2))
            d.rectangle([x0, 0, x0 + AN, AL], fill=ROJO + (255,))
            d.rectangle([x0 + AN, 0, x0 + AN + 40, AL], fill=AMARILLO + (255,))
        return fr

    escenas = [(i, pt["tipo"], pt["t0"], pt["t1"]) for i, p in enumerate(plan) if not p["tit"] for pt in p["partes"]]
    for i, p in enumerate(plan):                       # el control de calidad mira cada tarjeta del sumario y el golpe
        if p["tit"]:
            fins = [x["t0"] for x in p["tit"][1:]] + [golpe0 if golpe0 is not None else p["t0"] + p["dur"]]
            escenas[0:0] = [(i, f"titular{k + 1}", x["t0"], b) for k, (x, b) in enumerate(zip(p["tit"], fins))]
    if golpe0 is not None:
        escenas.insert(len(plan[0]["tit"]), (0, "golpe_marca", golpe0, golpe0 + GOLPE))
    if solo_fotogramas:
        sal = tmp / "fotogramas"
        sal.mkdir(exist_ok=True)
        for k, (i, tipo, a, b) in enumerate(escenas):
            cam.clear()
            cuadro(b - 0.3).convert("RGB").save(sal / f"{k:02d}_b{i}_{tipo}.png")
        print(f"FOTOGRAMAS {len(escenas)} -> {sal}")
        return
    out = dia / ("tramo_prueba.mp4" if desde else "inicio_prueba.mp4" if hasta else "episodio.mp4")
    f0 = int(desde * FPS)                              # --desde: solo un tramo, para revisar una escena
    nf = int(math.ceil((min(total, hasta) if hasta else total) * FPS)) - f0
    t_ini = time.time()
    n = trabajadores(nf)
    bordes = [f0 + nf * k // n for k in range(n + 1)]

    def dibuja_trozo(k):
        """Dibuja los fotogramas [bordes[k], bordes[k+1]) en tmp/trozoK.mp4 (solo imagen)."""
        a, b = bordes[k], bordes[k + 1]
        cam.clear()
        for fi in range(max(0, a - CALIENTA), a):      # la camara del tablero se asienta antes de grabar
            cuadro(fi / FPS)
        ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{AN}x{AL}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                               "-threads", "2", "-pix_fmt", "yuv420p", str(tmp / f"trozo{k}.mp4")], stdin=subprocess.PIPE)
        for fi in range(a, b):
            fr = cuadro(fi / FPS)                      # RGBA tal cual: ffmpeg convierte a yuv420p sin paso intermedio
            ff.stdin.write((fr if fr.mode == "RGBA" else fr.convert("RGBA")).tobytes())
            if k == 0 and (fi - a) % (FPS * 15) == 0:
                print(f"  fotograma {(fi - a) * n}/{nf} aprox. ({n} a la vez)", flush=True)
        ff.stdin.close()
        return ff.wait()

    if n > 1:                                          # en paralelo: un proceso por hilo del procesador (Linux)
        ctx = mp.get_context("fork")
        # OpenCV (caras con YuNet, desde el 4-nov) deja su grupo de hilos en marcha; si se hace fork con él vivo,
        # los hijos se quedan bloqueados para siempre (colgó dos montajes el 6-nov). Un solo hilo ANTES del fork.
        try:
            import cv2 as _cv2_padre
            _cv2_padre.setNumThreads(1)
        except ImportError:
            pass

        def hijo(k):
            try:
                if G2._cv2 is not None:
                    G2._cv2.setNumThreads(1)           # ya hay un proceso por hilo
                os._exit(dibuja_trozo(k))
            except Exception:
                traceback.print_exc()
                os._exit(1)
        procs = [ctx.Process(target=hijo, args=(k,)) for k in range(n)]
        for pr in procs:
            pr.start()
        for pr in procs:
            pr.join()
        if any(pr.exitcode for pr in procs):
            raise RuntimeError(f"fallo un trozo del render: {[pr.exitcode for pr in procs]}")
    elif dibuja_trozo(0):
        raise RuntimeError("fallo el render")
    lista_v = tmp / "trozos.txt"
    lista_v.write_text("".join(f"file 'trozo{k}.mp4'\n" for k in range(n)), encoding="utf-8")
    subprocess.run([V1.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista_v),
                    "-ss", f"{desde:.3f}", "-i", str(tmp / "audio.wav"), "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    for k in range(n):
        (tmp / f"trozo{k}.mp4").unlink(missing_ok=True)
    print(f"  render: {(time.time() - t_ini) / 60:.1f} min con {n} proceso(s) para {nf / FPS / 60:.1f} min de video", flush=True)
    if hasta or desde:
        print(f"PRUEBA de {desde:.0f} a {hasta or total:.0f} s -> {out}")
        return
    E.escribe_textos(dia, G, plan, subs, escenas, total, fin_voz, usadas)
    print(f"EPISODIO {total / 60:.1f} min -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dia")
    ap.add_argument("--fotogramas", action="store_true")
    ap.add_argument("--hasta", type=float, help="solo los primeros N s, en inicio_prueba.mp4 (para revisar el arranque)")
    ap.add_argument("--desde", type=float, default=0.0, help="con --hasta: solo ese tramo, en tramo_prueba.mp4")
    a = ap.parse_args()
    main(a.dia, a.fotogramas, a.hasta, a.desde)
