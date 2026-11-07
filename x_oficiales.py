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


async def _de_cuenta(api, n, h, desde, por_cuenta):
    u = await api.user_by_login(h)
    if u is None or u.username.lower() != h.lower() or u.followersCount < MIN_SEGUIDORES:
        raise ValueError(f"@{h} no parece la cuenta oficial")
    out = []
    async for t in api.user_tweets(u.id, limit=20):
        if t.user.id != u.id or t.retweetedTweet or t.date < desde:      # sin retuits: no son palabras suyas
            continue
        texto = t.rawContent
        if t.quotedTweet:                        # si cita otro tuit, sin él no se entiende lo que dice
            texto += f" [cita a @{t.quotedTweet.user.username}: {t.quotedTweet.rawContent}]"
        out.append({"quien": f"{n} (@{u.username})", "canal": "X, cuenta oficial", "fecha": t.date.astimezone(MADRID).isoformat(),
                    "texto": texto[:900], "enlace": t.url})
    return sorted(out, key=lambda x: x["fecha"], reverse=True)[:por_cuenta]


async def _recientes(horas, por_cuenta):
    api = await sesion()
    desde = datetime.now(timezone.utc) - timedelta(hours=horas)
    datos, fallos, seguidas = [], [], 0
    for n, h in CUENTAS.items():
        try:
            datos += await asyncio.wait_for(_de_cuenta(api, n, h, desde, por_cuenta), TOPE_CUENTA)
            seguidas = 0
        except asyncio.TimeoutError:             # tres seguidas sin respuesta: la sesión ha caído, no se espera por las demás
            fallos.append(f"@{h} (sin respuesta)")
            seguidas += 1
            if seguidas == 3:
                fallos.append("resto sin consultar")
                break
        except Exception as ex:                  # una cuenta que falla no para las demás
            fallos.append(f"@{h} ({type(ex).__name__})")
    return datos, fallos


def recientes(horas=30, por_cuenta=8):
    """(tuits, cuentas_que_fallan) de las últimas horas de toda la lista; sin retuits y con un tope por cuenta,
    para que ningún partido copie el dossier. Sin sesión en el .env devuelve todas las cuentas como fallo."""
    if "X_AUTH_TOKEN" not in env():
        return [], list(CUENTAS.values())
    return asyncio.run(_recientes(horas, por_cuenta))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["verifica"]:
        asyncio.run(verifica())
    elif a[:1] == ["tuits"] and len(a) >= 2:
        asyncio.run(tuits(a[1], a[2] if len(a) > 2 else None))
    else:
        print(__doc__)
