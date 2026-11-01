"""VINETAS de comic para el tablero (decision del usuario del 1-nov-2026: sustituyen a las notas manuscritas).

Cada vineta es una ilustracion de un catalogo propio de escenas genericas, dibujada a vectores con trazo de tinta,
tramado de puntos y lineas de accion, con el dato en una cartela de comic con letra de rotulista (Comic Neue).
Reglas: personajes genericos, nunca caricaturas de personas reales; nada de victimas ni de violencia explicita;
en los bloques sobrios, version apagada (sin onomatopeyas ni estallidos).

Uso:  vineta("tren", "LZB: sistema que impide que dos trenes coincidan en el mismo punto", ancho=520)
Escenas: ver ESCENAS al final."""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from genera_video2 import fuente

TINTA = (22, 22, 30)
K = 3                                   # se dibuja a 3x y se reduce: trazos limpios
CARTELA = (255, 228, 92)
PIEL = (241, 194, 160)
PIEL_SOMBRA = (214, 160, 128)
TRAJE = (40, 52, 86)


ESTILOS = ("comic", "plano", "3d", "pixel", "grafica")
# novela grafica: pocas tintas planas y negro para las sombras (paleta propia a partir de los colores del canal)
PALETA_G = [(18, 16, 22), (40, 44, 74), (150, 36, 44), (214, 160, 72), (196, 160, 126), (243, 228, 200)]


def _mezcla(c, d, u):
    return tuple(int(c[k] + (d[k] - c[k]) * u) for k in range(3))


