"""Comprueba las fuentes del canal de fútbol (futbol/fuentes.py):
  - cada RSS: responde y trae noticias de las últimas 48 h;
  - cada cuenta de X: existe, nombre que se muestra, verificada y seguidores (con la sesión de x_oficiales); si no existe,
    busca candidatas por el nombre para elegirla a mano (nunca se da por buena sola).
Escribe futbol/fuentes_comprobadas.md. Uso: python futbol/comprueba.py [rss|x]"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent))

import fuentes as F  # noqa: E402

MIN_SEG = 5000


def _fecha(e):
    """Segundos de la noticia: published/updated o, como en Sport, dc_created."""
    from email.utils import parsedate_to_datetime
    from datetime import datetime
    for k in ("published_parsed", "updated_parsed"):
        if e.get(k):
            return time.mktime(e[k])
    v = e.get("dc_created") or e.get("dc_modified")
    if v:
        for fn in (lambda x: datetime.fromisoformat(x.replace("Z", "+00:00")), parsedate_to_datetime):
            try:
                return fn(v).timestamp()
            except (ValueError, TypeError):
                pass
    return None


def rss():
    import feedparser
    import requests
    filas = []
    for n, u in F.MEDIOS.items():
        url = F.url_de(u)
        if u.startswith("gnews"):
            time.sleep(4)                                # Google Noticias corta (429) si se le pide todo seguido
        try:
            r = requests.get(url, headers=F.UA, timeout=25)
            f = feedparser.parse(r.content)
            ahora = time.time()
            recientes = [e for e in f.entries if (t := _fecha(e)) and ahora - t < 48 * 3600]
            ok = r.ok and len(recientes) > 0
            ej = (recientes or f.entries or [{}])[0].get("title", "")[:70]
            filas.append((n, u, ok, f"HTTP {r.status_code}, {len(f.entries)} noticias, {len(recientes)} de las últimas 48 h", ej))
        except Exception as e:
            filas.append((n, u, False, type(e).__name__, ""))
        print(("OK " if filas[-1][2] else "NO ") + n + " · " + filas[-1][3], flush=True)
    return filas


async def _x():
    import x_oficiales as XO
    api = await XO.sesion()
    filas = []
    for grupo, cuentas in F.X.items():
        for n, h in cuentas.items():
            try:
                u = await asyncio.wait_for(api.user_by_login(h), 45)
            except Exception as e:
                filas.append((grupo, n, h, None, f"error {type(e).__name__}", ""))
                print(f"?? {n} @{h}", flush=True)
                continue
            if u is None:
                cand = ""
                try:
                    res = []
                    async for c in api.search_user(n, limit=5):
                        res.append(f"@{c.username} «{c.displayname}» {c.followersCount:,}")
                    cand = "; ".join(res[:4])
                except Exception:
                    pass
                filas.append((grupo, n, h, False, "no existe", cand))
                print(f"NO {n} @{h} -> {cand}", flush=True)
                continue
            ok = u.followersCount >= MIN_SEG
            filas.append((grupo, n, h, ok, f"«{u.displayname}» · verificada={bool(u.verified or u.blue)} · "
                                          f"{u.followersCount:,} seguidores", ""))
            print(("OK " if ok else "?? ") + f"{n} @{u.username} «{u.displayname}» {u.followersCount:,}", flush=True)
    return filas


def main(que=("rss", "x")):
    md = ["# Fuentes del canal de fútbol: comprobación", "", f"_{time.strftime('%Y-%m-%d %H:%M')}_", ""]
    if "rss" in que:
        md += ["## Medios (RSS)", "", "| | Medio | Fuente | Estado | Ejemplo |", "|---|---|---|---|---|"]
        for n, u, ok, est, ej in rss():
            md.append(f"| {'✅' if ok else '❌'} | {n} | `{u}` | {est} | {ej} |")
        md.append("")
    if "x" in que:
        filas = asyncio.run(_x())
        for g in F.X:
            md += [f"## X · {g}", "", "| | Nombre | Cuenta | Comprobación | Candidatas si no existe |", "|---|---|---|---|---|"]
            for gg, n, h, ok, est, cand in filas:
                if gg == g:
                    md.append(f"| {'✅' if ok else ('❌' if ok is False else '⚠️')} | {n} | @{h} | {est} | {cand} |")
            md.append("")
    (AQUI / "fuentes_comprobadas.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"-> {AQUI / 'fuentes_comprobadas.md'}")


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or ("rss", "x"))
