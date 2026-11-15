"""RECORTES TRATADOS de la biblioteca de fotos (15-nov-2026, petición del usuario): deja a cada político SIN FONDO
(PNG transparente), tratado una sola vez, para reutilizarlo en muchos fondos sin volver a llamar a OpenAI.
Toma las mejores fotos de biblioteca_fotos (prefiere las de UNA sola cara, que recortan limpio), las recorta con rembg
(miniatura.recorte, que ya limpia el pelo y la base) y las guarda con biblioteca_fotos.guarda_recorte.
Uso:  python recortar_biblioteca.py [persona]   (sin persona: todas las de la biblioteca)"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

import biblioteca_fotos as BF
import miniatura as M

MAX_POR_PERSONA = 3                     # variedad sin pasarse (se reutilizan en muchos fondos)


def _una_cara(ruta):
    try:
        return M.n_caras(Image.open(ruta).convert("RGB")) == 1
    except Exception:
        return False


def recorta_persona(slug):
    fichas = BF._catalogo().get(slug, [])
    if not fichas:
        return 0
    # las de una sola cara primero (recorte limpio), luego por puntuación
    fichas = sorted(fichas, key=lambda f: (not _una_cara(BF.BIB / f["img"]), -float(f.get("puntos") or 0)))
    hechos = 0
    for f in fichas:
        if hechos >= MAX_POR_PERSONA:
            break
        src = BF.BIB / f["img"]
        try:
            rec = M.recorte(src)                       # RGBA sin fondo (cacheado junto a la foto)
        except Exception as e:
            print(f"    (no recorta {src.name}: {type(e).__name__})")
            continue
        if min(rec.size) < 200:                        # recorte pobre
            continue
        tmp = src.with_name(src.stem + "_rec.png")
        rec.save(tmp)
        BF.guarda_recorte(f["persona"], tmp, origen=f["hash"], puntos=f.get("puntos", ""))
        tmp.unlink(missing_ok=True)
        hechos += 1
        print(f"    {f['persona']}: recorte {hechos} ({rec.width}x{rec.height})")
    return hechos


if __name__ == "__main__":
    if len(sys.argv) > 1:
        slugs = [BF._slug(sys.argv[1])]
    else:
        slugs = [s for s in BF._catalogo() if not s.startswith("_")]
    tot = 0
    for s in slugs:
        print(f"· {s}")
        tot += recorta_persona(s)
    print(f"\nListo: {tot} recortes tratados.")
    print(BF.cuantas())
