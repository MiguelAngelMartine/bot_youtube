"""REDES: lo que los partidos y sus líderes han publicado en las últimas horas, de fuentes OFICIALES, gratuitas y legales
(decisión del usuario del 4-nov-2026: X no tiene acceso gratuito). Webs y RSS de los partidos, canales públicos de
Telegram y cuentas verificadas de Bluesky (solo las oficiales comprobadas: hay cuentas falsas). Equilibrado entre
partidos. El resultado lo usa el investigador de «La campaña en frases».
Uso: python redes.py AAAA-MM-DD [horas=30]    -> dia/<fecha>/redes.md (y redes.json)"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

RAIZ = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 (ElHoyformativo; +https://github.com/MiguelAngelMartine/bot_youtube)"}
# (partido o persona, tipo, dirección). Revisadas el 4-nov-2026; las cuentas de Bluesky, por seguidores y descripción.
FUENTES = [
    ("PP", "web_pp", "https://www.pp.es/actualidad"),
    ("PP · Isabel Díaz Ayuso / PP de Madrid", "rss", "https://www.ppmadrid.es/feed/"),
    ("Comunidad de Madrid · Isabel Díaz Ayuso", "rss_ayuso", "https://www.comunidad.madrid/rss.xml"),
    ("PNV", "web_pnv", "https://www.eaj-pnv.eus/es/noticias"),
    ("Vox · Santiago Abascal", "telegram", "santiagoabascal"),
    ("Vox · Jorge Buxadé", "telegram", "Jorgebuxade"),
    ("PSOE", "bluesky", "psoe-cef.bsky.social"),
    ("PSOE · Grupo Socialista en el Congreso", "bluesky", "gpscongreso.bsky.social"),
    ("PSOE · Pilar Alegría", "bluesky", "pilaralegria.bsky.social"),
    ("Sumar", "bluesky", "movimientosumar.es"),
    ("Sumar · Yolanda Díaz", "bluesky", "yolandadiaz.bsky.social"),
    ("Sumar", "rss", "https://movimientosumar.es/feed/"),
    ("Podemos", "bluesky", "ahorapodemos.bsky.social"),
    ("Podemos", "telegram", "ahorapodemos"),
    ("ERC", "rss", "https://www.esquerra.cat/ca/rss"),
    ("Junts", "rss", "https://junts.cat/feed/"),
    ("Junts", "telegram", "JuntsxCat"),
    ("EH Bildu", "telegram", "EHBildu"),
    ("EH Bildu", "bluesky", "ehbildu.bsky.social"),
    ("BNG", "rss", "https://www.bng.gal/rss"),
    ("Más Madrid", "bluesky", "masmadrid.org"),
    ("Compromís", "bluesky", "compromis.net"),
]


def _limpia(t):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or ""))).strip()


def _fecha(s):
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def bluesky(handle):
    r = requests.get("https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed", headers=UA, timeout=25,
                     params={"actor": handle, "limit": 40, "filter": "posts_no_replies"})
    out = []
    for it in r.json().get("feed", []):
        if it.get("reason"):                             # reenvíos de otros: fuera
            continue
        p = it["post"]
        rec = p.get("record", {})
        out.append((_fecha(rec.get("createdAt", "")), rec.get("text", ""),
                    f"https://bsky.app/profile/{handle}/post/{p['uri'].rsplit('/', 1)[-1]}"))
    return out


def telegram(canal):
    h = requests.get(f"https://t.me/s/{canal}", headers=UA, timeout=25).text
    out = []
    for bloque in re.split(r'<div class="tgme_widget_message_wrap', h)[1:]:
        txt = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', bloque, re.S)
        cuando = re.search(r'<time datetime="([^"]+)"', bloque)
        enlace = re.search(r'data-post="([^"]+)"', bloque)
        if txt:
            out.append((_fecha(cuando.group(1)) if cuando else None, _limpia(txt.group(1)),
                        f"https://t.me/{enlace.group(1)}" if enlace else f"https://t.me/s/{canal}"))
    return out


def rss(url):
    f = feedparser.parse(requests.get(url, headers=UA, timeout=25).content)
    out = []
    for e in f.entries:
        d = None
        if e.get("published_parsed"):
            d = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        out.append((d, _limpia(e.get("title", "")) + ". " + _limpia(e.get("summary", ""))[:600], e.get("link", url)))
    return out


def rss_ayuso(url):
    """Comunidad de Madrid: solo lo que habla de la presidenta (Ayuso vende mucho: decisión del usuario del 5-nov-2026)."""
    return [x for x in rss(url) if re.search(r"Ayuso|la presidenta", x[1], re.I)]


def _web(url, patron, max_art=14):
    """Lista de noticias de una web de partido: titular (suelen llevar la frase literal) y entradilla de cada una."""
    h = requests.get(url, headers=UA, timeout=25).text
    enlaces = list(dict.fromkeys(re.findall(patron, h)))[:max_art]
    out = []
    for e in enlaces:
        try:
            a = requests.get(e, headers=UA, timeout=25).text
        except requests.RequestException:
            continue
        tit = re.search(r'<meta property="og:title" content="([^"]+)"', a) or re.search(r"<h1[^>]*>(.*?)</h1>", a, re.S)
        desc = re.search(r'<meta (?:property="og:description"|name="description") content="([^"]+)"', a)
        fecha = re.search(r'"datePublished"\s*:\s*"([^"]+)"', a) or re.search(r'article:published_time" content="([^"]+)"', a)
        out.append((_fecha(fecha.group(1)) if fecha else None,
                    _limpia(tit.group(1) if tit else "") + ". " + _limpia(desc.group(1) if desc else ""), e))
    return out


def web_pp(url):
    return _web(url, r'href="(https://www\.pp\.es/actualidad/articulos/[^"]+)"')


def web_pnv(url):
    return _web(url, r'href="(https://www\.eaj-pnv\.eus/es/noticias/\d+/[^"]+)"')


CUENTAS_X = {h.lower() for h in (   # cuentas oficiales de X conocidas; ademas, cualquier autor que este en archivo/personas.json
    "sanchezcastejon", "NunezFeijoo", "Santi_ABASCAL", "IdiazAyuso", "Yolanda_Diaz_", "gabrielrufian", "oscar_puente_",
    "PSOE", "ppopular", "vox_es", "Sumar", "PODEMOS", "Esquerra_ERC", "JuntsXCat", "eajpnv", "ehbildu", "BNG_Nacionalista",
    "mjmonteroc", "salvadorilla", "patxilopez", "avtorresp", "Ione_Belarra", "IreneMontero", "LaMoncloa", "desdelamoncloa",
    "Congreso_Es", "ComunidadMadrid", "ppmadrid", "ivanedlm", "Jorgebuxade")}
PARTIDOS = ("psoe", "partido popular", "vox", "sumar", "podemos", "esquerra", "junts", "pnv", "bildu", "bng", "compromís",
            "más madrid", "gobierno de españa", "moncloa")


def _norm(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def tuits_oficiales(dia, dias=3):
    """Tuits que los medios incrustan en sus noticias (articulos.py guarda los enlaces), leídos con oEmbed, el servicio
    oficial y gratuito de X para mostrar tuits. Solo cuentas de políticos y partidos (5-nov-2026)."""
    f = dia / "articulos" / "tuits.json"
    if not f.exists():
        return []
    personas = set()
    pj = RAIZ / "archivo" / "personas.json"
    if pj.exists():
        personas = {_norm(n) for n in json.loads(pj.read_text(encoding="utf-8"))}
    out, vistos = [], set()
    for cuenta, tid, medio in json.loads(f.read_text(encoding="utf-8"))[:120]:
        if tid in vistos or cuenta.lower() in ("x", "twitter", "i", "user_id", "intent", "share", "home"):
            continue
        vistos.add(tid)
        try:
            r = requests.get("https://publish.twitter.com/oembed", headers=UA, timeout=15,
                             params={"url": f"https://x.com/{cuenta}/status/{tid}", "omit_script": "1"})
        except requests.RequestException:
            continue
        if not r.ok:
            continue
        j = r.json()
        autor = j.get("author_name", "")
        oficial = (cuenta.lower() in CUENTAS_X or _norm(autor) in personas
                   or any(p in _norm(autor) for p in PARTIDOS))
        if not oficial:
            continue
        m = re.search(r"<p[^>]*>(.*?)</p>.*?&mdash;.*?</a>", j.get("html", ""), re.S)
        texto = _limpia(m.group(1) if m else j.get("html", ""))
        texto = re.sub(r"pic\.twitter\.com/\S+", "", texto).strip()
        fecha = re.findall(r">([A-Z][a-z]+ \d{1,2}, \d{4})</a>", j.get("html", ""))
        try:                                            # solo de los ultimos dias (fuera promociones y tuits antiguos)
            d = datetime.strptime(fecha[-1], "%B %d, %Y").replace(tzinfo=timezone.utc)
            if d < datetime.now(timezone.utc) - timedelta(days=dias):
                continue
        except (IndexError, ValueError):
            continue
        out.append({"quien": f"{autor} (@{cuenta})", "canal": f"X, incrustado en {medio}",
                    "fecha": fecha[-1] if fecha else "", "texto": texto[:900], "enlace": f"https://x.com/{cuenta}/status/{tid}"})
    return out


def main(fecha, horas=30):
    dia = RAIZ / "dia" / fecha
    dia.mkdir(parents=True, exist_ok=True)
    desde = datetime.now(timezone.utc) - timedelta(hours=horas)
    funcs = {"bluesky": bluesky, "telegram": telegram, "rss": rss, "rss_ayuso": rss_ayuso, "web_pp": web_pp, "web_pnv": web_pnv}
    datos, resumen = [], []
    for quien, tipo, dir_ in FUENTES:
        try:
            items = funcs[tipo](dir_)
        except Exception as e:
            resumen.append(f"- {quien} ({tipo}): no responde ({type(e).__name__})")
            continue
        recientes = [(d, t, l) for d, t, l in items if t and len(t) > 25 and (d is None or d >= desde)][:12]
        resumen.append(f"- {quien} ({tipo}): {len(recientes)} publicaciones")
        for d, t, l in recientes:
            datos.append({"quien": quien, "canal": tipo, "fecha": d.isoformat() if d else "", "texto": t[:900], "enlace": l})
    tx = tuits_oficiales(dia)
    resumen.insert(0, f"- X (tuits oficiales que incrustan los medios, vía oEmbed): {len(tx)} mensajes")
    datos = tx + datos                                  # los tuits, primero: son los que más gancho tienen
    (dia / "redes.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Lo que publican los partidos (últimas {horas} h, fuentes oficiales)", "", *resumen, ""]
    for x in datos:
        md.append(f"- **{x['quien']}** ({x['canal']}, {x['fecha'][:16].replace('T', ' ')}): {x['texto']} ({x['enlace']})")
    (dia / "redes.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(resumen))
    print(f"{len(datos)} publicaciones -> {dia / 'redes.md'}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 30)
