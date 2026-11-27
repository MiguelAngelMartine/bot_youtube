"""MINIATURA PROFESIONAL DEL LARGO (27-nov-2026, el usuario: «muy importante: la calidad de las miniaturas tiene que subir
mucho»). Sigue el brief de NORMAS.md §6 («Miniaturas»): caras GRANDES (del pecho para arriba, ≥ 55 % del alto), un solo
punto de atención, 2-4 palabras ENTRE COMILLAS (es una cita, no la voz del canal), contraste alto, nada pisa una cara, la
esquina de abajo a la derecha libre (ahí va la duración de YouTube). Las caras salen de Imagenes/Políticos TAL CUAL (solo
escala y recorte: NORMAS §6, los rasgos son intocables).

Hace CUATRO diseños y un juez con visión (Gemini; si no responde, los modelos gratuitos) los puntúa con la lista del
brief, a tamaño completo y a 320 px (móvil); se queda el mejor. Informe en dia/<fecha>/revision/miniatura.md.
  duelo       las dos caras enormes, una a cada lado, mirándose; la frase abajo, sobre los pechos.
  primer_plano una cara enorme a la derecha; la frase apilada a la izquierda; quién lo dice en una etiqueta.
  cita        comillas gigantes amarillas, la frase a la izquierda, la cara a la derecha con filo amarillo.
  reaccion    quien lo dice, enorme a la derecha; a quien se lo dice, en un recuadro pequeño abajo a la izquierda.
Uso: python miniatura_pro.py AAAA-MM-DD [--sin-juez]"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import miniatura_moderna as MM

RAIZ = Path(__file__).parent
W, H = MM.W, MM.H
AMARILLO, ROJO, NAVY = MM.AMARILLO, MM.ROJO, MM.NAVY
BLANCO = (255, 255, 255)
LIBRE_DER, LIBRE_ABA = 190, 70          # esquina de la duración de YouTube


def _busto(ruta, alto, corte=0.32):
    return MM.busto(ruta, alto, corte)


def _pega(im, capa, x, y):
    """Pega una capa RGBA aunque salga por los bordes."""
    t = Image.new("RGBA", im.size, (0, 0, 0, 0))
    t.paste(capa, (x, y))
    im.alpha_composite(t)


def _figura(im, ruta, alto, lado, corte=0.32, color=BLANCO, fuera=0.12, espejo=False):
    b = _busto(ruta, alto, corte)
    if espejo:
        b = b.transpose(Image.FLIP_LEFT_RIGHT)
    c, pad = MM.contorno(b, MM.GROSOR, color)
    sale = int(b.width * fuera)
    x = -pad - sale if lado == "izq" else W - c.width + pad + sale
    y = H - c.height + pad + 6
    _pega(im, c, x, y)
    return (x + pad, y + pad, x + pad + b.width, y + pad + b.height)


def _frase(t):
    t = re.sub(r"[«»\"“”]", "", t or "").strip().rstrip(".")
    return t


def _palabras(frase, comillas=True):
    pal = frase.upper().split()
    if comillas and pal:
        pal[0], pal[-1] = "“" + pal[0], pal[-1] + "”"   # Anton dibuja «» como «<<»
    return pal


def _texto(d, x, y, frase, destaca, tam, ancho, alinea="izq", comillas=True):
    return MM._texto_bloque(d, x, y, _palabras(frase, comillas), (destaca or "").upper(), tam, ancho, alinea)


def _alto(frase, tam, ancho, comillas=True):
    return MM.alto_bloque(_palabras(frase, comillas), tam, ancho)


def _tam(frase, ancho, alto_max, tam=170, minimo=70, comillas=True):
    pal = _palabras(frase, comillas)
    while (MM.alto_bloque(pal, tam, ancho) > alto_max or
           max(MM.fuente("Anton-Regular.ttf", tam).getlength(w) for w in pal) > ancho) and tam > minimo:
        tam -= 4
    return tam


def _brillo(im, lado, color):
    """Un halo de color de marca detrás de cada persona: separa la figura del fondo sin desenfocarlo."""
    g = Image.radial_gradient("L").resize((W, H * 2)).point(lambda v: int(max(0, 255 - v) * 0.55))
    c = Image.new("RGBA", (W, H * 2), color + (255,))
    c.putalpha(g)
    c = c.crop((0, H // 2, W, H // 2 + H))
    off = -W // 2 + 120 if lado == "izq" else W // 2 - 120
    _pega(im, c, off, 0)


def duelo(salida, frase, destaca, quien, rival, etiqueta, fondo_ruta, comillas=True):
    im = MM.fondo(fondo_ruta, lado="izq")
    _brillo(im, "izq", (200, 30, 45))
    _brillo(im, "der", (30, 90, 200))
    alto = int(H * 0.98)
    _figura(im, quien, alto, "izq", fuera=0.10)
    _figura(im, rival, alto, "der", fuera=0.10)
    # la frase a todo lo ancho abajo, sobre los pechos (las caras quedan en el 55 % de arriba), con franja oscura
    ancho, alto_max = W - 180, int(H * 0.36)
    tam = _tam(frase, ancho, alto_max, tam=150, minimo=60, comillas=comillas)
    alto_t = _alto(frase, tam, ancho, comillas)
    hb = alto_t + 90 + LIBRE_ABA
    banda = Image.new("RGBA", (W, hb), (0, 0, 0, 255))
    banda.putalpha(Image.linear_gradient("L").resize((W, hb)).point(lambda v: int(min(255, v * 1.6) * 0.9)))
    im.alpha_composite(banda, (0, H - hb))
    d = ImageDraw.Draw(im)
    _texto(d, W // 2, H - LIBRE_ABA - 14 - alto_t, frase, destaca, tam, ancho, "centro", comillas)   # duración libre
    tw = MM.fuente("Inter-Black.ttf", 30).getlength(etiqueta.upper()) + 36
    MM._chip(d, int(W / 2 - tw / 2), 34, etiqueta.upper(), tam=30)
    im.convert("RGB").save(salida, quality=95)


def primer_plano(salida, frase, destaca, quien, nombre, fondo_ruta, comillas=True):
    im = MM.fondo(fondo_ruta, lado="izq")
    _brillo(im, "der", (200, 30, 45))
    bb = _figura(im, quien, int(H * 1.08), "der", corte=0.30, fuera=0.06)
    d = ImageDraw.Draw(im)
    ancho = min(640, bb[0] + int((bb[2] - bb[0]) * 0.12) - 56 - 30)   # hasta el hombro: nunca sobre la cara
    tam = _tam(frase, ancho, H - 150 - 70, comillas=comillas)
    y = _texto(d, 56, 60, frase, destaca, tam, ancho, comillas=comillas)
    MM._chip(d, 56, min(y + 16, H - 90), nombre.upper(), tam=34)
    im.convert("RGB").save(salida, quality=95)


def cita(salida, frase, destaca, quien, nombre, fondo_ruta):
    im = MM.fondo(fondo_ruta, lado="izq")
    bb = _figura(im, quien, int(H * 1.04), "der", corte=0.31, color=AMARILLO, fuera=0.06)
    d = ImageDraw.Draw(im)
    fq = MM.fuente("Inter-Black.ttf", 260)
    d.text((34, -40), "“", font=fq, fill=AMARILLO)
    ancho = min(620, bb[0] + int((bb[2] - bb[0]) * 0.12) - 60 - 30)
    tam = _tam(frase, ancho, H - 190 - 110, comillas=False)
    y = _texto(d, 60, 190, frase, destaca, tam, ancho, comillas=False)
    fn = MM.fuente("Inter-Black.ttf", 42)
    d.rectangle((60, y + 22, 70, y + 78), fill=ROJO)
    d.text((88, y + 26), nombre.upper(), font=fn, fill=BLANCO)
    im.convert("RGB").save(salida, quality=95)


def reaccion(salida, frase, destaca, quien, rival, nombre, nombre_rival, fondo_ruta, comillas=True):
    im = MM.fondo(fondo_ruta, lado="izq")
    _brillo(im, "der", (200, 30, 45))
    bb = _figura(im, quien, int(H * 1.06), "der", corte=0.30, fuera=0.06)
    d = ImageDraw.Draw(im)
    # recuadro pequeño del aludido, abajo a la izquierda
    r = _busto(rival, 300, 0.26)
    k = min(1.0, 300 / r.width)
    r = r.resize((int(r.width * k), int(r.height * k)))
    caja = Image.new("RGBA", (320, 250), (20, 26, 44, 255))
    caja.paste(r, ((320 - r.width) // 2, 250 - r.height + 40), r)
    x0, y0 = 50, H - 250 - 40
    d.rectangle((x0 - 6, y0 - 6, x0 + 326, y0 + 256), fill=BLANCO)
    im.alpha_composite(caja, (x0, y0))
    d = ImageDraw.Draw(im)
    MM._chip(d, x0, y0 - 64, ("A " + nombre_rival).upper(), tam=28)
    ancho = min(660, bb[0] + int((bb[2] - bb[0]) * 0.12) - 56 - 30)
    tam = _tam(frase, ancho, y0 - 80 - 50, tam=150, comillas=comillas)
    _texto(d, 56, 44, frase, destaca, tam, ancho, comillas=comillas)
    MM._chip(d, W - 40 - MM.fuente("Inter-Black.ttf", 30).getlength(nombre.upper()) - 36, 34, nombre.upper(), tam=30)
    im.convert("RGB").save(salida, quality=95)


CRITERIOS = """Eres director de arte de un canal de YouTube de noticias de política española (neutral y riguroso) y experto
en miniaturas que consiguen clics sin engañar. Te doy varias versiones de la miniatura de un vídeo; cada una va a tamaño
completo y reducida a 320 px (como se ve en el móvil). Puntúa CADA una de 0 a 10 con este brief:
1. Caras GRANDES y nítidas (del pecho para arriba, al menos media miniatura de alto); se reconoce a la persona a 320 px.
2. Un solo punto de atención: se entiende en 1 segundo quién dice qué (o quién contra quién).
3. Texto de 2-4 palabras, enorme, legible a 320 px, ENTRE COMILLAS (es una cita, no la opinión del canal).
4. Nada tapa una cara ni letras clave; nada se corta raro; la esquina de abajo a la derecha (la duración) sin nada clave.
5. Contraste alto y acabado profesional (no amateur): tipografía, color, limpieza, sin huecos vacíos sin sentido.
6. El gesto de la cara encaja con la noticia (una sonrisa en un choque duro resta).
7. Fiel al vídeo: no promete lo que no cuenta, sin morbo.
Responde SOLO JSON: {"versiones": [{"archivo": "...", "nota": 0-10, "legible_movil": true/false, "problemas": ["..."]}],
"elegida": "archivo", "por_que": "una frase"}"""


def juez(dia, archivos, contexto=""):
    import gem
    partes = [CRITERIOS + ("\n\nDe qué va el vídeo: " + contexto if contexto else "")]
    for a in archivos:
        im = Image.open(dia / a)
        partes += [f"Versión «{a}», tamaño completo:", gem.imagen(im, 1280), f"Versión «{a}», a 320 px:", gem.imagen(im, 320)]
    try:
        r = gem.pide(partes, como_json=True, limite_s=240)
    except Exception as e:
        print(f"  (juez sin respuesta: {type(e).__name__})")
        return None
    if not isinstance(r, dict) or not r.get("versiones"):
        return None
    return r


def _datos(fecha):
    import presentador as P
    dia = RAIZ / "dia" / fecha
    E = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    items = [it for s_ in E["secciones"] for p in s_.get("pasos", []) for it in (p.get("ve") or {}).get("items", [])
             if isinstance(it, dict) and it.get("titular")]
    item = next((it for it in items if it.get("persona") and MM._imagen(it["persona"])), None)
    if not item:
        return None
    fondos, _, _ = P.catalogo()
    try:
        fnd = json.loads((dia / "fondos_elegidos.json").read_text(encoding="utf-8"))
        fnd = next(iter(fnd.values())) if isinstance(fnd, dict) else fnd[0]
    except Exception:
        fnd = fondos[0]
    m = re.search(r"\ba\s+(.+)$", item.get("etiqueta", ""))
    rival = m.group(1).strip() if m else ""
    if not (rival and MM._imagen(rival)):
        rival = next((it["persona"] for it in items if it.get("persona") and it["persona"] != item["persona"]
                      and MM._imagen(it["persona"])), "")
    if rival and P._n(rival).split()[-1] == P._n(item["persona"]).split()[-1]:
        rival = ""
    # 27-nov-2026: comillas SOLO si la frase es literal (sale dentro de una cita «…» del episodio); si es un titular
    # nuestro, va sin comillas y sin el diseño «cita»
    dicho = " ".join(p.get("di", "") for s_ in E["secciones"] for p in s_.get("pasos", []))   # lo locutado, no titulares
    citas = re.findall(r"«([^»]+)»", dicho)
    literal = any(P._n(_frase(item["titular"])) in P._n(c) for c in citas)
    contexto = f"{E.get('titulo_video', '')}. " + " ".join(p.get("di", "") for p in E["secciones"][0].get("pasos", []))[:800]
    return {"frase": _frase(item["titular"]), "destaca": item.get("destaca", ""), "persona": item["persona"],
            "rival": rival, "etiqueta": item.get("etiqueta", "") or item["persona"], "fondo": fnd, "contexto": contexto, "literal": literal}


def _corto(nombre):
    p = (nombre or "").split()
    return p[-1] if p else ""


def versiones(fecha):
    dia = RAIZ / "dia" / fecha
    D = _datos(fecha)
    if not D:
        return [], None
    q = MM._imagen(D["persona"])
    r = MM._imagen(D["rival"]) if D["rival"] else None
    hechas = []
    c = D["literal"]
    planes = [("primer_plano", lambda s: primer_plano(s, D["frase"], D["destaca"], q, D["persona"], D["fondo"], c))]
    if c:
        planes.append(("cita", lambda s: cita(s, D["frase"], D["destaca"], q, D["persona"], D["fondo"])))
    if r:
        planes = [("duelo", lambda s: duelo(s, D["frase"], D["destaca"], q, r, D["etiqueta"], D["fondo"], c)),
                  ("reaccion", lambda s: reaccion(s, D["frase"], D["destaca"], q, r, _corto(D["persona"]),
                                                  _corto(D["rival"]), D["fondo"], c))] + planes
    for nombre, fn in planes:
        s = dia / f"miniatura_{nombre}.png"
        try:
            fn(s)
            hechas.append(s.name)
        except Exception as e:
            print(f"  ({nombre} sin hacer: {type(e).__name__}: {e})")
    return hechas, D


def main(fecha, con_juez=True):
    dia = RAIZ / "dia" / fecha
    hechas, D = versiones(fecha)
    if not hechas:
        print("sin persona con imagen: no hay miniatura profesional")
        return 1
    res = juez(dia, hechas, D["contexto"]) if con_juez and len(hechas) > 1 else None
    if res:
        notas = {v["archivo"]: v for v in res["versiones"] if v.get("archivo") in hechas}
        elegida = max(notas, key=lambda a: (notas[a].get("nota", 0), notas[a].get("legible_movil", True))) if notas \
            else hechas[0]
        lineas = [f"# Miniatura del {fecha}: juez de diseño", ""]
        for a, v in sorted(notas.items(), key=lambda kv: -kv[1].get("nota", 0)):
            lineas.append(f"## {a}: {v.get('nota')}/10 · móvil: {'sí' if v.get('legible_movil', True) else 'NO'}")
            lineas += [f"- {p}" for p in v.get("problemas", [])] + [""]
        lineas.append(f"**Elegida: {elegida}.** {res.get('por_que', '')}")
    else:
        elegida = hechas[0]                               # sin juez: el orden del brief (duelo si hay rival)
        lineas = [f"# Miniatura del {fecha}", "", f"Sin juez (no respondió): {elegida} por orden del brief."]
    (dia / "revision").mkdir(exist_ok=True)
    (dia / "revision" / "miniatura.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    shutil.copyfile(dia / elegida, dia / "miniatura.png")
    print("\n".join(lineas))
    print(f"-> miniatura.png = {elegida}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if "--versiones" in a:
        print(versiones(a[0])[0])
    else:
        sys.exit(main(a[0], "--sin-juez" not in a))
