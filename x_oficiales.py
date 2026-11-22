"""X (Twitter): tuits de las CUENTAS OFICIALES de políticos y partidos, con twscrape y la sesión del .env
(X_AUTH_TOKEN, X_CT0). La lista es cerrada: cualquier otra cuenta se rechaza, para no citar nunca una cuenta falsa o parodia.
Uso: python x_oficiales.py verifica             -> comprueba cada cuenta en X (nombre, verificada, seguidores)
     python x_oficiales.py tuits <cuenta> [AAAA-MM-DD]   -> tuits de ese día en hora de Madrid (por defecto, hoy)
redes.py llama a recientes() cada día para la redacción."""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from twscrape import API

RAIZ = Path(__file__).parent
MADRID = ZoneInfo("Europe/Madrid")
DB = RAIZ / "cache" / "x_cuentas.db"
MIN_SEGUIDORES = 10000          # una cuenta oficial no baja de aquí; si pasa, el nombre ha cambiado de dueño (ocurrió con @populares)
TOPE_CUENTA = 45                # s por cuenta: si X limita, twscrape espera sin fin y no puede atascar la jornada
# nombre -> cuenta. Solo se añade una cuenta tras comprobarla con «verifica».
CUENTAS = {
    "Pedro Sánchez": "sanchezcastejon", "Alberto Núñez Feijóo": "NunezFeijoo", "Santiago Abascal": "Santi_ABASCAL",
    "Isabel Díaz Ayuso": "IdiazAyuso", "Gabriel Rufián": "gabrielrufian", "Yolanda Díaz": "Yolanda_Diaz_",
    "Ione Belarra": "ionebelarra", "Óscar Puente": "oscar_puente_", "Salvador Illa": "salvadorilla",
    "Carles Puigdemont": "KRLS", "Oriol Junqueras": "junqueras", "Arnaldo Otegi": "ArnaldoOtegi", "Ana Pontón": "anaponton",
    "PSOE": "PSOE", "PP": "ppopular", "Vox": "vox_es", "Sumar": "sumar", "Podemos": "PODEMOS", "ERC": "Esquerra_ERC",
    "Junts": "JuntsXCat", "PNV": "eajpnv", "EH Bildu": "ehbildu", "BNG": "obloque", "Compromís": "compromis", "Más Madrid": "MasMadrid__",
    # 22-nov-2026: cuentas de los cruces de declaraciones (comprobadas con «verifica» antes de entrar)
    "Ester Muñoz": "EsterMunoz85", "Miguel Tellado": "Mtelladof", "Diana Morant": "dianamorantr",
    "Cayetana Álvarez de Toledo": "cayetanaAT", "Ada Colau": "AdaColau", "Irene Montero": "IreneMontero",
    "Mariano Rajoy": "marianorajoy", "Jorge Buxadé": "Jorgebuxade", "Félix Bolaños": "felixbolanosg",
    "Carlos Cuerpo": "carlos_cuerpo", "Míriam Nogueras": "miriamnoguerasM", "Alfonso Fernández Mañueco": "alferma1",
}


def env():
    return dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))


async def sesion():
    """Abre la cuenta de cookies en cache/x_cuentas.db; solo se rehace si la sesión del .env ha cambiado
    (rehacerla borraría el registro de límites de X que lleva twscrape)."""
    e = env()
    usuario = e.get("X_LOGIN", "sesion").strip().strip('"')
    api = API(str(DB))
    for c in await api.pool.get_all():
        if c.username == usuario and c.cookies.get("auth_token") == e["X_AUTH_TOKEN"].strip():
            return api
    await api.pool.delete_accounts(usuario)
    await api.pool.add_account(usuario, e.get("X_PASSWORD", "-"), e.get("X_EMAIL", "-"), "-",
                               cookies=f"auth_token={e['X_AUTH_TOKEN'].strip()}; ct0={e['X_CT0'].strip()}")
    return api


def oficial(texto):
    """Devuelve (nombre, cuenta) si está en la lista cerrada; si no, para."""
    t = texto.lstrip("@").lower()
    for n, h in CUENTAS.items():
        if t in (h.lower(), n.lower()):
            return n, h
    raise SystemExit(f"«{texto}» no está en la lista de cuentas oficiales: no se consulta")


