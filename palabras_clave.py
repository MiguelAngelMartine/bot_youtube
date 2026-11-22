"""PALABRAS CLAVE: lo que más se busca en YouTube sobre política española (22-nov-2026, el usuario: «hay que hacer una
investigación exhaustiva para encontrar las palabras que más se buscan en YouTube relacionadas con la política española e
incluirlas en nuestra descripción y hashtags para llegar al máximo posible de búsquedas»).

Dos fuentes, gratis:
  1. El AUTOCOMPLETADO de YouTube (España, español): lo que sugiere el buscador al escribir, que sale de lo que más busca
     la gente. Se pregunta por cada político, partido y tema, y por cada letra tras las semillas generales.
  2. Las ETIQUETAS de los vídeos de política española más vistos del último mes (API de YouTube, pocas consultas).
Guarda archivo/palabras_clave.json. La jornada lo refresca si tiene más de 3 días.

Al montar la publicación, para_video() elige SOLO las que tienen que ver con el vídeo: una búsqueda sobre una persona o un
tema entra si la persona o el tema salen en el vídeo y el resto de sus palabras son genéricas («hoy», «última hora»,
«en directo»...) o también salen. Las etiquetas engañosas son spam para YouTube y pueden costar la monetización.

Uso: python palabras_clave.py investiga [--sin-api]   ·   python palabras_clave.py muestra
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).parent
SALIDA = RAIZ / "archivo" / "palabras_clave.json"
URL = "https://suggestqueries.google.com/complete/search"

PARTIDOS = ["PSOE", "PP", "Vox", "Sumar", "Podemos", "ERC", "Junts", "PNV", "Bildu", "BNG", "Compromís", "Más Madrid",
            "Partido Popular", "Frente Amplio", "Se Acabó La Fiesta", "Alvise"]
TEMAS = ["política española", "politica españa", "noticias españa", "noticias de hoy", "última hora españa",
         "elecciones españa", "elecciones generales", "elecciones 29 noviembre", "debate electoral", "cara a cara",
         "campaña electoral", "encuestas elecciones", "sesión de control", "congreso de los diputados", "gobierno de españa",
         "corrupción psoe", "caso koldo", "begoña gómez", "fiscal general", "amnistía", "inmigración españa",
         "vivienda españa", "mitin", "actualidad política", "resumen noticias", "pedro sánchez dimisión",
         "moción de censura", "presupuestos generales"]
GENERALES = ["política española", "noticias españa", "elecciones españa", "pedro sánchez", "feijóo", "abascal"]
EXTRANJERO = ("argentin", "colombia", "peru", "perú", "mexic", "méxic", "chile", "venezuel", "brasil", "ecuador", "bolivia",
              "uruguay", "paraguay", "estados unidos", "eeuu", "usa", "trump", "milei", "petro", "real madrid", "barça",
              "barcelona fc", "futbol", "fútbol", "soziedad", "jarfaiter", "aristóteles", "honduras", "cuba", "guatemala")
# palabras que se pueden añadir a un nombre o un tema sin que la búsqueda deje de describir el vídeo
GENERICAS = set("""hoy ahora ultima ultimas hora noticia noticias en de del la el los las y a al 2026 actualidad
declaraciones polemica politica española espana españa ultimo resumen que dice dijo responde critica contra
ultimahora sobre""".split())   # «directo», «ayer», «entrevista»: solo si salen en el vídeo (prometerían otra cosa)

RELEVANTE = ("polític", "politic", "elecci", "congreso", "senado", "gobierno", "ministr", "president", "partido", "españa",
             "espana", "debate", "mitin", "encuesta", "votación", "votacion", "campaña", "moncloa", "diputad", "corrupci",
             "amnist", "noticias", "sesión de control", "sesion de control")


def _n(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip()


def sugerencias(q):
    """Lo que sugiere el buscador de YouTube en España para q, en orden (lo más buscado primero)."""
    for intento in range(3):
        try:
            r = requests.get(URL, params={"client": "firefox", "ds": "yt", "hl": "es", "gl": "es", "q": q}, timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.ok:
                return [s for s in r.json()[1] if isinstance(s, str)]
        except (requests.RequestException, ValueError):
            pass
        time.sleep(2 + 3 * intento)
    return []


def personas():
    """Políticos que nos importan: las cuentas oficiales de X y los que tienen imagen."""
    import x_oficiales
    nombres = [n for n in x_oficiales.CUENTAS if n not in PARTIDOS and n not in ("PP",)]
    try:
        d = json.loads((RAIZ / "archivo" / "personas.json").read_text(encoding="utf-8"))
        nombres += [n for n in d if "(" not in n]
    except (OSError, ValueError):
        pass
    return list(dict.fromkeys(nombres))


def _apellido(n):
    p = n.split()
    return " ".join(p[-2:]) if len(p) >= 3 and p[-2].lower() in ("díaz", "núñez", "álvarez", "fernández") else p[-1]


def investiga_autocompletado():
    puntos, por_semilla, escritura = Counter(), {}, {}
    semillas = []
    for n in personas():
        semillas += [n.lower(), _apellido(n).lower()]
    semillas += [p.lower() for p in PARTIDOS] + TEMAS
    semillas += [f"{g} {c}" for g in GENERALES for c in "abcdefghijlmnoprstuv"]
    semillas = list(dict.fromkeys(semillas))
    for i, q in enumerate(semillas):
        ss = sugerencias(q)
        por_semilla[q] = ss
        for k, s in enumerate(ss):
            puntos[_n(s)] += 10 - k
            escritura.setdefault(_n(s), s)                 # como la escribe la gente (con tildes)
        time.sleep(0.25)
        if i % 50 == 0:
            print(f"  autocompletado: {i}/{len(semillas)}")
    return puntos, por_semilla, escritura


def investiga_api(consultas=("política española", "noticias españa hoy", "elecciones generales españa",
                             "pedro sánchez", "feijóo", "debate electoral españa")):
    """Etiquetas de los vídeos más vistos del último mes sobre política española (unas 650 unidades de cuota)."""
    import subir
    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=subir.credenciales())
    desde = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids = []
    for q in consultas:
        r = yt.search().list(part="id", q=q, type="video", regionCode="ES", relevanceLanguage="es", order="viewCount",
                             publishedAfter=desde, maxResults=50).execute()
        ids += [x["id"]["videoId"] for x in r.get("items", [])]
    ids = list(dict.fromkeys(ids))
    etiquetas, hashtags, vistas, escritura = Counter(), Counter(), {}, {}
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics", id=",".join(ids[i:i + 50])).execute()
        for v in r.get("items", []):
            sn = v["snippet"]
            if (sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "es")[:2] != "es":
                continue
            peso = 1 + int(v.get("statistics", {}).get("viewCount", 0)) // 100000      # los más vistos pesan más
            for t in sn.get("tags", []) or []:
                etiquetas[_n(t)] += peso
                escritura.setdefault(_n(t), t.strip())
            for h in re.findall(r"#(\w+)", sn.get("description", "") + " " + sn.get("title", "")):
                hashtags[h] += peso
            vistas[v["id"]] = int(v.get("statistics", {}).get("viewCount", 0))
    return etiquetas, hashtags, len(vistas), escritura


def es_relevante(t, nombres_n):
    t = _n(t)
    if any(x in t for x in EXTRANJERO):
        return False
    return any(r in t for r in RELEVANTE) or any(n in t for n in nombres_n)


def investiga(con_api=True):
    nombres_n = set()
    for n in personas():
        nombres_n |= {_n(n), _n(_apellido(n))}
    nombres_n |= {_n(p) for p in PARTIDOS if len(p) > 2}
    print("Autocompletado de YouTube (España)...")
    puntos, por_semilla, escritura = investiga_autocompletado()
    etiquetas, hashtags, nv, esc2 = Counter(), Counter(), 0, {}
    if con_api:
        print("Etiquetas de los vídeos más vistos del mes (API de YouTube)...")
        try:
            etiquetas, hashtags, nv, esc2 = investiga_api()
        except Exception as e:                                   # sin cuota o sin token: queda el autocompletado
            print(f"  API no disponible: {type(e).__name__}")
    busquedas = [(escritura.get(t, t), p) for t, p in puntos.most_common() if es_relevante(t, nombres_n)]
    tags = [(esc2.get(t, t), p) for t, p in etiquetas.most_common(400) if es_relevante(t, nombres_n)]
    hn = Counter()
    forma = {}
    for h, p in hashtags.most_common():
        hn[_n(h)] += p
        forma.setdefault(_n(h), h)                       # la escritura más vista (most_common va de más a menos)
    hs = [(forma[h], p) for h, p in hn.most_common(200)
          if (es_relevante(h, nombres_n) or h in nombres_n) and not any(x in h for x in EXTRANJERO)]
    datos = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "busquedas": busquedas[:800], "etiquetas_top": tags[:300],
             "hashtags_top": hs[:150], "videos_analizados": nv, "por_semilla": por_semilla}
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(busquedas)} búsquedas relevantes, {len(tags)} etiquetas de {nv} vídeos -> {SALIDA}")
    return datos


def carga(max_dias=3, refrescar=False):
    """Los datos guardados; si tienen más de max_dias y refrescar=True, se vuelve a investigar (sin API)."""
    try:
        d = json.loads(SALIDA.read_text(encoding="utf-8"))
        viejo = datetime.now() - datetime.strptime(d["fecha"], "%Y-%m-%d %H:%M") > timedelta(days=max_dias)
    except (OSError, ValueError, KeyError):
        d, viejo = None, True
    if viejo and refrescar:
        d = investiga(con_api=False) | {k: v for k, v in (d or {}).items() if k in ("etiquetas_top", "hashtags_top")}
        SALIDA.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return d or {}


# apellidos que, solos, ya identifican a la persona en una búsqueda (los demás, «López», «Serrano», «Toledo», no)
UNICOS = set("""sanchez feijoo abascal ayuso rufian puigdemont tellado bolanos illa junqueras otegi belarra colau nogueras
marlaska pontón ponton zapatero rajoy aznar morant urtasun baldovi alvise sacristan""".split())
SIGLAS = {_n(p): p for p in PARTIDOS}


def _bonita(t):
    """La forma de escribirlo: siglas en mayúsculas, nombres con mayúscula y tildes; el resto, como se busca."""
    if _n(t) in SIGLAS:
        return SIGLAS[_n(t)]
    return t


def _hashtag(t):
    """«pedro sánchez» -> #PedroSánchez; «psoe» -> #PSOE."""
    if _n(t) in SIGLAS:
        return "#" + SIGLAS[_n(t)].replace(" ", "")
    return "#" + "".join(w[:1].upper() + w[1:] for w in re.findall(r"\w+", t))


