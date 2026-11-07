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


API_COMMONS = "https://commons.wikimedia.org/w/api.php"
LIC_OK = ("cc0", "public domain", "pdm", "dominio", "cc by", "cc-by", "attribution")


def _lic_ok(l):
    l = (l or "").lower()
    return any(x in l for x in LIC_OK) and not any(x in l for x in ("nc", "nd", "non-commercial", "noderivs"))


def commons_categoria(q, n):
    """Fotos de la categoria de Commons de una persona o un lugar (4-nov-2026): muchas mas y mas recientes que la busqueda
    por palabras (importaciones de Pool Moncloa, Parlamento Europeo, gobiernos autonomicos y partidos). Entra en las
    subcategorias (por año, las mas recientes primero) y devuelve primero las fotos mas nuevas."""
    import re as _re
    r = requests.get(API_COMMONS, headers=UA, timeout=30, params={"action": "query", "list": "search", "srsearch": q,
                     "srnamespace": 14, "format": "json", "srlimit": 5}).json()
    cats = [c["title"] for c in r.get("query", {}).get("search", [])]
    if not cats:
        return []
    exacta = [c for c in cats if c.lower() == f"category:{q.lower()}"]
    cat = (exacta or cats)[0]
    sub = requests.get(API_COMMONS, headers=UA, timeout=30, params={"action": "query", "list": "categorymembers",
                       "cmtitle": cat, "cmtype": "subcat", "cmlimit": 50, "format": "json"}).json()
    subs = [s["title"] for s in sub.get("query", {}).get("categorymembers", [])]
    for s_ in [s for s in subs if "by year" in s.lower() or "por año" in s.lower()]:   # un nivel más: «X by year»
        r2 = requests.get(API_COMMONS, headers=UA, timeout=30, params={"action": "query", "list": "categorymembers",
                          "cmtitle": s_, "cmtype": "subcat", "cmlimit": 50, "format": "json"}).json()
        subs += [x["title"] for x in r2.get("query", {}).get("categorymembers", [])]
    años = sorted([s for s in subs if _re.search(r"20\d\d", s)], key=lambda s: -int(_re.search(r"20\d\d", s).group()))
    años = [s for s in subs if "portrait" in s.lower() or "retrato" in s.lower()] + años
    out, vistos = [], set()
    for c_ in [cat] + años[:4]:
        res = requests.get(API_COMMONS, headers=UA, timeout=60, params={
            "action": "query", "generator": "categorymembers", "gcmtitle": c_, "gcmtype": "file", "gcmlimit": 60,
            "gcmsort": "timestamp", "gcmdir": "desc", "prop": "imageinfo", "iiprop": "url|size|extmetadata",
            "iiurlwidth": 1280, "iiextmetadatafilter": "LicenseShortName|Artist|DateTimeOriginal", "format": "json"}).json()
        for f in res.get("query", {}).get("pages", {}).values():
            ii = (f.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata", {})
            lic = md.get("LicenseShortName", {}).get("value", "")
            if not ii or f["title"] in vistos or not _lic_ok(lic) or ii.get("width", 0) < 900 or not f["title"].lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            vistos.add(f["title"])
            autor = _re.sub(r"<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()[:60] or "Wikimedia Commons"
            fecha = md.get("DateTimeOriginal", {}).get("value", "")[:10]
            out.append({"fuente": "Commons (categoría)", "licencia": lic, "orden": 0 if "cc0" in lic.lower() or "public" in lic.lower() else 1,
                        "ancho": ii["width"], "alto": ii["height"], "autor": autor, "titulo": f["title"][:120] + (f" ({fecha})" if fecha else ""),
                        "url": ii.get("thumburl") or ii["url"], "miniatura": ii.get("thumburl") or ii["url"],
                        "pagina": ii.get("descriptionurl", "")})
            if len(out) >= n:
                return out
    return out


MONCLOA = "https://www.lamoncloa.gob.es"
MONCLOA_INDICES = ["/multimedia/galeriasfotograficas/Paginas/index.aspx",
                   "/multimedia/galeriasfotograficas/presidente/Paginas/index.aspx",
                   "/multimedia/galeriasfotograficas/consejoministros/Paginas/index.aspx"]


def _texto_html(h):
    import html as _h
    import re as _re
    return _h.unescape(_re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", h)))


def moncloa(q, n):
    """Galerías de Pool Moncloa (4-nov-2026): fotos del presidente y los ministros del mismo día, 2000 px. Su aviso legal
    dice «Las imágenes firmadas Pool Moncloa son de libre acceso», citando «Origen de los datos: sitio web de
    lamoncloa.gob.es. Ministerio de la Presidencia» y la fecha, y sin desnaturalizar el contenido."""
    import re as _re
    import unicodedata as _u
    norm = lambda s: _u.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    claves = [w for w in norm(q).split() if len(w) > 3]
    if not claves:
        return []
    cache = RAIZ / "cache" / "moncloa"
    cache.mkdir(parents=True, exist_ok=True)
    enlaces = []
    for ind in MONCLOA_INDICES:
        try:
            h = requests.get(MONCLOA + ind, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
        except requests.RequestException:
            continue
        enlaces += [e for e in _re.findall(r'href="(/multimedia/galeriasfotograficas/[^"]+/Paginas/20\d\d/[^"]+\.aspx)"', h) if e not in enlaces]
    out, vistas = [], set()
    for e in list(dict.fromkeys(enlaces))[:40]:
        f = cache / (_re.sub(r"[^a-z0-9]+", "_", e.lower())[-90:] + ".html")
        if not f.exists():
            try:
                f.write_text(requests.get(MONCLOA + e, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text, encoding="utf-8")
            except requests.RequestException:
                continue
        h = f.read_text(encoding="utf-8")
        titulo = _texto_html((_re.search(r"<h1[^>]*>(.*?)</h1>", h, _re.S) or _re.search(r"<title>(.*?)</title>", h, _re.S)).group(1)).strip()
        cuerpo = _texto_html(h)
        i = cuerpo.find(titulo[:40]) if titulo else -1
        desc = cuerpo[i:i + 1500] if i >= 0 else ""
        if not all(k in norm(e + " " + titulo + " " + desc) for k in claves):
            continue
        m = _re.search(r"/(\d{2})(\d{2})(\d{2})-", e)
        fecha = f"{m.group(1)}/{m.group(2)}/20{m.group(3)}" if m else ""
        fotos_ = []
        for src in _re.findall(r'src="(/multimedia/fotos/[^"?]+\.jpg)', h, _re.I):
            if src not in fotos_:
                fotos_.append(src)
        for src in fotos_:
            if src in vistas:
                continue
            vistas.add(src)
            out.append({"fuente": "Pool Moncloa", "orden": 1, "ancho": 2000, "alto": 1333,
                        "autor": "Pool Moncloa / Ministerio de la Presidencia",
                        "licencia": f"libre acceso. Origen de los datos: sitio web de lamoncloa.gob.es. Ministerio de la Presidencia ({fecha})",
                        "titulo": f"{titulo[:100]} ({fecha})", "url": MONCLOA + src, "miniatura": MONCLOA + src + "?RenditionID=24",
                        "pagina": MONCLOA + e})
            if len(out) >= n:
                return out
    return out


def retrato_wikidata(nombre):
    """El retrato principal de la persona en Wikidata (propiedad P18): suele ser un primer plano oficial con licencia
    libre, en Commons. Devuelve una candidata con el mismo formato que las demás, o None (5-nov-2026)."""
    import re as _re
    r = requests.get("https://www.wikidata.org/w/api.php", headers=UA, timeout=30, params={
        "action": "wbsearchentities", "search": nombre, "language": "es", "type": "item", "limit": 3, "format": "json"}).json()
    import unicodedata as _u

    def _pal(t):
        return set(_re.findall(r"\w+", _u.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()))
    for ent in r.get("search", []):
        # la misma persona: todas las palabras del nombre en la etiqueta (o en el alias que ha casado) y que sea humano
        if not _pal(nombre) <= (_pal(ent.get("label")) | _pal(ent.get("match", {}).get("text"))):
            continue
        d = requests.get("https://www.wikidata.org/w/api.php", headers=UA, timeout=30, params={
            "action": "wbgetclaims", "entity": ent["id"], "format": "json"}).json().get("claims", {})
        if not any(c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") == "Q5" for c in d.get("P31", [])):
            continue
        fs = d.get("P18", [])
        if not fs:
            continue
        fichero = "File:" + fs[0]["mainsnak"]["datavalue"]["value"]
        ii = requests.get(API_COMMONS, headers=UA, timeout=30, params={
            "action": "query", "titles": fichero, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1280,
            "iiextmetadatafilter": "LicenseShortName|Artist", "format": "json"}).json()
        pg = next(iter(ii.get("query", {}).get("pages", {}).values()), {})
        info = (pg.get("imageinfo") or [{}])[0]
        lic = info.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
        if not info or not _lic_ok(lic):
            continue
        autor = _re.sub(r"<[^>]+>", "", info.get("extmetadata", {}).get("Artist", {}).get("value", "")).strip()[:60]
        return {"fuente": "Wikidata (retrato principal)", "licencia": lic, "orden": 0, "ancho": info["width"],
                "alto": info["height"], "autor": autor or "Wikimedia Commons", "titulo": fichero[:120],
                "url": info.get("thumburl") or info["url"], "miniatura": info.get("thumburl") or info["url"],
                "pagina": info.get("descriptionurl", "")}
    return None


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
    for f in (commons_categoria, moncloa, wikimedia, openverse):   # 4-nov: categoria de Commons, Pool Moncloa (del dia), ...
        try:
            for c in f(q, n):
                if c["pagina"] not in vistos:
                    vistos.add(c["pagina"])
                    cands.append(c)
        except Exception as e:                        # una fuente caida no para la otra
            print(f"  ({f.__name__} no responde: {type(e).__name__})")
    cat_ = [c for c in cands if c["fuente"] in ("Commons (categoría)", "Pool Moncloa")]   # las mas recientes primero
    cands = (cat_ + sorted([c for c in cands if c not in cat_], key=lambda c: c["orden"]))[:n]
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


ELIGE = """Eres editor gráfico de un informativo de YouTube profesional. Estas son fotos candidatas de {nombre}. Hay que
elegir las {n} MEJORES para usarla recortada y en grande (miniatura y retrato), para una noticia en la que el gesto
debería ser: {animo}. Puntúa cada una de 1 a 10 valorando, por este orden:
1) que sea de verdad {nombre} (si dudas, 0) y que la cara se vea grande, nítida, enfocada y bien iluminada;
2) gesto y expresión acordes con «{animo}» (nada de sonrisa de foto oficial para una mala noticia);
3) que mire a cámara o de tres cuartos (no de espaldas ni muy de perfil), sin nada delante de la cara;
4) aspecto profesional: traje o ropa de trabajo habitual, en un acto, tribuna o rueda de prensa; mejor reciente;
5) que no haya otras caras grandes que compitan.
Responde SOLO JSON: {{"puntos": [p0, p1, ...]}} con un número por foto, en el mismo orden."""


def mejores(dia_txt, nombre, animo="serio", n=3, extra_q=None):
    """7-nov-2026 (el usuario: «las fotos son muy malas, poco profesional»): reúne muchas candidatas de la persona
    (Wikidata, su categoría de Commons y subcategorías por año, Pool Moncloa), descarta las de cara pequeña o sin cara
    (YuNet) y Gemini elige las de más calidad y con el gesto que pide la noticia. Guarda retrato_<apellido>[_k].jpg con
    su crédito y persona. Devuelve las rutas guardadas."""
    import gem
    import miniatura as M
    dia = RAIZ / "dia" / dia_txt
    cands, vistos = [], set()
    fuentes = [lambda: [retrato_wikidata(nombre)], lambda: commons_categoria(nombre, 24), lambda: moncloa(nombre, 10)]
    if extra_q:
        fuentes.append(lambda: commons_categoria(extra_q, 12))
    for f in fuentes:
        try:
            for c in f() or []:
                if c and c["pagina"] not in vistos and _lic_ok(c["licencia"]):
                    vistos.add(c["pagina"])
                    cands.append(c)
        except Exception as e:
            print(f"  (una fuente no responde: {type(e).__name__})")
    buenas = []
    for c in cands[:30]:
        im = baja(c["miniatura"], 900)
        if im is None or min(im.size) < 300:
            continue
        k = M.cara(im)
        if not k or k[3] < 0.14 * im.height or k[3] < 70:        # cara pequeña: foto de grupo o de lejos
            continue
        buenas.append((c, im))
    if not buenas:
        print(f"  {nombre}: ninguna candidata con la cara grande")
        return []
    puntos = None
    for lote in range(0, len(buenas), 10):              # de 10 en 10 para no pasar el tamaño de la petición
        sub = buenas[lote:lote + 10]
        partes = [{"text": ELIGE.format(nombre=nombre, n=n, animo=animo)}]
        for j, (c, im) in enumerate(sub):
            partes += [{"text": f"Foto {j}:"}, gem.imagen(im, 640)]
        r = gem.pide(partes, como_json=True)
        p_ = (r or {}).get("puntos") if isinstance(r, dict) else None
        if not isinstance(p_, list) or len(p_) != len(sub):
            p_ = [6] * len(sub)                          # sin Gemini: las de cara grande, en el orden de siempre
        puntos = (puntos or []) + [float(x) if str(x).replace(".", "", 1).isdigit() else 0 for x in p_]
    orden = sorted(range(len(buenas)), key=lambda i: -puntos[i])
    ap = slug(nombre.split()[-1])
    cred_f = dia / "creditos.json"
    cred = json.loads(cred_f.read_text(encoding="utf-8")) if cred_f.exists() else {}
    (dia / "imagenes").mkdir(parents=True, exist_ok=True)
    guardadas = []
    for i in orden:
        if len(guardadas) >= n or puntos[i] < 6:
            break
        c, _ = buenas[i]
        im = baja(original(c["url"]), 3200) or baja(c["url"], 3200)
        if im is None:
            continue
        nom = f"retrato_{ap}{'' if not guardadas else '_' + str(len(guardadas) + 1)}.jpg"
        im.save(dia / "imagenes" / nom, quality=92)
        cred[nom] = {"titulo": c["titulo"], "url": c["url"], "ancho": im.width, "alto": im.height, "autor": c["autor"],
                     "licencia": c["licencia"], "pagina": c["pagina"], "fuente": c["fuente"], "persona": nombre,
                     "puntos_gemini": puntos[i]}
        guardadas.append(dia / "imagenes" / nom)
        print(f"  {nom}: {puntos[i]:.0f}/10 · {c['licencia']} · {c['autor'][:30]} · {c['titulo'][:60]}")
    cred_f.write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{nombre}: {len(guardadas)} retratos de {len(buenas)} candidatas con cara grande ({len(cands)} en total)")
    return guardadas


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "buscar":
        buscar(a[1], a[2], int(a[a.index("--n") + 1]) if "--n" in a else 8)
    elif a and a[0] == "mejores":                      # mejores <fecha> "<nombre>" [--animo "enfado"] [--n 3]
        mejores(a[1], a[2], a[a.index("--animo") + 1] if "--animo" in a else "serio",
                int(a[a.index("--n") + 1]) if "--n" in a else 3)
    elif a and a[0] == "elegir":
        elegir(*a[1:5], persona=a[a.index("--persona") + 1] if "--persona" in a else None)
    elif a and a[0] == "recorta":                      # recorta <fecha> <origen> <destino> x0 y0 x1 y1 [--persona N]
        recorta(a[1], a[2], a[3], *map(float, a[4:8]), persona=a[a.index("--persona") + 1] if "--persona" in a else None)
    else:
        print(__doc__)
