"""PRUEBA (13-nov-2026): fondo cómic de ambiente ANIMADO + Polaroid con la FOTO REAL de quien dice la frase, integrada y
en armonía con el fondo (marco y celo teñidos con el color dominante del fondo), a DOBLE tamaño que en los primeros
vídeos. Clip de ~10 s para validar el cambio. No entra en la jornada."""
from __future__ import annotations

import colorsys
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

import genera_video as V1
import motion_comic as MC
import voz
from genera_video2 import AMARILLO, BLANCO, ROJO, fuente
import render_ambiente as RA

W, H, FPS = 1920, 1080, 30
RAIZ = Path(__file__).parent


def _acento(crop):
    """Color de acento en armonía con el fondo: el dominante del recorte, más saturado y con cuerpo."""
    c = crop.convert("RGB").resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in c])
    s = min(1.0, s * 1.5 + 0.25)
    v = min(1.0, max(0.45, v * 0.95))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def polaroid_armonica(foto, nombre, cargo, ancho, acento):
    """Polaroid con la foto real, marco en armonía con el fondo (borde y celo del color de acento). Doble de tamaño."""
    alto_f = int(ancho * 0.80)                              # algo apaisada: a doble ancho, cabe entera en 16:9
    im = Image.new("RGBA", (ancho + 60, alto_f + 210), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([26, 34, ancho + 42, alto_f + 214], radius=14, fill=(0, 0, 0, 90))      # sombra
    d.rounded_rectangle([16, 24, ancho + 32, alto_f + 206], radius=12, fill=(250, 248, 243, 255))  # tarjeta hueso
    d.rounded_rectangle([16, 24, ancho + 32, alto_f + 206], radius=12, outline=acento + (255,), width=10)  # marco de acento
    # foto
    f = Image.open(foto).convert("RGB")
    rr = max((ancho - 20) / f.width, (alto_f - 20) / f.height)
    f = f.resize((math.ceil(f.width * rr), math.ceil(f.height * rr)), Image.LANCZOS)
    x0, y0 = (f.width - (ancho - 20)) // 2, int((f.height - (alto_f - 20)) * 0.22)
    foto_c = f.crop((x0, y0, x0 + ancho - 20, y0 + alto_f - 20))
    d.rectangle([34, 42, 34 + ancho - 20, 42 + alto_f - 20], fill=acento + (255,))               # fina orla de acento
    im.paste(foto_c, (38, 46))
    # nombre y cargo
    fn = fuente("Inter-Black.ttf", 56)
    while fn.getlength(nombre.upper()) > ancho - 10 and fn.size > 30:
        fn = fuente("Inter-Black.ttf", fn.size - 2)
    d.text(((ancho + 48) / 2, alto_f + 70), nombre.upper(), font=fn, fill=(20, 22, 28, 255), anchor="mt")
    d.text(((ancho + 48) / 2, alto_f + 136), cargo, font=fuente("Inter-SemiBold.ttf", 34), fill=acento + (255,), anchor="mt")
    d.text(((ancho + 48) / 2, alto_f + 184), "Foto de archivo · CC", font=fuente("Inter-Regular.ttf", 22),
           fill=(140, 140, 150, 255), anchor="mt")
    # celo (cinta) de acento, arriba
    celo = Image.new("RGBA", (260, 70), acento + (150,))
    celo = celo.rotate(5, expand=True)
    im.alpha_composite(celo, (int((ancho + 60) / 2 - 130), 0))
    return im.rotate(-3, expand=True, resample=Image.BICUBIC)


def main():
    salida = RAIZ / "dia" / "prueba-polaroid"
    salida.mkdir(parents=True, exist_ok=True)
    tmp = salida / "tmp"
    tmp.mkdir(exist_ok=True)
    foto = RAIZ / "dia" / "2026-11-01" / "imagenes" / "retrato_abascal.jpg"
    escena = RAIZ / "canal" / "pruebas" / "est_0.jpg"       # fondo cómic de ambiente (mitin de campaña)
    texto = ("«No tienen vergüenza». Lo suelta Santiago Abascal, desde Huesca, por la aparición de Begoña Gómez en el mitin "
             "del PSOE. Y remata diciendo que Sánchez debería estar en un banquillo, no en las tribunas.")
    pal, dur = voz.locuta([{"di": texto}], "normal", tmp / "voz.wav", cola=0.3)
    total = dur + 0.6
    base = ImageOps.fit(Image.open(escena).convert("RGB"), (int(W * 1.12), int(H * 1.12)), Image.LANCZOS, centering=(0.5, 0.42))
    # acento tomado de la zona del fondo donde irá la Polaroid (abajo-izquierda)
    acento = _acento(base.crop((0, int(base.height * 0.45), int(base.width * 0.4), base.height)))
    anchoP = 680                                            # doble de los primeros vídeos (~340)
    pol = polaroid_armonica(foto, "Santiago Abascal", "Líder de Vox", anchoP, acento)
    cab = RA._cabecera16("2026-11-13", 1, 1, "«No tienen vergüenza»", "Europa Press · El País")
    caja = RA.SH._caja(texto.split("». ", 1)[1] if "». " in texto else texto, ancho=980, tam=44)

    def cuadro(t):
        fr = MC.anima(base, escena, t, W, H, semilla=1, dur=total + 2).convert("RGBA")
        g = Image.linear_gradient("L").resize((W, 420)).point(lambda v: int(max(0, v - 70) * 1.3))
        som = Image.new("RGBA", (W, 420), (6, 10, 22, 255))
        som.putalpha(g)
        fr.alpha_composite(som, (0, H - 420))
        fr.alpha_composite(cab, (0, 0))
        # Polaroid abajo-izquierda, entra con un pop
        e = min(1.0, t / 0.45)
        s = 0.86 + 0.14 * (1 - (1 - e) ** 2)
        p = pol.resize((int(pol.width * s), int(pol.height * s)), Image.BILINEAR) if s < 0.999 else pol
        px, py = 70, max(165, H - p.height - 55)
        fr.alpha_composite(p, (px, py))
        # recuadro de la frase, a la derecha de la Polaroid
        fr.alpha_composite(caja, (px + pol.width + 10, H - 120 - caja.height))
        d = ImageDraw.Draw(fr)
        d.rectangle([0, H - 10, int(W * min(1.0, t / total)), H], fill=AMARILLO + (255,))
        return fr

    out = salida / "prueba.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "voz.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "21", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], stdin=subprocess.PIPE)
    for fi in range(int(math.ceil(total * FPS))):
        ff.stdin.write(cuadro(fi / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"PRUEBA polaroid {total:.1f} s -> {out}")


if __name__ == "__main__":
    main()
