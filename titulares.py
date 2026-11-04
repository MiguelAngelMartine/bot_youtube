"""SUMARIO A PANTALLA COMPLETA (arranque del largo horizontal, elegido por el usuario el 1-nov-2026).
El video empieza directamente con los titulares del dia, sin presentacion: cada titular es una tarjeta a pantalla completa
con el lenguaje de la miniatura (foto del tema de fondo, protagonista recortado, letra enorme con relieve y una etiqueta
roja) que entra de golpe cuando la voz lo nombra. Despues, un golpe de marca (logo y sintonia) y empieza el primer bloque.

Cada item de la escena "sumario" puede llevar:
  "titular": 2-5 palabras de gancho, literales (si falta, se usa "texto"); "destaca": la palabra en amarillo;
  "etiqueta": tema en 1-3 palabras (por defecto, el numero); "persona": nombre con retrato en creditos.json;
  "foto": fichero de imagenes/ para el fondo (si falta, la primera foto de su bloque); "seccion": indice de su bloque.
Los items cuyo bloque es "sobrio" (tragedias) van en grises, con letra lisa y sin golpes."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

import genera_video2 as G2
import miniatura as M
from genera_video2 import AN, AL, AMARILLO, ROJO, BLANCO, suave

ENTRA = 0.28                                  # s que tarda el titular en caer en su sitio


def _fondo(ruta: Path | None, sobrio: bool):
    """Fondo un poco mas grande que la pantalla para poder acercarse despacio (Ken Burns)."""
    if ruta is None or not ruta.exists():
        return G2.fondo_marca(1.0).resize((int(AN * 1.08), int(AL * 1.08))).convert("RGBA")
    f = ImageOps.fit(Image.open(ruta).convert("RGB"), (int(AN * 1.08), int(AL * 1.08)), Image.LANCZOS)
    if sobrio:
        f = ImageOps.grayscale(f).convert("RGB")
    f = f.filter(ImageFilter.GaussianBlur(3))
    f = ImageEnhance.Brightness(f).enhance(0.55 if sobrio else 0.68)
    f = ImageEnhance.Contrast(f).enhance(1.15).convert("RGBA")
    f.alpha_composite(_oscuro().resize(f.size, Image.BILINEAR))    # la sombra de abajo va ya en la foto (una vez)
    return f


def _seccion_de(k, item, secs):
    if "seccion" in item:
        return item["seccion"]
    bloques = [i for i, s in enumerate(secs) if i > 0 and s["titulo"].lower() != "corrección"]
    return bloques[k] if k < len(bloques) else None


def prepara(ve, secs, carpeta: Path, fotos: dict, cred: dict, usadas: dict):
    """Tarjetas del sumario ya dibujadas (lo fijo) para animarlas luego fotograma a fotograma."""
    tarjetas = []
    n = len(ve["items"])
    for k, it in enumerate(ve["items"]):
        i = _seccion_de(k, it, secs)
        sec = secs[i] if i is not None and i < len(secs) else None
        sobrio = bool(sec and sec.get("tono") == "sobrio")
        foto = it.get("foto")
        if not foto and sec:                   # la primera foto de su bloque
            foto = next((p["ve"]["foto"] for p in sec["pasos"] if (p.get("ve") or {}).get("foto")), None)
        ruta = carpeta / foto if foto else None
        if foto and ruta.exists() and foto in cred:
            usadas[foto] = cred[foto]
        persona = None
        if it.get("persona") and it["persona"] in fotos and fotos[it["persona"]].exists():
            pr = fotos[it["persona"]]
            c = M.recorte(pr)
            if sobrio:
                c = Image.merge("RGBA", (*ImageOps.grayscale(c.convert("RGB")).convert("RGB").split(), c.getchannel("A")))
            esc = min(900 / c.height, 900 / c.width)
            persona = M.silueta(c.resize((int(c.width * esc), int(c.height * esc)), Image.LANCZOS))
            if pr.name in cred:
                usadas[pr.name] = cred[pr.name]
        ancho = 1750 if persona is None else AN - persona[0].width + 150 + persona[1] + 70
        tam, lineas = M.ajusta(it.get("titular") or it["texto"], it.get("destaca", ""), ancho, sobrio)
        texto = M.texto(lineas, min(tam, 190), sobrio, espacio=0.55)
        if not sobrio:
            texto = texto.rotate(3, resample=Image.BICUBIC, expand=True)
        eti = M.etiqueta((it.get("etiqueta") or f"{k + 1} de {n}").upper(), sobrio)
        num = M.etiqueta(f"{k + 1}/{n}", sobrio, 44) if it.get("etiqueta") and not sobrio else None
        tarjetas.append({"fondo": _fondo(ruta, sobrio), "persona": persona, "texto": texto, "eti": eti, "num": num,
                         "sobrio": sobrio, "cuando": it.get("cuando")})
    return tarjetas


def cuadro(tj, tl, t_abs):
    """Una tarjeta en el instante tl (s desde que entra)."""
    f = tj["fondo"]
    z = 1.0 + 0.06 * min(tl / 6.0, 1.0)                       # acercamiento lento
    cw, ch = int(AN * 1.08 / z), int(AL * 1.08 / z)
    x0, y0 = (f.width - cw) // 2, (f.height - ch) // 2
    fr = G2.escala(f, (AN, AL), box=(x0, y0, x0 + cw, y0 + ch))
    if tj["persona"]:
        c, pad = tj["persona"]
        a = suave(tl / 0.35)
        G2.pega(fr, c, AN - c.width + 150 + int(160 * (1 - a)), AL - c.height + pad + 30, a)
    t = tj["texto"]
    if tj["sobrio"]:
        a = suave(tl / 0.5)
        G2.pega(fr, t, 70, AL - t.height - 70 + int(30 * (1 - a)), a)
    else:                                                      # cae de golpe: grande y transparente -> su sitio
        a = min(1.0, tl / ENTRA)
        s = 1.0 + 0.35 * (1 - suave(a)) - 0.04 * max(0.0, 1 - abs(tl - ENTRA) / 0.12)
        tt = t.resize((max(1, int(t.width * s)), max(1, int(t.height * s))), Image.BILINEAR) if abs(s - 1) > 0.005 else t
        sacude = 10 * max(0.0, 1 - (tl - ENTRA) / 0.18) if tl > ENTRA else 0
        dx = int(sacude * ((int(t_abs * 50) % 3) - 1))
        G2.pega(fr, tt, 30 - (tt.width - t.width) // 2 + dx, AL - t.height - 50 - (tt.height - t.height) // 2, min(1.0, a * 1.6))
    e = tj["eti"]
    ae = suave((tl - 0.15) / 0.3)
    G2.pega(fr, e, 80 - int(60 * (1 - ae)), AL - t.height - 50 - e.height + 20, ae)
    if tj["num"]:
        G2.pega(fr, tj["num"], AN - tj["num"].width - 60, 50, ae)
    G2.pega(fr, G2.logo(90), 50, 40)
    if tl < 0.12 and not tj["sobrio"]:                          # destello al entrar
        fl = Image.new("RGBA", (AN, AL), (255, 255, 255, int(200 * (1 - tl / 0.12))))
        fr.alpha_composite(fl)
    return fr


_osc = []


def _oscuro():
    """Sombra fija abajo y en los bordes para que el texto se lea siempre."""
    if not _osc:
        g = Image.linear_gradient("L").resize((1, 620)).point(lambda v: int(225 * (v / 255) ** 1.3))
        capa = Image.new("RGBA", (AN, AL), (0, 0, 0, 0))
        negro = Image.new("RGBA", (AN, 620), (0, 0, 0, 255))
        negro.putalpha(g.resize((AN, 620)))
        capa.alpha_composite(negro, (0, AL - 620))
        _osc.append(capa)
    return _osc[0]

