"""CORTO VERTICAL (9:16) estilo explicador de TikTok: un tablero donde se van pegando polaroids con fotos reales, notas,
sellos, pegatinas y flechas; la camara viaja de pieza en pieza cuando la voz las nombra, barridos con desenfoque
entre partes, subtitulos de 1-2 palabras con la palabra clave destacada y Urni narrando abajo.
Toma UNA seccion de episodio.json (sus pasos y escenas) y las fotos de imagenes/ + creditos.json.
Uso: python corto.py AAAA-MM-DD <n_seccion> [--gancho "frase inicial"] [--cierre "pregunta final"]"""
from __future__ import annotations

import argparse
import asyncio
import bisect
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import episodio as E
import genera_video as V1
import genera_video2 as G2
import musica
import voz
import prototipo_animado as P
from genera_video2 import AMARILLO, BLANCO, ROJO, fuente, pega

AN, AL, FPS = 1080, 1920, 30
VY0, VY1 = 210, 1390                  # zona del tablero en pantalla
NAVY = (12, 20, 38)
PAPEL = (246, 243, 234)
TINTA = (25, 30, 45)
F = "C:/Windows/Fonts/"


def estrecha(tam, peso="Bold"):
    f = ImageFont.truetype(F + "bahnschrift.ttf", tam)
    try:
        f.set_variation_by_name(f"{peso} Condensed")
    except Exception:
        pass
    return f


def mano(tam):
    return ImageFont.truetype(F + "segoeprb.ttf", tam)


def lineas(txt, fnt, ancho):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    return G2.texto_lineas(d, txt, fnt, ancho)


def celo(im, x, ang=0):
    """Tira de celo semitransparente arriba de una pieza."""
    t = Image.new("RGBA", (130, 40), (235, 225, 180, 170))
    t = t.rotate(ang, expand=True)
    im.alpha_composite(t, (int(x), 0))


# ------------------------------------------------------------------ piezas del tablero (RGBA, con margen arriba para el celo)

