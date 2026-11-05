"""SHORTS DEL DÍA (decisión del usuario del 5-nov-2026): tras subir el vídeo largo, hasta 3 Shorts verticales, uno por
frase con más gancho, cada uno con su portada. Todo en el servidor, sin agentes (ahorro de tokens):
  1) shorts_guion.py elige y comprueba las frases (Gemini; si no responde, hoy no hay Shorts: son un extra);
  2) short.py renderiza cada uno;
  3) deja shorts/hoja.png con 5 fotogramas de cada Short para la revisión visual antes de subir.
Después, quien coordina mira hoja.png y, si está bien, sube con: python subir.py <fecha> shorts
Uso: python shorts_dia.py AAAA-MM-DD [n=3]"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
PY = sys.executable


def hoja(carpeta):
    import cv2
    import numpy as np
    filas = []
    for f in sorted(carpeta.glob("short_*.mp4")):
        d = json.loads(f.with_suffix(".json").read_text(encoding="utf-8"))
        T = d.get("duracion", 20)
        cap = cv2.VideoCapture(str(f))
        fr = []
        for t in (0.3, T * 0.35, T * 0.6, T * 0.8, T - 0.5):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, im = cap.read()
            if ok:
                fr.append(cv2.resize(im, (300, 533)))
        if fr:
            filas.append(np.hstack(fr + [np.zeros_like(fr[0])] * (5 - len(fr))))
    if filas:
        cv2.imwrite(str(carpeta / "hoja.png"), np.vstack(filas))


def main(fecha, n=3):
    carpeta = RAIZ / "dia" / fecha / "shorts"
    import time
    for intento in range(2):                            # Gemini gratis se satura a ratos: un segundo intento a los 3 min
        r = subprocess.run([PY, "shorts_guion.py", fecha, str(n)], cwd=RAIZ)
        if r.returncode != 2:
            break
        if intento == 0:
            print("Gemini saturado: nuevo intento en 3 minutos", flush=True)
            time.sleep(180)
    if r.returncode != 0:
        print("SIN SHORTS: no hay frases válidas o Gemini no responde (no se gasta Claude en esto)")
        sys.exit(2)
    hechos = []
    for f in sorted(carpeta.glob("short_*.json"), key=lambda x: int(x.stem.split("_")[1])):
        k = f.stem.split("_")[1]
        r = subprocess.run([PY, "short.py", fecha, k], cwd=RAIZ, capture_output=True, text=True)
        if r.returncode != 0 or not (carpeta / f"short_{k}.mp4").exists():
            print(f"short_{k}: FALLO al renderizar\n{r.stderr[-1500:]}")
            f.unlink()
            continue
        print(r.stdout.strip().splitlines()[-1])
        hechos.append(k)
    if not hechos:
        sys.exit(1)
    hoja(carpeta)
    print(f"{len(hechos)} Shorts listos. Revisa {carpeta / 'hoja.png'} y sube con: python subir.py {fecha} shorts")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3)
