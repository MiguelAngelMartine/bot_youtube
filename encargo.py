"""ENCARGO DEL DIRECTOR (7-nov-2026): el usuario puede pedir para un día concreto la frase de la miniatura y de un Short
(p. ej., un tuit de Ayuso). La norma no cambia: solo se usa si se comprueba que es REAL y LITERAL.

dia/<fecha>/encargo.json:
  {"persona": "Isabel Díaz Ayuso", "frase": "Hay que ser cobarde", "tema": "Sánchez quiere evitar el cara a cara con
   Feijóo", "canal": "X", "cuenta": "IdiazAyuso", "enlace": "https://x.com/IdiazAyuso/status/..." (opcional),
   "para": ["miniatura", "short"]}

Comprobación (sin gastar Claude): 1) si hay enlace, el texto del tuit con oEmbed (servicio oficial y gratuito de X):
autor = la cuenta y la frase literal dentro; 2) si no, la frase literal en los artículos del día (articulos/*.txt) o en
redes.md, con el apellido de la persona cerca. Escribe "verificada": true/false y "prueba" en el mismo fichero.
Uso: python encargo.py AAAA-MM-DD   (salida 0 = verificada, 1 = no verificada, 2 = no hay encargo)"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import requests

RAIZ = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 (ElHoyformativo; +https://github.com/MiguelAngelMartine/bot_youtube)"}


def _n(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def por_enlace(e):
    r = requests.get("https://publish.twitter.com/oembed", headers=UA, timeout=20,
                     params={"url": e["enlace"], "omit_script": "1"})
    if not r.ok:
        return None, f"oEmbed no responde ({r.status_code})"
    j = r.json()
    autor_url = j.get("author_url", "").rstrip("/").rsplit("/", 1)[-1].lower()
    m = re.search(r"<p[^>]*>(.*?)</p>", j.get("html", ""), re.S)
    texto = re.sub(r"<[^>]+>", " ", m.group(1) if m else "")
    if e.get("cuenta") and autor_url != e["cuenta"].lower():
        return False, f"el tuit es de @{autor_url}, no de @{e['cuenta']}"
    if _n(e["frase"]) in _n(texto):
        return True, f"tuit de @{autor_url} ({j.get('author_name', '')}): «{texto.strip()[:200]}» {e['enlace']}"
    return False, f"el tuit de @{autor_url} no contiene la frase literal: «{texto.strip()[:200]}»"


def por_noticias(dia, e):
    frase, apellido = _n(e["frase"]), _n(e["persona"].split()[-1])
    textos = [(f.name, f.read_text(encoding="utf-8", errors="ignore")) for f in sorted((dia / "articulos").glob("*.txt"))]
    if (dia / "redes.md").exists():
        textos.append(("redes.md", (dia / "redes.md").read_text(encoding="utf-8")))
    for nombre, t in textos:
        tn = _n(t)
        for m in re.finditer(re.escape(frase), tn):
            cerca = tn[max(0, m.start() - 400): m.end() + 400]
            if apellido in cerca:
                url = re.search(r"https?://\S+", t)
                return True, f"literal en {nombre} junto a «{e['persona']}»" + (f" ({url.group(0)})" if url else "")
    return False, "no aparece literal en los artículos ni en las redes del día"


def main(fecha):
    dia = RAIZ / "dia" / fecha
    f = dia / "encargo.json"
    if not f.exists():
        print("sin encargo del director")
        return 2
    e = json.loads(f.read_text(encoding="utf-8"))
    ok, prueba = (por_enlace(e) if e.get("enlace") else (None, ""))
    if not ok:
        ok2, prueba2 = por_noticias(dia, e)
        if ok2:
            ok, prueba = True, prueba2
        else:
            prueba = "; ".join(x for x in (prueba, prueba2) if x)
    e["verificada"], e["prueba"] = bool(ok), prueba
    f.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")
    print(("VERIFICADA: " if ok else "NO VERIFICADA: ") + prueba)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
