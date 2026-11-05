"""SHORT VERTICAL DE UNA FRASE (decisión del usuario del 5-nov-2026). 1080x1920, 25-35 s:
  1) gancho (desde el fotograma 0, que es también la miniatura): la persona recortada en grande, el antetítulo
     («SÁNCHEZ, A FEIJÓO») y la frase literal enorme;
  2) contexto: el porqué, en un recuadro;
  3) réplica, si la hay: el aludido y su frase escribiéndose;
  4) cierre: «Todo el cruce, en el vídeo de hoy» y suscribirse.
Voz de Tristán, subtítulos grandes, música baja y crédito de las fotos. Fotos siempre a color, contorno suave.
Uso: python short.py AAAA-MM-DD N     -> dia/<fecha>/shorts/short_N.mp4 y short_N_portada.png"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import corto as C
import episodio as E
import genera_video as V1
import genera_video2 as G2
import ia_vinetas as IAV
import miniatura as M
import musica
import voz
from genera_video2 import AMARILLO, BLANCO, ROJO, fuente

RAIZ = Path(__file__).parent
AN, AL, FPS = 1080, 1920, 30
NAVY = (12, 20, 38)


def _fondo():
    im = Image.new("RGB", (AN, AL), NAVY)
    d = ImageDraw.Draw(im)
    for y in range(0, AL, 20):                         # trama de cómic, muy suave
        for x in range((y // 20) % 2 * 10, AN, 20):
            d.ellipse([x, y, x + 6, y + 6], fill=(24, 36, 70))
    g = Image.linear_gradient("L").resize((AN, AL)).point(lambda v: int(v * 0.75))
    im.paste(Image.new("RGB", (AN, AL), (6, 10, 22)), (0, 0), g)
    return im.convert("RGBA")


def _cabecera(fecha):
    cab = Image.new("RGBA", (AN, 150))
    d = ImageDraw.Draw(cab)
    d.rectangle([0, 0, AN, 10], fill=ROJO + (255,))
    d.rectangle([0, 10, AN, 16], fill=AMARILLO + (255,))
    cab.alpha_composite(G2.logo(80), (40, 42))
    d.text((140, 82), "EL HOYFORMATIVO", font=fuente("Inter-Black.ttf", 40), fill=AMARILLO + (255,), anchor="lm")
    y, m, dd = (int(x) for x in fecha[:10].split("-"))
    fe = f"{dd} {['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'][m - 1]}"
    d.rounded_rectangle([AN - 200, 54, AN - 40, 112], radius=10, fill=ROJO + (255,))
    d.text((AN - 120, 83), fe, font=fuente("Inter-Black.ttf", 36), fill=BLANCO + (255,), anchor="mm")
    return cab


ZONA = (150, 940)                                     # la persona vive en la mitad de arriba (y de 150 a 940)


def _busca_foto(dia, nombre):
    """Sin retrato del día: la primera foto de su categoría de Commons en la que se detecta una cara (con crédito)."""
    import fotos as F
    try:
        w = F.retrato_wikidata(nombre)                  # primero, su retrato principal de Wikidata
        cands = ([w] if w else []) + F.commons_categoria(nombre, 14)
        cands.sort(key=lambda c_: 0 if c_["fuente"].startswith("Wikidata") or any(
            x in c_["titulo"].lower() for x in ("retrato", "portrait", "oficial", "official")) else 1)
    except Exception:
        return None
    for k, cd in enumerate(cands):
        im = F.baja(F.original(cd["url"]), 2400) or F.baja(cd["url"], 2400)
        if im is None:
            continue
        import hashlib
        nom = f"short_{F.slug(nombre)}_{hashlib.sha1(cd['url'].encode()).hexdigest()[:8]}.jpg"   # un nombre por foto: sin cachés cruzadas
        (dia / "imagenes").mkdir(exist_ok=True)
        im.save(dia / "imagenes" / nom, quality=92)
        rc = M.recorte(dia / "imagenes" / nom)
        k_ = M.cara(rc)
        # un retrato de verdad: una cara grande dentro del recorte (en las fotos de grupo la cara es pequeña) y nítida
        if k_ and k_[2] >= 0.22 * rc.width and k_[3] >= 140:
            cred_f = dia / "creditos.json"
            cred = json.loads(cred_f.read_text(encoding="utf-8")) if cred_f.exists() else {}
            cred[nom] = {k_: cd[k_] for k_ in ("titulo", "url", "autor", "licencia", "pagina", "fuente")} | {"persona": nombre}
            cred_f.write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
            return dia / "imagenes" / nom
    return None


def _persona(dia, nombre, cargo, centro, alto_cara):
    """(imagen, x, y, credito) de la persona en la mitad de arriba: foto real a color con contorno suave (la del día o,
    si no hay, de su categoría de Commons), o la ilustración de su ámbito."""
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    fotos = C.fotos_personas({nombre}, cred, dia / "imagenes")
    ruta = fotos.get(nombre) if nombre in fotos and fotos[nombre].exists() else _busca_foto(dia, nombre)
    if ruta:
        cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8"))
        c = M.recorte(ruta)
        alto = ZONA[1] - ZONA[0]
        r = M.encuadre_cara(c, AN, alto, (0.5, 0.42), 0.34, suave=True)
        if r is None:
            k = alto / c.height
            cc, pad = M.silueta_suave(c.resize((int(c.width * k), int(c.height * k)), Image.LANCZOS))
            r = (cc, (AN - cc.width) // 2, 0)
        im, x, y = r
        caja2 = Image.new("RGBA", (AN, alto))          # recorte a la zona: el cuerpo no baja a los textos
        caja2.paste(im, (x, y), im)
        cr = cred.get(ruta.name, {})
        autor = re.sub(r"^(Foto:\s*)+", "", cr.get("autor", ""))
        return caja2, 0, ZONA[0], f"Foto: {autor[:40]} · {cr.get('licencia', '')}"
    amb = IAV.ilustracion_ambito(cargo)
    if amb:
        im = Image.open(amb).convert("RGB")
        im.thumbnail((760, ZONA[1] - ZONA[0] - 90), Image.LANCZOS)   # que no tape el crédito (y = 935)
        im = im.convert("RGBA")
        return im, (AN - im.width) // 2, ZONA[0] + 30, "Ilustración IA · sin foto libre"
    return None


def _kicker(txt, tam=56):
    f = fuente("Inter-Black.ttf", tam)
    w = int(f.getlength(txt)) + 56
    e = Image.new("RGBA", (w + 12, int(tam * 1.5) + 12))
    d = ImageDraw.Draw(e)
    d.rectangle([10, 10, w + 10, int(tam * 1.5) + 10], fill=(0, 0, 0, 150))
    d.rectangle([0, 0, w, int(tam * 1.5)], fill=ROJO + (255,))
    d.text((28, tam * 0.75 + 2), txt, font=f, fill=BLANCO + (255,), anchor="lm")
    return e


ALTO_CITA = 330                                       # la frase ocupa de 1090 a 1420; el contexto, de 1430 a 1640


def _cita(txt, destaca, ancho=960, max_tam=118):
    """Frase en Anton, blanca, con la palabra clave en franja amarilla (como la miniatura «informativo»)."""
    palabras = ("«" + txt.strip().rstrip(".") + "»").upper().split()
    tam = max_tam
    while tam > 60:
        f = fuente(M.ANTON, tam)
        lineas, cur = [], []
        for w in palabras:
            if cur and f.getlength(" ".join(cur + [w])) + 40 > ancho:
                lineas.append(cur)
                cur = [w]
            else:
                cur.append(w)
        lineas.append(cur)
        if len(lineas) * tam * 1.05 <= ALTO_CITA:
            break
        tam -= 6
    marca = {w.lower().strip(M.LIMPIA) for w in (destaca or "").split()}
    return M._txt_capa(lineas, fuente(M.ANTON, tam), marca)


def _caja(txt, ancho=940, tam=46):
    f = fuente("ComicNeue-Bold.ttf", tam)
    ls = C.lineas(txt, f, ancho - 50)[:6]
    h = 40 + int(tam * 1.25) * len(ls)
    im = Image.new("RGBA", (ancho + 14, h + 14))
    d = ImageDraw.Draw(im)
    d.rectangle([12, 12, ancho + 12, h + 12], fill=(0, 0, 0, 255))
    d.rectangle([0, 0, ancho, h], fill=(250, 240, 205, 255), outline=(0, 0, 0, 255), width=5)
    for j, l in enumerate(ls):
        d.text((26, 20 + int(tam * 1.25) * j), l, font=f, fill=(15, 15, 15, 255))
    return im


def main(fecha, n):
    dia = RAIZ / "dia" / fecha
    S = json.loads((dia / "shorts" / f"short_{n}.json").read_text(encoding="utf-8"))
    tmp = dia / "shorts" / f"tmp_{n}"
    tmp.mkdir(parents=True, exist_ok=True)
    texto = S["voz"]
    pal, dur = voz.locuta([{"di": texto}], "normal", tmp / "voz.wav", cola=0.4)
    T = E.Tiempos(texto, pal, 0.0)
    t_ctx = T.en(texto.find("». ") + 3) if "». " in texto else dur * 0.45
    t_rep = T.en(texto.find(S["replica"]["quien"], 5)) if S.get("replica") else None
    t_fin = T.en(texto.find("Todo el cruce"))
    total = dur + 1.4

    fondo, cab = _fondo(), _cabecera(fecha)
    p1 = _persona(dia, S["quien"], S.get("cargo", ""), (0.5, 0.27), 0.17)
    k1 = _kicker(S["kicker"].upper())
    c1 = _cita(S["cita"], S.get("destaca", ""))
    ctx = _caja(S["contexto"], tam=38)
    if S.get("replica"):
        rp = S["replica"]
        p2 = _persona(dia, rp["quien"], rp.get("cargo", ""), (0.5, 0.27), 0.15)
        k2 = _kicker(f"{rp['quien'].split()[-1].upper()} RESPONDE")
    fte = fuente("Inter-SemiBold.ttf", 26)
    caps = C.grupos_palabras(T, set())
    ini = [x[0] for x in caps]

    def persona_en(fr, p, a=1.0, dy=0):
        if not p:
            return
        im, x, y, credito = p
        G2.pega(fr, im, x, y + dy, a)
        ImageDraw.Draw(fr).text((AN // 2, 935), credito, font=fte, fill=(200, 205, 215, int(220 * a)), anchor="mm")

    def cuadro(t):
        fr = fondo.copy()
        if t_rep is not None and t >= t_rep and t < t_fin:          # 3) réplica
            tl = t - t_rep
            persona_en(fr, p2, G2.suave(tl / 0.3))
            fr.alpha_composite(k2, (60, 975))
            n_ = max(1, int(len(S["replica"]["cita"]) * min(1.0, (tl - 0.3) / 1.6)))
            cr = _cita_cache(S["replica"]["cita"][:n_] if tl < 1.9 else S["replica"]["cita"], "")
            fr.alpha_composite(cr, (40, 1075))
        elif t >= t_fin:                                             # 4) cierre
            lg = G2.logo(260)
            fr.alpha_composite(lg, ((AN - lg.width) // 2, 520))
            d = ImageDraw.Draw(fr)
            d.text((AN // 2, 900), "Todo el cruce, en el", font=fuente("Inter-Black.ttf", 62), fill=BLANCO + (255,), anchor="mm")
            d.text((AN // 2, 985), "vídeo de hoy", font=fuente("Inter-Black.ttf", 62), fill=AMARILLO + (255,), anchor="mm")
            d.rounded_rectangle([AN // 2 - 250, 1100, AN // 2 + 250, 1210], radius=55, fill=ROJO + (255,))
            d.text((AN // 2, 1155), "SUSCRÍBETE", font=fuente("Inter-Black.ttf", 54), fill=BLANCO + (255,), anchor="mm")
        else:                                                        # 1) gancho y 2) contexto
            z = 1.0 + 0.025 * min(t, 6) / 6
            persona_en(fr, p1, 1.0, int(-12 * z))
            fr.alpha_composite(k1, (60, 975))
            fr.alpha_composite(c1, (40, 1075))
            if t >= t_ctx:                                           # el contexto entra encima, abajo
                a = min(1.0, (t - t_ctx) / 0.25)
                G2.pega(fr, ctx, 60, 1440 + int(40 * (1 - a)), a)
        fr.alpha_composite(cab, (0, 0))
        ImageDraw.Draw(fr).rectangle([0, AL - 12, int(AN * min(1.0, t / dur)), AL], fill=AMARILLO + (255,))
        j = max(0, np.searchsorted(ini, t, side="right") - 1)    # subtítulos grandes
        if t < caps[j][1] and t >= caps[j][0]:
            _, _, ws, clave, _ = caps[j]
            cp = C.capa_cap(ws, clave, 0, 0.9, AN - 120)
            fr.alpha_composite(cp, ((AN - cp.width) // 2, 1745 - cp.height // 2))
        ImageDraw.Draw(fr).text((AN // 2, AL - 50), f"Fuente: {S.get('fuente', '')}"[:70], font=fte,
                                fill=(170, 178, 195, 255), anchor="mm")
        return fr

    _cc = {}

    def _cita_cache(txt, dest):
        if txt not in _cc:
            _cc[txt] = _cita(txt, dest, max_tam=104)
        return _cc[txt]

    cortes = [x for x in (t_ctx, t_rep, t_fin) if x]
    musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", 0.0, 1.4, [], efectos=[(x, "whoosh") for x in cortes], con_sintonia=False)
    cuadro(0.6).convert("RGB").save(dia / "shorts" / f"short_{n}_portada.png")       # el fotograma 0 = la miniatura
    out = dia / "shorts" / f"short_{n}.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "21", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], stdin=subprocess.PIPE)
    for fi in range(int(math.ceil(total * FPS))):
        ff.stdin.write(cuadro(fi / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
    # créditos para la descripción de YouTube (los lee subir.py)
    S["creditos"] = [p[3] + f" ({nom})" for p, nom in ((p1, S["quien"]), (p2 if S.get("replica") else None,
                     (S.get("replica") or {}).get("quien"))) if p]
    S["duracion"] = round(total, 1)
    (dia / "shorts" / f"short_{n}.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"SHORT {n}: {total:.1f} s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
