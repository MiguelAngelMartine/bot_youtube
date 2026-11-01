"""EPISODIO completo con la identidad fija del canal: misma marca, presentador (la urna), colores, voz, sintonia,
cortinillas, tarjetas y estilo de fuentes cada dia. Lo que cambia es el contenido: cada paso del guion dice que
escena de la biblioteca lo acompana (sumario, mapa, cifra, claves, cronologia, persona, citas, posturas,
calendario, breve, despedida). Los bloques con tono "sobrio" (tragedias) van sin presentador y con la musica mas baja.
Uso: python episodio.py AAAA-MM-DD   (lee dia/AAAA-MM-DD/episodio.json)"""
from __future__ import annotations

import asyncio
import bisect
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageChops, ImageDraw

import genera_video as V1
import genera_video2 as G2
import musica
import voz
import prototipo_animado as P
from genera_video2 import AMARILLO, AN, AL, BLANCO, FPS, ROJO, fuente, pega, suave
from prototipo_animado import GRIS, NAVY, PANEL, PARTIDO, S, baja, f, lienzo

# colores aproximados de cada formacion (solo para identificar la tarjeta, igual tratamiento para todas)
PARTIDO.update({"PSC": (227, 6, 19), "Sumar": (230, 50, 110), "Junts": (32, 192, 178), "ERC": (255, 178, 0),
                "EH Bildu": (150, 190, 30), "CC": (240, 200, 0), "UPN": (0, 80, 160), "SALF": (70, 70, 70),
                "Compromís": (240, 130, 0), "UGT": (110, 120, 140), "CCOO": (110, 120, 140),
                "Gobierno": (90, 100, 120), "Institución": (90, 100, 120), "Encuesta": (90, 100, 120)})
TOP = 228
ZONA = {"normal": (620, 1840), "sobrio": (200, 1720)}     # x de la zona de contenido segun el tono
PANEL2 = (34, 52, 90)


# ------------------------------------------------------------------ voz con el tiempo de cada palabra

async def voz_palabras(texto, mp3):
    com = edge_tts.Communicate(texto, G2.VOZ[0], rate=G2.VOZ[1], pitch=G2.VOZ[2], boundary="WordBoundary")
    pal = []
    with open(mp3, "wb") as fh:
        async for c in com.stream():
            if c["type"] == "audio":
                fh.write(c["data"])
            elif c["type"] == "WordBoundary":
                pal.append((c["offset"] / 1e7, (c["offset"] + c["duration"]) / 1e7, c["text"]))
    return pal


def norm(w):
    return re.sub(r"\W", "", w.lower())


class Tiempos:
    """Casa las palabras que devuelve la voz con las del texto: tiempo de cualquier trozo del guion."""

    def __init__(self, texto, pal, t0):
        self.texto = texto
        self.toks = [(m.start(), m.group()) for m in re.finditer(r"\S+", texto)]
        tt = [None] * len(self.toks)
        j = 0
        for a, b, w in pal:
            nw = norm(w)
            if not nw:
                continue
            for k in range(j, min(j + 6, len(self.toks))):
                nt = norm(self.toks[k][1])
                if nt and (nt == nw or nt.startswith(nw) or nw.startswith(nt)):
                    tt[k] = (t0 + a, t0 + b)
                    j = k + 1
                    break
        ult = (t0, t0)
        for k in range(len(tt)):
            if tt[k] is None:
                tt[k] = (ult[1], ult[1])
            ult = tt[k]
        self.tt = tt
        self.casadas = sum(1 for x in tt if x[1] > x[0])
        self.eventos = []

    def en(self, c):
        k = max(i for i, (s, _) in enumerate(self.toks) if s <= max(c, 0)) if self.toks else 0
        return self.tt[k][0]

    def cuando(self, trozo, desde=0, defecto=None):
        c = self.texto.find(trozo, desde)
        if c < 0:
            c = self.texto.find(trozo)
        if c < 0:
            print(f"  AVISO: no encuentro «{trozo}» en la narracion")
            if defecto is not None:
                self.eventos.append(defecto)
            return defecto
        self.eventos.append(self.en(c))         # cada dato que entra en pantalla: golpe de camara, salto de Urni y "pop"
        return self.en(c)

    def trozos_palabras(self, maximo=3):
        """Subtitulo estilo TikTok: grupos de 1-3 palabras con el tiempo de cada una."""
        grupos, cur = [], []
        for k, (_, w) in enumerate(self.toks):
            cur.append(k)
            if len(cur) >= maximo or w[-1] in ".?!:;,":
                grupos.append(cur)
                cur = []
        if cur:
            grupos.append(cur)
        out = []
        for n, g in enumerate(grupos):
            a = self.tt[g[0]][0]
            fin = self.tt[g[-1]][1]
            sig = self.tt[grupos[n + 1][0]][0] if n + 1 < len(grupos) else fin + 0.5
            out.append((a, min(sig, fin + 0.6), [(self.toks[k][1], self.tt[k][0]) for k in g]))
        return out

    def subtitulos(self):
        out, cur = [], []
        for k, (s, w) in enumerate(self.toks):
            cur.append(k)
            if len(cur) >= 8 or (w[-1] in ".?!:;" and len(cur) >= 3) or (w[-1] == "," and len(cur) >= 6):
                out.append(cur)
                cur = []
        if cur:
            out.append(cur)
        subs = []
        for n, g in enumerate(out):
            a = self.tt[g[0]][0]
            b = self.tt[g[-1]][1]
            sig = self.tt[out[n + 1][0]][0] if n + 1 < len(out) else b + 0.4
            subs.append((a, sig if sig - b < 0.7 else b + 0.3, " ".join(self.toks[k][1] for k in g)))
        return subs


# ------------------------------------------------------------------ piezas

