"""SHORT VERTICAL DE UNA FRASE (decisión del usuario del 5-nov-2026). 1080x1920, 40-55 s (6-nov: más largo):
  1) gancho (desde el fotograma 0, que es también la miniatura): la persona recortada MUY grande sobre la imagen del
     tema en movimiento, el antetítulo («SÁNCHEZ, A FEIJÓO») y la frase literal enorme;
  2) contexto: el porqué, con las viñetas y fotos del tema pasando a pantalla completa arriba y el texto abajo;
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


def _fondo_tema(ruta):
    """6-nov-2026 (el usuario: «el fondo siempre azul parece un PowerPoint»): la imagen del tema a pantalla completa,
    desenfocada, con color y la luz de la marca, algo mayor que la pantalla para moverla despacio."""
    if ruta is None or not Path(ruta).exists():
        return _fondo().resize((int(AN * 1.12), int(AL * 1.12)))
    from PIL import ImageEnhance, ImageOps
    import titulares as TIT
    w, h = int(AN * 1.12), int(AL * 1.12)
    im = ImageOps.fit(Image.open(ruta).convert("RGB"), (w // 2, h // 2), Image.LANCZOS, centering=(0.5, 0.35))
    im = im.filter(ImageFilter.GaussianBlur(9))
    im = ImageEnhance.Color(im).enhance(1.35)
    im = ImageEnhance.Brightness(im).enhance(0.55).resize((w, h), Image.BILINEAR).convert("RGBA")
    im.alpha_composite(TIT._tinte((w, h), False))
    g = Image.linear_gradient("L").resize((w, h)).point(lambda v: int(max(0, v - 110) * 1.4))
    sombra = Image.new("RGBA", (w, h), (6, 10, 22, 255))
    sombra.putalpha(g)                                 # abajo, más oscuro: ahí van la frase y los subtítulos
    im.alpha_composite(sombra)
    return im


def _mueve(base, t, total):
    """Ken Burns del fondo: se acerca y se desplaza despacio durante todo el Short."""
    q = min(1.0, t / max(total, 1))
    z = 1.0 + 0.06 * q
    cw, ch = int(base.width / 1.12 / z * 1.0), int(base.height / 1.12 / z * 1.0)
    x0 = int((base.width - cw) * (0.3 + 0.4 * q))
    y0 = int((base.height - ch) * 0.5)
    return base.crop((x0, y0, x0 + cw, y0 + ch)).resize((AN, AL), Image.BILINEAR)


def _panel(ruta):
    """Viñeta o foto del tema para la parte de arriba durante el contexto (ancho completo, de ZONA[0] a ZONA[1])."""
    from PIL import ImageOps
    alto = ZONA[1] - ZONA[0]
    im = ImageOps.fit(Image.open(ruta).convert("RGB"), (int(AN * 1.1), int(alto * 1.1)), Image.LANCZOS,
                      centering=(0.5, 0.4))
    return im


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


ZONA = (150, 1050)                                    # la persona vive arriba (y de 150 a 1050): 6-nov, más grande


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


ALTO_CITA = 300                                       # la frase ocupa de 1180 a 1480; el contexto, de 1500 a 1690


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


def _seccion(dia, cita):
    """Bloque del episodio donde sale la frase (para usar sus viñetas y fotos)."""
    import shorts_guion as SG
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    for i, sec in enumerate(G["secciones"]):
        if i and SG._norm(cita)[:40] in SG._norm(json.dumps(sec, ensure_ascii=False)):
            return i, sec
    return None, None


def _imagenes_tema(dia, i, sec, quien):
    """Viñetas y fotos del bloque de la frase (sin la de la persona, que ya sale): el «B-roll» del contexto."""
    out = []
    if i is not None:
        out += sorted((dia / "vinetas").glob(f"s{i}_*.jpg"))
        for p in sec["pasos"]:
            f = (p.get("ve") or {}).get("foto")
            if f and (dia / "imagenes" / f).exists():
                out.append(dia / "imagenes" / f)
    return list(dict.fromkeys(out))[:5]


def main(fecha, n):
    dia = RAIZ / "dia" / fecha
    S = json.loads((dia / "shorts" / f"short_{n}.json").read_text(encoding="utf-8"))
    tmp = dia / "shorts" / f"tmp_{n}"
    tmp.mkdir(parents=True, exist_ok=True)
    texto = S["voz"]
    pal, dur = voz.locuta([{"di": texto}], "normal", tmp / "voz.wav", cola=0.4)
    T = E.Tiempos(texto, pal, 0.0)
    t_ctx = T.en(texto.find("». ") + 3) if "». " in texto else dur * 0.3
    k_rep = texto.find(f"{S['replica']['quien']} le responde") if S.get("replica") else -1
    t_rep = T.en(k_rep) if k_rep >= 0 else None        # (buscar solo el nombre fallaba si el contexto lo nombraba)
    t_fin = T.en(texto.find("Todo el cruce"))
    total = dur + 1.4

    i_sec, sec = _seccion(dia, S["cita"])
    broll = _imagenes_tema(dia, i_sec, sec, S["quien"])
    cab = _cabecera(fecha)
    p1 = _persona(dia, S["quien"], S.get("cargo", ""), (0.5, 0.36), 0.42)
    fondo_img = broll[0] if broll else None
    if fondo_img is None and p1 and not p1[3].startswith("Ilustración"):
        fondo_img = next((f for f, c in json.loads((dia / "creditos.json").read_text(encoding="utf-8")).items()
                          if c.get("persona") == S["quien"] and (dia / "imagenes" / f).exists()), None)
        fondo_img = dia / "imagenes" / fondo_img if fondo_img else None
    fondo = _fondo_tema(fondo_img)
    k1 = _kicker(S["kicker"].upper())
    c1 = _cita(S["cita"], S.get("destaca", ""))
    # 6-nov: el contexto, frase a frase y sincronizado con la voz (entero no cabía y se cortaba)
    c_ini = texto.find(S["contexto"].strip()[:30])
    frases_ctx, pos = [], c_ini
    for fr_ in re.split(r"(?<=[.?!])\s+", S["contexto"].strip()):
        k_ = texto.find(fr_[:25], pos)
        if k_ >= 0:
            frases_ctx.append((T.en(k_), _caja(fr_, tam=52)))
            pos = k_ + 1
    if not frases_ctx:
        frases_ctx = [(t_ctx, _caja(S["contexto"], tam=44))]

    def ctx_en(t):
        k_ = max([j for j, (tt, _) in enumerate(frases_ctx) if tt <= t + 0.05] or [0])
        return frases_ctx[k_][1], t - frases_ctx[k_][0]
    p2 = k2 = None
    if S.get("replica"):
        rp = S["replica"]
        p2 = _persona(dia, rp["quien"], rp.get("cargo", ""), (0.5, 0.36), 0.42)
        k2 = _kicker(f"{rp['quien'].split()[-1].upper()} RESPONDE")
    fte = fuente("Inter-SemiBold.ttf", 26)
    caps = C.grupos_palabras(T, set())
    ini = [x[0] for x in caps]
    # contexto: un panel del tema cada ~4,5 s (si no hay imágenes del tema, se queda la persona)
    fin_ctx = t_rep if t_rep is not None else t_fin
    paneles = []
    if broll:
        nk = max(1, min(len(broll), int((fin_ctx - t_ctx) / 4.5) or 1))
        paneles = [(t_ctx + k * (fin_ctx - t_ctx) / nk, _panel(broll[k])) for k in range(nk)]
    golpes = [0.0, t_ctx] + ([t_rep] if t_rep is not None else [])

    def persona_en(fr, p, t0, t, a=1.0):
        """La persona, grande, con un golpe de cámara al entrar (se acerca y se asienta)."""
        if not p:
            return
        im, x, y, credito = p
        tl = t - t0
        s_ = 1.0 + 0.10 * (1 - G2.suave(min(1.0, tl / 0.35))) + 0.03 * min(tl, 8) / 8
        if abs(s_ - 1) > 0.003:
            im = im.resize((int(im.width * s_), int(im.height * s_)), Image.BILINEAR)
        G2.pega(fr, im, x - (im.width - p[0].width) // 2, y - (im.height - p[0].height) // 2, a)
        ImageDraw.Draw(fr).text((AN - 30, ZONA[1] - 16), credito, font=fte, fill=(225, 230, 240, int(235 * a)), anchor="rd",
                                stroke_width=2, stroke_fill=(0, 0, 0, int(160 * a)))

    def panel_en(fr, t):
        k = max(j for j, (tp, _) in enumerate(paneles) if tp <= t + 1e-6) if any(tp <= t for tp, _ in paneles) else 0
        tp, im = paneles[k]
        tl = t - tp
        alto = ZONA[1] - ZONA[0]
        z = 1.0 + 0.06 * min(tl, 5) / 5
        cw, ch = int(im.width / 1.1 / z), int(im.height / 1.1 / z)
        x0 = int((im.width - cw) * (0.3 + 0.4 * min(tl, 5) / 5))
        y0 = (im.height - ch) // 2
        vista = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((AN, alto), Image.BILINEAR).convert("RGBA")
        entra = G2.suave(min(1.0, tl / 0.35)) if k > 0 else G2.suave(min(1.0, tl / 0.3))
        dx = int(AN * (1 - entra))
        fr.alpha_composite(vista, (dx, ZONA[0]) if dx < AN else (AN - 1, ZONA[0]))
        d = ImageDraw.Draw(fr)
        d.rectangle([0, ZONA[0] - 6, AN, ZONA[0]], fill=AMARILLO + (255,))
        d.rectangle([0, ZONA[1], AN, ZONA[1] + 6], fill=AMARILLO + (255,))
        ff = fuente("Inter-SemiBold.ttf", 22)
        et = "Ilustración IA" if "vinetas" in str(broll[k]) else "Foto del tema"
        d.text((AN - 24, ZONA[1] - 14), et, font=ff, fill=(255, 255, 255, 230), anchor="rd")

    def cuadro(t):
        fr = _mueve(fondo, t, total).convert("RGBA")
        if t_rep is not None and t_rep <= t < t_fin:                  # 3) réplica
            tl = t - t_rep
            persona_en(fr, p2, t_rep, t, G2.suave(min(1.0, tl / 0.3)))
            fr.alpha_composite(k2, (60, 1080))
            n_ = max(1, int(len(S["replica"]["cita"]) * min(1.0, (tl - 0.3) / 1.6)))
            cr = _cita_cache(S["replica"]["cita"][:n_] if tl < 1.9 else S["replica"]["cita"], "")
            fr.alpha_composite(cr, (40, 1180))
        elif t >= t_fin:                                             # 4) cierre
            lg = G2.logo(300)
            tl = t - t_fin
            s_ = 1.0 + 0.25 * (1 - G2.suave(min(1.0, tl / 0.4)))
            lg = lg.resize((int(lg.width * s_), int(lg.height * s_)), Image.BILINEAR)
            fr.alpha_composite(lg, ((AN - lg.width) // 2, 470 - (lg.height - 300) // 2))
            d = ImageDraw.Draw(fr)
            d.text((AN // 2, 900), "Todo el cruce, en el", font=fuente("Inter-Black.ttf", 66), fill=BLANCO + (255,), anchor="mm")
            d.text((AN // 2, 990), "vídeo de hoy", font=fuente("Inter-Black.ttf", 66), fill=AMARILLO + (255,), anchor="mm")
            pulso = 1.0 + 0.04 * math.sin(tl * 6)
            w2, h2 = int(260 * pulso), int(58 * pulso)
            d.rounded_rectangle([AN // 2 - w2, 1110 - h2, AN // 2 + w2, 1110 + h2], radius=h2, fill=ROJO + (255,))
            d.text((AN // 2, 1110), "SUSCRÍBETE", font=fuente("Inter-Black.ttf", 56), fill=BLANCO + (255,), anchor="mm")
        elif t >= t_ctx and paneles:                                 # 2) contexto con imágenes del tema
            panel_en(fr, t)
            fr.alpha_composite(k1, (60, ZONA[1] + 40))
            ctx, tc = ctx_en(t)
            a = G2.suave(min(1.0, tc / 0.25))
            G2.pega(fr, ctx, 60, ZONA[1] + 150 + int(40 * (1 - a)), a)
        else:                                                        # 1) gancho (y contexto sin imágenes)
            persona_en(fr, p1, 0.0, t)
            fr.alpha_composite(k1, (60, 1080))
            if t < t_ctx:
                fr.alpha_composite(c1, (40, 1180))
            else:                                                    # el contexto ocupa el sitio de la frase
                ctx, tc = ctx_en(t)
                a = G2.suave(min(1.0, tc / 0.25))
                G2.pega(fr, ctx, 60, 1190 + int(40 * (1 - a)), a)
        for g in golpes:                                             # destello breve en cada cambio de parte
            if 0 <= t - g < 0.08 and g > 0:
                fr.alpha_composite(Image.new("RGBA", (AN, AL), (255, 255, 255, int(150 * (1 - (t - g) / 0.08)))))
        fr.alpha_composite(cab, (0, 0))
        ImageDraw.Draw(fr).rectangle([0, AL - 12, int(AN * min(1.0, t / dur)), AL], fill=AMARILLO + (255,))
        j = max(0, np.searchsorted(ini, t, side="right") - 1)    # subtítulos grandes
        if t < caps[j][1] and t >= caps[j][0]:
            _, _, ws, clave, _ = caps[j]
            cp = C.capa_cap(ws, clave, 0, 0.9, AN - 120)
            fr.alpha_composite(cp, ((AN - cp.width) // 2, 1760 - cp.height // 2))
        ImageDraw.Draw(fr).text((AN // 2, AL - 50), f"Fuente: {S.get('fuente', '')}"[:70], font=fte,
                                fill=(190, 198, 215, 255), anchor="mm")
        return fr

    _cc = {}

    def _cita_cache(txt, dest):
        if txt not in _cc:
            _cc[txt] = _cita(txt, dest, max_tam=104)
        return _cc[txt]

    cortes = [x for x in (t_ctx, t_rep, t_fin) if x] + [tp for tp, _ in paneles[1:]]
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
    S["creditos"] = [p[3] + f" ({nom})" for p, nom in ((p1, S["quien"]), (p2, (S.get("replica") or {}).get("quien")))
                     if p]
    cred_all = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    for f in broll:                                    # las imágenes del tema que salen en el contexto o el fondo
        if "vinetas" in str(f):
            continue
        c_ = cred_all.get(Path(f).name, {})
        S["creditos"].append(f"Foto: {c_.get('autor', '')[:40]} · {c_.get('licencia', '')} (tema)")
    if any("vinetas" in str(f) for f in broll):
        S["creditos"].append("Ilustración IA (viñetas del tema)")
        org = dia / "vinetas" / "origen.json"
        org = json.loads(org.read_text(encoding="utf-8")) if org.exists() else {}
        S["sintetico"] = any(org.get(Path(f).stem, {}).get("persona") for f in broll)   # personas reales dibujadas
    S["duracion"] = round(total, 1)
    (dia / "shorts" / f"short_{n}.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"SHORT {n}: {total:.1f} s -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
