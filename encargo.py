"""ENCARGO DEL DIRECTOR (7-nov-2026): el usuario puede pedir para un día concreto la frase de la miniatura y de un Short
(p. ej., un tuit de Ayuso). La norma no cambia: solo se usa si se comprueba que es REAL y LITERAL.

dia/<fecha>/encargo.json:
  {"persona": "Isabel Díaz Ayuso", "frase": "Hay que ser cobarde", "tema": "Sánchez quiere evitar el cara a cara con
   Feijóo", "canal": "X", "cuenta": "IdiazAyuso", "enlace": "https://x.com/IdiazAyuso/status/..." (opcional),
   "para": ["miniatura", "short"]}

Comprobación (sin gastar Claude): 1) si hay enlace, el texto del tuit con oEmbed (servicio oficial y gratuito de X):
autor = la cuenta y la frase literal dentro; 2) si no, la frase literal en los artículos del día (articulos/*.txt) o en
redes.md, con el apellido de la persona cerca. Escribe "verificada": true/false y "prueba" en el mismo fichero.
Cruce (21-nov-2026): "cruce": [{persona, partido, cuenta, enlace, frase, papel}, ...] — un Short de cruce de declaraciones
(frase y réplicas); cada frase se comprueba por separado y solo se usan las comprobadas.
Tema (23-nov-2026): "short_tema": {"tema": "...", "instrucciones": "..."} — un Short sobre un tema, sin frase dada:
lo más fuerte del material comprobado (con "busca_x" para traer los tuits de las cuentas del tema).
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


def cruce(f, e, dia):
    """Cada frase del cruce se comprueba igual que una sola (tuit por oEmbed y, si no, noticias del día). Las que no
    se comprueban se quedan fuera; el cruce vale si quedan al menos dos de partidos distintos."""
    for x in e["cruce"]:
        ok, prueba = por_enlace(x) if x.get("enlace") else (None, "")
        if not ok:
            ok2, prueba2 = por_noticias(dia, x)
            ok, prueba = (True, prueba2) if ok2 else (False, "; ".join(y for y in (prueba, prueba2) if y))
        x["verificada"], x["prueba"] = bool(ok), prueba
        print(("  OK " if ok else "  NO ") + f"{x['persona']}: «{x['frase'][:60]}» — {prueba[:120]}")
    buenas = [x for x in e["cruce"] if x["verificada"]]
    e["verificada"] = len(buenas) >= 2 and len({x.get("partido") for x in buenas}) >= 2
    e["prueba"] = f"{len(buenas)} de {len(e['cruce'])} frases del cruce comprobadas"
    f.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")
    print(("VERIFICADO: " if e["verificada"] else "NO VERIFICADO: ") + e["prueba"])
    return 0 if e["verificada"] else 1


def main(fecha):
    dia = RAIZ / "dia" / fecha
    f = dia / "encargo.json"
    if not f.exists():
        print("sin encargo del director")
        return 2
    e = json.loads(f.read_text(encoding="utf-8"))
    if e.get("cruce"):                                  # 21-nov-2026: Short de cruce de declaraciones por encargo
        return cruce(f, e, dia)
    if not e.get("frase") or not e.get("persona"):      # 20-nov: encargo sin frase (p. ej., solo día monográfico)
        print("encargo sin frase que comprobar")
        return 2
    ok, prueba = (por_enlace(e) if e.get("enlace") else (None, ""))
    if ok is False and e.get("enlace"):                 # el tuit dice otra cosa o es de otra cuenta: nunca se usa
        e.pop("comprobada_a_mano", None)
    if not ok:
        ok2, prueba2 = por_noticias(dia, e)
        if ok2:
            ok, prueba = True, prueba2
        else:
            prueba = "; ".join(x for x in (prueba, prueba2) if x)
    if not ok and e.get("comprobada_a_mano"):           # comprobación hecha a mano con pruebas (p. ej., la vista previa
        ok, prueba = True, e["comprobada_a_mano"]       # del tuit + su enlace t.co resuelto), si el oEmbed no la contradice
    e["verificada"], e["prueba"] = bool(ok), prueba
    f.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")
    print(("VERIFICADA: " if ok else "NO VERIFICADA: ") + prueba)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