def icono(nombre, tam=84):
    im, d = lienzo(tam, tam)
    u = tam * S / 100
    U = lambda *v: [x * u for x in v]
    d.ellipse(U(0, 0, 100, 100), fill=PANEL2)
    B, Y, N = BLANCO, AMARILLO, NAVY
    if nombre == "vela":
        d.rounded_rectangle(U(40, 42, 60, 80), radius=3 * u, fill=B)
        d.ellipse(U(42, 20, 58, 42), fill=Y)
        d.line(U(50, 36, 50, 44), fill=N, width=int(3 * u))
    elif nombre == "persona":
        d.ellipse(U(36, 20, 64, 48), fill=B)
        d.pieslice(U(24, 52, 76, 104), 180, 360, fill=B)
    elif nombre == "documento":
        d.rounded_rectangle(U(30, 20, 70, 80), radius=4 * u, fill=B)
        for y in (34, 46, 58):
            d.line(U(38, y, 62, y), fill=N, width=int(4 * u))
    elif nombre == "reloj":
        d.ellipse(U(24, 24, 76, 76), outline=B, width=int(6 * u))
        d.line(U(50, 50, 50, 34), fill=Y, width=int(5 * u))
        d.line(U(50, 50, 62, 56), fill=Y, width=int(5 * u))
    elif nombre == "escudo":
        d.polygon(U(50, 20, 76, 30, 72, 62, 50, 82, 28, 62, 24, 30), fill=B)
        d.polygon(U(50, 30, 66, 36, 63, 58, 50, 72), fill=Y)
    elif nombre == "tren":
        d.rounded_rectangle(U(30, 22, 70, 74), radius=10 * u, fill=B)
        d.rectangle(U(36, 32, 64, 50), fill=N)
        d.ellipse(U(36, 58, 44, 66), fill=Y)
        d.ellipse(U(56, 58, 64, 66), fill=Y)
        d.line(U(36, 74, 28, 84), fill=B, width=int(4 * u))
        d.line(U(64, 74, 72, 84), fill=B, width=int(4 * u))
    elif nombre == "mazo":
        d.polygon(U(30, 30, 52, 18, 64, 40, 42, 52), fill=B)
        d.line(U(53, 40, 76, 72), fill=Y, width=int(8 * u))
        d.rectangle(U(24, 76, 60, 84), fill=B)
    elif nombre == "altavoz":
        d.polygon(U(24, 42, 40, 42, 66, 24, 66, 76, 40, 58, 24, 58), fill=B)
        d.arc(U(60, 34, 84, 66), 300, 60, fill=Y, width=int(5 * u))
    elif nombre == "tienda":
        d.rectangle(U(24, 40, 76, 78), fill=B)
        for k in range(4):
            d.rectangle(U(24 + 13 * k, 26, 37 + 13 * k, 40), fill=ROJO if k % 2 == 0 else Y)
        d.line(U(32, 50, 68, 72), fill=N, width=int(5 * u))
        d.line(U(32, 72, 68, 50), fill=N, width=int(5 * u))
    elif nombre == "grafico":
        for k, h in enumerate((30, 48, 22)):
            d.rectangle(U(28 + 16 * k, 76 - h, 40 + 16 * k, 76), fill=Y if k == 1 else B)
    elif nombre == "urna":
        d.rectangle(U(28, 44, 72, 78), fill=B)
        d.rectangle(U(24, 38, 76, 46), fill=ROJO)
        d.rectangle(U(40, 20, 60, 42), fill=Y)
    elif nombre == "alerta":
        d.polygon(U(50, 20, 80, 76, 20, 76), fill=Y)
        d.text((50 * u, 60 * u), "!", font=f("Inter-Black.ttf", tam * 0.34), fill=N, anchor="mm")
    return baja(im)


def fila_icono(nombre, txt, ancho, tam=36):
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ls = G2.texto_lineas(d0, txt, fuente("Inter-SemiBold.ttf", tam), ancho - 150)
    alto = max(104, int(len(ls) * tam * 1.32) + 34)
    im, d = lienzo(ancho, alto)
    d.rounded_rectangle([0, 0, ancho * S, alto * S], radius=20 * S, fill=PANEL + (235,))
    ic = icono(nombre, 76)
    y0 = (alto - len(ls) * tam * 1.32) / 2
    for j, l in enumerate(ls):
        d.text((124 * S, (y0 + j * tam * 1.32) * S), l, font=f("Inter-SemiBold.ttf", tam), fill=BLANCO)
    im = baja(im)
    im.alpha_composite(ic, (26, (alto - 76) // 2))
    return im


def fila_numero(num, txt, ancho):
    im, d = lienzo(ancho, 100)
    d.rounded_rectangle([0, 0, ancho * S, 100 * S], radius=20 * S, fill=PANEL + (235,))
    d.rounded_rectangle([22 * S, 22 * S, 102 * S, 78 * S], radius=28 * S, fill=ROJO)
    d.text((62 * S, 50 * S), num, font=f("Inter-Black.ttf", 30), fill=BLANCO, anchor="mm")
    tam = 38
    while tam > 26 and d.textlength(txt, font=f("Inter-SemiBold.ttf", tam)) > (ancho - 150) * S:
        tam -= 2
    d.text((128 * S, 50 * S), txt, font=f("Inter-SemiBold.ttf", tam), fill=BLANCO, anchor="lm")
    return baja(im)


def pie(txt):
    return P.texto(txt, 22, GRIS)


def rebote(x):
    """Entrada con rebote (sobrepasa un poco y vuelve): da el golpe visual de los videos cortos."""
    x = min(max(x, 0.0), 1.0)
    c1 = 1.9
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def aparece(lay, capa, x, y, t, t1, dx=60):
    """Entra en 0,32 s creciendo desde el 70 % con rebote, anclado a su borde izquierdo."""
    a = (t - t1) / 0.32
    if a <= 0:
        return
    if a >= 1:
        pega(lay, capa, x, y)
        return
    s = 0.7 + 0.3 * rebote(a)
    c = capa.resize((max(1, int(capa.width * s)), max(1, int(capa.height * s))), Image.BILINEAR)
    pega(lay, c, x + dx * 0.3 * (1 - a), y + (capa.height - c.height) / 2, min(1.0, a * 3))


def capa_particulas():
    """Lamina de puntos tenues (dos alturas de pantalla, repetida) que se desplaza hacia arriba detras de todo."""
    rng = np.random.default_rng(7)
    base = Image.new("RGBA", (AN, AL), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    for _ in range(70):
        x, y, r = rng.uniform(0, AN), rng.uniform(0, AL), rng.uniform(1.5, 5)
        col = AMARILLO if rng.random() < 0.3 else BLANCO
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(rng.uniform(30, 90)),))
    lam = Image.new("RGBA", (AN, 2 * AL), (0, 0, 0, 0))
    lam.paste(base, (0, 0))
    lam.paste(base, (0, AL))
    return lam


def capa_teaser(siguiente):
    f1, f2 = fuente("Inter-Black.ttf", 26), fuente("Inter-SemiBold.ttf", 30)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w1 = d0.textlength("A CONTINUACIÓN", font=f1)
    w = int(w1 + d0.textlength(siguiente, font=f2)) + 90
    im = Image.new("RGBA", (w, 58), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w, 58], radius=29, fill=(10, 18, 34, 235), outline=AMARILLO + (255,), width=3)
    d.text((26, 29), "A CONTINUACIÓN", font=f1, fill=AMARILLO + (255,), anchor="lm")
    d.text((w1 + 50, 29), siguiente, font=f2, fill=BLANCO + (255,), anchor="lm")
    return im


