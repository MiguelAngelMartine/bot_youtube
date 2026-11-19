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


def _ascii(s):
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode())


# Apellidos compartidos (15-nov-2026): el slug por defecto es el último apellido, pero cuando dos políticos lo comparten
# hay que distinguirlos por el nombre completo, o se mezclan sus fotos (p. ej. Irene Montero vs María Jesús Montero).
_DESAMBIGUA = {
    "iremontero": {"irene"}, "mjmontero": {"maria", "mariajesus", "jesus", "mariaj"},   # Montero
}


def misma(pedida, ficha):
    """19-nov-2026 (fallo real: en un Short salió Koldo García por José Ignacio García): la biblioteca se agrupa por
    apellido, así que una ficha solo vale si es de LA MISMA persona. Si se pide solo el apellido, vale cualquiera;
    si no, todos los nombres de pila pedidos tienen que estar en el nombre de la ficha (o al revés)."""
    a = [_ascii(w) for w in (pedida or "").split()]
    b = [_ascii(w) for w in (ficha or "").split()]
    if len(a) <= 1 or not b:
        return True
    sa, sb = set(a), set(b)
    return sa <= sb or sb <= sa or (a[0] == b[0] and a[-1] == b[-1])


def _slug(nombre):
    base = _ascii((nombre or "").split()[-1]) or "otro"
    nom = _ascii(" ".join((nombre or "").split()[:-1]))     # nombre de pila (sin el apellido final)
    for slug, pistas in _DESAMBIGUA.items():
        if slug.endswith(base) and any(p in nom for p in pistas):
            return slug
    return base


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
    out = [f for f in _catalogo().get(slug, []) if (BIB / f["img"]).exists() and misma(persona, f.get("persona"))]
    out.sort(key=lambda f: -float(f.get("puntos") or 0))
    return out


# --- RECORTES TRATADOS (15-nov-2026, petición del usuario): la persona ya SIN FONDO (PNG transparente), tratada una vez,
# para reutilizarla en MUCHOS fondos sin volver a llamar a OpenAI. Se guardan aparte, en <slug>/recortes/, y el índice va
# en la clave "_recortes" del catálogo (las claves que empiezan por "_" no son personas). ---
REC = "recortes"


def guarda_recorte(persona, png_ruta, origen="", puntos=""):
    """Guarda un recorte tratado (persona sin fondo, PNG) reutilizable. No repite (hash). Devuelve la ruta o None."""
    png = Path(png_ruta)
    if not png.exists():
        return None
    datos = png.read_bytes()
    h = hashlib.sha1(datos).hexdigest()[:16]
    slug = _slug(persona)
    cat = _catalogo()
    recs = cat.setdefault("_recortes", {}).setdefault(slug, [])
    if any(r.get("hash") == h for r in recs):
        return BIB / slug / REC / f"{h}.png"
    carpeta = BIB / slug / REC
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{h}.png"
    shutil.copyfile(png, destino)
    recs.append({"hash": h, "img": f"{slug}/{REC}/{h}.png", "persona": persona,
                 "origen": origen, "puntos": puntos, "guardado": time.strftime("%Y-%m-%d")})
    _guarda_catalogo(cat)
    return destino


def recortes(persona):
    """Recortes tratados de la persona existentes en disco, de mejor a peor puntuación."""
    slug = _slug(persona)
    out = [r for r in _catalogo().get("_recortes", {}).get(slug, []) if (BIB / r["img"]).exists() and misma(persona, r.get("persona"))]
    out.sort(key=lambda r: -float(r.get("puntos") or 0))
    return out


def mejor_recorte(persona, usadas=()):
    """RESPALDO reutilizable: (ruta, ficha) del mejor recorte tratado sin usar; si no quedan, el mejor igualmente."""
    rs = recortes(persona)
    frescos = [r for r in rs if r["hash"] not in set(usadas)] or rs
    return (BIB / frescos[0]["img"], frescos[0]) if frescos else (None, None)


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
    return {s: len(v) for s, v in cat.items() if not s.startswith("_")}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(f"{sys.argv[1]}: {cuantas(sys.argv[1])} fotos en la biblioteca")
    else:
        tot = cuantas()
        rec = {s: len(v) for s, v in _catalogo().get("_recortes", {}).items()}
        print(f"Biblioteca de fotos: {sum(tot.values())} fotos de {len(tot)} personas"
              f"  ·  recortes tratados: {sum(rec.values())} de {len(rec)}")
        for s, n in sorted(tot.items(), key=lambda x: -x[1]):
            print(f"  {s}: {n} fotos, {rec.get(s, 0)} recortes")
