"""IMPORTAR PNGs TRANSPARENTES del usuario a la biblioteca de fotos (15-nov-2026, petición del usuario): copia los
recortes ya hechos a mano (fondo transparente, organizados por carpeta con el nombre del político) a la biblioteca local
de recortes tratados, para usarlos de forma fiable (identidad verificada por el usuario, sin artefactos de rembg).
Estructura esperada:  <raiz>/<Nombre del político>/<loquesea>.png   (también vale <raiz>/png_transparentes/<Político>/*.png)
Uso:  python importar_png.py <carpeta>    (p. ej. _importar/png_transparentes)"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

import biblioteca_fotos as BF


def _es_transparente(p):
    try:
        im = Image.open(p)
        return im.mode in ("RGBA", "LA") or "transparency" in im.info
    except Exception:
        return False


def importar(raiz):
    raiz = Path(raiz)
    if not raiz.exists():
        print(f"no existe: {raiz}")
        return 0
    # si dentro hay una sola carpeta png_transparentes, entra en ella
    hijos = [d for d in raiz.iterdir() if d.is_dir()]
    if len(hijos) == 1 and hijos[0].name.lower() in ("png_transparentes", "politicos_png"):
        raiz = hijos[0]
    total = 0
    for carpeta in sorted(d for d in raiz.iterdir() if d.is_dir()):
        persona = carpeta.name.replace("_", " ").strip()
        pngs = sorted(carpeta.glob("*.png")) + sorted(carpeta.glob("*.PNG"))
        n = 0
        for png in pngs:
            if not _es_transparente(png):
                print(f"  (saltada, sin transparencia: {png.name})")
                continue
            # puntos altos: recortes curados a mano por el usuario
            if BF.guarda_recorte(persona, png, origen="png_usuario", puntos="10"):
                n += 1
        if n:
            print(f"· {persona}: {n} recortes importados")
            total += n
    print(f"\nTotal: {total} recortes transparentes importados a la biblioteca.")
    print(BF.cuantas())
    return total


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python importar_png.py <carpeta con subcarpetas por político>")
        sys.exit(2)
    importar(sys.argv[1])
