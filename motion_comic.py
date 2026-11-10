"""VIÑETAS ANIMADAS ESTILO «MOTION COMIC» (decisión del usuario del 10-nov-2026, opción 3: base para todas las viñetas;
los clips de vídeo con IA, si convencen, solo para escenas clave). Cada viñeta se anima con una cámara 2,5D: un mapa
de profundidad (Depth Anything V2 small, ONNX en CPU, ~3 s por imagen, guardado en cache/profundidad/) hace que lo
cercano se acerque y se desplace más que el fondo, como una cámara que entra en la escena. Sin recortar la figura (no
quedan huecos ni borrones) y sin deformar caras. Encima, polvo en el aire y líneas de acción al entrar (no en sobrio).
Sin onomatopeyas ni textos inventados: los textos son los del guion."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).parent
CACHE = RAIZ / "cache" / "profundidad"
MODELO = RAIZ / "modelos" / "depth" / "onnx" / "model.onnx"
_ses = None
_mem = {}


def _sesion():
    global _ses
    if _ses is None:
        import onnxruntime as ort
        _ses = ort.InferenceSession(str(MODELO), providers=["CPUExecutionProvider"])
    return _ses


def profundidad(ruta):
    """Mapa de profundidad 0..1 (1 = cerca) a 512x288 aprox., cacheado en disco por el contenido del fichero."""
    import cv2
    ruta = Path(ruta)
    clave = hashlib.sha1(ruta.read_bytes()).hexdigest()[:20]
    if clave in _mem:
        return _mem[clave]
    f = CACHE / f"{clave}.npy"
    if f.exists():
        d = np.load(f)
    else:
        if not MODELO.exists():
            return None
        rgb = cv2.cvtColor(cv2.imread(str(ruta)), cv2.COLOR_BGR2RGB)
        x = cv2.resize(rgb, (518, 518)).astype(np.float32) / 255
        x = ((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype(np.float32)
        s = _sesion()
        d = s.run(None, {s.get_inputs()[0].name: x})[0][0]
        d = (d - d.min()) / (d.max() - d.min() + 1e-6)
        h, w = rgb.shape[:2]
        d = cv2.resize(d, (512, max(1, int(512 * h / w)))).astype(np.float32)
        d = cv2.GaussianBlur(d, (0, 0), 2)
        CACHE.mkdir(parents=True, exist_ok=True)
        np.save(f, d)
    _mem[clave] = d
    return d


def prepara(rutas):
    """Calcula (y guarda) la profundidad de varias imágenes antes del montaje en paralelo."""
    for r in rutas:
        try:
            profundidad(r)
        except Exception as e:
            print(f"  (sin profundidad para {Path(r).name}: {type(e).__name__})")


_rejillas = {}


def anima(base, ruta, tl, w, h, semilla=0, dur=8.0):
    """base: PIL RGB algo mayor que (w, h) (≈ +12 %). Devuelve PIL RGB (w, h) con la cámara 2,5D en el instante tl."""
    import cv2
    from PIL import Image
    d = profundidad(ruta) if ruta else None
    q = min(tl, dur) / dur
    e = q * q * (3 - 2 * q)
    arr = np.asarray(base)
    bh, bw = arr.shape[:2]
    if (w, h) not in _rejillas:
        _rejillas[(w, h)] = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    X, Y = _rejillas[(w, h)]
    dn = cv2.resize(d, (w, h)) if d is not None else np.full((h, w), 0.5, np.float32)
    lado = 1 if semilla % 2 == 0 else -1
    z = (bw / w) / (1.0 + 0.08 * e)                     # se acerca despacio
    z_cerca = 1 + 0.06 * e * (dn - 0.4)                  # lo cercano, más deprisa (profundidad)
    cx, cy = w / 2, h / 2
    mx = (bw / 2) + (X - cx) * z / z_cerca + lado * 30 * e * (dn - 0.35)
    my = (bh / 2) + (Y - cy) * z / z_cerca - 18 * e * (dn - 0.35)
    out = cv2.remap(arr, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return Image.fromarray(out)


def ambiente(im, tl, t_abs, semilla=0, sobrio=False):
    """Polvo flotando y, al entrar, líneas de acción que se abren desde el centro (no en sobrio). im: PIL RGBA."""
    from PIL import Image, ImageDraw, ImageFilter
    if sobrio:
        return im
    w, h = im.size
    rng = np.random.default_rng(semilla)
    capa = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(capa)
    for _ in range(45):
        x, y, r, v = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(1.5, 3.5), rng.uniform(12, 35)
        xx, yy = (x + 18 * math.sin(t_abs * 0.7 + y)) % w, (y - v * t_abs) % h
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(255, 240, 210, 90))
    a = max(0.0, 1 - tl / 0.45)
    if a > 0:                                           # líneas de acción al entrar la viñeta
        cx, cy = w / 2, h * 0.45
        for k in range(48):
            ang = k / 48 * 2 * math.pi
            r0, r1 = 0.24 * w + 50 * math.sin(k * 3.1), 1.2 * w
            d.polygon([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)),
                       (cx + r1 * math.cos(ang - 0.01), cy + r1 * math.sin(ang - 0.01)),
                       (cx + r1 * math.cos(ang + 0.01), cy + r1 * math.sin(ang + 0.01))], fill=(12, 12, 16, int(170 * a)))
    im.alpha_composite(capa.filter(ImageFilter.GaussianBlur(0.8)))
    return im
