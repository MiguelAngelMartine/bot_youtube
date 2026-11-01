"""ILUSTRACIONES DE LAS VINETAS con IA (Cloudflare Workers AI, plan gratuito; decision del usuario del 1-nov-2026).

- Escenas genericas: FLUX.1 schnell con la plantilla de estilo del canal (la de canal/estilo_vineta.jpg).
- Personas con nombre propio: FLUX.2 klein 4B con dos imagenes, su retrato real y la vineta de referencia (solo la tecnica de dibujo)
  con licencia libre (el de creditos.json), para que sea esa persona y no una cara inventada.
Reglas: el texto nunca lo dibuja la IA (lo pone vinetas.py en la franja de narracion); gesto sereno e igual para todos
(nada de caricaturas que ridiculicen ni de escenas que no ocurrieron); nunca victimas.
Las imagenes se guardan en cache/vinetas/: la misma escena no vuelve a gastar cuota.
Las claves estan en el .env del proyecto (CLOUDFLARE_ACCOUNT_ID y CLOUDFLARE_API_TOKEN) y nunca se imprimen."""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path

import requests
from PIL import Image

RAIZ = Path(__file__).parent
CACHE = RAIZ / "cache" / "vinetas"
REFERENCIA = RAIZ / "canal" / "estilo_vineta.jpg"     # vineta modelo del estilo del canal (elegida por el usuario)
ESCENAS = "@cf/black-forest-labs/flux-1-schnell"       # escenas: el estilo que eligio el usuario, rapido y barato
PERSONAS = "@cf/black-forest-labs/flux-2-klein-4b"     # personas: admite su foto real y la referencia de estilo
# sin la palabra "comic": con ella el modelo dibuja bocadillos con letras inventadas
ESTILO = "wordless graphic novel illustration, flat limited colors, thick black ink outlines, heavy black shadows, silent scene: "
PERSONA = ("Redraw the person from image 0 as a wordless graphic novel illustration, using only the drawing technique of "
           "image 1 (flat limited colors, thick black ink outlines, heavy solid black shadows, simple shapes). Do not copy "
           "anything else from image 1: no train, no objects, no background from it. Keep the likeness of image 0 exactly: "
           "same face shape, same hair, same beard, same age, and do not add glasses, hats or accessories that are not in "
           "image 0. Same pose and framing as image 0, calm serious expression, drawn with respect. {escena}"
           "Plain simple background. No text, no letters, no speech bubbles.")
SOBRIO = ", muted desaturated colors, quiet respectful mood"


def _claves():
    env = {}
    for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in l and not l.strip().startswith("#"):
            k, v = l.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]


def _jpg(ruta, lado=500):
    im = Image.open(ruta).convert("RGB")
    im.thumbnail((lado, lado))                       # el modelo de personas pide imagenes de menos de 512x512
    b = io.BytesIO()
    im.save(b, "JPEG", quality=92)
    return b.getvalue()


def ilustra(escena, retrato: Path | None = None, sobrio=False, intento=0):
    """escena: descripcion en ingles de lo que se ve (sin texto). retrato: foto real de la persona, si la hay.
    intento: para pedir otra version de la misma escena. Devuelve RGB o lanza RuntimeError (sin claves)."""
    if retrato:
        modelo = PERSONAS
        prompt = PERSONA.format(escena=(escena.strip().rstrip(".") + ". ") if escena else "") + (SOBRIO if sobrio else "")
        fotos = [_jpg(retrato), _jpg(REFERENCIA)]
    else:
        modelo = ESCENAS
        prompt = ESTILO + escena.strip().rstrip(".") + (SOBRIO if sobrio else "")
        fotos = []
    clave = hashlib.sha1((modelo + prompt + str(intento)).encode() + b"".join(fotos)).hexdigest()[:20]
    f = CACHE / f"{clave}.jpg"
    if f.exists():
        return Image.open(f).convert("RGB")
    acc, tok = _claves()
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{modelo}"
    cab = {"Authorization": f"Bearer {tok}"}
    if fotos:
        campos = {"prompt": (None, prompt), "width": (None, "1024"), "height": (None, "592"), "seed": (None, str(intento))}
        for k, b in enumerate(fotos):
            campos[f"input_image_{k}"] = (f"img{k}.jpg", b, "image/jpeg")
        r = requests.post(url, headers=cab, files=campos, timeout=180)
    else:
        r = requests.post(url, headers=cab, json={"prompt": prompt + (" " * intento), "steps": 6}, timeout=180)
    try:
        j = r.json()
    except ValueError:
        raise RuntimeError(f"respuesta no valida ({r.status_code})")
    img = (j.get("result") or {}).get("image")
    if not img:
        msg = "; ".join(str(e.get("message")) for e in j.get("errors", []))
        raise RuntimeError((msg or f"sin imagen ({r.status_code})").replace(acc, "<cuenta>").replace(tok, "<token>"))
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(base64.b64decode(img))
    return Image.open(f).convert("RGB")
