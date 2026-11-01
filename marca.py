"""GOLPE DE MARCA del largo horizontal: la pieza de 2,6 s entre el sumario de titulares y el primer bloque.

Esta coreografiado con la sintonia (musica.sintonia: arpegio de 0 a 0,75 s y golpe a los 0,9 s):
  0,00-0,42  barrido diagonal rojo-amarillo-azul que tapa el ultimo titular (con un whoosh);
  0,28-0,80  el cuadrado rojo del logo entra con rebote, durante el arpegio;
  0,58-0,90  el sobre cae en la ranura y aterriza justo en el golpe: pulso del logo, onda amarilla y destello;
  0,92-1,45  el nombre sale de detras del logo con el espaciado cerrandose; la linea amarilla se dibuja; entra la fecha;
  1,45-2,05  reposo con acercamiento lento;
  2,05-2,60  el logo y el nombre vuelan a su sitio en la cabecera del bloque mientras el fondo se retira y aparece el tablero:
             al terminar, coinciden con la cabecera y el corte no se nota.
Todo se dibuja a partir de vectores (sin reescalar mapas de bits pequenos) para que los bordes salgan limpios."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

import genera_video2 as G2
from genera_video2 import AN, AL, AMARILLO, BLANCO, ROJO, fuente

DUR = 2.6
GOLPE_T = 0.90                      # instante del golpe de la sintonia
AZUL = (12, 20, 38)
L = 230                             # lado del logo en reposo
TAM_NOMBRE = 112
GRIS = (200, 208, 222)
SLANT = 320                         # inclinacion de los barridos (como las franjas del fondo)

# cabecera de los bloques (genera_video2.capa_cabecera): logo de 46 en (100, 39) y nombre de 30 en (160, 62) "lm"
CAB_LOGO, CAB_NOMBRE, CAB_TAM = (100, 39, 46), (160, 62), 30


# ---------------------------------------------------------------- curvas
def _c(x):
    return min(max(x, 0.0), 1.0)


def sale_expo(x):
    x = _c(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def sale_cubica(x):
    return 1 - (1 - _c(x)) ** 3


def entra_sale(x):
    x = _c(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def rebote(x, s=1.9):
    x = _c(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def tramo(t, a, b):
    return _c((t - a) / (b - a))


# ---------------------------------------------------------------- piezas (se dibujan una vez, grandes)
def _logo_partes(tam):
    """Cuadrado con la urna (sin sobre) y el sobre aparte, dibujados a 4x con la geometria de genera_video2.logo."""
    k = 4
    T = tam * k
    u = lambda *v: [x * T / 100 for x in v]
    base = Image.new("RGBA", (T, T))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(u(0, 0, 100, 100), radius=T // 6, fill=ROJO + (255,))
    d.rounded_rectangle(u(22, 34, 78, 44), radius=T // 40, fill=BLANCO + (255,))     # tapa
    d.rounded_rectangle(u(39, 37.5, 61, 40.5), radius=T // 80, fill=ROJO + (255,))  # ranura
    d.rounded_rectangle(u(27, 46, 73, 82), radius=T // 25, fill=BLANCO + (255,))     # cuerpo
    d.rectangle(u(27, 70, 73, 74), fill=AMARILLO + (255,))                          # franja
    sobre = Image.new("RGBA", (T, T))
    d = ImageDraw.Draw(sobre)
    d.rectangle(u(41, 17, 59, 38), fill=AMARILLO + (255,))
    d.line(u(41, 17, 50, 25, 59, 17), fill=ROJO + (255,), width=max(1, T // 50))
    tapa = Image.new("L", (T, T))                                                    # lo que tapa al sobre al entrar
    ImageDraw.Draw(tapa).rectangle(u(0, 39, 100, 100), fill=255)
    return [x.resize((tam, tam), Image.LANCZOS) for x in (base, sobre)] + [tapa.resize((tam, tam), Image.LANCZOS)]


def _nombre(tam, color, espaciado=0.0):
    """El nombre del canal con espaciado extra (en fracciones de la altura), anclado a la izquierda y centrado en vertical."""
    f = fuente("Inter-Black.ttf", tam)
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    extra = espaciado * tam
    ancho = int(sum(d0.textlength(ch, font=f) for ch in G2.MARCA) + extra * len(G2.MARCA)) + 20
    h = int(tam * 1.5)
    im = Image.new("RGBA", (ancho, h))
    d = ImageDraw.Draw(im)
    if espaciado == 0:
        d.text((0, h / 2), G2.MARCA, font=f, fill=color + (255,), anchor="lm")
    else:
        x = 0.0
        for ch in G2.MARCA:
            d.text((x, h / 2), ch, font=f, fill=color + (255,), anchor="lm")
            x += d0.textlength(ch, font=f) + extra
    return im


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
         "diciembre"]


def _fecha(fecha):
    txt = " · ".join(x.strip() for x in fecha.upper().split(",", 1))
    f = fuente("Inter-SemiBold.ttf", 34)
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    extra = 5
    ancho = int(sum(d0.textlength(ch, font=f) + extra for ch in txt)) + 10
    im = Image.new("RGBA", (ancho, 50))
    d = ImageDraw.Draw(im)
    x = 0.0
    for ch in txt:
        d.text((x, 25), ch, font=f, fill=GRIS + (255,), anchor="lm")
        x += d0.textlength(ch, font=f) + extra
    return im


def _resplandor():
    """Luz suave detras del logo: da profundidad al fondo azul sin que se note el truco."""
    g = Image.new("L", (AN // 4, AL // 4))
    ImageDraw.Draw(g).ellipse([AN // 8 - 150, AL // 8 - 110, AN // 8 + 150, AL // 8 + 110], fill=255)
    g = g.filter(ImageFilter.GaussianBlur(60)).resize((AN, AL), Image.BICUBIC).point(lambda v: int(v * 0.33))
    luz = Image.new("RGBA", (AN, AL), (70, 110, 190, 0))
    luz.putalpha(g)
    vi = Image.new("L", (AN // 4, AL // 4), 0)
    ImageDraw.Draw(vi).ellipse([-120, -110, AN // 4 + 120, AL // 4 + 110], fill=255)
    vi = vi.filter(ImageFilter.GaussianBlur(50)).resize((AN, AL), Image.BICUBIC).point(lambda v: int((255 - v) * 0.7))
    sombra = Image.new("RGBA", (AN, AL), (0, 0, 0, 0))
    sombra.putalpha(vi)
    luz.alpha_composite(sombra)
    return luz


class Golpe:
    def __init__(self, fecha):
        self.base, self.sobre, _ = _logo_partes(L)
        self.nombre_fin = _nombre(TAM_NOMBRE, BLANCO)
        self.nombre_cab = _nombre(TAM_NOMBRE, AMARILLO)
        self.fecha = _fecha(fecha)
        self.luz = _resplandor()
        self.velo = Image.new("RGBA", (AN, AL), AZUL + (115,))
        b = Image.new("L", (300, 300))
        ImageDraw.Draw(b).ellipse([105, 105, 195, 195], fill=255)
        self.brillo = Image.merge("RGBA", (*Image.new("RGB", (300, 300), (255, 226, 140)).split(),
                                           b.filter(ImageFilter.GaussianBlur(30))))
        self._abiertos = {}
        # composicion centrada: logo + 44 px + nombre; la fecha debajo del nombre
        ancho = L + 44 + self.nombre_fin.width - 20
        self.lx = (AN - ancho) // 2
        self.ly = AL // 2 - L // 2 - 10
        self.nx = self.lx + L + 44
        self.ncy = self.ly + L * 0.40                       # centro vertical del nombre
        self.fy = self.ly + L * 0.40 + TAM_NOMBRE * 0.62 + 34

    def nombre_abierto(self, esp):
        k = round(esp, 3)
        if k not in self._abiertos:
            self._abiertos[k] = _nombre(TAM_NOMBRE, BLANCO, k)
        return self._abiertos[k]

    def fondo(self, t):
        fr = G2.fondo_marca(t * 0.6 + 5)
        fr.alpha_composite(self.velo)                     # franjas mas discretas que en la cabecera antigua
        fr.alpha_composite(self.luz)
        return fr

    def cuadro(self, tl, previo, siguiente):
        """previo: ultimo fotograma del sumario; siguiente: primer fotograma del bloque (los dos RGBA de AN x AL)."""
        fondo = self.fondo(tl)
        # ---- barrido de entrada: rojo, amarillo y azul, en diagonal de derecha a izquierda
        u = entra_sale(tramo(tl, 0.0, 0.42))
        if u < 1:
            fr = previo.copy()
            X = AN + 40 - (AN + SLANT + 300) * u
            capas = [(0, 70, ROJO), (70, 92, AMARILLO)]
            masc = Image.new("L", (AN, AL))
            ImageDraw.Draw(masc).polygon([(X + 92 + SLANT, 0), (AN + SLANT + 400, 0), (AN + SLANT + 400, AL), (X + 92, AL)], fill=255)
            fr.paste(fondo, (0, 0), masc)
            d = ImageDraw.Draw(fr)
            for a, b, col in capas:
                d.polygon([(X + a + SLANT, 0), (X + b + SLANT, 0), (X + b, AL), (X + a, AL)], fill=col + (255,))
        else:
            fr = fondo
        # ---- salida: el fondo se retira hacia la izquierda y deja ver el tablero
        v = entra_sale(tramo(tl, 2.05, 2.55))
        if v > 0:
            X = AN + 40 - (AN + SLANT + 300) * v
            masc = Image.new("L", (AN, AL))
            ImageDraw.Draw(masc).polygon([(X + SLANT, 0), (AN + SLANT + 400, 0), (AN + SLANT + 400, AL), (X, AL)], fill=255)
            fr.paste(siguiente, (0, 0), masc)
            ImageDraw.Draw(fr).polygon([(X - 14 + SLANT, 0), (X + SLANT, 0), (X, AL), (X - 14, AL)], fill=AMARILLO + (255,))
        # ---- composicion: acercamiento lento y vuelo a la cabecera al final
        vuelo = entra_sale(tramo(tl, 2.0, 2.58))
        empuje = 1 + 0.025 * tramo(tl, 0.9, 2.0)
        # logo
        s_in = rebote(tramo(tl, 0.28, 0.80))
        pulso = 1 + 0.07 * math.exp(-max(0.0, tl - GOLPE_T) / 0.09) * (tl >= GOLPE_T)
        esc = max(0.0, s_in) * pulso * empuje
        tam = L * (esc * (1 - vuelo) + (CAB_LOGO[2] / L) * vuelo)
        cx0, cy0 = self.lx + L / 2, self.ly + L / 2
        cx1, cy1 = CAB_LOGO[0] + CAB_LOGO[2] / 2, CAB_LOGO[1] + CAB_LOGO[2] / 2
        cx, cy = cx0 + (cx1 - cx0) * vuelo, cy0 + (cy1 - cy0) * vuelo
        if GOLPE_T <= tl < GOLPE_T + 0.5 and vuelo == 0:      # brillo calido detras del logo en el golpe
            q = (tl - GOLPE_T) / 0.5
            br = self.brillo.resize((int(L * 3.4 * (0.8 + 0.4 * q)),) * 2, Image.BILINEAR)
            G2.pega(fr, br, cx - br.width / 2, cy - br.height / 2, 0.6 * (1 - q) ** 2)
        if tam > 2:
            giro = -14 * (1 - sale_cubica(tramo(tl, 0.28, 0.75)))
            lg = self.base.copy()
            # sobre: cae desde arriba y entra en la ranura en el golpe (por detras de la tapa)
            caida = tramo(tl, 0.58, GOLPE_T) ** 2
            dy = int(-L * 0.75 * (1 - caida))
            if tl >= 0.58:
                capa = Image.new("RGBA", (L, int(L * 1.8)))
                sob = self.sobre.copy()
                capa.alpha_composite(sob, (0, int(L * 0.8) + dy))
                # lo que asoma por encima del cuadrado se ve; lo que queda por debajo de la ranura, no
                corte = Image.new("L", capa.size, 255)
                ImageDraw.Draw(corte).rectangle([0, int(L * 0.8) + int(L * 0.39), L, capa.height], fill=0)
                capa.putalpha(Image.composite(capa.getchannel("A"), Image.new("L", capa.size), corte))
                todo = Image.new("RGBA", capa.size)
                todo.alpha_composite(lg, (0, int(L * 0.8)))
                todo.alpha_composite(capa)
                lg, alto_extra = todo, int(L * 0.8)
            else:
                alto_extra = 0
            if giro:
                lg = lg.rotate(giro, resample=Image.BICUBIC, expand=False, center=(L / 2, alto_extra + L / 2))
            k = tam / L
            lg = lg.resize((max(1, int(lg.width * k)), max(1, int(lg.height * k))), Image.LANCZOS)
            G2.pega(fr, lg, cx - lg.width / 2, cy - tam / 2 - alto_extra * k, 1.0)
        # onda y destello del golpe
        if GOLPE_T <= tl < GOLPE_T + 0.38 and vuelo == 0:
            q = (tl - GOLPE_T) / 0.38
            r = L * (0.62 + 0.5 * sale_cubica(q))
            onda = Image.new("RGBA", (AN, AL))
            ImageDraw.Draw(onda).ellipse([cx - r, cy - r, cx + r, cy + r], outline=AMARILLO + (int(230 * (1 - q)),),
                                         width=max(2, int(10 * (1 - q))))
            fr.alpha_composite(onda)
        # nombre: sale de detras del logo, con el espaciado cerrandose
        a_n = tramo(tl, 0.92, 1.45)
        if a_n > 0:
            esp = 0.18 * (1 - sale_expo(a_n))
            nm = self.nombre_abierto(esp) if esp > 0.002 else self.nombre_fin
            if vuelo > 0:
                nm = Image.blend(self.nombre_fin, self.nombre_cab, min(1.0, vuelo * 1.5))
            k = (1 - vuelo) * empuje + (CAB_TAM / TAM_NOMBRE) * vuelo
            nx0 = self.nx - 70 * (1 - sale_expo(a_n))
            x = nx0 + (CAB_NOMBRE[0] - nx0) * vuelo
            yc = self.ncy + (CAB_NOMBRE[1] - self.ncy) * vuelo
            nm2 = nm.resize((max(1, int(nm.width * k)), max(1, int(nm.height * k))), Image.LANCZOS) if abs(k - 1) > 1e-3 else nm
            if vuelo == 0:                                   # recorte: no asoma por detras del logo
                tope = int(cx + tam / 2 + 10 - x)
                if tope > 0:
                    a = nm2.getchannel("A").copy()
                    ImageDraw.Draw(a).rectangle([0, 0, tope, nm2.height], fill=0)
                    nm2 = nm2.copy()
                    nm2.putalpha(a)
            G2.pega(fr, nm2, x, yc - nm2.height / 2, sale_cubica(a_n * 1.6))
            # linea amarilla bajo el nombre
            la = sale_cubica(tramo(tl, 1.05, 1.45)) * (1 - tramo(tl, 1.95, 2.15))
            if la > 0:
                y = self.ncy + TAM_NOMBRE * 0.52
                ImageDraw.Draw(fr).rectangle([self.nx, y, self.nx + int((self.nombre_fin.width - 30) * la), y + 9],
                                             fill=AMARILLO + (255,))
        # fecha
        a_f = sale_cubica(tramo(tl, 1.18, 1.6)) * (1 - tramo(tl, 1.95, 2.12))
        if a_f > 0:
            G2.pega(fr, self.fecha, self.nx, self.fy + 18 * (1 - a_f), a_f)
        # al final, lo que vuela ocupa el sitio exacto del logo y el nombre de la cabecera (siguiente viene sin ellos)
        return fr
