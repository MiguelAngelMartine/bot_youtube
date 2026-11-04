"""Herramienta del EDITOR GRAFICO: busca fotos de licencia libre (Openverse, que reune Flickr y Wikimedia, y Wikimedia
Commons directo), baja miniaturas para mirarlas antes de decidir, y guarda la elegida con su credito en creditos.json.
Uso:  python fotos.py buscar AAAA-MM-DD "consulta" [--n 8]      -> dia/<fecha>/fotos_candidatas/<slug>_<k>.jpg + .json
      python fotos.py elegir AAAA-MM-DD <slug> <k> <nombre.jpg> [--persona "Nombre Apellido"]
                                                                 -> dia/<fecha>/imagenes/<nombre.jpg> + credito
      (--persona: es el retrato de esa persona; el tablero lo pone en su polaroid)
Licencias admitidas: CC0, dominio publico, CC BY (preferidas) y CC BY-SA (solo si no hay otra). Nunca NC ni ND."""
from __future__ import annotations

import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image

import imagenes

RAIZ = Path(__file__).parent
UA = {"User-Agent": "ElHoyformativo/0.2 (https://github.com/MiguelAngelMartine/bot_youtube) python-requests"}   # Wikimedia exige un contacto; sin el, responde 429
ORDEN = {"cc0": 0, "pdm": 0, "public domain": 0, "by": 1, "by-sa": 2}


def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")[:40]


CAIDA = RAIZ / "cache" / "openverse_caido"           # si Openverse falla, se salta 30 min (el 2-nov tardaba 106 s en fallar)


def openverse(q, n):
    import time
    if CAIDA.exists() and time.time() - CAIDA.stat().st_mtime < 1800:
        raise RuntimeError("Openverse falló hace menos de 30 min; se salta")
    try:
        r = requests.get("https://api.openverse.org/v1/images/", headers=UA, timeout=15,
                         params={"q": q, "license": "cc0,pdm,by,by-sa", "page_size": n * 2})
        datos = r.json()
    except Exception:
        CAIDA.parent.mkdir(parents=True, exist_ok=True)
        CAIDA.touch()
        raise
    out = []
    for x in datos.get("results", []):
        if (x.get("width") or 0) < 1000:
            continue
        lic = x["license"]
        out.append({"fuente": f"Openverse/{x['source']}", "licencia": ("CC0" if lic == "cc0" else "Dominio público" if lic == "pdm"
                    else f"CC {lic.upper()} {x.get('license_version') or ''}".strip()), "orden": ORDEN.get(lic, 9),
                    "ancho": x["width"], "alto": x["height"], "autor": (x.get("creator") or "Desconocido")[:60],
                    "titulo": x["title"][:120], "url": x["url"], "miniatura": x.get("thumbnail") or x["url"],
                    "pagina": x.get("foreign_landing_url")})
    return out


def wikimedia(q, n):
    out = []
    for c in imagenes.busca(q, n, ancho=1280):
        lic = c["licencia"].lower()
        o = 0 if ("cc0" in lic or "public" in lic or "domin" in lic) else 2 if "sa" in lic else 1
        out.append({"fuente": "Wikimedia Commons", "licencia": c["licencia"], "orden": o, "ancho": c["ancho"], "alto": c["alto"],
                    "autor": c["autor"], "titulo": c["titulo"], "url": c["url"], "miniatura": c["url"], "pagina": c["pagina"]})
    return out


def baja(url, max_ancho):
    for k in range(5):
        r = requests.get(url, headers=UA, timeout=60)
        if r.ok and r.headers.get("content-type", "").startswith("image/"):
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if im.width > max_ancho:
                im = im.resize((max_ancho, int(im.height * max_ancho / im.width)), Image.LANCZOS)
            return im
        time.sleep(4 * (k + 1))
    return None