async def verifica():
    api = await sesion()
    for n, h in CUENTAS.items():
        try:
            u = await api.user_by_login(h)
        except Exception as ex:
            print(f"  ERROR {n:24s} @{h}: {type(ex).__name__}")
            continue
        if u is None:
            print(f"  NO EXISTE {n:24s} @{h}")
            continue
        print(f"  {n:24s} @{u.username:18s} «{u.displayname}» verificada={bool(u.verified or u.blue)} seguidores={u.followersCount:,}", flush=True)


async def tuits(cuenta, dia=None):
    n, h = oficial(cuenta)
    dia = dia or datetime.now(MADRID).strftime("%Y-%m-%d")
    api = await sesion()
    u = await api.user_by_login(h)
    if u is None:
        raise SystemExit(f"X no devuelve la cuenta @{h} (¿sesión caducada?)")
    print(f"{n} · @{u.username} «{u.displayname}» · verificada={bool(u.verified or u.blue)} · {u.followersCount:,} seguidores · día {dia}\n")
    vistos = 0
    async for t in api.user_tweets(u.id, limit=60):
        if t.user.id != u.id:                    # el muro puede traer tuits ajenos que no son de la cuenta
            continue
        loc = t.date.astimezone(MADRID)
        if loc.strftime("%Y-%m-%d") == dia:
            vistos += 1
            tipo = "RT " if t.retweetedTweet else ""
            print(f"[{loc:%H:%M}] {tipo}{t.rawContent}\n   {t.url}\n")
    print(f"{vistos} tuits ese día")


def _oficial_de(handle):
    """Nombre de la lista cerrada para una cuenta (sin distinguir mayúsculas), o None."""
    h = (handle or "").lower()
    return next((n for n, x in CUENTAS.items() if x.lower() == h), None)


async def _de_cuenta(api, n, h, desde, por_cuenta):
    """22-nov-2026: también sus RESPUESTAS, pero solo a otra cuenta oficial (un cruce de declaraciones) o a sí misma (un
    hilo): ahí es donde los políticos se contestan. Cada cruce lleva el tuit al que responde o que cita (responde_a)."""
    u = await api.user_by_login(h)
    if u is None or u.username.lower() != h.lower() or u.followersCount < MIN_SEGUIDORES:
        raise ValueError(f"@{h} no parece la cuenta oficial")
    out = []
    async for t in api.user_tweets_and_replies(u.id, limit=40):
        if t.user.id != u.id or t.retweetedTweet or t.date < desde:      # sin retuits: no son palabras suyas
            continue
        otro = None
        if t.inReplyToTweetId:
            dest = _oficial_de(t.inReplyToScreenName or (t.inReplyToUser.username if t.inReplyToUser else ""))
            if dest is None:
                continue                         # respuesta a un particular: no es un cruce ni noticia
            if dest != n:
                try:
                    pt = await asyncio.wait_for(api.tweet_details(t.inReplyToTweetId), 20)
                except Exception:
                    pt = None
                if pt is not None and _oficial_de(pt.user.username) == dest:
                    otro = {"quien": f"{dest} (@{pt.user.username})", "texto": pt.rawContent[:600], "enlace": pt.url,
                            "fecha": pt.date.astimezone(MADRID).isoformat(), "como": "responde"}
        texto = t.rawContent
        if t.quotedTweet:                        # si cita otro tuit, sin él no se entiende lo que dice
            texto += f" [cita a @{t.quotedTweet.user.username}: {t.quotedTweet.rawContent}]"
            dest = _oficial_de(t.quotedTweet.user.username)
            if otro is None and dest and dest != n:
                q = t.quotedTweet
                otro = {"quien": f"{dest} (@{q.user.username})", "texto": q.rawContent[:600], "enlace": q.url,
                        "fecha": q.date.astimezone(MADRID).isoformat(), "como": "cita"}
        d = {"quien": f"{n} (@{u.username})", "canal": "X, cuenta oficial", "fecha": t.date.astimezone(MADRID).isoformat(),
             "texto": texto[:600], "enlace": t.url}
        if otro:
            d["responde_a"] = otro
        out.append(d)
    out.sort(key=lambda x: x["fecha"], reverse=True)
    cruces = [x for x in out if x.get("responde_a")]
    resto = [x for x in out if not x.get("responde_a")]
    return (cruces + resto)[:max(por_cuenta, len(cruces))]   # los cruces no se recortan


