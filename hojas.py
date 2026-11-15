"""HOJAS DE CONTACTO desde el mp4 (15-nov-2026): el motor nuevo (render_ambiente) no escribe escenas.json, así que
control_calidad.py no puede sacar las hojas para el control visual de Gemini. Este script muestrea el vídeo a intervalos
regulares y deja calidad/hoja_NN.png (rejilla de fotogramas), que es lo que mira jornada.control_visual.
Uso: python hojas.py AAAA-MM-DD [segundos_entre_fotogramas=12]"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).parent


def hojas(fecha, cada=12, por_hoja=9, ancho=480):
    import cv2
    import numpy as np
    dia = RAIZ / "dia" / fecha
    mp4 = dia / "episodio.mp4"
    if not mp4.exists():
        print("no hay episodio.mp4")
        return 0
    cal = dia / "calidad"
    cal.mkdir(parents=True, exist_ok=True)
    for viejo in cal.glob("hoja_*.png"):
        viejo.unlink()
    cap = cv2.VideoCapture(str(mp4))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    dur = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
    alto = int(ancho * 9 / 16)
    tiempos = [t for t in range(3, int(dur), cada)]
    fr = []
    for t in tiempos:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, im = cap.read()
        if ok:
            fr.append(cv2.resize(im, (ancho, alto)))
    n = 0
    for i in range(0, len(fr), por_hoja):
        grupo = fr[i:i + por_hoja]
        filas = [np.hstack(grupo[j:j + 3] + [np.zeros_like(grupo[0])] * (3 - len(grupo[j:j + 3])))
                 for j in range(0, len(grupo), 3)]
        n += 1
        cv2.imwrite(str(cal / f"hoja_{n:02d}.png"), np.vstack(filas))
    print(f"{n} hojas de contacto -> {cal}")
    return n


if __name__ == "__main__":
    hojas(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 12)