def buscar(dia_txt, q, n=8):
    dest = RAIZ / "dia" / dia_txt / "fotos_candidatas"
    dest.mkdir(parents=True, exist_ok=True)
    cands, vistos = [], set()
    for f in (wikimedia, openverse):                  # Wikimedia primero: es la que responde siempre
        try:
            for c in f(q, n):
                if c["pagina"] not in vistos:
                    vistos.add(c["pagina"])
                    cands.append(c)
        except Exception as e:                        # una fuente caida no para la otra
            print(f"  ({f.__name__} no responde: {type(e).__name__})")
    cands = sorted(cands, key=lambda c: c["orden"])[:n]
    s = slug(q)
    for k, c in enumerate(cands):
        im = baja(c["miniatura"], 640)
        if im is not None:
            im.save(dest / f"{s}_{k}.jpg", quality=85)
        print(f"  [{k}] {c['licencia']:16s} {c['ancho']}x{c['alto']} {c['fuente']:22s} {c['autor'][:28]:28s} | {c['titulo'][:70]}")
    (dest / f"{s}.json").write_text(json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(cands)} candidatas -> {dest}/{s}_<k>.jpg  (mira cada una antes de elegir)")


def original(url):
    """Wikimedia da una miniatura de 1280 px; para retratos y miniaturas hace falta la foto original (3-nov-2026)."""
    import re as _re
    m = _re.match(r"https?://[^/]*wikimedia\.org(/wikipedia/commons)/thumb/(.+)/[^/]+$", url.split("?")[0])
    return f"https://upload.wikimedia.org{m.group(1)}/{m.group(2)}" if m else url


def recorta(dia_txt, origen, destino, x0, y0, x1, y1, persona=None):
    """Recorta una persona de una foto de grupo (fracciones 0-1 del ancho y del alto) conservando el credito."""
    dia = RAIZ / "dia" / dia_txt
    im = Image.open(dia / "imagenes" / origen)
    w, h = im.size
    im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))).save(dia / "imagenes" / destino, quality=93)
    cred_f = dia / "creditos.json"
    cred = json.loads(cred_f.read_text(encoding="utf-8"))
    cred[destino] = dict(cred[origen])
    cred[destino].pop("persona", None)
    if persona:
        cred[destino]["persona"] = persona
    cred_f.write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"recortada {destino} de {origen} ({int((x1 - x0) * w)}x{int((y1 - y0) * h)} px)")


def elegir(dia_txt, s, k, nombre, persona=None):
    dia = RAIZ / "dia" / dia_txt
    c = json.loads((dia / "fotos_candidatas" / f"{s}.json").read_text(encoding="utf-8"))[int(k)]
    im = baja(original(c["url"]), 3200) or baja(c["url"], 3200)   # la original, a maxima resolucion
    if im is None:
        raise SystemExit("no se pudo bajar la foto")
    (dia / "imagenes").mkdir(exist_ok=True)
    im.save(dia / "imagenes" / nombre, quality=90)
    cred_f = dia / "creditos.json"
    cred = json.loads(cred_f.read_text(encoding="utf-8")) if cred_f.exists() else {}
    cred[nombre] = {"titulo": c["titulo"], "url": c["url"], "ancho": im.width, "alto": im.height, "autor": c["autor"],
                    "licencia": c["licencia"], "pagina": c["pagina"], "fuente": c["fuente"]}
    if persona:
        cred[nombre]["persona"] = persona
    cred_f.write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"guardada {nombre} ({im.width}x{im.height}, {c['licencia']}, {c['autor']})")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "buscar":
        buscar(a[1], a[2], int(a[a.index("--n") + 1]) if "--n" in a else 8)
    elif a and a[0] == "elegir":
        elegir(*a[1:5], persona=a[a.index("--persona") + 1] if "--persona" in a else None)
    elif a and a[0] == "recorta":                      # recorta <fecha> <origen> <destino> x0 y0 x1 y1 [--persona N]
        recorta(a[1], a[2], a[3], *map(float, a[4:8]), persona=a[a.index("--persona") + 1] if "--persona" in a else None)
    else:
        print(__doc__)