_VACIAS = set("""Gobierno España Sánchez Feijóo Abascal Congreso PSOE Vox Partido Popular Presidente Madrid Hoy Este Esta
Estos Estas Para Pero Porque Cuando Todo Todos Hay Hoy Gracias Nuestro Nuestra Nosotros Vamos Ahora Aquí Allí Elecciones
VotaPSOE LaFuerzaDeLaGente Entrevista Necesario Gente Gracias Buenos Feliz Directo""".split())


def voces(tuits, minimo=2):
    """22-nov-2026 (el usuario: «aunque no sea un cruce directo, también sirven comentarios relacionados con la historia
    principal»): agrupa los tuits de cuentas DISTINTAS que hablan de la misma historia: comparten un nombre propio o una
    etiqueta poco frecuente ese día (no a principio de frase, ni de los que salen en todo: Sánchez, Feijóo...).
    Devuelve [(claves, [tuits])], de más voces a menos."""
    import re
    from collections import Counter

    def claves(t):
        t = re.sub(r"https?://\S+|@\w+", " ", t.split(" [cita a ")[0])
        out = set()
        for m in re.finditer(r"(#?)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,})\b", t):
            antes = t[:m.start()].rstrip()
            if not m.group(1) and (not antes or antes[-1] in ".!?:¿¡«\"\n"):
                continue                                   # mayúscula de principio de frase
            if m.group(2) not in _VACIAS:
                out.add(m.group(2))
        return out
    ks = [claves(x["texto"]) for x in tuits]
    df = Counter(w for k in ks for w in k)
    tope = max(3, len(tuits) // 12)                        # lo que sale en todo no identifica una historia
    por_pal = {}
    for i, k in enumerate(ks):
        for w in k:
            if df[w] <= tope:
                por_pal.setdefault(w, set()).add(i)
    grupos = []                                            # [palabras, índices]; se unen si comparten casi los mismos tuits
    for w, idx in sorted(por_pal.items(), key=lambda z: -len(z[1])):
        if len({tuits[i]["quien"] for i in idx}) < minimo:
            continue
        g = next((g for g in grupos if len(g[1] & idx) / len(g[1] | idx) >= 0.5), None)
        if g:
            g[0].append(w); g[1] |= idx
        else:
            grupos.append([[w], set(idx)])
    out, usados = [], set()
    for ws, idx in sorted(grupos, key=lambda g: -len({tuits[i]["quien"] for i in g[1]})):
        if idx <= usados:
            continue
        usados |= idx
        out.append((ws, [tuits[i] for i in sorted(idx)]))
    return out


def cruces(tuits):
    """Los intercambios reales entre dos cuentas oficiales distintas (uno responde o cita al otro), sin repetir."""
    vistos, out = set(), []
    for x in tuits:
        r = x.get("responde_a")
        if r and x["enlace"] not in vistos:
            vistos.add(x["enlace"])
            out.append({"de": r, "replica": {k: x[k] for k in ("quien", "texto", "enlace", "fecha")}})
    return out


async def _recientes(horas, por_cuenta):
    api = await sesion()
    desde = datetime.now(timezone.utc) - timedelta(hours=horas)
    datos, fallos, sin_respuesta, seguidas = [], [], [], 0
    for n, h in CUENTAS.items():
        try:
            datos += await asyncio.wait_for(_de_cuenta(api, n, h, desde, por_cuenta), TOPE_CUENTA)
            seguidas = 0
        except asyncio.TimeoutError:
            sin_respuesta.append((n, h))
            seguidas += 1
            if seguidas == 3:                    # tres seguidas: la sesión ha caído, no se espera por las demás
                fallos = [f"@{x} (sin respuesta)" for _, x in sin_respuesta] + ["resto sin consultar"]
                return datos, fallos
        except Exception as ex:                  # una cuenta que falla no para las demás
            fallos.append(f"@{h} ({type(ex).__name__})")
    for n, h in sin_respuesta:                   # segunda pasada: la primera llamada de la sesión puede tardar mucho
        try:
            datos += await asyncio.wait_for(_de_cuenta(api, n, h, desde, por_cuenta), TOPE_CUENTA)
        except Exception as ex:
            fallos.append(f"@{h} ({type(ex).__name__})")
    return datos, fallos


def por_turnos(datos):
    """Primero el tuit más reciente de cada cuenta, luego el segundo de cada una...: si el dossier se recorta por
    el final, el recorte toca a todas por igual y no a las últimas de la lista."""
    vistos, orden = {}, []
    for x in datos:
        vistos[x["quien"]] = vistos.get(x["quien"], 0) + 1
        orden.append((vistos[x["quien"]], x))
    return [x for _, x in sorted(orden, key=lambda z: z[0])]


def recientes(horas=30, por_cuenta=5):
    """(tuits, cuentas_que_fallan) de las últimas horas de toda la lista; sin retuits y con un tope por cuenta,
    para que ningún partido copie el dossier. Sin sesión en el .env devuelve todas las cuentas como fallo."""
    if "X_AUTH_TOKEN" not in env():
        return [], list(CUENTAS.values())
    datos, fallos = asyncio.run(_recientes(horas, por_cuenta))
    return por_turnos(datos), fallos


async def _encargo(cuentas, busqueda, horas, por_cuenta):
    """21-nov-2026: material extra del encargo del director (encargo.json → "busca_x"): los tuits recientes de las
    cuentas del encargo (comprobadas como en _de_cuenta: nombre exacto y 10.000+ seguidores) y, si hay búsqueda, los
    tuits que la contienen SOLO de esas cuentas o de las de la lista cerrada (nunca de cuentas anónimas)."""
    api = await sesion()
    desde = datetime.now(timezone.utc) - timedelta(hours=horas)
    datos, fallos = [], []
    for n, h in cuentas.items():
        try:
            datos += await asyncio.wait_for(_de_cuenta(api, n, h, desde, por_cuenta), TOPE_CUENTA)
        except Exception as ex:
            fallos.append(f"@{h} ({type(ex).__name__})")
    validas = {h.lower(): n for n, h in {**CUENTAS, **cuentas}.items()}
    for q in busqueda:
        try:
            async def _busca():
                out = []
                async for t in api.search(q, limit=60):
                    h = t.user.username.lower()
                    if h in validas and not t.retweetedTweet and t.date >= desde and t.user.followersCount >= MIN_SEGUIDORES:
                        texto = t.rawContent
                        if t.quotedTweet:
                            texto += f" [cita a @{t.quotedTweet.user.username}: {t.quotedTweet.rawContent}]"
                        out.append({"quien": f"{validas[h]} (@{t.user.username})", "canal": f"X, búsqueda «{q}»",
                                    "fecha": t.date.astimezone(MADRID).isoformat(), "texto": texto[:600], "enlace": t.url})
                return out
            datos += await asyncio.wait_for(_busca(), TOPE_CUENTA * 2)
        except Exception as ex:
            fallos.append(f"búsqueda «{q}» ({type(ex).__name__})")
    vistos, out = set(), []
    for x in datos:
        if x["enlace"] not in vistos:
            vistos.add(x["enlace"])
            out.append(x)
    return out, fallos


def encargo(cuentas, busqueda=(), horas=48, por_cuenta=8):
    """(tuits, fallos) del encargo del director; sin sesión de X, nada."""
    if "X_AUTH_TOKEN" not in env():
        return [], ["sin sesión de X"]
    return asyncio.run(_encargo(dict(cuentas), list(busqueda), horas, por_cuenta))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["verifica"]:
        asyncio.run(verifica())
    elif a[:1] == ["tuits"] and len(a) >= 2:
        asyncio.run(tuits(a[1], a[2] if len(a) > 2 else None))
    else:
        print(__doc__)