class Lienzo:
    """Coordenadas normalizadas (0-1) sobre un lienzo a K aumentos. El estilo decide como se pinta cada forma:
    comic (tinta y trama), plano (sin contornos, tipo Crehana), 3d (volumen con sombreado y sombra suave, tipo
    Pixar) y pixel (se pinta plano y al final se pixela con paleta reducida)."""

    def __init__(self, w, h, fondo, estilo="comic"):
        self.w, self.h = w * K, h * K
        self.estilo = estilo
        self.im = Image.new("RGBA", (self.w, self.h), fondo + (255,))
        self.d = ImageDraw.Draw(self.im)
        self.t = max(2, int(self.w * 0.007))           # grosor de tinta

    def p(self, x, y):
        return (x * self.w, y * self.h)

    def pts(self, *v):
        return [self.p(v[i], v[i + 1]) for i in range(0, len(v), 2)]

    def _forma(self, dibuja, fill, tinta, ancho):
        """dibuja(draw, fill, outline, width) pinta la forma; aqui se decide el acabado segun el estilo."""
        rgba = fill + (255,) if len(fill) == 3 else fill
        if self.estilo == "comic":
            dibuja(self.d, rgba, TINTA + (255,) if tinta else None, (ancho or self.t) if tinta else 0)
            return
        grafica = self.estilo == "grafica"
        if (self.estilo != "3d" and not grafica) or rgba[3] < 255:
            dibuja(self.d, rgba, None, 0)
            return
        # 3d: mascara de la forma -> sombra suave debajo, relleno con degradado (luz arriba) y brillo en el borde alto
        m = Image.new("L", self.im.size)
        dibuja(ImageDraw.Draw(m), 255, None, 0)
        bb = m.getbbox()
        if not bb:
            return
        if grafica and (bb[3] - bb[1]) < self.h * 0.40:   # formas pequenas (caras, manos): tinta plana, sin bandas
            dibuja(self.d, rgba, TINTA + (255,) if tinta else None, max(2, int(self.t * 0.6)) if tinta else 0)
            return
        pad = int(self.w * 0.03)
        x0, y0 = max(0, bb[0] - pad), max(0, bb[1] - pad)
        x1, y1 = min(self.w, bb[2] + pad), min(self.h, bb[3] + pad)
        mc = m.crop((x0, y0, x1, y1))
        if not grafica:
            sombra = mc.filter(ImageFilter.GaussianBlur(self.w * 0.008)).point(lambda v: int(v * 0.28))
            self.im.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", mc.size, (10, 12, 30)).split(), sombra)),
                                    (x0, y0 + int(self.w * 0.006)))
        hh = max(1, bb[3] - bb[1])
        grad = Image.linear_gradient("L").resize((1, hh))
        if grafica:                                  # luz dura desde arriba: la parte baja cae a negro al reducir tintas
            grad = grad.point(lambda v: int(255 * max(0.0, (v / 255 - 0.35) / 0.65) ** 1.5))
            claro, oscuro = _mezcla(rgba[:3], (255, 255, 255), 0.12), _mezcla(rgba[:3], (0, 0, 0), 0.75)
        else:
            claro, oscuro = _mezcla(rgba[:3], (255, 255, 255), 0.30), _mezcla(rgba[:3], (0, 0, 20), 0.28)
        col = Image.merge("RGB", [grad.point(lambda v, a=claro[k], b=oscuro[k]: int(a + (b - a) * v / 255)) for k in range(3)])
        relleno = Image.new("RGB", mc.size, rgba[:3])
        relleno.paste(col.resize((mc.width, hh)), (0, bb[1] - y0))
        self.im.paste(relleno, (x0, y0), mc)
        if grafica and tinta:                        # contorno fino de tinta
            dibuja(self.d, None, TINTA + (255,), max(2, int(self.t * 0.6)))
            return
        borde = ImageChops.subtract(mc, ImageChops.offset(mc, 0, int(self.w * 0.004))).filter(ImageFilter.GaussianBlur(2))
        self.im.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", mc.size, (255, 255, 255)).split(),
                                                     borde.point(lambda v: int(v * 0.55)))), (x0, y0))
        self.d = ImageDraw.Draw(self.im)

    def poli(self, fill, *v, tinta=True, ancho=None):
        pts = self.pts(*v)
        self._forma(lambda d, f, o, w: d.polygon(pts, fill=f, outline=o, width=w), fill, tinta, ancho)

    def caja(self, fill, x0, y0, x1, y1, r=0.0, tinta=True, ancho=None):
        bb = [*self.p(x0, y0), *self.p(x1, y1)]
        self._forma(lambda d, f, o, w: d.rounded_rectangle(bb, radius=r * self.w, fill=f, outline=o, width=w),
                    fill, tinta, ancho)

    def elipse(self, fill, x0, y0, x1, y1, tinta=True, ancho=None):
        bb = [*self.p(x0, y0), *self.p(x1, y1)]
        self._forma(lambda d, f, o, w: d.ellipse(bb, fill=f, outline=o, width=w), fill, tinta, ancho)

    def linea(self, color, *v, ancho=None):
        self.d.line(self.pts(*v), fill=color + (255,) if len(color) == 3 else color, width=ancho or self.t, joint="curve")

    def degradado(self, arriba, abajo, y0=0.0, y1=1.0):
        a, b = int(y0 * self.h), int(y1 * self.h)
        for y in range(a, b):
            u = (y - a) / max(1, b - a - 1)
            self.d.line([(0, y), (self.w, y)], fill=tuple(int(arriba[i] + (abajo[i] - arriba[i]) * u) for i in range(3)) + (255,))

    def trama(self, color, x0=0.0, y0=0.0, x1=1.0, y1=1.0, paso=0.035, crece="abajo", maximo=0.42):
        """Tramado de puntos de comic: puntos que crecen hacia un lado (solo en el estilo comic)."""
        if self.estilo != "comic":
            return
        s = paso * self.w
        capa = Image.new("RGBA", (self.w, self.h))
        dc = ImageDraw.Draw(capa)
        fila = 0
        y = y0 * self.h
        while y < y1 * self.h:
            x = x0 * self.w + (s / 2 if fila % 2 else 0)
            while x < x1 * self.w:
                if crece == "abajo":
                    u = (y - y0 * self.h) / max(1, (y1 - y0) * self.h)
                elif crece == "arriba":
                    u = 1 - (y - y0 * self.h) / max(1, (y1 - y0) * self.h)
                else:
                    u = (x - x0 * self.w) / max(1, (x1 - x0) * self.w)
                r = s * maximo * u
                if r > 0.6:
                    dc.ellipse([x - r, y - r, x + r, y + r], fill=color)
                x += s
            y += s * 0.87
            fila += 1
        self.im.alpha_composite(capa)

    def rafaga(self, color, cx, cy, n=28, r0=0.12, r1=1.2, grosor=0.018):
        """Lineas de accion radiales (cuñas) desde un punto (en 3d no: rompen el volumen)."""
        if self.estilo == "3d":
            return
        for k in range(n):
            a = 2 * math.pi * k / n + (0.07 if k % 2 else 0)
            g = grosor * (1.4 if k % 3 == 0 else 1.0)
            pa = (cx + math.cos(a - g) * r0, cy + math.sin(a - g) * r0 * self.w / self.h)
            pb = (cx + math.cos(a + g) * r0, cy + math.sin(a + g) * r0 * self.w / self.h)
            pc = (cx + math.cos(a) * r1, cy + math.sin(a) * r1 * self.w / self.h)
            self.d.polygon([self.p(*pa), self.p(*pb), self.p(*pc)], fill=color)

    def estrella(self, fill, cx, cy, r, puntas=10, interior=0.55, giro=0.0, tinta=True):
        v = []
        for k in range(puntas * 2):
            a = math.pi * k / puntas + giro
            rr = r if k % 2 == 0 else r * interior
            v += [cx + math.cos(a) * rr, cy + math.sin(a) * rr * self.w / self.h]
        self.poli(fill, *v, tinta=tinta)

    def rota(self, cx, cy, ang, *v):
        """Puntos (x, y) normalizados girados ang grados alrededor de (cx, cy), corrigiendo la proporcion."""
        a = math.radians(ang)
        r = self.w / self.h
        out = []
        for i in range(0, len(v), 2):
            dx, dy = (v[i] - cx) * r, v[i + 1] - cy
            out += [cx + (dx * math.cos(a) - dy * math.sin(a)) / r, cy + dx * math.sin(a) + dy * math.cos(a)]
        return out

    def final(self, w, h):
        if self.estilo == "grafica":                  # se reduce a las tintas de la paleta, sin tramado
            pal = Image.new("P", (1, 1))
            pal.putpalette([c for col in PALETA_G for c in col] + [0] * (768 - 3 * len(PALETA_G)))
            t = self.im.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE)
            return t.convert("RGBA").resize((w, h), Image.LANCZOS)
        if self.estilo == "pixel":                    # 6 px de pantalla por pixel y paleta de 24 colores
            peq = self.im.convert("RGB").resize((w // 6, h // 6), Image.BOX).quantize(24, method=Image.Quantize.MEDIANCUT)
            return peq.convert("RGBA").resize((w, h), Image.NEAREST)
        return self.im.resize((w, h), Image.LANCZOS)


# ------------------------------------------------------------------ personaje generico
def persona(L, cx, base, alto, traje=TRAJE, corbata=(200, 16, 46), pelo=(52, 40, 34), boca="habla", brazos="atril",
            gafas=False):
    """Figura generica de medio cuerpo (no representa a nadie): cabeza, pelo, traje y corbata."""
    cab = alto * 0.36
    w = alto * 0.62 * L.h / L.w
    # cuerpo
    L.poli(traje, cx - w * 0.5, base, cx - w * 0.42, base - alto * 0.5, cx - w * 0.15, base - alto * 0.6,
           cx + w * 0.15, base - alto * 0.6, cx + w * 0.42, base - alto * 0.5, cx + w * 0.5, base)
    L.poli((245, 247, 250), cx - w * 0.13, base - alto * 0.6, cx + w * 0.13, base - alto * 0.6, cx, base - alto * 0.38)
    L.poli(corbata, cx - w * 0.04, base - alto * 0.57, cx + w * 0.04, base - alto * 0.57, cx + w * 0.06, base - alto * 0.3,
           cx, base - alto * 0.24, cx - w * 0.06, base - alto * 0.3)
    # cuello y cabeza
    cw = cab * L.h / L.w * 0.78
    L.caja(PIEL_SOMBRA, cx - cw * 0.22, base - alto * 0.66, cx + cw * 0.22, base - alto * 0.56, tinta=False)
    cy = base - alto * 0.66 - cab * 0.5
    L.elipse(PIEL, cx - cw * 0.5, cy - cab * 0.55, cx + cw * 0.5, cy + cab * 0.5)
    L.elipse(PIEL, cx - cw * 0.6, cy - cab * 0.08, cx - cw * 0.42, cy + cab * 0.16)
    L.elipse(PIEL, cx + cw * 0.42, cy - cab * 0.08, cx + cw * 0.6, cy + cab * 0.16)
    L.poli(pelo, cx - cw * 0.52, cy - cab * 0.05, cx - cw * 0.5, cy - cab * 0.42, cx - cw * 0.2, cy - cab * 0.6,
           cx + cw * 0.3, cy - cab * 0.58, cx + cw * 0.52, cy - cab * 0.32, cx + cw * 0.5, cy - cab * 0.1,
           cx + cw * 0.3, cy - cab * 0.3, cx - cw * 0.3, cy - cab * 0.28)
    # cara: seria, neutra
    for s in (-1, 1):
        L.elipse(TINTA, cx + s * cw * 0.2 - cw * 0.05, cy - cab * 0.02, cx + s * cw * 0.2 + cw * 0.05, cy + cab * 0.1, tinta=False)
        L.linea(TINTA, cx + s * cw * 0.1, cy - cab * 0.13, cx + s * cw * 0.32, cy - cab * 0.11, ancho=int(L.t * 1.2))
        if gafas:
            L.elipse((0, 0, 0, 0), cx + s * cw * 0.2 - cw * 0.13, cy - cab * 0.08, cx + s * cw * 0.2 + cw * 0.13, cy + cab * 0.16)
    L.linea(PIEL_SOMBRA, cx, cy + cab * 0.02, cx - cw * 0.04, cy + cab * 0.2, cx + cw * 0.03, cy + cab * 0.22, ancho=L.t)
    L.boca = (cx + cw * 0.15, cy + cab * 0.33)          # hacia aqui apunta el bocadillo
    if boca == "habla":
        L.elipse((120, 40, 50), cx - cw * 0.12, cy + cab * 0.28, cx + cw * 0.12, cy + cab * 0.38)
    else:
        L.linea(TINTA, cx - cw * 0.12, cy + cab * 0.33, cx + cw * 0.12, cy + cab * 0.33)


# ------------------------------------------------------------------ escenas
def esc_tren(L, sobrio):
    L.degradado((120, 190, 235), (200, 230, 248), 0, 0.62)
    L.degradado((150, 150, 160), (110, 110, 122), 0.62, 1)
    if not sobrio:
        L.rafaga((255, 255, 255, 150), 0.86, 0.5, n=36, r0=0.05)
    # via que se pierde hacia el fondo
    L.poli((90, 84, 80), -0.1, 1.0, 0.55, 1.0, 0.86, 0.6, 0.82, 0.6, tinta=False)
    for k in range(9):
        u = k / 9
        y = 1.0 - (0.4 * (1 - (1 - u) ** 2))
        x0 = -0.1 + (0.82 + 0.0 - (-0.1)) * (1 - (1 - u) ** 2)
        L.linea((60, 52, 48), x0 - 0.02, y, x0 + 0.42 * (1 - u) + 0.02, y, ancho=int(L.t * (1.4 - u)))
    L.linea((200, 200, 210), -0.05, 1.0, 0.83, 0.6, ancho=int(L.t * 1.6))
    L.linea((200, 200, 210), 0.5, 1.0, 0.855, 0.6, ancho=int(L.t * 1.6))
    # tren de alta velocidad en tres cuartos, acercandose
    L.poli((248, 248, 250), -0.02, 0.24, 0.30, 0.30, 0.52, 0.40, 0.66, 0.55, 0.70, 0.66, 0.62, 0.74, 0.30, 0.86, -0.02, 0.96)
    L.poli((200, 16, 46), -0.02, 0.70, 0.30, 0.66, 0.62, 0.66, 0.70, 0.66, 0.66, 0.70, 0.30, 0.76, -0.02, 0.82, tinta=False)
    L.linea(TINTA, -0.02, 0.70, 0.30, 0.66, 0.70, 0.66)
    L.poli((36, 48, 70), 0.42, 0.41, 0.55, 0.45, 0.65, 0.56, 0.50, 0.55)                       # parabrisas
    L.poli((255, 255, 255, 120), 0.45, 0.42, 0.50, 0.435, 0.56, 0.52, 0.51, 0.52, tinta=False)
    for k in range(5):                                                                        # ventanillas
        x = 0.02 + k * 0.075
        L.caja((36, 48, 70), x, 0.37 + k * 0.012, x + 0.05, 0.43 + k * 0.012, r=0.008)
    L.elipse((255, 236, 140), 0.60, 0.62, 0.65, 0.65)                                          # faro
    L.linea(TINTA, 0.10, 0.27, 0.16, 0.16, 0.24, 0.12)                                        # pantografo
    L.linea(TINTA, 0.16, 0.16, 0.26, 0.20)
    L.linea((60, 60, 70), -0.1, 0.10, 1.1, 0.06, ancho=L.t)                                   # catenaria


def esc_juzgado(L, sobrio):
    L.degradado((150, 96, 60), (110, 68, 42))
    for k in range(9):                                                                        # paneles de madera
        L.linea((95, 58, 36), k / 8, 0, k / 8, 0.62, ancho=int(L.t * 0.8))
    L.trama((70, 40, 24, 120), 0, 0, 1, 0.62, crece="arriba")
    # balanza al fondo
    L.linea((230, 190, 80), 0.80, 0.08, 0.80, 0.45, ancho=L.t * 2)
    L.linea((230, 190, 80), 0.66, 0.16, 0.94, 0.16, ancho=L.t * 2)
    for x in (0.66, 0.94):
        L.linea((230, 190, 80), x, 0.16, x - 0.05, 0.30, ancho=L.t)
        L.linea((230, 190, 80), x, 0.16, x + 0.05, 0.30, ancho=L.t)
        L.poli((240, 200, 90), x - 0.07, 0.30, x + 0.07, 0.30, x + 0.04, 0.35, x - 0.04, 0.35)
    # estrado
    L.poli((90, 52, 30), -0.05, 0.62, 1.05, 0.62, 1.05, 1.05, -0.05, 1.05)
    L.poli((122, 74, 44), -0.05, 0.58, 1.05, 0.58, 1.05, 0.66, -0.05, 0.66)
    # taco y mazo golpeando
    L.elipse((70, 40, 24), 0.33, 0.56, 0.63, 0.64)
    L.caja((150, 92, 52), 0.35, 0.52, 0.61, 0.60, r=0.02)
    if not sobrio:
        for a in range(-70, 80, 25):
            r = math.radians(a - 90)
            L.linea((255, 236, 140), 0.48 + math.cos(r) * 0.17, 0.5 + math.sin(r) * 0.17 * L.w / L.h,
                    0.48 + math.cos(r) * 0.25, 0.5 + math.sin(r) * 0.25 * L.w / L.h, ancho=L.t * 2)
    mango = L.rota(0.5, 0.42, -28, 0.50, 0.40, 0.88, 0.40, 0.88, 0.45, 0.50, 0.45)
    L.poli((110, 64, 36), *mango)
    cabeza = L.rota(0.5, 0.42, -28, 0.36, 0.30, 0.56, 0.30, 0.56, 0.52, 0.36, 0.52)
    L.poli((128, 76, 42), *cabeza)
    for x in (0.39, 0.53):
        banda = L.rota(0.5, 0.42, -28, x, 0.30, x + 0.025, 0.30, x + 0.025, 0.52, x, 0.52)
        L.poli((230, 190, 80), *banda, tinta=False)


def esc_policia(L, sobrio):
    L.degradado((18, 26, 52), (40, 52, 90))
    if not sobrio:                                                                            # destellos de sirena
        for (cx, col) in ((0.36, (60, 120, 255)), (0.56, (235, 50, 60))):
            g = Image.new("RGBA", L.im.size)
            ImageDraw.Draw(g).ellipse([*L.p(cx - 0.3, 0.05), *L.p(cx + 0.3, 0.75)], fill=col + (110,))
            L.im.alpha_composite(g.filter(ImageFilter.GaussianBlur(L.w * 0.05)))
            L.d = ImageDraw.Draw(L.im)
    L.trama((255, 255, 255, 40), 0, 0, 1, 0.5, crece="arriba", maximo=0.25)
    L.poli((70, 72, 84), -0.05, 0.78, 1.05, 0.78, 1.05, 1.05, -0.05, 1.05, tinta=False)     # calzada
    # coche patrulla de lado
    L.poli((248, 248, 250), 0.08, 0.72, 0.12, 0.55, 0.30, 0.52, 0.40, 0.36, 0.66, 0.36, 0.76, 0.52, 0.90, 0.56, 0.93, 0.72)
    L.poli((36, 48, 70), 0.42, 0.40, 0.53, 0.40, 0.53, 0.52, 0.34, 0.52)
    L.poli((36, 48, 70), 0.56, 0.40, 0.65, 0.40, 0.73, 0.52, 0.56, 0.52)
    L.poli((30, 80, 190), 0.09, 0.62, 0.92, 0.62, 0.92, 0.67, 0.085, 0.67, tinta=False)
    L.caja((60, 120, 255), 0.45, 0.31, 0.52, 0.36, r=0.01)
    L.caja((235, 50, 60), 0.53, 0.31, 0.60, 0.36, r=0.01)
    for x in (0.25, 0.75):
        L.elipse(TINTA, x - 0.07, 0.64, x + 0.07, 0.84)
        L.elipse((170, 170, 180), x - 0.035, 0.70, x + 0.035, 0.78)
    # cinta de cordon policial en primer plano
    cinta = (-0.05, 0.86, 1.05, 0.74, 1.05, 0.82, -0.05, 0.94)
    L.poli((255, 214, 0), *cinta)
    f = fuente("Bangers-Regular.ttf", int(L.h * 0.055))
    capa = Image.new("RGBA", L.im.size)
    dc = ImageDraw.Draw(capa)
    x = 0.0
    while x < 1.0:
        dc.text(L.p(x, 0.875 - x * 0.11), "POLICÍA", font=f, fill=TINTA + (255,), anchor="lm")
        x += 0.24
    L.im.alpha_composite(capa.rotate(0, resample=Image.BICUBIC))


def esc_atril(L, sobrio):
    L.degradado((40, 70, 140), (24, 44, 96))
    L.trama((255, 255, 255, 45), 0, 0, 1, 0.8, crece="arriba", maximo=0.3)
    if not sobrio:
        for (x, y, r) in ((0.10, 0.18, 0.07), (0.90, 0.25, 0.06), (0.82, 0.10, 0.04)):        # flashes
            L.estrella((255, 255, 255), x, y, r, puntas=8, interior=0.3, tinta=False)
    persona(L, 0.5, 0.95, 0.85)
    # atril con microfonos
    L.poli((220, 224, 232), 0.28, 0.66, 0.72, 0.66, 0.68, 1.05, 0.32, 1.05)
    L.poli((190, 196, 208), 0.26, 0.62, 0.74, 0.62, 0.72, 0.68, 0.28, 0.68)
    L.elipse((200, 16, 46), 0.45, 0.76, 0.55, 0.90)
    for k, (x, ang) in enumerate(((0.40, -18), (0.46, -6), (0.54, 6), (0.60, 18))):
        top = (0.5 + (x - 0.5) * 0.35, 0.50)
        L.linea(TINTA, x, 0.64, *top, ancho=L.t)
        L.elipse((40, 40, 46), top[0] - 0.018, top[1] - 0.03, top[0] + 0.018, top[1] + 0.02)


def esc_movil(L, sobrio):
    L.degradado((90, 60, 170), (40, 150, 170))
    L.trama((255, 255, 255, 50), 0, 0, 1, 1, crece="lado", maximo=0.3)
    if not sobrio:
        L.rafaga((255, 255, 255, 70), 0.5, 0.55, n=24, r0=0.2)
    # mano con movil
    L.poli(PIEL, 0.30, 1.05, 0.36, 0.78, 0.44, 0.70, 0.62, 0.70, 0.70, 0.80, 0.72, 1.05)
    L.caja((24, 24, 30), 0.36, 0.14, 0.64, 0.92, r=0.03)
    L.caja((235, 240, 250), 0.38, 0.19, 0.62, 0.86, r=0.012, tinta=False)
    for k, (x0, x1, col) in enumerate(((0.40, 0.54, (220, 226, 236)), (0.46, 0.60, (120, 200, 140)),
                                       (0.40, 0.56, (220, 226, 236)), (0.44, 0.60, (120, 200, 140)))):
        y = 0.24 + k * 0.14
        L.caja(col, x0, y, x1, y + 0.09, r=0.02, ancho=max(1, L.t // 2))
        for j in range(2):
            L.linea((90, 96, 110), x0 + 0.015, y + 0.03 + j * 0.03, x1 - 0.03 - j * 0.03, y + 0.03 + j * 0.03,
                    ancho=max(1, L.t // 2))
    L.poli(PIEL, 0.34, 0.78, 0.38, 0.66, 0.42, 0.66, 0.42, 0.80)                             # pulgar
    # notificaciones que salen del movil: me gusta, compartir, reproducir, comentario
    for (x, y, tipo) in ((0.17, 0.30, "corazon"), (0.83, 0.24, "compartir"), (0.85, 0.60, "play"), (0.15, 0.64, "comenta")):
        col = {"corazon": (255, 70, 90), "compartir": (255, 214, 0), "play": (255, 255, 255), "comenta": (120, 200, 140)}[tipo]
        L.elipse(col, x - 0.075, y - 0.075 * L.w / L.h, x + 0.075, y + 0.075 * L.w / L.h)
        r = 0.035
        ry = r * L.w / L.h
        if tipo == "corazon":
            L.elipse((255, 255, 255), x - r, y - ry * 0.7, x, y + ry * 0.2, tinta=False)
            L.elipse((255, 255, 255), x, y - ry * 0.7, x + r, y + ry * 0.2, tinta=False)
            L.poli((255, 255, 255), x - r * 0.97, y - ry * 0.1, x + r * 0.97, y - ry * 0.1, x, y + ry * 0.9, tinta=False)
        elif tipo == "compartir":
            L.poli(TINTA, x - r, y + ry * 0.6, x - r * 0.2, y - ry * 0.3, x - r * 0.2, y - ry * 0.75, x + r, y - ry * 0.05,
                   x - r * 0.2, y + ry * 0.65, x - r * 0.2, y + ry * 0.2, tinta=False)
        elif tipo == "play":
            L.poli((200, 16, 46), x - r * 0.6, y - ry * 0.8, x + r * 0.9, y, x - r * 0.6, y + ry * 0.8, tinta=False)
        else:
            L.caja((255, 255, 255), x - r, y - ry * 0.7, x + r, y + ry * 0.4, r=0.01, tinta=False)
            L.poli((255, 255, 255), x - r * 0.5, y + ry * 0.35, x - r * 0.1, y + ry * 0.35, x - r * 0.6, y + ry * 0.9, tinta=False)


def esc_protesta(L, sobrio):
    """Concentracion generica: edificios al fondo, gente de espaldas y pancartas sin lemas (no se inventan consignas)."""
    L.degradado((250, 200, 120), (245, 150, 110), 0, 0.7)
    for (x0, x1, top, col) in ((-0.02, 0.18, 0.18, (200, 120, 110)), (0.16, 0.34, 0.08, (220, 150, 120)),
                               (0.32, 0.52, 0.22, (190, 110, 100)), (0.50, 0.70, 0.12, (215, 140, 115)),
                               (0.68, 0.86, 0.26, (195, 118, 104)), (0.84, 1.02, 0.15, (210, 135, 112))):
        L.caja(col, x0, top, x1, 0.8, ancho=max(1, L.t // 2))
        for fy in range(3):
            for fx in range(2):
                wx = x0 + 0.03 + fx * (x1 - x0 - 0.06) / 1.6
                wy = top + 0.05 + fy * 0.11
                if wy + 0.06 < 0.7:
                    L.caja((255, 230, 170), wx, wy, wx + 0.04, wy + 0.06, tinta=False)
    if not sobrio:
        L.trama((255, 255, 255, 60), 0, 0, 1, 0.5, crece="arriba", maximo=0.3)
    # pancartas en alto
    for (x, y, ang, col) in ((0.22, 0.30, -8, (255, 255, 255)), (0.55, 0.22, 5, (255, 214, 0)), (0.80, 0.34, -4, (255, 255, 255))):
        L.linea(TINTA, x, y + 0.12, x + 0.01, 0.75, ancho=L.t)
        p = L.rota(x, y, ang, x - 0.11, y - 0.08, x + 0.11, y - 0.08, x + 0.11, y + 0.12, x - 0.11, y + 0.12)
        L.poli(col, *p)
        for j in range(2):
            q = L.rota(x, y, ang, x - 0.07, y - 0.02 + j * 0.08, x + 0.07, y - 0.02 + j * 0.08)
            L.linea((200, 16, 46) if col != (255, 255, 255) else (40, 70, 140), *q, ancho=L.t * 2)
    # multitud de espaldas (cabezas y hombros)
    cols = [(40, 52, 86), (120, 60, 70), (60, 110, 90), (200, 16, 46), (70, 70, 80), (150, 120, 60)]
    for fila, (y, esc) in enumerate(((0.80, 0.8), (0.92, 1.0), (1.04, 1.2))):
        n = 7 - fila
        for k in range(n + 1):
            cx = (k + (0.5 if fila % 2 else 0)) / n
            w = 0.09 * esc
            hh = w * L.w / L.h
            col = cols[(k * 3 + fila) % len(cols)]
            L.elipse(col, cx - w, y - hh * 0.55, cx + w, y + hh * 1.2)
            L.elipse((60, 44, 36) if (k + fila) % 3 else (150, 110, 70), cx - w * 0.45, y - hh * 1.15, cx + w * 0.45, y - hh * 0.25)


ESCENAS = {"tren": esc_tren, "juzgado": esc_juzgado, "policia": esc_policia, "atril": esc_atril, "movil": esc_movil, "protesta": esc_protesta}


# ------------------------------------------------------------------ montaje de la vineta
def _lineas(d, texto, f, ancho):
    out, cur = [], ""
    for w in texto.split():
        prueba = (cur + " " + w).strip()
        if d.textlength(prueba, font=f) <= ancho:
            cur = prueba
        else:
            out.append(cur)
            cur = w
    return out + [cur]


def _redondea(im, r, arriba=True, abajo=True):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=r, fill=255)
    if not arriba:
        ImageDraw.Draw(m).rectangle([0, 0, im.width, r], fill=255)
    if not abajo:
        ImageDraw.Draw(m).rectangle([0, im.height - r, im.width, im.height], fill=255)
    out = im.copy()
    out.putalpha(ImageChops.multiply(im.getchannel("A"), m))
    return out


# cartela de cada estilo: (tipografia, tamano relativo, mayusculas, color de fondo, color de texto)
CARTELAS = {"comic": ("ComicNeue-Bold.ttf", 0.055, True, CARTELA, TINTA),
            "plano": ("Inter-Bold.ttf", 0.050, False, (255, 255, 255), (24, 30, 48)),
            "3d": ("Inter-Black.ttf", 0.050, False, (24, 36, 70), (255, 255, 255)),
            "pixel": ("VT323-Regular.ttf", 0.068, True, (16, 16, 24), (255, 230, 90))}


def _bocadillo(im, texto, f, ancho_max, ancla, arriba_izq=True):
    """Globo de dialogo blanco con contorno de tinta y rabito hacia 'ancla' (px). Devuelve la caja usada."""
    d = ImageDraw.Draw(im)
    lin = _lineas(d, texto, f, ancho_max)
    al = int(f.size * 1.12)
    tw = max(d.textlength(l, font=f) for l in lin)
    w, h = int(tw * 1.38 + f.size), int(al * len(lin) * 1.45 + f.size * 0.6)
    x0 = int(im.width * 0.03) if arriba_izq else int(im.width - w - im.width * 0.03)
    y0 = int(im.height * 0.05)
    cx, cy = x0 + w / 2, y0 + h / 2
    # rabito: triangulo desde el borde inferior del globo hacia quien habla
    ax, ay = ancla
    bx = min(max(ax, x0 + w * 0.25), x0 + w * 0.75)
    d.polygon([(bx - f.size * 0.6, y0 + h - 6), (bx + f.size * 0.6, y0 + h - 6), (ax, min(ay, y0 + h + f.size * 2.4))],
              fill=(255, 255, 255, 255), outline=TINTA + (255,), width=3)
    d.ellipse([x0, y0, x0 + w, y0 + h], fill=(255, 255, 255, 255), outline=TINTA + (255,), width=3)
    d.polygon([(bx - f.size * 0.6 + 3, y0 + h - 9), (bx + f.size * 0.6 - 3, y0 + h - 9),
               (ax, min(ay, y0 + h + f.size * 2.4) - 5)], fill=(255, 255, 255, 255))
    y = cy - al * len(lin) / 2
    for l in lin:
        d.text((cx, y + al / 2), l, font=f, fill=TINTA + (255,), anchor="mm")
        y += al
    return (x0, y0, x0 + w, y0 + h)


def _cartela_dentro(im, texto, f, ancho_max, abajo=False):
    """Recuadro de narracion rectangular dentro de la vineta (arriba a la izquierda o abajo)."""
    d = ImageDraw.Draw(im)
    lin = _lineas(d, texto, f, ancho_max)
    al = int(f.size * 1.14)
    tw = max(d.textlength(l, font=f) for l in lin)
    w, h = int(tw + f.size * 1.0), int(al * len(lin) + f.size * 0.7)
    x0 = int(im.width * 0.03)
    y0 = int(im.height - h - im.height * 0.04) if abajo else int(im.height * 0.04)
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=(248, 240, 222, 255), outline=TINTA + (255,), width=3)
    y = y0 + f.size * 0.35
    for l in lin:
        d.text((x0 + f.size * 0.5, y), l, font=f, fill=TINTA + (255,))
        y += al


def vineta_grafica(escena, texto, ancho=520, sobrio=False, fuente_txt=None, giro=0.0, proporcion=0.68):
    """Novela grafica: el dato va dentro de la ilustracion. Si es una cita («...»), en bocadillo hacia quien habla
    y el autor en un recuadro de narracion; si no, en el recuadro de narracion."""
    import re
    alto = int(ancho * proporcion)
    cita = re.match(r"^\s*([^«:]{1,60}):\s*«(.+)»\s*$", texto)
    f = fuente("ComicNeue-Bold.ttf", max(16, int(ancho * 0.05)))
    if cita:                                         # encuadre de cine: quien habla a la derecha, el globo a la izquierda
        sub = int(ancho * 0.64)
        L = Lienzo(sub, alto, (255, 255, 255), "grafica")
        L.boca = None
        ESCENAS[escena](L, sobrio)
        parte = L.final(sub, alto)
        ilus = Image.new("RGBA", (ancho, alto), PALETA_G[1] + (255,))
        ilus.paste(parte.crop((0, 0, 1, alto)).resize((ancho - sub, alto)), (0, 0))   # el fondo se prolonga
        ilus.paste(parte, (ancho - sub, 0))
        ancla = ((ancho - sub) + L.boca[0] * sub, L.boca[1] * alto) if L.boca else (ancho * 0.55, alto * 0.45)
        _bocadillo(ilus, cita.group(2).upper(), f, ancho * 0.36, ancla, arriba_izq=True)
        _cartela_dentro(ilus, cita.group(1).upper(), f, ancho * 0.4, abajo=True)
    else:
        L = Lienzo(ancho, alto, (255, 255, 255), "grafica")
        ESCENAS[escena](L, sobrio)
        ilus = L.final(ancho, alto)
        _cartela_dentro(ilus, texto.upper(), f, ancho * 0.84, abajo=True)
    if sobrio:
        from PIL import ImageEnhance
        ilus = ImageEnhance.Color(ilus).enhance(0.25)
    if fuente_txt:
        ff = fuente("Inter-SemiBold.ttf", max(13, int(ancho * 0.026)))
        ImageDraw.Draw(ilus).text((ancho - 12, 10), fuente_txt, font=ff, fill=(248, 240, 222, 255), anchor="rt",
                                  stroke_width=3, stroke_fill=TINTA + (255,))
    m = 10                                           # medianil blanco y marco de tinta, como una pagina impresa
    out = Image.new("RGBA", (ancho + 2 * m + 12, alto + 2 * m + 12))
    do = ImageDraw.Draw(out)
    do.rectangle([8, 10, ancho + 2 * m + 8, alto + 2 * m + 10], fill=(0, 0, 0, 80))
    do.rectangle([0, 0, ancho + 2 * m, alto + 2 * m], fill=(252, 250, 244, 255))
    out.alpha_composite(ilus, (m, m))
    do.rectangle([m, m, m + ancho - 1, m + alto - 1], outline=TINTA + (255,), width=4)
    if giro:
        out = out.rotate(giro, resample=Image.BICUBIC, expand=True)
    return out


def tono_de(im):
    """Color de la franja a juego con la ilustracion: el matiz del tono con color mas presente en la vineta, llevado a
    una version intensa y algo oscura (como las cartelas de la novela grafica), con texto crema encima."""
    import colorsys
    peq = im.convert("RGB").resize((64, 64), Image.BILINEAR).quantize(8, method=Image.Quantize.MEDIANCUT)
    pal = peq.getpalette()
    total = 64 * 64
    mejor, puntos = None, -1.0
    for n, i in peq.getcolors():
        c = pal[i * 3:i * 3 + 3]
        h, sat, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
        if v < 0.18 or (sat < 0.12 and v > 0.85):          # casi negro o casi blanco: no dan color a la franja
            continue
        p = (n / total) * (0.25 + sat)
        if p > puntos:
            mejor, puntos = (h, sat, v), p
    h, sat, v = mejor or (0.6, 0.4, 0.4)
    r, g, b = colorsys.hsv_to_rgb(h, min(0.75, max(0.42, sat * 1.25)), 0.40)
    return (int(r * 255), int(g * 255), int(b * 255)), (248, 240, 222)


def vineta(escena, texto, ancho=520, sobrio=False, fuente_txt=None, giro=0.0, proporcion=0.58, estilo="comic",
           imagen=None):
    """Vineta lista para pegar en el tablero: el dato arriba (cartela del estilo) y la ilustracion entera debajo.
    imagen: ilustracion ya hecha (por ejemplo, de ia_vinetas.ilustra); si no, se dibuja la escena del catalogo."""
    if estilo == "grafica":
        return vineta_grafica(escena, texto, ancho, sobrio, fuente_txt, giro)
    tipo, rel, mayus, fondo_c, tinta_c = CARTELAS[estilo]
    if sobrio:
        fondo_c = {"comic": (242, 238, 226), "plano": (245, 245, 245), "3d": (50, 54, 64), "pixel": (30, 30, 34)}[estilo]
        tinta_c = (230, 230, 230) if estilo in ("3d", "pixel") else TINTA
    f = fuente(tipo, max(14, int(ancho * rel)))
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    margen = f.size * (0.6 if estilo != "plano" else 1.3)
    lin = _lineas(d0, texto.upper() if mayus else texto, f, ancho - margen - f.size * 0.7)
    alto_l = int(f.size * (1.16 if estilo != "pixel" else 1.0))
    hc = alto_l * len(lin) + int(f.size * (0.75 if estilo != "pixel" else 0.6))
    alto_i = int(ancho * proporcion)
    if imagen is not None:
        from PIL import ImageOps
        ilus = ImageOps.fit(imagen.convert("RGB"), (ancho, alto_i), Image.LANCZOS).convert("RGBA")
        if estilo == "comic":                        # franja del color de la propia vineta
            fondo_c, tinta_c = tono_de(ilus)
    else:
        L = Lienzo(ancho, alto_i, (255, 255, 255), estilo)
        ESCENAS[escena](L, sobrio)
        if sobrio:                                   # version apagada para tragedias
            from PIL import ImageEnhance
            L.im = ImageEnhance.Color(L.im).enhance(0.3)
        ilus = L.final(ancho, alto_i)
    if fuente_txt:
        ff = fuente("Inter-SemiBold.ttf", max(13, int(ancho * 0.027)))
        tw = d0.textlength(fuente_txt, font=ff)
        di = ImageDraw.Draw(ilus)
        if estilo == "comic":
            di.rectangle([ancho - tw - 24, alto_i - ff.size - 16, ancho, alto_i], fill=(255, 255, 255, 235))
            di.line([(ancho - tw - 24, alto_i - ff.size - 16), (ancho - tw - 24, alto_i)], fill=TINTA + (255,), width=2)
            di.line([(ancho - tw - 24, alto_i - ff.size - 16), (ancho, alto_i - ff.size - 16)], fill=TINTA + (255,), width=2)
        else:
            di.rounded_rectangle([ancho - tw - 34, alto_i - ff.size - 22, ancho - 10, alto_i - 10],
                                 radius=0 if estilo == "pixel" else (ff.size + 12) // 2, fill=(255, 255, 255, 225))
        di.text((ancho - 12 - (10 if estilo != "comic" else 0), alto_i - 8 - (8 if estilo != "comic" else 0)),
                fuente_txt, font=ff, fill=(60, 60, 70, 255), anchor="rb")
    panel = Image.new("RGBA", (ancho, hc + alto_i), fondo_c + (255,))
    dp = ImageDraw.Draw(panel)
    y = int(f.size * (0.36 if estilo != "pixel" else 0.25))
    x = f.size * 0.6
    if estilo == "plano":                            # barra de acento a la izquierda de la cartela
        dp.rounded_rectangle([f.size * 0.5, y, f.size * 0.5 + 6, y + alto_l * len(lin) - f.size * 0.15], radius=3,
                             fill=(200, 16, 46, 255))
        x = margen
    for l in lin:
        dp.text((x, y), l, font=f, fill=tinta_c + (255,))
        y += alto_l
    panel.alpha_composite(ilus, (0, hc))
    w, h = panel.size
    if estilo == "comic":
        dp.line([(0, hc), (ancho, hc)], fill=TINTA + (255,), width=4)
        m = 9
        out = Image.new("RGBA", (w + 2 * m + 12, h + 2 * m + 12))
        do = ImageDraw.Draw(out)
        do.rectangle([8, 10, w + 2 * m + 8, h + 2 * m + 10], fill=(0, 0, 0, 80))
        do.rectangle([0, 0, w + 2 * m, h + 2 * m], fill=(250, 250, 246, 255))
        out.alpha_composite(panel, (m, m))
        do.rectangle([m, m, m + w - 1, m + h - 1], outline=TINTA + (255,), width=4)
    elif estilo == "pixel":                          # marco de videojuego: negro, blanco y negro, en escalones
        b = 6
        out = Image.new("RGBA", (w + 6 * b, h + 6 * b), (0, 0, 0, 0))
        do = ImageDraw.Draw(out)
        do.rectangle([b, 0, w + 5 * b, h + 6 * b], fill=(16, 16, 24, 255))
        do.rectangle([0, b, w + 6 * b, h + 5 * b], fill=(16, 16, 24, 255))
        do.rectangle([b, b, w + 5 * b, h + 5 * b], fill=(255, 255, 255, 255))
        out.alpha_composite(panel, (3 * b, 3 * b))
        do.rectangle([3 * b, 3 * b + hc - b // 2, 3 * b + w, 3 * b + hc + b // 2], fill=(255, 255, 255, 255))
    else:                                            # plano y 3d: tarjeta redondeada con sombra suave
        r = 22 if estilo == "plano" else 30
        panel = _redondea(panel, r)
        sombra = Image.new("RGBA", (w + 60, h + 60))
        ImageDraw.Draw(sombra).rounded_rectangle([30, 34, w + 30, h + 34], radius=r,
                                                  fill=(0, 0, 0, 90 if estilo == "3d" else 55))
        out = sombra.filter(ImageFilter.GaussianBlur(14 if estilo == "3d" else 8))
        out.alpha_composite(panel, (30, 30 - (4 if estilo == "3d" else 0)))
        if estilo == "plano":
            ImageDraw.Draw(out).line([(30, 30 + hc), (30 + w, 30 + hc)], fill=(230, 232, 238, 255), width=2)
    if giro:
        out = out.rotate(giro, resample=Image.BICUBIC, expand=True)
    return out
