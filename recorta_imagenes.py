"""RECORTE AUTOMÁTICO DE PERSONAJES (27-nov-2026, el usuario: «sí, hazlo»). El montaje solo usa figuras con fondo
transparente; las que el usuario sube con fondo (negro, liso) se descartaban sin avisar. Este script recorta cada PNG sin
transparencia con rembg (modelo isnet-general-use, en el servidor, sin coste) y guarda la copia transparente en una
subcarpeta «recortadas» junto al original (el original no se toca; la cara no se retoca: solo se quita el fondo).
Se salta las fotos de grupo (nombres con «fila», «grupo», «varios») y lo ya recortado. La jornada lo llama al empezar.
Uso: python recorta_imagenes.py [carpeta ...]   (por defecto: Imagenes/Políticos e Imagenes/Presentador)"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).parent
POR_DEFECTO = [RAIZ / "Imagenes" / "Políticos", RAIZ / "Imagenes" / "Presentador"]
GRUPO = ("fila", "grupo", "varios")


def _transparente(im):
    return im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 20


def pendientes(carpetas):
    out = []
    for c in carpetas:
        for p in sorted(Path(c).rglob("*.png")):
            if "recortadas" in p.parts or any(g in p.stem.lower() for g in GRUPO):
                continue
            destino = p.parent / "recortadas" / p.name
            if destino.exists():
                continue
            try:
                if not _transparente(Image.open(p)):
                    out.append((p, destino))
            except OSError:
                continue
    return out


def main(carpetas):
    lista = pendientes(carpetas)
    if not lista:
        print("recorte: nada pendiente")
        return []
    from rembg import new_session, remove
    ses = new_session("isnet-general-use")
    hechas = []
    for p, destino in lista:
        destino.parent.mkdir(exist_ok=True)
        out = remove(Image.open(p).convert("RGB"), session=ses)
        out.save(destino)
        hechas.append(destino)
        print(f"recortada: {p.relative_to(RAIZ)} -> {destino.relative_to(RAIZ)}")
    return hechas


if __name__ == "__main__":
    main([Path(a) for a in sys.argv[1:]] or POR_DEFECTO)