def para_video(texto, nombres=(), max_tags=25, temas=()):
    """Búsquedas reales que describen ESTE vídeo (texto = guion + título): entran si todas sus palabras no genéricas
    salen en el vídeo, y si es una sola palabra, si es un partido o un apellido que solo ya identifica a la persona.
    Devuelve (etiquetas, hashtags) ordenadas de más a menos buscadas."""
    d = carga()
    if not d:
        return [], []
    tn = _n(texto + " " + " ".join(nombres))
    palabras = set(re.findall(r"\w+", tn))
    propios = {w for t in temas for w in re.findall(r"\w+", _n(t).lstrip("#"))} & palabras   # los temas del vídeo

    def describe(t):
        ws = re.findall(r"\w+", _n(t))
        if not ws or not all(w in GENERICAS or w in palabras for w in ws):
            return False
        propias = [w for w in ws if w not in GENERICAS]
        if not propias:
            return False
        if len(set(propias)) == 1:                         # «toledo españa», «lópez lópez»: un apellido ambiguo no basta
            return propias[0] in UNICOS or propias[0] in SIGLAS or propias[0] in propios or propias[0] == "shorts"
        return True
    puntos, forma = Counter(), {}
    vivas = []                                            # lo del día («lorca», «pinto censura»): se pregunta en directo
    for tema in list(dict.fromkeys(_n(t).lstrip("#") for t in temas if t))[:6]:
        vivas += [(x, 10 - k) for k, x in enumerate(sugerencias(tema))]
        time.sleep(0.2)
    for fuente, peso in (("vivas", 1.2), ("busquedas", 1.0), ("etiquetas_top", 0.5)):
        for t, p in (vivas if fuente == "vivas" else d.get(fuente, [])):
            if describe(t):
                k = _n(t)
                puntos[k] += p * peso
                if k not in forma or sum(ord(c) > 127 for c in t) > sum(ord(c) > 127 for c in forma[k]):
                    forma[k] = t                              # la variante con tildes
    etiquetas = [_bonita(forma[k]) for k, _ in puntos.most_common(max_tags)]
    hs, vis = [], set()
    for h, _ in d.get("hashtags_top", []):
        k = _n(h)
        if k in vis or not (describe(h) or k in palabras and (k in UNICOS or k in SIGLAS)):
            continue
        vis.add(k)
        hs.append(_hashtag(forma.get(k, h)) if k in forma else ("#" + SIGLAS[k].replace(" ", "") if k in SIGLAS else "#" + h))
    return etiquetas, hs[:6]


def muestra():
    d = carga()
    print(f"Datos del {d.get('fecha')} · {d.get('videos_analizados', 0)} vídeos analizados")
    print("\nBÚSQUEDAS MÁS FRECUENTES (autocompletado):")
    for t, p in d.get("busquedas", [])[:60]:
        print(f"  {p:4d}  {t}")
    print("\nETIQUETAS DE LOS VÍDEOS MÁS VISTOS:")
    for t, p in d.get("etiquetas_top", [])[:50]:
        print(f"  {p:5d}  {t}")
    print("\nHASHTAGS DE LOS VÍDEOS MÁS VISTOS:")
    print("  " + "  ".join(f"#{h}" for h, _ in d.get("hashtags_top", [])[:40]))


if __name__ == "__main__":
    if sys.argv[1:2] == ["investiga"]:
        investiga(con_api="--sin-api" not in sys.argv)
    else:
        muestra()
