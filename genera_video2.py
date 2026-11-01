"""MONTAJE DINAMICO (v2): fotos libres con zoom lento (Ken Burns) y fundidos, cortinilla entre bloques, titular que entra
deslizando, puntos que aparecen segun avanza la narracion, subtitulos en pantalla y credito de cada foto.
Cada fotograma se dibuja con Pillow y se pasa a ffmpeg por una tuberia.
Uso: python genera_video2.py AAAA-MM-DD [voz]   (necesita guion.json, imagenes/ y creditos.json del dia)"""
from __future__ import annotations

import asyncio
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import genera_video as V1
import musica

# identidad del canal: todo lo de marca en un sitio
MARCA = "EL HOYFORMATIVO"
PRESENTADORA = "Urni"
LEMA = "La política española del día, en claro"
VOZ = ("es-ES-AlvaroNeural", "+14%", "+6Hz")      # elegida por el usuario (muestra 2)
INTRO, OUTRO = 3.0, 8.0                            # s de cabecera con sintonia y de cierre (pantalla final de YouTube: 5-20 s)

AN, AL, FPS = 1920, 1080, 25
ZOOM = 1.14
FUNDIDO = 0.7                      # s de fundido entre fotos
CORTINILLA = 0.55                  # s de la barra que barre la pantalla al cambiar de bloque
ROJO, AMARILLO, BLANCO = (200, 16, 46), (241, 191, 0), (245, 247, 250)
F = str(Path(__file__).parent / "fuentes") + "/"     # tipografias libres (OFL) del repositorio: Inter, Barlow Condensed, Caveat


def fuente(n, t):
    return ImageFont.truetype(F + n, t)


def suave(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ------------------------------------------------------------------ fotos

def base_foto(ruta):
    """Imagen de ZOOM x pantalla que cubre todo. Las verticales van nitidas a la derecha sobre un fondo desenfocado."""
    im = Image.open(ruta).convert("RGB")
    W, H = int(AN * ZOOM), int(AL * ZOOM)
    def cubre(img):
        r = max(W / img.width, H / img.height)
        img = img.resize((math.ceil(img.width * r), math.ceil(img.height * r)), Image.LANCZOS)
        x, y = (img.width - W) // 2, (img.height - H) // 3          # algo por encima del centro: caras
        return img.crop((x, y, x + W, y + H))
    if im.width / im.height >= 1.2:
        return cubre(im)
    fondo = cubre(im).filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.55))
    r = H * 0.92 / im.height
    fg = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    fondo.paste(fg, (int(W * 0.66 - fg.width / 2), int((H - fg.height) / 2)))
    return fondo


def ken_burns(base, p, k):
    """p 0..1 dentro del tramo de la foto; k alterna acercar/alejar y el sentido del desplazamiento."""
    z = 1 + (ZOOM - 1) * (p if k % 2 == 0 else 1 - p)
    w, h = base.width / z, base.height / z
    dx = (base.width - w) * (0.5 + 0.35 * (p - 0.5) * (1 if k % 3 else -1))
    dy = (base.height - h) * 0.45
    return base.resize((AN, AL), Image.BILINEAR, box=(dx, dy, dx + w, dy + h))


# ------------------------------------------------------------------ capas de texto (RGBA, se dibujan una vez)

def capa_sombra():
    """Oscurece la izquierda (texto) y abajo (subtitulos) para que se lea sobre cualquier foto."""
    a = Image.new("L", (AN, 1))
    a.putdata([int(225 * max(0.0, 1 - x / (AN * 0.68)) ** 1.25) for x in range(AN)])
    a = a.resize((AN, AL))
    b = Image.new("L", (1, AL))
    b.putdata([int(200 * max(0.0, (y - AL * 0.72) / (AL * 0.28)) ** 1.6) for y in range(AL)])
    a = ImageChops.lighter(a, b.resize((AN, AL)))
    capa = Image.new("RGBA", (AN, AL), (8, 14, 28, 0))
    capa.putalpha(Image.eval(a, lambda v: min(v, 235)))
    return capa


def texto_lineas(d, txt, f, ancho):
    return V1.parte_lineas(d, txt, f, ancho)


