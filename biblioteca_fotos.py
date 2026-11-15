"""BIBLIOTECA LOCAL DE FOTOS por político (15-nov-2026, petición del usuario): acumula los retratos buenos que vamos
bajando (fotos.mejores), bien etiquetados (persona, licencia, autor, fuente, url, título, fecha de la foto, nota, gesto),
para tener VARIEDAD en local y no depender de la red. Si un día falla la red o las fuentes, se tira de aquí.
- Carpeta en git para el servidor: canal/biblioteca_fotos/<apellido>/<hash>.jpg + catalogo.json (un índice central).
- guarda(persona, ruta, credito): copia el retrato a la biblioteca con su ficha (sin repetir, por hash del contenido).
- busca(persona, n, usadas): devuelve rutas de la biblioteca para esa persona (respaldo), evitando las ya usadas.
Documentación de referencia de TODA la biblioteca: canal/biblioteca_fotos/LEEME.md.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).parent
BIB = RAIZ / "canal" / "biblioteca_fotos"
CAT = BIB / "catalogo.json"


def _slug(nombre):
    s = unicodedata.normalize("NFKD", (nombre or "").split()[-1]).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s) or "otro"


def _catalogo():
    try:
        return json.loads(CAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _guarda_catalogo(cat):
    BIB.mkdir(parents=True, exist_ok=True)
    CAT.write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")


def guarda(persona, ruta, credito=None, gesto=""):
    """Añade un retrato a la biblioteca de `persona` con su ficha. No repite (hash del contenido). Devuelve la ruta en la
    biblioteca, o None si no se pudo."""
    ruta = Path(ruta)
    if not ruta.exists():
        return None
    datos = ruta.read_bytes()
    h = hashlib.sha1(datos).hexdigest()[:16]
    slug = _slug(persona)
    cat = _catalogo()
    fichas = cat.setdefault(slug, [])
    if any(f.get("hash") == h for f in fichas):            # ya está (mismo contenido)
        return BIB / slug / f"{h}.jpg"
    carpeta = BIB / slug
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{h}.jpg"
    shutil.copyfile(ruta, destino)
    c = credito or {}
    fichas.append({
        "hash": h, "img": f"{slug}/{h}.jpg", "persona": persona,
        "licencia": c.get("licencia", ""), "autor": c.get("autor", ""), "fuente": c.get("fuente", ""),
        "url": c.get("url", ""), "pagina": c.get("pagina", ""), "titulo": c.get("titulo", ""),
        "gesto": gesto or c.get("gesto", ""), "puntos": c.get("puntos_gemini", c.get("puntos", "")),
        "guardado": time.strftime("%Y-%m-%d"),
    })
    _guarda_catalogo(cat)
    return destino


def fichas(persona):
    """Fichas (con img y crédito) de la persona en la biblioteca, existentes en disco, de mejor a peor puntuación."""
    slug = _slug(persona)
    out = [f for f in _catalogo().get(slug, []) if (BIB / f["img"]).exists()]
    out.sort(key=lambda f: -float(f.get("puntos") or 0))
    return out


def busca(persona, n=3, usadas=()):
    """RESPALDO: rutas de hasta n retratos de la biblioteca para esa persona, evitando las usadas (por hash); si no quedan
    sin usar, devuelve las mejores igualmente (mejor repetir que no tener foto). Devuelve [(ruta, ficha), ...]."""
    fs = fichas(persona)
    if not fs:
        return []
    frescas = [f for f in fs if f["hash"] not in set(usadas)] or fs
    return [(BIB / f["img"], f) for f in frescas[:n]]


def cuantas(persona=None):
    cat = _catalogo()
    if persona:
        return len(cat.get(_slug(persona), []))
    return {s: len(v) for s, v in cat.items()}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(f"{sys.argv[1]}: {cuantas(sys.argv[1])} fotos en la biblioteca")
    else:
        tot = cuantas()
        print(f"Biblioteca de fotos: {sum(tot.values())} fotos de {len(tot)} personas")
        for s, n in sorted(tot.items(), key=lambda x: -x[1]):
            print(f"  {s}: {n}")