def polaroid(foto, nombre, cargo, partido, credito=None, ancho=420):
    alto_f = int(ancho * 1.0)
    im = Image.new("RGBA", (ancho + 30, alto_f + 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([15, 20, ancho + 15, alto_f + 160], fill=(0, 0, 0, 70))          # sombra
    d.rectangle([8, 12, ancho + 8, alto_f + 152], fill=BLANCO + (255,))
    if foto is not None:
        f = Image.open(foto).convert("RGB")
        r = max((ancho - 40) / f.width, (alto_f - 40) / f.height)
        f = f.resize((math.ceil(f.width * r), math.ceil(f.height * r)), Image.LANCZOS)
        x0, y0 = (f.width - (ancho - 40)) // 2, int((f.height - (alto_f - 40)) * 0.25)
        im.paste(f.crop((x0, y0, x0 + ancho - 40, y0 + alto_f - 40)), (28, 32))
    else:
        col = P.PARTIDO.get(partido, (90, 100, 120))
        d.rectangle([28, 32, ancho - 12, alto_f - 8], fill=col + (255,))
        d.text((ancho / 2 + 8, alto_f / 2 + 12), P.iniciales(nombre), font=fuente("seguibl.ttf", 150), fill=BLANCO, anchor="mm")
    d.text((ancho / 2 + 8, alto_f + 22), nombre.upper(), font=estrecha(46), fill=TINTA, anchor="mt")
    d.text((ancho / 2 + 8, alto_f + 76), cargo, font=fuente("segoeui.ttf", 24), fill=(90, 95, 110), anchor="mt")
    if credito:
        d.text((ancho / 2 + 8, alto_f + 118), f"Foto: {credito['autor'][:34]} · {credito['licencia']}",
               font=fuente("segoeui.ttf", 17), fill=(130, 135, 145), anchor="mt")
    celo(im, ancho / 2 - 50, 4)
    return im


def nota(texto, ancho=520, tam=40, fuente_txt=None, color=PAPEL):
    fnt = mano(tam)
    ls = lineas(texto, fnt, ancho - 70)
    alto = 70 + int(len(ls) * tam * 1.45) + (44 if fuente_txt else 10)
    im = Image.new("RGBA", (ancho + 20, alto + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([14, 22, ancho + 14, alto + 22], fill=(0, 0, 0, 70))
    d.rectangle([6, 14, ancho + 6, alto + 14], fill=color + (255,))
    for j, l in enumerate(ls):
        d.text((40, 50 + j * tam * 1.45), l, font=fnt, fill=TINTA)
    if fuente_txt:
        d.text((40, alto - 24), fuente_txt, font=fuente("segoeui.ttf", 20), fill=(110, 115, 125))
    celo(im, ancho / 2 - 60, -3)
    return im


def pegatina(texto, fondo=AMARILLO, tinta=(15, 15, 15), tam=40):
    fnt = estrecha(tam)
    w = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(texto, font=fnt)) + 44
    im = Image.new("RGBA", (w + 8, tam + 38), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([6, 6, w + 6, tam + 34], fill=(0, 0, 0, 110))
    d.rectangle([0, 0, w, tam + 28], fill=fondo + (255,))
    d.text((w / 2, (tam + 28) / 2), texto, font=fnt, fill=tinta, anchor="mm")
    return im


def sello(texto, color=ROJO, tam=66):
    fnt = estrecha(tam)
    w = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(texto, font=fnt)) + 60
    im = Image.new("RGBA", (w, tam + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([4, 4, w - 4, tam + 46], radius=12, outline=color + (235,), width=8)
    d.text((w / 2, (tam + 50) / 2), texto, font=fnt, fill=color + (235,), anchor="mm")
    return im.rotate(-9, expand=True, resample=Image.BICUBIC)


def mapa(puntos, ruta, ancho=760):
    k = ancho / 10.5
    pr = lambda lo, la: (30 + (lo + 9.6) * math.cos(math.radians(40)) * k, 30 + (44 - la) * k)
    alto = int(8.4 * k) + 60
    im = Image.new("RGBA", (ancho + 60, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, ancho + 60, alto], radius=26, fill=PAPEL + (255,))
    pts = [pr(lo, la) for lo, la in P.ESPANA]
    d.polygon(pts, fill=(214, 220, 232), outline=(120, 135, 160))
    d.line(pts + [pts[0]], fill=(120, 135, 160), width=4)
    xy = {p["nombre"]: pr(p["lon"], p["lat"]) for p in puntos}
    if len(ruta) > 1:
        d.line([xy[n] for n in ruta], fill=ROJO + (255,), width=10, joint="curve")
    for p in puntos:
        x, y = xy[p["nombre"]]
        d.ellipse([x - 14, y - 14, x + 14, y + 14], fill=ROJO + (255,) if p.get("aviso") else TINTA + (255,), outline=BLANCO, width=4)
        tw = d.textlength(p["nombre"], font=estrecha(38))
        tx = x - tw - 22 if p.get("izq") else x + 22
        d.text((tx, y - 22), p["nombre"], font=estrecha(38), fill=TINTA)
    celo(im, ancho / 2, 2)
    return im


def flecha_img(p0, p1):
    return ("flecha", p0, p1)


# ------------------------------------------------------------------ de la escena del guion a piezas en el tablero

def piezas_de(ve, T, c0, t0, fotos, cred):
    """Lista de (pieza, x, y, t_aparece) sobre un tablero de 1080 de ancho. Las fotos se buscan por nombre de persona."""
    def foto_de(nombre):
        f = fotos.get(nombre)
        return (f, cred.get(f.name)) if f else (None, None)
    def cuando(tr, defecto):
        return T.cuando(tr, c0, defecto) if tr else defecto
    out, tipo = [], ve["tipo"]
    if tipo == "persona":
        p = ve["persona"]
        f, c = foto_de(p["nombre"])
        out.append((polaroid(f, p["nombre"], p["cargo"], p["partido"], c), 60, 40, t0 + 0.1))
        if ve.get("sello"):
            out.append((sello(ve["sello"]), 300, 330, cuando(ve.get("sello_cuando"), t0 + 1.2)))
        if p.get("cita"):
            out.append((nota(p["cita"], 470, 44, "Fuente: " + p.get("medio", "")), 530, 520, cuando(p.get("cita_cuando"), t0 + 2)))
        fl = ve.get("flujo")
        if fl:
            a = fl["a"]
            f2, c2 = foto_de(a["nombre"])
            ta = cuando(fl.get("a_cuando"), t0 + 4)
            out.append((("flecha", (390, 760), (560, 1020)), 0, 0, cuando(fl.get("cuando"), ta - 1)))
            out.append((nota(fl["etiqueta"], 360, 34, color=(255, 238, 150)), 20, 700, cuando(fl.get("cuando"), ta - 1)))
            out.append((polaroid(f2, a["nombre"], a["cargo"], a["partido"], c2, 380), 380, 1030, ta))
            if a.get("cita"):
                out.append((nota(a["cita"], 440, 36, "Fuente: " + a.get("medio", "")), 40, 1560, ta + 1.2))
    elif tipo == "mapa":
        out.append((mapa(ve["puntos"], ve.get("ruta", [])), 60, 60, t0 + 0.1))
        out.append((pegatina(ve["titular"].upper(), tam=44), 60, 800, t0 + 1.2))
        out.append((nota(ve.get("sub", ""), 620, 38, "Fuente: " + ve.get("fuente", "")), 300, 900, t0 + 2.0))
    elif tipo == "citas":
        out.append((pegatina(ve["titulo"], tam=48), 60, 30, t0 + 0.1))
        y = 160
        for k, it in enumerate(ve["items"]):
            f, c = foto_de(it["nombre"])
            ti = cuando(it.get("cuando"), t0 + 1 + 3 * k)
            x = 40 if k % 2 == 0 else 470
            out.append((polaroid(f, it["nombre"], it["cargo"], it["partido"], c, 300), x, y, ti))
            out.append((nota(it["cita"], 560, 36, "Fuente: " + it["medio"]), 470 if k % 2 == 0 else 20, y + 140, ti + 0.6))
            y += 620
    elif tipo == "posturas":
        out.append((pegatina(ve["titulo"], tam=46), 60, 30, t0 + 0.1))
        cc = ve["centro"]
        f, c = foto_de(cc["nombre"])
        out.append((polaroid(f, cc["nombre"], cc["cargo"], cc["partido"], c, 340), 40, 160, t0 + 0.3))
        y = 160
        for k, it in enumerate(ve["presionan"]):
            col = P.PARTIDO.get(it["partido"], (90, 100, 120))
            ti = cuando(it.get("cuando"), t0 + 1 + 0.5 * k)
            out.append((pegatina(it["nombre"].upper(), col, BLANCO, 46), 620, y, ti))
            out.append((("flecha", (610, y + 40), (400, 380 + 30 * k)), 0, 0, ti + 0.25))
            y += 130
        out.append((nota(ve["etiqueta"], 420, 38), 600, y + 10, cuando(ve.get("etiqueta_cuando"), t0 + 3)))
        ap = ve["aparte"]
        ta = cuando(ap.get("cuando"), t0 + 6)
        out.append((pegatina(ap["nombre"].upper(), (150, 150, 160), BLANCO, 46), 60, 820, ta))
        out.append((nota(ap["texto"], 600, 36, "Fuentes: " + ve.get("fuente", "")), 60, 940, ta + 0.5))
    elif tipo in ("claves", "cronologia"):
        out.append((pegatina(ve["titulo"], tam=46), 60, 30, t0 + 0.1))
        y = 160
        for k, it in enumerate(ve["items"]):
            txt = (it.get("hora", "") + " · " if it.get("hora") else "") + it["texto"]
            out.append((nota(txt, 760, 38, color=(255, 246, 196) if k % 2 else PAPEL), 60 + 80 * (k % 2), y,
                        cuando(it.get("cuando"), t0 + 1 + k)))
            y += 300
    elif tipo == "cifra":
        out.append((pegatina(ve["numero"], ROJO, BLANCO, 200), 80, 80, t0 + 0.1))
        out.append((pegatina(ve["etiqueta"].upper(), tam=50), 80, 430, t0 + 0.6))
        out.append((nota(ve.get("sub", ""), 640, 40, "Fuente: " + ve.get("fuente", "")), 240, 560, t0 + 1.2))
    return out


# ------------------------------------------------------------------ montaje

def fondo_vertical(t):
    im = Image.new("RGB", (AN, AL), NAVY)
    d = ImageDraw.Draw(im)
    x0 = int(-900 + 90 * t) % 1800 - 900
    for k in range(4):
        x = x0 + k * 600
        d.polygon([(x, AL), (x + 260, AL), (x + 260 + 900, 0), (x + 900, 0)], fill=(18, 30, 54))
    return im.convert("RGBA")


def tablero_base(alto):
    """Pizarra azul con cuadricula tenue: el 'tablero de redaccion' del canal."""
    im = Image.new("RGBA", (AN, alto), (22, 36, 64, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, AN, 60):
        d.line([(x, 0), (x, alto)], fill=(30, 46, 78, 255), width=2)
    for y in range(0, alto, 60):
        d.line([(0, y), (AN, y)], fill=(30, 46, 78, 255), width=2)
    return im


_cache_cap = {}


def capa_cap(palabras, clave, activa):
    k = (tuple(palabras), clave, activa)
    if k in _cache_cap:
        return _cache_cap[k]
    partes = []
    for j, w in enumerate(palabras):
        es_clave = j == clave
        fnt = fuente("seguibl.ttf", 112 if es_clave else 92)
        col = AMARILLO if es_clave else BLANCO
        d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        tw = int(d0.textlength(w, font=fnt)) + 30
        im = Image.new("RGBA", (tw, 170), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((15, 20), w, font=fnt, fill=col + (255,), stroke_width=9, stroke_fill=(0, 0, 0, 255))
        if es_clave:
            im = im.rotate(4, expand=True, resample=Image.BICUBIC)
        partes.append(im)
    w = sum(p.width for p in partes) + 10 * (len(partes) - 1)
    out = Image.new("RGBA", (max(w, 1), max(p.height for p in partes)), (0, 0, 0, 0))
    x = 0
    for p in partes:
        out.alpha_composite(p, (x, (out.height - p.height) // 2))
        x += p.width + 10
    if out.width > AN - 60:
        r = (AN - 60) / out.width
        out = out.resize((int(out.width * r), int(out.height * r)), Image.LANCZOS)
    _cache_cap[k] = out
    return out


def grupos_palabras(T, claves):
    """1-2 palabras por pantalla; corta en la puntuacion. La palabra clave es la mas larga o un nombre/cifra."""
    out, cur = [], []
    for k, (_, w) in enumerate(T.toks):
        cur.append(k)
        if len(cur) >= 2 or w[-1] in ".?!:;,":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    res = []
    for n, g in enumerate(out):
        ws = [T.toks[k][1] for k in g]
        lim = [w.strip(".,;:¿?¡!«»\"") for w in ws]
        cand = [j for j, w in enumerate(lim) if w.lower() in claves or (w[:1].isupper() and j > 0) or any(ch.isdigit() for ch in w)]
        clave = cand[0] if cand else (max(range(len(lim)), key=lambda j: len(lim[j])) if max(len(x) for x in lim) >= 7 else -1)
        a = T.tt[g[0]][0]
        sig = T.tt[out[n + 1][0]][0] if n + 1 < len(out) else T.tt[g[-1]][1] + 0.4
        res.append((a, sig, [w.strip("«»\"") for w in ws], clave, [T.tt[k][0] for k in g]))
    return res


def main(dia_txt, n_sec, gancho=None, cierre=None):
    dia = Path(__file__).parent / "dia" / dia_txt
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    sec = json.loads(json.dumps(G["secciones"][n_sec]))
    if gancho:
        sec["pasos"][0]["di"] = gancho + " " + sec["pasos"][0]["di"]
    if cierre:
        sec["pasos"][-1]["di"] = sec["pasos"][-1]["di"] + " " + cierre
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    fotos = {}                                         # nombre de persona -> foto, por el titulo del fichero de Commons
    for fich, c in cred.items():
        for nombre in ("Óscar Puente", "Pedro Sánchez", "Santiago Abascal", "Juan Bravo", "Salvador Illa", "Alberto Núñez Feijóo"):
            if nombre.split()[-1] in c["titulo"] or nombre in c["titulo"]:
                fotos.setdefault(nombre, dia / "imagenes" / fich)
    tmp = dia / "tmp_corto"
    tmp.mkdir(exist_ok=True)
    texto = " ".join(p["di"] for p in sec["pasos"])
    pal, dur = voz.locuta(sec["pasos"], sec["tono"], tmp / "voz.wav", cola=0.3)
    T = E.Tiempos(texto, pal, 0.0)
    print(f"  voz {dur:.1f} s, {T.casadas}/{len(T.toks)} palabras", flush=True)
    partes, c = [], 0
    claves = set()
    for p in sec["pasos"]:
        t0 = T.en(c) if partes else 0.0
        if p.get("ve"):
            pz = piezas_de(p["ve"], T, c, t0, fotos, cred)
            fte = p["ve"].get("fuente") or ", ".join(sec.get("fuentes", [])[:2])
            partes.append({"t0": t0, "piezas": pz, "fuente": fte,
                           "alto": max(y + (pc.height if not isinstance(pc, tuple) else 0) for pc, x, y, _ in pz) + 80})
        c += len(p["di"]) + 1
    for a, b in zip(partes, partes[1:]):
        a["t1"] = b["t0"]
    partes[-1]["t1"] = dur + 0.2
    for p in partes:
        p["base"] = tablero_base(max(p["alto"], VY1 - VY0))
    caps = grupos_palabras(T, claves)
    ini_caps = [x[0] for x in caps]
    total = dur + 1.6
    pops = sorted(T.eventos)
    cambios = [p["t0"] for p in partes[1:]]
    musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", 0.0, 1.6, [], efectos=[(x, "pop") for x in pops] + [(x, "whoosh") for x in cambios],
                  con_sintonia=False)
    v, sr = musica.lee_wav(tmp / "voz.wav")
    hop = sr // FPS
    rms = np.sqrt(np.mean(v[: len(v) // hop * hop, 0].reshape(-1, hop) ** 2, axis=1))
    boca = np.clip(rms / np.percentile(rms[rms > 0.01], 90), 0, 1) ** 0.8
    # cabecera fija
    cab = Image.new("RGBA", (AN, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(cab)
    d.rectangle([0, 0, AN, 10], fill=ROJO + (255,))
    d.rectangle([0, 10, AN, 16], fill=AMARILLO + (255,))
    cab.alpha_composite(G2.logo(70), (40, 50))
    d.text((126, 85), G2.MARCA, font=fuente("seguibl.ttf", 38), fill=AMARILLO + (255,), anchor="lm")
    y_, m_, dd_ = (int(x) for x in dia_txt.split("-")) if dia_txt[:2] == "20" else (2026, 10, 31)
    fe = f"{dd_} {['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'][m_ - 1]}"
    d.rounded_rectangle([AN - 190, 58, AN - 40, 112], radius=10, fill=ROJO + (255,))
    d.text((AN - 115, 85), fe, font=estrecha(40), fill=BLANCO, anchor="mm")
    pie_fuentes = {}
    tema = nota(sec["titulo"], 560, 40, color=(255, 238, 150)).rotate(3, expand=True, resample=Image.BICUBIC)

    out = dia / f"corto_s{n_sec}.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "21", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], stdin=subprocess.PIPE)
    cam = None                                         # (cx, cy, z) suavizado entre fotogramas
    VW, VH = AN, VY1 - VY0
    nf = int(math.ceil(total * FPS))
    for fi in range(nf):
        t = fi / FPS
        if t >= dur:                                   # cierre de marca breve
            fr = fondo_vertical(t)
            q = E.rebote((t - dur) / 0.4)
            lg = G2.logo(int(260 * max(q, 0.05)))
            pega(fr, lg, AN / 2 - lg.width / 2, 640)
            dd = ImageDraw.Draw(fr)
            dd.text((AN / 2, 1000), G2.MARCA, font=fuente("seguibl.ttf", 76), fill=BLANCO + (255,), anchor="mm")
            dd.text((AN / 2, 1090), "Cada tarde, la política del día", font=fuente("seguisb.ttf", 44), fill=AMARILLO + (255,), anchor="mm")
            ff.stdin.write(fr.convert("RGB").tobytes())
            continue
        k = max(j for j, p in enumerate(partes) if p["t0"] <= t + 1e-9)
        p = partes[k]
        visibles = [(pc, x, y, ta) for pc, x, y, ta in p["piezas"] if ta <= t]
        # la camara apunta a la ultima pieza que ha entrado (la que se esta contando)
        if visibles:
            pc, x, y, ta = max(visibles, key=lambda z: z[3])
            if isinstance(pc, tuple):
                (x0, y0), (x1, y1) = pc[1], pc[2]
                w, h = abs(x1 - x0) + 200, abs(y1 - y0) + 200
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            else:
                w, h = pc.width, pc.height
                cx, cy = x + w / 2, y + h / 2
            z = min(1.28, max(1.0, min(VW / (w * 1.18), VH / (h * 1.18))))      # la pieza entera y algo de aire
        else:
            cx, cy, z = AN / 2, VH / 2, 1.0
        objetivo = (cx, cy, z)
        if cam is None or t - p["t0"] < 1 / FPS:
            cam = objetivo
        else:
            a = 1 - math.exp(-(1 / FPS) / 0.22)
            cam = tuple(c0 + (c1 - c0) * a for c0, c1 in zip(cam, objetivo))
        ccx, ccy, cz = cam
        vw, vh = VW / cz, VH / cz
        bx = min(max(ccx - vw / 2, 0), AN - vw)
        by = min(max(ccy - vh / 2, 0), max(p["base"].height - vh, 0))
        vista = p["base"].crop((int(bx), int(by), int(bx + vw) + 1, int(by + vh) + 1)).convert("RGBA")
        dv = ImageDraw.Draw(vista)
        for pc, x, y, ta in sorted(p["piezas"], key=lambda z: z[3]):
            if ta > t:
                continue
            e = (t - ta) / 0.3
            if isinstance(pc, tuple):                  # flecha que se dibuja
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
        vista = vista.resize((VW, VH), Image.BILINEAR)
        # barrido con desenfoque al cambiar de parte
        for borde, sentido in ((p["t0"], 1), (p.get("t1", dur), -1)):
            dt = (t - borde) if sentido == 1 else (borde - t)
            if 0 <= dt < 0.22 and (sentido == -1 or k > 0):
                off = int((1 - dt / 0.22) ** 2 * 700) * sentido
                capas = [vista.transform(vista.size, Image.AFFINE, (1, 0, -(off + j * 40 * sentido), 0, 1, 0)) for j in range(5)]
                acc = np.mean([np.asarray(cc, dtype=np.float32) for cc in capas], axis=0)
                vista = Image.fromarray(acc.astype(np.uint8), "RGBA")
        fr = fondo_vertical(t)
        fr.alpha_composite(vista, (0, VY0))
        dd = ImageDraw.Draw(fr)
        dd.rectangle([0, VY0 - 4, AN, VY0], fill=AMARILLO + (255,))
        dd.rectangle([0, VY1, AN, VY1 + 4], fill=AMARILLO + (255,))
        fr.alpha_composite(cab)
        if p["fuente"] not in pie_fuentes:
            pie_fuentes[p["fuente"]] = pegatina("FUENTE: " + p["fuente"].upper()[:60], (10, 18, 34), BLANCO, 22)
        fr.alpha_composite(pie_fuentes[p["fuente"]], (40, 142))
        # Urni narra abajo a la izquierda
        kb = min(int(t * FPS), len(boca) - 1)
        salto = max([math.sin(math.pi * (t - x) / 0.34) for x in pops if 0 <= t - x < 0.34] + [0])
        m = P.mascota(t, float(boca[kb]), (t % 3.7) < 0.12, 0.6)
        m = m.resize((int(m.width * 0.78), int(m.height * 0.78)), Image.BILINEAR)
        pega(fr, m, 30, AL - m.height - 20 - 30 * salto)
        fr.alpha_composite(tema, (AN - tema.width - 30, AL - tema.height - 70))
        # subtitulo 1-2 palabras
        j = bisect.bisect_right(ini_caps, t) - 1
        if j >= 0 and t < caps[j][1]:
            a, _, ws, clave, tws = caps[j]
            cp = capa_cap(ws, clave, 0)
            s = 0.8 + 0.2 * E.rebote((t - a) / 0.12)
            cp2 = cp.resize((int(cp.width * s), int(cp.height * s)), Image.BILINEAR)
            pega(fr, cp2, AN / 2 - cp2.width / 2, 1450 - cp2.height / 2)
        dd = ImageDraw.Draw(fr)
        dd.rectangle([0, AL - 10, int(AN * t / dur), AL], fill=AMARILLO + (255,))
        ff.stdin.write(fr.convert("RGB").tobytes())
        if fi % (FPS * 10) == 0:
            print(f"  fotograma {fi}/{nf}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"CORTO {total:.1f} s -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dia")
    ap.add_argument("seccion", type=int)
    ap.add_argument("--gancho")
    ap.add_argument("--cierre")
    a = ap.parse_args()
    main(a.dia, a.seccion, a.gancho, a.cierre)
