"""CIERRE del largo horizontal: la despedida a pantalla completa y la pantalla final de YouTube (decision del 1-nov-2026).

Es el espejo del golpe de marca (marca.py): un barrido tapa el ultimo breve y el logo y el nombre vuelan desde la cabecera
hasta su sitio. Despues, sincronizado con lo que dice Urni:
  «suscribete»      -> el cursor llega al boton rojo, lo pulsa y pasa a «SUSCRITO»;
  «campanita»       -> el cursor pulsa la campana, que se balancea y se enciende en amarillo;
  «Gracias por vernos» -> entra el texto de despedida.
Urni habla a la derecha y se retira al terminar la voz, porque la mitad derecha queda libre durante los ultimos segundos
para los elementos de la pantalla final que se ponen en YouTube Studio (video sugerido y boton de suscripcion)."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

import genera_video2 as G2
import marca as MK
import prototipo_animado as P
from genera_video2 import AN, AL, AMARILLO, BLANCO, ROJO, fuente
from marca import entra_sale, rebote, sale_cubica, sale_expo, tramo

GRIS_BOTON = (58, 63, 75)
L2 = 150                                  # logo en el cierre
X0, Y0 = 150, 250                         # esquina del logo
TAM_N = 72


def _boton(texto, fondo, ancho=440, alto=100, check=False):
    k = 3
    im = Image.new("RGBA", (ancho * k, alto * k))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, ancho * k - 1, alto * k - 1], radius=alto * k // 2, fill=fondo + (255,))
    f = fuente("Inter-Black.ttf", 40 * k)
    if check:
        cx = 62 * k
        d.line([(cx - 16 * k, alto * k / 2), (cx - 4 * k, alto * k / 2 + 13 * k), (cx + 18 * k, alto * k / 2 - 14 * k)],
               fill=BLANCO + (255,), width=9 * k, joint="curve")
        d.text((ancho * k / 2 + 24 * k, alto * k / 2), texto, font=f, fill=BLANCO + (255,), anchor="mm")
    else:
        d.text((ancho * k / 2, alto * k / 2), texto, font=f, fill=BLANCO + (255,), anchor="mm")
    return im.resize((ancho, alto), Image.LANCZOS)


def _campana(tam, activa):
    """Circulo con una campana dibujada a vectores; activa: fondo amarillo y campana oscura."""
    k = 4
    T = tam * k
    im = Image.new("RGBA", (T, T))
    d = ImageDraw.Draw(im)
    fondo = AMARILLO if activa else GRIS_BOTON
    tinta = (20, 24, 34) if activa else BLANCO
    d.ellipse([0, 0, T - 1, T - 1], fill=fondo + (255,))
    u = lambda *v: [x * T for x in v]
    d.ellipse(u(0.455, 0.17, 0.545, 0.26), fill=tinta + (255,))                       # asa
    d.pieslice(u(0.31, 0.22, 0.69, 0.60), 180, 360, fill=tinta + (255,))             # cupula
    d.polygon(u(0.31, 0.41, 0.69, 0.41, 0.75, 0.66, 0.25, 0.66), fill=tinta + (255,))  # cuerpo
    d.rounded_rectangle(u(0.20, 0.64, 0.80, 0.71), radius=T // 60, fill=tinta + (255,))  # borde
    d.ellipse(u(0.44, 0.70, 0.56, 0.80), fill=tinta + (255,))                        # badajo
    return im.resize((tam, tam), Image.LANCZOS)


def _cursor(tam=54):
    k = 4
    T = tam * k
    im = Image.new("RGBA", (T, int(T * 1.3)))
    d = ImageDraw.Draw(im)
    p = [(0.08, 0.04), (0.08, 0.92), (0.30, 0.72), (0.46, 1.10), (0.60, 1.04), (0.44, 0.67), (0.74, 0.67)]
    pts = [(x * T, y * T) for x, y in p]
    d.polygon(pts, fill=(15, 15, 15, 255))
    interior = [((x - 0.08) * 0.78 + 0.08 + 0.025) * T for x, _ in p]
    pts2 = [(xi, (y * 0.80 + 0.09) * T) for xi, (_, y) in zip(interior, p)]
    d.polygon(pts2, fill=(255, 255, 255, 255))
    return im.resize((tam, int(tam * 1.3)), Image.LANCZOS)


class Cierre:
    def __init__(self, fecha):
        g = MK.Golpe(fecha)
        self.g = g
        self.base, self.sobre, _ = MK._logo_partes(L2)
        self.logo = self.base.copy()
        self.logo.alpha_composite(self.sobre)
        self.nombre = MK._nombre(TAM_N, BLANCO)
        self.nombre_cab = MK._nombre(TAM_N, AMARILLO)
        f = fuente("Inter-Regular.ttf", 36)
        self.lema = Image.new("RGBA", (900, 60))
        ImageDraw.Draw(self.lema).text((0, 30), G2.LEMA, font=f, fill=MK.GRIS + (255,), anchor="lm")
        self.sus = _boton("SUSCRÍBETE", ROJO)
        self.suscrito = _boton("SUSCRITO", GRIS_BOTON, check=True)
        self.camp = _campana(100, False)
        self.camp_on = _campana(100, True)
        self.cursor = _cursor()
        fg = fuente("Inter-Black.ttf", 60)
        self.gracias = Image.new("RGBA", (1100, 90))
        dg = ImageDraw.Draw(self.gracias)
        dg.text((0, 45), "Gracias por vernos.", font=fg, fill=BLANCO + (255,), anchor="lm")
        w = dg.textlength("Gracias por vernos. ", font=fg)
        dg.text((w, 45), "Mañana, más.", font=fg, fill=AMARILLO + (255,), anchor="lm")
        # posiciones
        self.nx, self.ncy = X0 + L2 + 34, Y0 + L2 * 0.42
        self.by = Y0 + L2 + 150
        self.bx_sus, self.bx_camp = X0, X0 + 440 + 30

    def cuadro(self, tl, previo, ev, urni=None, fin_voz_tl=None):
        """tl: s desde que empieza la despedida; previo: el ultimo fotograma del tablero; ev: {"suscribete", "campanita",
        "gracias"} en s desde el inicio de la despedida (None si no se dice); urni: imagen de Urni hablando o None."""
        fondo = self.g.fondo(tl + 3)
        u = entra_sale(tramo(tl, 0.0, 0.45))
        if u < 1:                                          # barrido de entrada (de izquierda a derecha, espejo del golpe)
            fr = previo.copy()
            X = -MK.SLANT - 300 + (AN + MK.SLANT + 400) * u
            masc = Image.new("L", (AN, AL))
            ImageDraw.Draw(masc).polygon([(-MK.SLANT - 600, 0), (X - 92 + MK.SLANT, 0), (X - 92, AL), (-MK.SLANT - 600, AL)], fill=255)
            fr.paste(fondo, (0, 0), masc)
            d = ImageDraw.Draw(fr)
            for a, b, col in ((-92, -70, AMARILLO), (-70, 0, ROJO)):
                d.polygon([(X + a + MK.SLANT, 0), (X + b + MK.SLANT, 0), (X + b, AL), (X + a, AL)], fill=col + (255,))
        else:
            fr = fondo
        # logo y nombre: vuelan desde la cabecera
        v = entra_sale(tramo(tl, 0.1, 0.75))
        cab_x, cab_y, cab_t = MK.CAB_LOGO
        tam = cab_t + (L2 - cab_t) * v
        x = cab_x + (X0 - cab_x) * v
        y = cab_y + (Y0 - cab_y) * v
        lg = self.logo.resize((max(1, int(tam)), max(1, int(tam))), Image.LANCZOS)
        fr.alpha_composite(lg, (int(x), int(y)))
        k = (MK.CAB_TAM + (TAM_N - MK.CAB_TAM) * v) / TAM_N
        nm = Image.blend(self.nombre_cab, self.nombre, v)
        nm = nm.resize((max(1, int(nm.width * k)), max(1, int(nm.height * k))), Image.LANCZOS)
        nx = MK.CAB_NOMBRE[0] + (self.nx - MK.CAB_NOMBRE[0]) * v
        ny = MK.CAB_NOMBRE[1] + (self.ncy - MK.CAB_NOMBRE[1]) * v
        fr.alpha_composite(nm, (int(nx), int(ny - nm.height / 2)))
        d = ImageDraw.Draw(fr)
        la = sale_cubica(tramo(tl, 0.65, 1.0))
        if la > 0:
            yl = self.ncy + TAM_N * 0.55
            d.rectangle([self.nx, yl, self.nx + int((self.nombre.width - 24) * la), yl + 7], fill=AMARILLO + (255,))
        G2.pega(fr, self.lema, self.nx, self.ncy + TAM_N * 0.75 + 12 * (1 - la), la)
        # botones
        e_sus, e_camp = ev.get("suscribete"), ev.get("campanita")
        ab = sale_cubica(tramo(tl, 0.7, 1.15))
        if ab > 0:
            dy = int(40 * (1 - ab))
            pulsa_s = e_sus is not None and tl >= e_sus
            pres = 1 - 0.07 * math.exp(-max(0.0, tl - e_sus) / 0.06) if pulsa_s else 1.0
            b = self.suscrito if pulsa_s else self.sus
            if abs(pres - 1) > 0.002:
                b = b.resize((int(b.width * pres), int(b.height * pres)), Image.LANCZOS)
            G2.pega(fr, b, self.bx_sus + (440 - b.width) / 2, self.by + dy + (100 - b.height) / 2, ab)
            pulsa_c = e_camp is not None and tl >= e_camp
            c = self.camp_on if pulsa_c else self.camp
            if pulsa_c:
                q = tl - e_camp
                ang = 22 * math.exp(-q / 0.45) * math.sin(q * 2 * math.pi * 3.2)
                c = c.rotate(ang, resample=Image.BICUBIC, center=(50, 18))
                if q < 0.5:                                # destellos alrededor
                    rr = 64 + 40 * sale_cubica(q / 0.5)
                    cx, cy = self.bx_camp + 50, self.by + 50 + dy
                    for a in (-60, -30, 0, 30, 60):
                        ang_r = math.radians(a - 90)
                        p0 = (cx + math.cos(ang_r) * rr, cy + math.sin(ang_r) * rr)
                        p1 = (cx + math.cos(ang_r) * (rr + 22), cy + math.sin(ang_r) * (rr + 22))
                        d.line([p0, p1], fill=AMARILLO + (int(255 * (1 - q / 0.5)),), width=6)
            G2.pega(fr, c, self.bx_camp, self.by + dy, ab)
        # cursor: entra desde abajo, pulsa el boton y luego la campana, y se va
        if e_sus is not None:
            pts = [(-1.0, (AN * 0.45, AL + 80)), (e_sus - 0.05, (self.bx_sus + 300, self.by + 62))]
            if e_camp is not None:
                pts += [(e_camp - 0.05, (self.bx_camp + 62, self.by + 66))]
            ult = pts[-1][0]
            pts += [(ult + 0.9, (self.bx_camp + 300, AL + 80))]
            pts[0] = (pts[1][0] - 0.75, pts[0][1])
            if pts[0][0] <= tl <= pts[-1][0]:
                for (ta, pa), (tb, pb) in zip(pts, pts[1:]):
                    if ta <= tl <= tb:
                        s = entra_sale((tl - ta) / max(0.01, tb - ta)) if tb - ta < 1.2 else \
                            entra_sale(tramo(tl, tb - 0.7, tb))
                        cx = pa[0] + (pb[0] - pa[0]) * s
                        cy = pa[1] + (pb[1] - pa[1]) * s
                        clic = min([abs(tl - e) for e in (e_sus, e_camp) if e is not None])
                        esc = 1 - 0.15 * max(0.0, 1 - clic / 0.08)
                        cu = self.cursor if esc > 0.995 else self.cursor.resize(
                            (int(self.cursor.width * esc), int(self.cursor.height * esc)), Image.LANCZOS)
                        fr.alpha_composite(cu, (int(cx), int(cy)))
                        break
        # despedida
        e_g = ev.get("gracias")
        if e_g is not None:
            ag = sale_expo(tramo(tl, e_g, e_g + 0.6))
            G2.pega(fr, self.gracias, X0 - 40 * (1 - ag), self.by + 190, ag)
        # Urni a la derecha mientras habla; se retira al acabar la voz (la mitad derecha es para la pantalla final)
        if urni is not None:
            entra = sale_cubica(tramo(tl, 0.5, 1.1))
            sale = entra_sale(tramo(tl, fin_voz_tl + 0.2, fin_voz_tl + 0.8)) if fin_voz_tl is not None else 0
            if entra > 0 and sale < 1:
                G2.pega(fr, urni, 1420 - urni.width / 2, AL - urni.height - 40 + 500 * (1 - entra) + 600 * sale,
                        min(1.0, entra * 1.5))
        return fr