_cache_pal = {}


def capa_palabras(palabras, activa, ancho_max=1150):
    """Grupo de palabras grandes con contorno negro; la que se esta diciendo, en amarillo."""
    clave = (tuple(palabras), activa)
    if clave in _cache_pal:
        return _cache_pal[clave]
    txt = " ".join(palabras)
    tam = 78
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    while tam > 48 and d0.textlength(txt, font=fuente("Inter-Black.ttf", tam)) > ancho_max:
        tam -= 4
    fnt = fuente("Inter-Black.ttf", tam)
    w = int(d0.textlength(txt, font=fnt)) + 40
    im = Image.new("RGBA", (w, int(tam * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 20
    for k, pw in enumerate(palabras):
        col = AMARILLO if k == activa else BLANCO
        d.text((x, 8), pw, font=fnt, fill=col + (255,), stroke_width=7, stroke_fill=(0, 0, 0, 255))
        x += d0.textlength(pw + " ", font=fnt)
    _cache_pal[clave] = im
    return im


# ------------------------------------------------------------------ escenas: cada una prepara sus capas y devuelve dibuja(lay, t)

def esc_sumario(ve, T, c0, X0, X1, t0):
    W = X1 - X0
    filas = [(fila_numero(f"{k + 1:02d}", it["texto"], W), T.cuando(it["cuando"], c0, t0 + 1 + k)) for k, it in enumerate(ve["items"])]
    rot = P.rotulo("HOY EN EL RESUMEN")
    def dibuja(lay, t):
        pega(lay, rot, X0, TOP - 10, suave((t - t0) / 0.4))
        y = TOP + 50
        for capa, t1 in filas:
            aparece(lay, capa, X0, y, t, t1)
            y += capa.height + 18
    return dibuja


def proy(lon, lat, X0, k=72):
    return X0 + (lon + 9.6) * math.cos(math.radians(40)) * k, TOP + 20 + (44 - lat) * k


_mapas = {}


def base_mapa(X0):
    if X0 not in _mapas:
        im, d = lienzo(AN, AL)
        pts = [(x * S, y * S) for x, y in (proy(lo, la, X0) for lo, la in P.ESPANA)]
        d.polygon(pts, fill=(28, 46, 80))
        d.line(pts + [pts[0]], fill=(80, 110, 160), width=4 * S)
        cx, cy = proy(3.0, 39.6, X0)
        d.ellipse([(cx - 30) * S, (cy - 15) * S, (cx + 30) * S, (cy + 15) * S], fill=(28, 46, 80), outline=(80, 110, 160), width=3 * S)
        _mapas[X0] = baja(im)
    return _mapas[X0]


def esc_mapa(ve, T, c0, X0, X1, t0):
    base = base_mapa(X0)
    pts = []
    for p in ve["puntos"]:
        x, y = proy(p["lon"], p["lat"], X0)
        et = P.texto(p["nombre"], 32, BLANCO, "Inter-SemiBold.ttf", 400)
        w = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(p["nombre"], font=fuente("Inter-SemiBold.ttf", 32)))
        ex = x - w / 2 if p.get("abajo") else (x - w - 26 if p.get("izq") else x + 24)
        ey = y + 18 if p.get("abajo") else y - 24
        t1 = T.cuando(p["cuando"], c0, t0 + 0.4) if p.get("cuando") else t0 + 0.4
        pts.append({"x": x, "y": y, "et": et, "ex": ex, "ey": ey, "w": w, "t1": t1, **p})
    por_nombre = {p["nombre"]: p for p in pts}
    ruta = [(por_nombre[n]["x"], por_nombre[n]["y"]) for n in ve.get("ruta", [])]
    tren = P.tren(math.atan2(ruta[-1][1] - ruta[0][1], ruta[-1][0] - ruta[0][0])) if ve.get("tren") else None
    av = P.aviso()
    XT = X0 + 760
    WT = X1 - XT
    tit = P.texto(ve["titular"], 44, BLANCO, "Inter-Black.ttf", WT)
    sub = P.texto(ve.get("sub", ""), 30, GRIS, ancho=WT)
    fte = pie("Fuente: " + ve["fuente"])
    largos = [math.dist(a, b) for a, b in zip(ruta, ruta[1:])]
    def punto_en(p):
        r = p * sum(largos)
        for (a, b), L in zip(zip(ruta, ruta[1:]), largos):
            if r <= L:
                return a[0] + (b[0] - a[0]) * r / L, a[1] + (b[1] - a[1]) * r / L
            r -= L
        return ruta[-1]
    def dibuja(lay, t):
        pega(lay, base, 0, 0, suave((t - t0) / 0.5))
        d = ImageDraw.Draw(lay)
        if len(ruta) > 1:
            p = suave((t - t0 - 0.5) / 2.2)
            if p > 0:
                n = 40
                d.line([punto_en(p * k / n) for k in range(n + 1)], fill=AMARILLO + (255,), width=9, joint="curve")
                if tren:
                    x, y = punto_en(min(p, 0.62))
                    pega(lay, tren, x - tren.width / 2, y - tren.height / 2 - 30)
            if ve.get("aviso_ruta"):
                s = suave((t - t0 - 2.8) / 0.4)
                if s > 0:
                    x, y = punto_en(0.8)
                    pega(lay, av, x - 60, y - 130 - 20 * (1 - s), s)
        for p in pts:
            a = suave((t - p["t1"]) / 0.4)
            if a <= 0:
                continue
            if p.get("pulso"):
                for fase in (0.0, 0.5):
                    q = ((t - p["t1"]) / 1.4 + fase) % 1
                    r = 14 + 46 * q
                    d.ellipse([p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r], outline=ROJO + (255,), width=max(1, int(6 * (1 - q))))
            r = 12 + 4 * (1 - a)
            d.ellipse([p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r], fill=ROJO + (255,) if p.get("aviso") or p.get("pulso") else BLANCO + (255,), outline=NAVY + (255,), width=4)
            pega(lay, p["et"], p["ex"], p["ey"], a)
            if p.get("aviso"):
                ax = p["ex"] - 134 if p.get("izq") else p["ex"] + p["w"] + 14
                pega(lay, av, ax, p["y"] - 62 - 20 * (1 - a), a)
        a = suave((t - t0 - 1.0) / 0.5)
        y = TOP + 200
        for capa in (tit, sub, fte):
            pega(lay, capa, XT + 40 * (1 - a), y, a)
            y += capa.height + 14
    return dibuja


def esc_cifra(ve, T, c0, X0, X1, t0):
    W = X1 - X0
    fn = fuente("Inter-Black.ttf", 230)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    wn = d0.textlength(ve["numero"], font=fn)
    et = P.texto(ve["etiqueta"], 64, BLANCO, "Inter-Black.ttf", int(W - wn - 60))
    sub = P.texto(ve.get("sub", ""), 38, GRIS, ancho=int(W - wn - 60))
    nota = None
    if ve.get("nota"):
        nota = fila_icono("alerta", ve["nota"], W, 34)
        tn = T.cuando(ve["cuando_nota"], c0, t0 + 3)
    fte = pie("Fuente: " + ve["fuente"])
    def dibuja(lay, t):
        a = suave((t - t0 - 0.2) / 1.2)
        try:
            n = int(ve["numero"])
            txt = str(int(round(n * a)))
        except ValueError:
            txt = ve["numero"]
        d = ImageDraw.Draw(lay)
        if a > 0:
            d.text((X0, TOP + 40), txt, font=fn, fill=AMARILLO + (255,))
        aparece(lay, et, X0 + wn + 50, TOP + 90, t, t0 + 0.6)
        aparece(lay, sub, X0 + wn + 50, TOP + 90 + et.height + 6, t, t0 + 0.9)
        y = TOP + 340
        if nota is not None:
            aparece(lay, nota, X0, y, t, tn)
            y += nota.height + 16
        pega(lay, fte, X0, y, suave((t - t0 - 1.0) / 0.5))
    return dibuja


def esc_claves(ve, T, c0, X0, X1, t0):
    W = X1 - X0
    rot = P.rotulo(ve["titulo"])
    filas = [(fila_icono(it["icono"], it["texto"], W), T.cuando(it["cuando"], c0, t0 + 0.8 + k)) for k, it in enumerate(ve["items"])]
    fte = pie("Fuente: " + ve["fuente"]) if ve.get("fuente") else None
    def dibuja(lay, t):
        pega(lay, rot, X0, TOP - 10, suave((t - t0) / 0.4))
        y = TOP + 46
        for capa, t1 in filas:
            aparece(lay, capa, X0, y, t, t1)
            y += capa.height + 14
        if fte:
            pega(lay, fte, X0, y + 4, suave((t - filas[0][1]) / 0.5))
    return dibuja


def esc_cronologia(ve, T, c0, X0, X1, t0):
    W = X1 - X0
    rot = P.rotulo(ve["titulo"])
    items = []
    for k, it in enumerate(ve["items"]):
        h = P.texto(it["hora"], 38, AMARILLO, "Inter-Black.ttf", W - 90)
        tx = P.texto(it["texto"], 32, BLANCO, "Inter-SemiBold.ttf", W - 90)
        items.append((h, tx, T.cuando(it["cuando"], c0, t0 + 0.8 + k)))
    fte = pie("Fuente: " + ve["fuente"])
    def dibuja(lay, t):
        pega(lay, rot, X0, TOP - 10, suave((t - t0) / 0.4))
        d = ImageDraw.Draw(lay)
        y = TOP + 56
        for h, tx, t1 in items:
            a = suave((t - t1) / 0.5)
            alto = h.height + tx.height + 26
            if a > 0:
                d.line([(X0 + 22, y + 10), (X0 + 22, y + 10 + alto * a)], fill=(80, 110, 160, 255), width=6)
                r = 14
                d.ellipse([X0 + 22 - r, y + 18 - r, X0 + 22 + r, y + 18 + r], fill=AMARILLO + (255,), outline=NAVY + (255,), width=4)
                pega(lay, h, X0 + 64 + 40 * (1 - a), y, a)
                pega(lay, tx, X0 + 64 + 40 * (1 - a), y + h.height + 2, a)
            y += alto
        pega(lay, fte, X0 + 64, y + 4, suave((t - items[0][2]) / 0.5))
    return dibuja


def esc_persona(ve, T, c0, X0, X1, t0):
    p = ve["persona"]
    sin = P.tarjeta(p["nombre"], p["cargo"], p["partido"], 660)
    con = P.tarjeta(p["nombre"], p["cargo"], p["partido"], 660, p.get("cita"), p.get("medio")) if p.get("cita") else sin
    tc = T.cuando(p["cita_cuando"], c0, t0 + 1.5) if p.get("cita_cuando") else t0 + 1.0
    sello = P.sello(ve["sello"]) if ve.get("sello") else None
    ts = T.cuando(ve["sello_cuando"], c0, t0 + 1.2) if sello else 0
    fl = ve.get("flujo")
    if fl:
        dst = fl["a"]
        tarj_b = P.tarjeta(dst["nombre"], dst["cargo"], dst["partido"], 620, dst.get("cita"), dst.get("medio"))
        tf = T.cuando(fl["cuando"], c0, t0 + 3)
        tb = T.cuando(fl["a_cuando"], c0, tf + 2)
        etq = P.texto(fl["etiqueta"], 30, GRIS, ancho=430)
    def dibuja(lay, t):
        a = suave((t - t0 - 0.2) / 0.5)
        b = suave((t - tc) / 0.5)
        pega(lay, sin, X0 + 60 * (1 - a), TOP + 20, a * (1 - b))
        pega(lay, con, X0 + 60 * (1 - a), TOP + 20, a * b)
        alto = sin.height + (con.height - sin.height) * b
        if sello is not None:
            s = suave((t - ts) / 0.35)
            if s > 0:
                st = sello.resize((int(sello.width * (1.5 - 0.5 * s)), int(sello.height * (1.5 - 0.5 * s))))
                pega(lay, st, X0 + 560 - st.width / 2, TOP + 26 - st.height / 2, s)
        if fl:
            d = ImageDraw.Draw(lay)
            yb = TOP + 20 + con.height + 90
            P.flecha(d, (X0 + 470, TOP + 20 + alto + 14), (X1 - 600, yb - 6), suave((t - tf - 0.3) / 0.8), AMARILLO + (255,))
            pega(lay, etq, X0, TOP + 20 + alto + 40, suave((t - tf) / 0.5))
            aparece(lay, tarj_b, X1 - 620, yb, t, tb)
    return dibuja


def esc_citas(ve, T, c0, X0, X1, t0):
    W = X1 - X0
    rot = P.rotulo(ve["titulo"])
    tarj = [(P.tarjeta_compacta(it["nombre"], it["cargo"], it["partido"], W, it["cita"], it["medio"]), T.cuando(it["cuando"], c0, t0 + 1 + 3 * k))
            for k, it in enumerate(ve["items"])]
    def dibuja(lay, t):
        pega(lay, rot, X0, TOP - 10, suave((t - t0) / 0.4))
        y = TOP + 44
        for capa, t1 in tarj:
            aparece(lay, capa, X0, y, t, t1, 80)
            y += capa.height + 12
    return dibuja


def esc_posturas(ve, T, c0, X0, X1, t0):
    rot = P.rotulo(ve["titulo"])
    c = ve["centro"]
    centro = P.tarjeta(c["nombre"], c["cargo"], c["partido"], 500)
    chips = [(P.chip(it["nombre"], it["partido"], 400), T.cuando(it["cuando"], c0, t0 + 1 + 0.4 * k)) for k, it in enumerate(ve["presionan"])]
    etq = P.texto(ve["etiqueta"], 30, BLANCO, "Inter-SemiBold.ttf", 420)
    te = T.cuando(ve["etiqueta_cuando"], c0, t0 + 2)
    ap = ve["aparte"]
    chip_ap = P.chip(ap["nombre"], ap["partido"], 400, apagado=True)
    txt_ap = P.texto(ap["texto"], 28, GRIS, ancho=420)
    ta = T.cuando(ap["cuando"], c0, t0 + 6)
    fte = pie("Fuentes: " + ve["fuente"])
    XC = X1 - 420
    yc_centro = TOP + 200
    def dibuja(lay, t):
        pega(lay, rot, X0, TOP - 10, suave((t - t0) / 0.4))
        aparece(lay, centro, X0, yc_centro, t, t0 + 0.2)
        d = ImageDraw.Draw(lay)
        y = TOP + 30
        for k, (cp, t1) in enumerate(chips):
            aparece(lay, cp, XC, y, t, t1, 120)
            P.flecha(d, (XC - 12, y + 39), (X0 + 512, yc_centro + 75 + 14 * (k - 1.5)), suave((t - t1 - 0.5) / 0.5), AMARILLO + (255,), 6)
            y += 92
        pega(lay, etq, XC, y + 2, suave((t - te) / 0.5))
        y += etq.height + 24
        aparece(lay, chip_ap, XC, y, t, ta)
        pega(lay, txt_ap, XC, y + 88, suave((t - ta) / 0.5))
        pega(lay, fte, X0, yc_centro + centro.height + 30, suave((t - t0 - 1) / 0.5))
    return dibuja


def hoja_calendario(dia, mes, pie_txt):
    im, d = lienzo(340, 380)
    d.rounded_rectangle([0, 0, 340 * S, 380 * S], radius=26 * S, fill=BLANCO)
    d.rounded_rectangle([0, 0, 340 * S, 96 * S], radius=26 * S, fill=ROJO)
    d.rectangle([0, 60 * S, 340 * S, 96 * S], fill=ROJO)
    d.text((170 * S, 50 * S), mes, font=f("Inter-Black.ttf", 38), fill=BLANCO, anchor="mm")
    d.text((170 * S, 210 * S), dia, font=f("Inter-Black.ttf", 170), fill=NAVY, anchor="mm")
    d.text((170 * S, 335 * S), pie_txt, font=f("Inter-SemiBold.ttf", 30), fill=NAVY, anchor="mm")
    for x in (90, 250):
        d.ellipse([(x - 12) * S, -12 * S, (x + 12) * S, 12 * S], fill=NAVY)
    return baja(im)


def esc_calendario(ve, T, c0, X0, X1, t0):
    hoja = hoja_calendario(ve["dia"], ve["mes"], ve["pie"])
    W = X1 - X0 - 420
    items = [(P.texto(it["hora"], 36, AMARILLO, "Inter-Black.ttf", W), P.texto(it["texto"], 32, BLANCO, "Inter-SemiBold.ttf", W),
              T.cuando(it["cuando"], c0, t0 + 1 + k)) for k, it in enumerate(ve["items"])]
    fte = pie("Fuentes: " + ve["fuente"])
    def dibuja(lay, t):
        a = suave((t - t0 - 0.1) / 0.6)
        if a > 0:
            h = hoja.rotate(-4 * (1 - a), expand=True, resample=Image.BICUBIC)
            pega(lay, h, X0, TOP + 30 + 40 * (1 - a), a)
        y = TOP + 40
        for hh, tx, t1 in items:
            aparece(lay, hh, X0 + 420, y, t, t1)
            aparece(lay, tx, X0 + 420, y + hh.height, t, t1 + 0.1)
            y += hh.height + tx.height + 30
        pega(lay, fte, X0, TOP + 440, suave((t - t0 - 1) / 0.5))
    return dibuja


def esc_breve(ve, T, c0, X0, X1, t0):
    W = X1 - X0
    ic = icono(ve["icono"], 130)
    lugar = P.texto(ve["lugar"], 40, AMARILLO, "Inter-Black.ttf", W - 170)
    tit = P.texto(ve["titular"], 54, BLANCO, "Inter-Black.ttf", W)
    sub = P.texto(ve["sub"], 34, GRIS, ancho=W)
    fte = pie("Fuente: " + ve["fuente"])
    def dibuja(lay, t):
        a = suave((t - t0) / 0.5)
        pega(lay, ic, X0, TOP + 10, a)
        aparece(lay, lugar, X0 + 160, TOP + 50, t, t0 + 0.1)
        y = TOP + 180
        for k, capa in enumerate((tit, sub, fte)):
            aparece(lay, capa, X0, y, t, t0 + 0.3 + 0.25 * k)
            y += capa.height + 18
    return dibuja


def esc_despedida(ve, T, c0, X0, X1, t0):
    t1 = P.texto("Gracias por vernos.", 72, BLANCO, "Inter-Black.ttf", X1 - X0)
    t2 = P.texto("Mañana, más.", 56, AMARILLO, "Inter-Black.ttf", X1 - X0)
    def dibuja(lay, t):
        aparece(lay, t1, X0, TOP + 160, t, t0 + 0.1)
        aparece(lay, t2, X0, TOP + 280, t, t0 + 0.9)
    return dibuja


# fondos de foto: solo en escenas de texto; mapa, posturas, calendario, sumario y despedida son animacion pura
CON_FOTO = {"persona", "citas", "claves", "cronologia", "cifra", "breve"}


def base_foto_marca(ruta):
    """Foto a pantalla completa (algo mayor, para el zoom lento), oscurecida y tenida del azul del canal,
    con mas sombra abajo (subtitulos) y a la izquierda (presentador), para que todo se lea encima."""
    im = Image.open(ruta).convert("RGB")
    W, H = int(AN * 1.08), int(AL * 1.08)
    r = max(W / im.width, H / im.height)
    im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 3
    im = im.crop((x, y, x + W, y + H))
    im = Image.blend(im.point(lambda v: int(v * 0.62)), Image.new("RGB", (W, H), NAVY), 0.38)
    sombra = Image.new("L", (1, H))
    sombra.putdata([int(200 * max(0.0, (yy - H * 0.62) / (H * 0.38)) ** 1.4) for yy in range(H)])
    lado = Image.new("L", (W, 1))
    lado.putdata([int(150 * max(0.0, 1 - xx / (W * 0.35)) ** 1.5) for xx in range(W)])
    mascara = ImageChops.lighter(sombra.resize((W, H)), lado.resize((W, H)))
    im.paste(Image.new("RGB", (W, H), NAVY), (0, 0), mascara)
    return im.convert("RGBA")


def capa_credito_foto(c):
    txt = f"Foto de archivo · {c['autor']} · {c['licencia']}"
    f = fuente("Inter-Regular.ttf", 20)
    w = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(txt, font=f)) + 24
    im = Image.new("RGBA", (w, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w, 32], radius=8, fill=(0, 0, 0, 150))
    d.text((12, 16), txt, font=f, fill=(225, 228, 235, 255), anchor="lm")
    return im


def con_foto(dib, ruta, credito, t0):
    """Envuelve una escena: debajo, la foto con zoom lento; encima, el contenido; abajo a la derecha, el credito."""
    base = base_foto_marca(ruta)
    cred = capa_credito_foto(credito)
    def dibuja(lay, t):
        p = min(max((t - t0) / 14, 0), 1)
        z = 1 + 0.06 * p
        w, h = base.width / z, base.height / z
        x0 = (base.width - w) * (0.3 + 0.4 * p)
        y0 = (base.height - h) * 0.5
        lay.alpha_composite(base.resize((AN, AL), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h)))
        pega(lay, cred, AN - cred.width - 24, AL - cred.height - 16)
        dib(lay, t)
    return dibuja