def capa_titulo(titulo, n_sec, i):
    im = Image.new("RGBA", (1150, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 0
    if i > 0:
        etiqueta = f"{i:02d} / {n_sec - 1:02d}"
        d.rounded_rectangle([0, 0, 170, 52], radius=26, fill=ROJO + (255,))
        d.text((85, 26), etiqueta, font=fuente("Inter-Black.ttf", 28), fill=BLANCO, anchor="mm")
        y = 76
    ft = fuente("Inter-Black.ttf", 92 if i == 0 else 78)
    for l in texto_lineas(d, titulo, ft, 1120):
        d.text((4, y + 4), l, font=ft, fill=(0, 0, 0, 120))
        d.text((0, y), l, font=ft, fill=BLANCO)
        y += 104 if i == 0 else 90
    return im.crop((0, 0, 1150, y + 10))


def capa_punto(txt):
    f = fuente("Inter-SemiBold.ttf", 42)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ls = texto_lineas(d0, txt, f, 900)
    alto = 58 * len(ls) + 28
    im = Image.new("RGBA", (1000, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 990, alto], radius=16, fill=(10, 18, 34, 175))
    d.rounded_rectangle([0, 0, 12, alto], radius=6, fill=AMARILLO + (255,))
    for j, l in enumerate(ls):
        d.text((40, 12 + 58 * j), l, font=f, fill=BLANCO)
    return im


def capa_subtitulo(txt):
    f = fuente("Inter-SemiBold.ttf", 44)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ls = texto_lineas(d0, txt, f, 1500)
    w = int(max(d0.textlength(l, font=f) for l in ls)) + 60
    h = 60 * len(ls) + 24
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w, h], radius=14, fill=(0, 0, 0, 165))
    for j, l in enumerate(ls):
        d.text((w // 2, 12 + 60 * j + 30), l, font=f, fill=BLANCO, anchor="mm")
    return im


def capa_credito(c):
    txt = f"Foto: {c['autor']} · {c['licencia']} · Wikimedia Commons"
    f = fuente("Inter-Regular.ttf", 22)
    d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    w = int(d0.textlength(txt, font=f)) + 24
    im = Image.new("RGBA", (w, 36), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w, 36], radius=8, fill=(0, 0, 0, 120))
    d.text((12, 18), txt, font=f, fill=(225, 228, 235), anchor="lm")
    return im


def capa_cabecera(fecha, con_marca=True):
    """con_marca=False: sin logo ni nombre (el golpe de marca los trae volando hasta aqui)."""
    im = Image.new("RGBA", (AN, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, AN, 8], fill=ROJO + (255,))
    d.rectangle([0, 8, AN, 13], fill=AMARILLO + (255,))
    fm = fuente("Inter-Black.ttf", 30)
    if con_marca:
        im.alpha_composite(logo(46), (100, 62 - 23))
        d.text((160, 62), MARCA, font=fm, fill=AMARILLO + (255,), anchor="lm")
    x = 160 + d.textlength(MARCA, font=fm) + 18
    d.text((x, 62), "·  " + fecha, font=fuente("Inter-Regular.ttf", 28), fill=(220, 225, 235, 255), anchor="lm")
    return im


_liso = []

try:                                   # OpenCV reescala 3-4 veces mas rapido que Pillow (si no esta, se usa Pillow)
    import cv2 as _cv2
except ImportError:
    _cv2 = None


def escala(im, tam, box=None):
    """im.resize(tam, BILINEAR, box=box), con OpenCV cuando esta instalado. box: (x0, y0, x1, y1) enteros."""
    if _cv2 is None:
        return im.resize(tam, Image.BILINEAR, box=box)
    a = np.asarray(im)
    if box is not None:
        a = a[int(box[1]):int(box[3]), int(box[0]):int(box[2])]
    return Image.fromarray(_cv2.resize(a, tam, interpolation=_cv2.INTER_LINEAR), im.mode)


def fondo_marca(t):
    """Fondo azul con franjas diagonales que se desplazan despacio (cabecera y cierre).
    Pasados unos segundos las franjas ya han salido de pantalla: entonces se devuelve una copia del fondo liso."""
    if -600 + 140 * t > AN:
        if not _liso:
            _liso.append(Image.new("RGBA", (AN, AL), (12, 20, 38, 255)))
        return _liso[0].copy()
    im = Image.new("RGB", (AN, AL), (12, 20, 38))
    d = ImageDraw.Draw(im)
    x0 = int(-600 + 140 * t)
    for k, c in enumerate([(18, 30, 54), (22, 36, 64), (18, 30, 54)]):
        x = x0 + k * 520
        d.polygon([(x, AL), (x + 380, AL), (x + 380 + 700, 0), (x + 700, 0)], fill=c)
    return im.convert("RGBA")


_logo_cache = {}


def logo_partes(T=1600):
    """Logo del canal (elegido por el usuario el 1-nov-2026, opcion B): primer plano de Urni en un circulo azul con aro
    amarillo. Devuelve (sin_sobre, sobre, ranura): el logo sin el sobre, el sobre suelto en su sitio y la altura
    (fraccion) de la ranura de la tapa, para que el golpe de marca haga caer el sobre dentro de Urni."""
    if T in _logo_cache:
        return _logo_cache[T]
    import prototipo_animado as P
    def urni(con_sobre):
        P.S, viejo = 4, P.baja
        P.baja = lambda im: im
        try:
            u = P.mascota(0.6, 0.0, False, 0.0, sobre=con_sobre)
        finally:
            P.S, P.baja = 2, viejo
        return u
    def compone(u, caja):
        fondo = Image.new("RGBA", (T, T))
        ImageDraw.Draw(fondo).ellipse([0, 0, T - 1, T - 1], fill=(22, 40, 78, 255))
        cara = u.crop((caja[0], caja[1], caja[2], caja[1] + int((caja[3] - caja[1]) * 0.80)))
        k = T * 0.7375 / cara.width
        cara = cara.resize((int(cara.width * k), int(cara.height * k)), Image.LANCZOS)
        capa = Image.new("RGBA", (T, T))
        capa.alpha_composite(cara, ((T - cara.width) // 2, int(T * 0.53 - cara.height / 2)))
        m = Image.new("L", (T, T))
        ImageDraw.Draw(m).ellipse([T * 0.056, T * 0.056, T * 0.944, T * 0.944], fill=255)
        capa.putalpha(ImageChops.multiply(capa.getchannel("A"), m))
        fondo.alpha_composite(capa)
        ImageDraw.Draw(fondo).ellipse([T * 0.019, T * 0.019, T * 0.981, T * 0.981], outline=AMARILLO + (255,),
                                      width=int(T * 0.0375))
        return fondo
    con, sin = urni(True), urni(False)
    caja = con.getchannel("A").getbbox()                 # el mismo encuadre para las dos versiones
    a, b = compone(con, caja), compone(sin, caja)
    dif = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L").point(lambda v: 255 if v > 12 else 0)
    sobre = a.copy()
    sobre.putalpha(dif)
    bb = dif.getbbox()
    _logo_cache[T] = (b, sobre, bb[3] / T)
    return _logo_cache[T]


def logo(tam):
    """El logo del canal a cualquier tamano (circulo con fondo transparente fuera)."""
    sin, sobre, _ = logo_partes()
    im = sin.copy()
    im.alpha_composite(sobre)
    return im.resize((tam, tam), Image.LANCZOS)


def cuadro_intro(t, fecha):
    fr = fondo_marca(t)
    a = suave((t - 0.15) / 0.6)
    lg = logo(220)
    pega(fr, lg, 160, 330 + 40 * (1 - a), a)
    b = suave((t - 0.45) / 0.6)
    ft = fuente("Inter-Black.ttf", 120)
    tx = Image.new("RGBA", (1400, 150), (0, 0, 0, 0))
    ImageDraw.Draw(tx).text((0, 0), MARCA, font=ft, fill=BLANCO)
    pega(fr, tx, 430 + 80 * (1 - b), 330, b)
    c = suave((t - 0.9) / 0.5)
    d = ImageDraw.Draw(fr)
    d.rectangle([430, 480, 430 + int(d.textlength(MARCA, font=ft) * c), 490], fill=AMARILLO + (255,))
    tf = Image.new("RGBA", (1400, 70), (0, 0, 0, 0))
    ImageDraw.Draw(tf).text((0, 0), fecha, font=fuente("Inter-Regular.ttf", 50), fill=(220, 225, 235))
    pega(fr, tf, 430, 510, suave((t - 1.1) / 0.5))
    return fr


def cuadro_cierre(t, fecha):
    """Logo y texto a la izquierda; la mitad derecha libre para los elementos de la pantalla final de YouTube."""
    fr = fondo_marca(t + 2)
    a = suave((t - 0.3) / 0.6)
    pega(fr, logo(150), 120, 300, a)
    tx = Image.new("RGBA", (800, 520), (0, 0, 0, 0))
    d = ImageDraw.Draw(tx)
    d.text((0, 0), MARCA, font=fuente("Inter-Black.ttf", 64), fill=BLANCO)
    d.rectangle([0, 92, 520, 99], fill=AMARILLO + (255,))
    y = 130
    for l in texto_lineas(d, LEMA, fuente("Inter-Regular.ttf", 40), 760):
        d.text((0, y), l, font=fuente("Inter-Regular.ttf", 40), fill=(220, 225, 235))
        y += 54
    d.text((0, y + 40), "Gracias por vernos. Mañana, más.", font=fuente("Inter-SemiBold.ttf", 40), fill=AMARILLO)
    pega(fr, tx, 120, 480, suave((t - 0.6) / 0.6))
    return fr


def con_opacidad(capa, o):
    if o >= 0.999:
        return capa
    c = capa.copy()
    c.putalpha(c.getchannel("A").point(lambda v: int(v * o)))
    return c


def pega(frame, capa, x, y, o=1.0):
    if o <= 0.001:
        return
    frame.alpha_composite(con_opacidad(capa, o), (int(x), int(y)))


# ------------------------------------------------------------------ montaje

def main(dia_txt, subtitulos=True):
    dia = Path(__file__).parent / "dia" / dia_txt
    G = json.loads((dia / "guion.json").read_text(encoding="utf-8"))
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8"))
    tmp = dia / "tmp2"
    tmp.mkdir(exist_ok=True)
    secs = G["secciones"]
    n = len(secs)

    # voz por bloque (con los tiempos de cada frase para subtitulos y para sacar los puntos)
    plan, t0, wavs, srt = [], INTRO, [], []
    for i, s in enumerate(secs):
        mp3, wav = tmp / f"s{i}.mp3", tmp / f"s{i}.wav"
        frases = asyncio.run(V1.voz(s["texto"], mp3, *VOZ))
        dur = V1.a_wav(mp3, wav)
        wavs.append(wav)
        fotos = [f"s{i}_{j}.jpg" for j in range(len(s.get("imagenes", []))) if f"s{i}_{j}.jpg" in cred]
        subs = [(t0 + a, t0 + b, txt) for a, b, txt in V1.trocea(frases, 9)]
        srt += subs
        plan.append({"t0": t0, "dur": dur, "sec": s, "fotos": fotos, "subs": subs})
        t0 += dur
        print(f"  voz bloque {i}: {dur:.1f} s, {len(fotos)} fotos", flush=True)
    fin_voz = t0
    lista = tmp / "audio.txt"
    lista.write_text("".join(f"file '{w.name}'\n" for w in wavs), encoding="utf-8")
    subprocess.run([V1.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(tmp / "voz.wav")], check=True)
    # musica propia: fondo que se aparta al hablar, sintonia al principio y al final, barrido en cada cortinilla
    total = musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", INTRO, OUTRO, [p["t0"] for p in plan] + [fin_voz])
    print(f"  audio mezclado: {total:.1f} s", flush=True)

    # capas fijas
    sombra, cabecera = capa_sombra(), capa_cabecera(G["fecha"])
    bases, creds = {}, {}
    for p in plan:
        for f in p["fotos"]:
            if f not in bases:
                bases[f] = base_foto(dia / "imagenes" / f)
                creds[f] = capa_credito(cred[f])
        p["capa_t"] = capa_titulo(p["sec"]["titulo"], n, plan.index(p))
        p["capas_p"] = [capa_punto(x) for x in p["sec"]["puntos"]]
        p["capas_s"] = [(a, b, capa_subtitulo(t)) for a, b, t in p["subs"]] if subtitulos else []
        # el punto k aparece repartido a lo largo de la narracion del bloque
        k = len(p["capas_p"])
        p["t_p"] = [p["t0"] + 1.4 + j * (p["dur"] - 4.0) / max(k, 1) for j in range(k)]

    out = dia / "video_dinamico.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)],
                          stdin=subprocess.PIPE)
    nf = int(math.ceil(total * FPS))
    for fi in range(nf):
        t = fi / FPS
        if t < INTRO or t >= fin_voz:
            frame = cuadro_intro(t, G["fecha"]) if t < INTRO else cuadro_cierre(t - fin_voz, G["fecha"])
            d = ImageDraw.Draw(frame)
            q = (t - fin_voz) / CORTINILLA                  # cortinilla de entrada al cierre
            if 0 <= q < 1:
                x0 = int(AN * (2.2 * q - 1.2))
                d.rectangle([x0, 0, x0 + AN, AL], fill=ROJO + (255,))
                d.rectangle([x0 + AN, 0, x0 + AN + 40, AL], fill=AMARILLO + (255,))
            ff.stdin.write(frame.convert("RGB").tobytes())
            continue
        i = max(j for j, p in enumerate(plan) if p["t0"] <= t + 1e-9)
        p = plan[i]
        tl = t - p["t0"]
        # foto (y fundido con la siguiente)
        fotos = p["fotos"] or [None]
        tramo = p["dur"] / len(fotos)
        k = min(int(tl // tramo), len(fotos) - 1)
        def foto(kk, tt):
            f = fotos[kk]
            if f is None:
                return Image.new("RGB", (AN, AL), (15, 26, 46))
            return ken_burns(bases[f], min(max(tt / (tramo + FUNDIDO), 0), 1), i * 3 + kk)
        frame = foto(k, tl - k * tramo)
        resto = (k + 1) * tramo - tl
        if k + 1 < len(fotos) and resto < FUNDIDO:
            frame = Image.blend(frame, foto(k + 1, FUNDIDO - resto), 1 - resto / FUNDIDO)
        frame = frame.convert("RGBA")
        frame.alpha_composite(sombra)
        frame.alpha_composite(cabecera)
        # titular: entra deslizando
        a = suave((tl - 0.25) / 0.6)
        y_t = 200 if i else 260
        pega(frame, p["capa_t"], 100 - 70 * (1 - a), y_t, a)
        # puntos: aparecen de uno en uno
        y = y_t + p["capa_t"].height + 30
        for cp, tp in zip(p["capas_p"], p["t_p"]):
            b = suave((t - tp) / 0.45)
            if b > 0:
                pega(frame, cp, 100 + 50 * (1 - b), y, b)
            y += cp.height + 16
        # credito de la foto
        if fotos[k] is not None:
            c = creds[fotos[k]]
            pega(frame, c, AN - c.width - 40, 40, 0.95)
        # subtitulos
        for a0, b0, cs in p["capas_s"]:
            if a0 <= t < b0:
                pega(frame, cs, (AN - cs.width) / 2, AL - cs.height - 46)
                break
        # barra de avance
        d = ImageDraw.Draw(frame)
        d.rectangle([0, AL - 8, int(AN * (t - INTRO) / (fin_voz - INTRO)), AL], fill=AMARILLO + (255,))
        # cortinilla al empezar cada bloque
        if tl < CORTINILLA:
            q = tl / CORTINILLA
            x0 = int(AN * (2.2 * q - 1.2))
            d.rectangle([x0, 0, x0 + AN, AL], fill=ROJO + (255,))
            d.rectangle([x0 + AN, 0, x0 + AN + 40, AL], fill=AMARILLO + (255,))
        ff.stdin.write(frame.convert("RGB").tobytes())
        if fi % (FPS * 20) == 0:
            print(f"  fotograma {fi}/{nf}", flush=True)
    ff.stdin.close()
    ff.wait()
    (dia / "subtitulos.srt").write_text("\n".join(f"{j+1}\n{V1.hms(a)} --> {V1.hms(b)}\n{t}\n"
                                                  for j, (a, b, t) in enumerate(srt)), encoding="utf-8")
    creditos_txt = "\n".join(f"- {c['autor']} ({c['licencia']}): {c['pagina']}" for c in
                             {c["pagina"]: c for c in cred.values()}.values())
    desc = (dia / "descripcion.txt").read_text(encoding="utf-8") if (dia / "descripcion.txt").exists() else ""
    if "Fotografías" not in desc:
        (dia / "descripcion.txt").write_text(desc + "\n\nFotografías (Wikimedia Commons, licencias libres):\n" + creditos_txt,
                                             encoding="utf-8")
    print(f"VIDEO DINAMICO {total/60:.1f} min -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
