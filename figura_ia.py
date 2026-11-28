"""FIGURA DE UN PERSONAJE QUE FALTA, CON IA (28-nov-2026, el usuario: «para recrear al personaje puedes usar cualquier
foto [...] y puedes usar ChatGPT»). Cuando una noticia trae a alguien sin figura en Imagenes/ (o futbol/imagenes), se le
pide a OpenAI (gpt-image-2, /images/edits) una figura de cuerpo entero en el MISMO estilo que las del catálogo: se le pasan
sus fotos reales (cualquiera, para el parecido) y 2 figuras del catálogo como modelo de estilo (encuadre, luz, fondo negro).
Es un BORRADOR: el usuario lo aprueba antes de que entre en el catálogo (nunca va directo a un vídeo). Después,
recorta_imagenes.py le quita el fondo como a las demás. Gemini 2.5 Flash Image no sirve sin facturación (cuota 0) y
FLUX.2 klein de Cloudflare bloquea las personas reales («output flagged»).
Uso: python figura_ia.py "Nombre" destino_dir foto1 [foto2 ...] --estilo fig1.png fig2.png [--n 2] [--ropa "..."]"""
from __future__ import annotations

import argparse
import base64
import io
from pathlib import Path

import requests
from PIL import Image

import imagen_fondo

PROMPT = ("The first {nf} image(s) are photos of the same real man, {nombre}. The last {ne} images are STYLE references: "
          "full-body figures of other TV personalities on a plain black background. Create a full-body image of the man from "
          "the photos, standing, head to shoes, with exactly the same look, realism, framing, soft studio lighting and plain "
          "pure black background as the style references. Keep his face faithful to the photos (features, hair, beard, "
          "glasses, age). Outfit: {ropa}. Natural relaxed pose, one hand slightly raised as if speaking, confident expression. "
          "Do not copy the faces of the style references. No text, no logos.")


def _png(p, w=1024):
    im = Image.open(p)
    im.thumbnail((w, w))
    if im.mode == "RGBA":
        f = Image.new("RGB", im.size, (0, 0, 0))
        f.paste(im, mask=im.getchannel("A"))
        im = f
    b = io.BytesIO()
    im.convert("RGB").save(b, "PNG")
    return b.getvalue()


def genera(nombre, fotos, estilo, destino, n=2, ropa="dark smart-casual clothes"):
    key = imagen_fondo.clave_openai()
    if not key:
        raise SystemExit("sin clave de OpenAI")
    prompt = PROMPT.format(nf=len(fotos), ne=len(estilo), nombre=nombre, ropa=ropa)
    r = requests.post("https://api.openai.com/v1/images/edits", headers={"Authorization": f"Bearer {key}"}, timeout=500,
                      data={"model": "gpt-image-2", "prompt": prompt, "size": "1024x1536", "quality": "high", "n": str(n)},
                      files=[("image[]", (f"r{i}.png", _png(p), "image/png")) for i, p in enumerate([*fotos, *estilo])])
    if not r.ok:
        raise SystemExit(f"OpenAI no la genera: HTTP {r.status_code} {r.json().get('error', {}).get('message', '')[:200]}")
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    hechas = []
    for i, d in enumerate(r.json()["data"], 1):
        f = destino / f"{nombre.replace(' ', '')}_ia_{i}.png"
        f.write_bytes(base64.b64decode(d["b64_json"]))
        hechas.append(f)
        print(f"hecha: {f}")
    return hechas


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("nombre")
    a.add_argument("destino")
    a.add_argument("fotos", nargs="+")
    a.add_argument("--estilo", nargs=2, required=True)
    a.add_argument("--n", type=int, default=2)
    a.add_argument("--ropa", default="dark smart-casual clothes")
    x = a.parse_args()
    genera(x.nombre, x.fotos, x.estilo, x.destino, x.n, x.ropa)
