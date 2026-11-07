"""X (Twitter): tuits de las CUENTAS OFICIALES de políticos y partidos, con twscrape y la sesión del .env
(X_AUTH_TOKEN, X_CT0). La lista es cerrada: cualquier otra cuenta se rechaza, para no citar nunca una cuenta falsa o parodia.
Uso: python x_oficiales.py verifica             -> comprueba cada cuenta en X (nombre, verificada, seguidores)
     python x_oficiales.py tuits <cuenta> [AAAA-MM-DD]   -> tuits de ese día en hora de Madrid (por defecto, hoy)"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from twscrape import API

RAIZ = Path(__file__).parent
MADRID = ZoneInfo("Europe/Madrid")
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
    """Abre la cuenta de cookies en cache/x_cuentas.db (se rehace si las cookies del .env han cambiado)."""
    e = env()
    usuario = e.get("X_LOGIN", "sesion").strip().strip('"')
    api = API(str(RAIZ / "cache" / "x_cuentas.db"))
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


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["verifica"]:
        asyncio.run(verifica())
    elif a[:1] == ["tuits"] and len(a) >= 2:
        asyncio.run(tuits(a[1], a[2] if len(a) > 2 else None))
    else:
        print(__doc__)
