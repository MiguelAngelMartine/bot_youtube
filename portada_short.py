"""PORTADA DE LOS SHORTS (27-nov-2026, el usuario: «en los shorts podemos poner en el fotograma 1 la miniatura y después
elegir ese fotograma como miniatura»). Para cada Short del formato presentador:
  1) dibuja la portada vertical (1080×1920): el fondo del Short, la persona (o las dos del cruce) con su imagen de
     Imagenes/Políticos SIN TOCAR la cara (solo escala), la frase gancho grande con la palabra destacada en amarillo y el
     rótulo de quién; nada se pisa (el texto va por encima de las cabezas);
  2) la guarda en shorts/short_N_portada.png (subir.py la pone como miniatura con thumbnails.set);
  3) la mete en el PRIMER FOTOGRAMA del vídeo (sustituye al fotograma 0, el audio no se mueve), para que el fotograma
     que YouTube coja para el feed sea también la portada.
Uso: python portada_short.py AAAA-MM-DD [N ...]   (sin N: todos los Shorts del día)"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import presentador as P

RAIZ = Path(__file__).parent
W, H = 1080, 1920
BLANCO = (255, 255, 255)


def _fondo(S, carpeta, n):
    fondos, _, _ = P.catalogo()
    cache = carpeta / f"fondo_short_{n}.json"
    if S.get("fondo") and (P.IMG / "Fondos" / S["fondo"]).exists():
        ruta = P.IMG / "Fondos" / S["fondo"]
    else:
        ruta = P.elige_fondos([f"{S.get('titulo', '')}. {S.get('contexto', '')}"], fondos, cache)[0]
    im = Image.open(ruta).convert("RGB")
    k = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * k) + 1, int(im.height * k) + 1), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x0, y0, x0 + W, y0 + H)).convert("RGBA")


def _personas(S):
    """Quién sale: el protagonista y, si lo hay, quien le replica (o la segunda persona con cita)."""
    out = [S.get("quien", "")]
    rep = (S.get("replica") or {}).get("quien")
    if rep:
        out.append(rep)
    else:
        for q in (S.get("quien_citas") or {}).values():
            if q and q not in out and q not in ("PSOE", "PP", "Vox", "Sumar", "Podemos", "Gobierno"):
                out.append(q)
                break
    return [q for q in out if q][:2]


def _frase(S):
    t = (S.get("portada") or S.get("gancho") or S.get("cita") or "").strip().strip("«»\"").rstrip(".")
    palabras = t.split()
    if len(palabras) > 9:                                 # la portada se lee de un vistazo: como mucho 9 palabras
        t = " ".join(palabras[-9:]) if S.get("portada") else " ".join(palabras[:9]) + "…"
    return t[:1].upper() + t[1:]


def _texto(d, lineas, f, y, destaca):
    dn = P._n(destaca or "")
    for ln in lineas:
        x = (W - f.getlength(ln)) / 2
        for w in ln.split(" "):
            amarillo = dn and P._n(w).strip(" .,;:¿?¡!«»") in dn.split()
            col = P.AMARILLO if amarillo else BLANCO
            d.text((x, y), w, font=f, fill=col + (255,), stroke_width=7, stroke_fill=(0, 0, 0, 255))
            x += f.getlength(w + " ")
        y += int(f.size * 1.12)
    return y


def portada(fecha, n):
    dia = RAIZ / "dia" / fecha
    carpeta = dia / "shorts"
    S = json.loads((carpeta / f"short_{n}.json").read_text(encoding="utf-8"))
    lienzo = _fondo(S, carpeta, n)
    # oscurece arriba (texto) y abajo (rótulo) para que se lea sobre cualquier fondo
    g = Image.linear_gradient("L").resize((W, H))
    capa = Image.new("RGBA", (W, H), (6, 10, 22, 255))
    capa.putalpha(g.point(lambda v: int(70 + 0.35 * v)))
    lienzo.alpha_composite(capa)
    arriba = Image.new("RGBA", (W, 760), (6, 10, 22, 255))
    arriba.putalpha(Image.linear_gradient("L").rotate(180).resize((W, 760)).point(lambda v: int(v * 0.75)))
    lienzo.alpha_composite(arriba, (0, 0))
    # personas (la cara, intacta: solo se escala)
    _, _, pols = P.catalogo()
    gente = [(q, P.figura_de(q, pols, {})) for q in _personas(S)]
    gente = [(q, r) for q, r in gente if r]
    top_cabeza = H
    if gente:
        alto = int(H * (0.67 if len(gente) == 1 else 0.60))
        figs = [P.recorte(r, alto) for _, r in gente]
        if len(figs) == 2:
            esc = min(1.0, (W / 2 + 130) / max(f.width for f in figs))   # los brazos de fuera pueden salir
            figs = [f.resize((int(f.width * esc), int(f.height * esc)), Image.LANCZOS) for f in figs]
            pos = [(W // 4 - figs[0].width // 2 - 20, H - figs[0].height),
                   (3 * W // 4 - figs[1].width // 2 + 20, H - figs[1].height)]
        else:
            pos = [((W - figs[0].width) // 2, H - figs[0].height)]
        for f, (x, y) in zip(figs, pos):
            capa_f = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # capa entera: admite figuras que salen por el borde
            capa_f.paste(P.sombra(f), (x + 14, y + 10))
            lienzo.alpha_composite(capa_f)
            capa_f = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            capa_f.paste(f, (x, y))
            lienzo.alpha_composite(capa_f)
            top_cabeza = min(top_cabeza, y)
    d = ImageDraw.Draw(lienzo)
    # cabecera de la marca
    d.rectangle([0, 0, W, 12], fill=P.ROJO + (255,))
    d.rectangle([0, 12, W, 18], fill=P.AMARILLO + (255,))
    fm = P.fuente("Inter-Black.ttf", 40)
    d.text((W // 2 - fm.getlength("EL HOY FORMATIVO") / 2, 70), "EL HOY ", font=fm, fill=BLANCO + (255,), anchor="lm")
    d.text((W // 2 - fm.getlength("EL HOY FORMATIVO") / 2 + fm.getlength("EL HOY "), 70), "FORMATIVO", font=fm,
           fill=P.AMARILLO + (255,), anchor="lm")
    # la frase, grande, en el hueco sobre las cabezas (si no cabe, se reduce la letra; nunca pisa una cara)
    frase = "«" + _frase(S) + "»"
    limite = (top_cabeza if gente else int(H * 0.62)) - 40
    y0 = 150
    for tam in (128, 116, 104, 94, 84, 76, 68):
        f = P.fuente("Inter-Black.ttf", tam)
        lineas = P.envuelve(frase, f, W - 110)
        alto_txt = len(lineas) * int(tam * 1.12)
        if len(lineas) <= 4 and y0 + alto_txt + 110 <= limite:
            break
    y = _texto(d, lineas, f, y0, S.get("destaca") or "")
    # rótulo de quién lo dice, bajo la frase
    quien = (S.get("quien") or "").upper()
    if S.get("replica"):
        quien = f"{quien.split()[-1]} VS {S['replica']['quien'].upper().split()[-1]}"
    fr = P.fuente("Inter-Black.ttf", 46)
    wq = int(fr.getlength(quien)) + 60
    y += 18
    d.rectangle([(W - wq) // 2, y, (W + wq) // 2, y + 74], fill=P.ROJO + (255,))
    d.text((W // 2, y + 37), quien, font=fr, fill=BLANCO + (255,), anchor="mm")
    if y + 74 > limite + 40:
        print(f"  AVISO short_{n}: el rótulo queda cerca de las cabezas ({y + 74} > {limite})")
    out = carpeta / f"short_{n}_portada.png"
    lienzo.convert("RGB").save(out)
    return out


def al_primer_fotograma(mp4, png):
    """Sustituye el fotograma 0 del vídeo por la portada (el audio se copia tal cual; la duración no cambia)."""
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
    mp4 = Path(mp4)
    tmp = mp4.with_name(mp4.stem + "_conportada.mp4")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(mp4), "-i", str(png), "-filter_complex",
                    "[1:v]scale=1080:1920,format=yuv420p[p];[0:v][p]overlay=0:0:enable='eq(n,0)'[v]",
                    "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(mp4)
    marca = mp4.with_name(mp4.stem + "_portada.ok")
    marca.write_text(png.name, encoding="utf-8")


def hecha(mp4):
    """True si el vídeo ya lleva la portada en el fotograma 0 (y no se ha vuelto a renderizar desde entonces)."""
    m = Path(mp4).with_name(Path(mp4).stem + "_portada.ok")
    return m.exists() and m.stat().st_mtime >= Path(mp4).stat().st_mtime - 5


def main(fecha, ns=None):
    carpeta = RAIZ / "dia" / fecha / "shorts"
    if not ns:
        ns = sorted({re.sub(r"\D", "", f.stem) for f in carpeta.glob("short_*.mp4") if re.fullmatch(r"short_\d+", f.stem)},
                    key=int)
    for n in ns:
        mp4 = carpeta / f"short_{n}.mp4"
        if not mp4.exists():
            continue
        png = portada(fecha, n)
        if not hecha(mp4):
            al_primer_fotograma(mp4, png)
        print(f"short_{n}: portada -> {png.name} (y en el fotograma 1 del vídeo)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    main(a[0], a[1:] or None)
