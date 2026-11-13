"""PRUEBA de estilo visual (13-nov-2026): Short de ~10 s con ESCENAS de línea clara animadas a PANTALLA COMPLETA,
sin personajes en primer plano (lo que pidió el usuario). Cada escena entra con la frase que se narra; encima, la
cabecera EH y el recuadro con la frase. No entra en la jornada: es solo para validar el estilo."""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

import corto as C
import episodio as E
import genera_video as V1
import genera_video2 as G2
import motion_comic as MC
import voz
from genera_video2 import AMARILLO, BLANCO, ROJO, fuente
import short as SH

AN, AL, FPS = 1080, 1920, 30
RAIZ = Path(__file__).parent


def base_escena(ruta):
    return ImageOps.fit(Image.open(ruta).convert("RGB"), (int(AN * 1.12), int(AL * 1.12)), Image.LANCZOS,
                        centering=(0.5, 0.42))


def main():
    salida = RAIZ / "dia" / "prueba-estilo"
    (salida).mkdir(parents=True, exist_ok=True)
    tmp = salida / "tmp"
    tmp.mkdir(exist_ok=True)
    escenas = [RAIZ / "canal" / "pruebas" / f"est_{k}.jpg" for k in range(3)]
    frases = [
        "O ganamos, o se acabó.",
        "Con esa frase, Isabel Díaz Ayuso arrancó la campaña del PP en Madrid,",
        "en la que llamó la campaña más decisiva de la democracia.",
    ]
    texto = " ".join(frases)
    pal, dur = voz.locuta([{"di": texto}], "normal", tmp / "voz.wav", cola=0.3)
    T = E.Tiempos(texto, pal, 0.0)
    # tiempo de inicio de cada frase (cambia la escena cuando empieza a decirse)
    t_esc, pos = [], 0
    for fr in frases:
        k = texto.find(fr[:18], pos)
        t_esc.append(T.en(k) if k >= 0 else 0.0)
        pos = (k if k >= 0 else pos) + len(fr)
    t_esc[0] = 0.0
    total = dur + 0.6
    bases = [base_escena(e) for e in escenas]
    cab = SH._cabecera("2026-11-13", "POLÉMICA")
    cajas = [SH._caja(fr, ancho=940, tam=52) for fr in frases]

    def escena_en(t):
        k = max([j for j, te in enumerate(t_esc) if te <= t] or [0])
        t1 = t_esc[k + 1] if k + 1 < len(t_esc) else total
        tl = t - t_esc[k]
        dur_k = max(1.0, t1 - t_esc[k] + (1.2 if k == len(t_esc) - 1 else 0))
        vista = MC.anima(bases[k], escenas[k], tl, AN, AL, semilla=k, dur=dur_k + 2).convert("RGBA")
        MC.ambiente(vista, tl, t, semilla=k)
        if k > 0 and tl < 0.5:                             # transición: la nueva entra deslizando
            q = G2.suave(tl / 0.5)
            prev = MC.anima(bases[k - 1], escenas[k - 1], t - t_esc[k - 1], AN, AL, semilla=k - 1, dur=total).convert("RGBA")
            fr = Image.new("RGBA", (AN, AL))
            fr.paste(prev, (int(-AN * 0.25 * q), 0))
            fr.alpha_composite(vista, (int(AN * (1 - q)), 0))
            vista = fr
        return vista, k

    def cuadro(t):
        fr, k = escena_en(t)
        # oscurecer un poco abajo para que se lea el texto
        g = Image.linear_gradient("L").resize((AN, 700)).point(lambda v: int(max(0, v - 90) * 1.3))
        som = Image.new("RGBA", (AN, 700), (6, 10, 22, 255))
        som.putalpha(g)
        fr.alpha_composite(som, (0, AL - 700))
        fr.alpha_composite(cab, (0, 0))
        caja = cajas[k]
        fr.alpha_composite(caja, ((AN - caja.width) // 2, AL - 260 - caja.height // 2))
        d = ImageDraw.Draw(fr)
        d.text((AN // 2, AL - 70), "Fuente: El Debate", font=fuente("Inter-SemiBold.ttf", 26),
               fill=(210, 216, 230, 255), anchor="mm")
        d.rectangle([0, AL - 12, int(AN * min(1.0, t / total)), AL], fill=AMARILLO + (255,))
        return fr

    out = salida / "prueba.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "voz.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "21", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], stdin=subprocess.PIPE)
    for fi in range(int(math.ceil(total * FPS))):
        ff.stdin.write(cuadro(fi / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"PRUEBA {total:.1f} s -> {out}")


if __name__ == "__main__":
    main()