ESCENAS = {"sumario": esc_sumario, "mapa": esc_mapa, "cifra": esc_cifra, "claves": esc_claves, "cronologia": esc_cronologia,
           "persona": esc_persona, "citas": esc_citas, "posturas": esc_posturas, "calendario": esc_calendario,
           "breve": esc_breve, "despedida": esc_despedida}


# ------------------------------------------------------------------ montaje

def main(dia_txt):
    dia = Path(__file__).parent / "dia" / dia_txt
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    tmp = dia / "tmp_ep"
    tmp.mkdir(exist_ok=True)
    secs = G["secciones"]
    n = len(secs)
    t = G2.INTRO
    plan, wavs, subs, calma, palabras = [], [], [], [], []
    creditos = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    fotos_usadas = {}
    for i, s in enumerate(secs):
        texto = " ".join(p["di"] for p in s["pasos"])
        pal, dur = voz.locuta(s["pasos"], s["tono"], tmp / f"s{i}.wav")      # voz de la muestra 1, sin entonacion, pausas naturales (opcion B)
        wavs.append(tmp / f"s{i}.wav")
        T = Tiempos(texto, pal, t)
        print(f"  bloque {i}: {dur:5.1f} s, {T.casadas}/{len(T.toks)} palabras con tiempo", flush=True)
        X0, X1 = ZONA[s["tono"]]
        escenas, c = [], 0
        for p in s["pasos"]:
            if p.get("ve"):
                t0 = t if not escenas else T.en(c)
                dib = ESCENAS[p["ve"]["tipo"]](p["ve"], T, c, X0, X1, t0)
                foto = p["ve"].get("foto")
                if foto and p["ve"]["tipo"] in CON_FOTO:
                    if foto in creditos and (dia / "imagenes" / foto).exists():
                        dib = con_foto(dib, dia / "imagenes" / foto, creditos[foto], t0)
                        fotos_usadas[foto] = creditos[foto]
                    else:
                        print(f"  AVISO: la foto {foto} no esta en imagenes/ o no tiene credito; la escena va sin foto")
                escenas.append([t0, None, dib, p["ve"]["tipo"]])
            c += len(p["di"]) + 1
        for a, b in zip(escenas, escenas[1:]):
            a[1] = b[0]
        escenas[-1][1] = t + dur + 0.3
        subs += [(a, b, None, x) for a, b, x in T.subtitulos()]          # solo para el .srt de YouTube
        palabras += T.trozos_palabras()
        etiqueta = "HOY" if i == 0 else f"{i:02d} / {n - 1:02d}"
        plan.append({"t0": t, "dur": dur, "sec": s, "escenas": escenas, "X": (X0, X1),
                     "blq": P.capa_bloque(s["titulo"], etiqueta), "pops": sorted(T.eventos),
                     "cambios": [e[0] for e in escenas[1:]]})
        if s["tono"] == "sobrio":
            calma.append((t, t + dur))
        t += dur
    fin_voz = t
    lista = tmp / "voz.txt"
    lista.write_text("".join(f"file '{w.name}'\n" for w in wavs), encoding="utf-8")
    subprocess.run([V1.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(tmp / "voz.wav")], check=True)
    # ritmo: cada dato que entra (pops) y cada cambio de escena; en los bloques sobrios no hay golpes ni "pop"
    normal = [p for p in plan if p["sec"]["tono"] != "sobrio"]
    pops = sorted(x for p in normal for x in p["pops"])
    cambios = sorted(x for p in plan for x in p["cambios"])
    efectos = [(x, "pop") for x in pops] + [(x, "whoosh") for x in cambios]
    total = musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", G2.INTRO, G2.OUTRO, [p["t0"] for p in plan] + [fin_voz],
                          calma=calma, efectos=efectos)
    golpes_n = sorted(set(pops + [x for p in normal for x in p["cambios"]]))

    def recientes(lista, t, ventana):
        k = bisect.bisect_right(lista, t)
        return [t - x for x in lista[max(0, k - 6):k] if t - x < ventana]

    def zoom(t, sobrio):
        """Camara: deriva lenta siempre; en tono normal, golpe de zoom cuando entra un dato o cambia la escena."""
        z = 1.025 + 0.015 * math.sin(t * 0.33)
        if not sobrio:
            z += max([0.045 * math.exp(-x / 0.16) for x in recientes(golpes_n, t, 1.0)] + [0])
        return z

    def salto(t):
        return max([math.sin(math.pi * x / 0.34) for x in recientes(pops, t, 0.34)] + [0])

    # labios y gesto del presentador
    v, sr = musica.lee_wav(tmp / "voz.wav")
    hop = sr // FPS
    rms = np.sqrt(np.mean(v[: len(v) // hop * hop, 0].reshape(-1, hop) ** 2, axis=1))
    boca = np.clip(rms / np.percentile(rms[rms > 0.01], 90), 0, 1) ** 0.8
    gesto = np.convolve(boca, np.ones(25) / 25, mode="same")

    cab = G2.capa_cabecera(G["fecha"])
    particulas = capa_particulas()
    inicio_pal = [x[0] for x in palabras]
    for j, p in enumerate(plan[:-1]):
        p["teaser"] = capa_teaser(plan[j + 1]["sec"]["titulo"])
    out = dia / "episodio.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], stdin=subprocess.PIPE)
    def presente(t):
        """1 si el presentador esta en pantalla (bloques normales), con entrada y salida suaves."""
        i = max(j for j, p in enumerate(plan) if p["t0"] <= t + 1e-9)
        dentro = plan[i]["sec"]["tono"] != "sobrio"
        antes = plan[i - 1]["sec"]["tono"] != "sobrio" if i > 0 else False
        x = suave((t - plan[i]["t0"] - 0.3) / 0.6)
        return (antes + (dentro - antes) * x) if i > 0 else float(dentro) * suave((t - plan[0]["t0"]) / 0.6)
    nf = int(math.ceil(total * FPS))
    for fi in range(nf):
        t = fi / FPS
        if t < G2.INTRO or t >= fin_voz:
            fr = G2.cuadro_intro(t, G["fecha"]) if t < G2.INTRO else G2.cuadro_cierre(t - fin_voz, G["fecha"])
            d = ImageDraw.Draw(fr)
            q = (t - fin_voz) / G2.CORTINILLA
            if 0 <= q < 1:
                x0 = int(AN * (2.2 * q - 1.2))
                d.rectangle([x0, 0, x0 + AN, AL], fill=ROJO + (255,))
                d.rectangle([x0 + AN, 0, x0 + AN + 40, AL], fill=AMARILLO + (255,))
            ff.stdin.write(fr.convert("RGB").tobytes())
            continue
        i = max(j for j, p in enumerate(plan) if p["t0"] <= t + 1e-9)
        p = plan[i]
        sobrio = p["sec"]["tono"] == "sobrio"
        fr = G2.fondo_marca(t)
        off = int((AL - (t * 38) % AL)) % AL                         # particulas que suben despacio
        fr.alpha_composite(particulas.crop((0, off, AN, off + AL)))
        for a, b, dib, _ in p["escenas"]:
            if a - 0.01 <= t < b:
                entra = (t - a) / 0.28 if a > p["t0"] + 0.01 else 1.0  # corte rapido: la escena nueva llega barriendo
                sale = (b - t) / 0.2
                if entra >= 1 and sale >= 1:
                    dib(fr, t)
                else:
                    lay = Image.new("RGBA", (AN, AL), (0, 0, 0, 0))
                    dib(lay, t)
                    ox, o = 0.0, 1.0
                    if entra < 1:
                        e = 1 - (1 - max(entra, 0)) ** 3
                        ox += 320 * (1 - e)
                        o = min(o, e * 1.6)
                    if sale < 1:
                        e = 1 - max(sale, 0)
                        ox -= 260 * e * e
                        o = min(o, 1 - e)
                    if o > 0.001:
                        pega(fr, lay, ox, 0, min(o, 1.0))
        # presentador: da un saltito con cada dato que entra
        pm = presente(t)
        if pm > 0.001:
            k = min(int((t - G2.INTRO) * FPS), len(boca) - 1)
            despedida = p["escenas"][-1][3] == "despedida" and t >= p["escenas"][-1][0]
            ge = 1.0 if despedida else float(gesto[k])
            par = (t % 3.7) < 0.12 or (t % 5.3) < 0.1
            m = P.mascota(t, float(boca[k]), par, ge)
            pega(fr, m, 90, 520 + 260 * (1 - pm) - 34 * salto(t), pm)
        # camara (todo lo de arriba se mueve; cabecera, subtitulos y barra quedan fijos)
        z = zoom(t, sobrio)
        w, h = AN / z, AL / z
        cx, cy = AN * 0.56, AL * 0.52
        x0c = min(max(cx - w / 2, 0), AN - w)
        y0c = min(max(cy - h / 2, 0), AL - h)
        fr = fr.resize((AN, AL), Image.BILINEAR, box=(x0c, y0c, x0c + w, y0c + h))
        fr.alpha_composite(cab)
        pega(fr, p["blq"], 100, 108)
        # "A continuacion": los ultimos segundos de cada bloque anuncian el siguiente (retencion)
        if 0 < i < len(plan) - 1:
            falta = plan[i + 1]["t0"] - t
            if falta < 4.5:
                tz = p["teaser"]
                e = rebote((4.5 - falta) / 0.4)
                pega(fr, tz, AN - 50 - tz.width * e, 106, min(1.0, (4.5 - falta) * 3))
        # subtitulos grandes palabra a palabra
        X0, X1 = p["X"]
        k = bisect.bisect_right(inicio_pal, t) - 1
        if k >= 0 and t < palabras[k][1]:
            a, _, grupo = palabras[k]
            activa = max(j for j, (_, ts) in enumerate(grupo) if ts <= t + 0.02) if grupo[0][1] <= t + 0.02 else 0
            cp = capa_palabras([g[0] for g in grupo], activa)
            s = 0.86 + 0.14 * rebote((t - a) / 0.14)
            if s < 0.999:
                cp = cp.resize((int(cp.width * s), int(cp.height * s)), Image.BILINEAR)
            pega(fr, cp, (X0 + X1) / 2 - cp.width / 2, AL - 70 - cp.height)
        d = ImageDraw.Draw(fr)
        d.rectangle([0, AL - 8, int(AN * (t - G2.INTRO) / (fin_voz - G2.INTRO)), AL], fill=AMARILLO + (255,))
        tl = t - p["t0"]
        if tl < G2.CORTINILLA:
            q = tl / G2.CORTINILLA
            x0 = int(AN * (2.2 * q - 1.2))
            d.rectangle([x0, 0, x0 + AN, AL], fill=ROJO + (255,))
            d.rectangle([x0 + AN, 0, x0 + AN + 40, AL], fill=AMARILLO + (255,))
        ff.stdin.write(fr.convert("RGB").tobytes())
        if fi % (FPS * 30) == 0:
            print(f"  fotograma {fi}/{nf}", flush=True)
    ff.stdin.close()
    ff.wait()

    escribe_textos(dia, G, plan, [(a, b, x) for a, b, _, x in subs],
                   [(i, tipo, a, b) for i, p in enumerate(plan) for a, b, _, tipo in p["escenas"]], total, fin_voz, fotos_usadas)
    print(f"EPISODIO {total / 60:.1f} min -> {out}")


def escribe_textos(dia, G, plan, subs, escenas, total, fin_voz, fotos_usadas):
    """episodio.srt, escenas.json (para el control de calidad) y episodio_descripcion.txt con capitulos, fuentes y creditos.
    plan: [{"t0", "sec"}] por bloque; subs: [(a, b, texto)]; escenas: [(n_bloque, tipo, t0, t1)]."""
    secs = G["secciones"]
    srt = "\n".join(f"{j + 1}\n{V1.hms(a)} --> {V1.hms(b)}\n{x}\n" for j, (a, b, x) in enumerate(subs))
    (dia / "episodio.srt").write_text(srt, encoding="utf-8")
    # mapa de escenas para el control de calidad: de que segundo a que segundo va cada una
    escenas = [{"seccion": i, "titulo": plan[i]["sec"]["titulo"], "tono": plan[i]["sec"]["tono"], "tipo": tipo,
                "t0": round(a, 2), "t1": round(b, 2)} for i, tipo, a, b in escenas]
    (dia / "escenas.json").write_text(json.dumps({"total": round(total, 2), "fin_voz": round(fin_voz, 2), "escenas": escenas},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    capitulos = "0:00 Inicio\n" + "\n".join(f"{int(p['t0'] // 60)}:{int(p['t0'] % 60):02d} {p['sec']['titulo']}" for p in plan)
    fuentes = sorted({x for s in secs for x in s.get("fuentes", [])})
    desc = (f"{G['titulo_video']}\n\n{G2.MARCA.title().replace(' En ', ' en ')}: lo más relevante de la política española del "
            f"{G['fecha'].lower()}, contado por {G2.PRESENTADORA} con datos, "
            f"citas textuales y la fuente de cada información.\n\nCapítulos:\n{capitulos}\n\nFuentes: {', '.join(fuentes)}.\n\n"
            "Resumen informativo elaborado con ayuda de inteligencia artificial a partir de noticias publicadas por los medios citados, "
            "y revisado antes de su publicación. Voz sintética. Gráficos, animaciones y música originales del canal.")
    if fotos_usadas:
        desc += ("\n\nFotografías de archivo (licencias libres, adaptadas con el color y encuadre del canal):\n"
                 + "\n".join(f"- {c['autor']} ({c['licencia']}): {c['pagina']}" for c in fotos_usadas.values()))
    (dia / "episodio_descripcion.txt").write_text(desc, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
