"""ILUSTRACIONES DE LAS VINETAS con IA (Cloudflare Workers AI, plan gratuito; decision del usuario del 1-nov-2026).

- Escenas genericas: FLUX.2 klein 4B a partir de una descripcion de la escena y una plantilla de estilo fija.
- Personas con nombre propio: se parte de su retrato real con licencia libre (el de creditos.json) y la IA lo redibuja
  en version comic, para que sea esa persona y no una cara inventada.
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
MODELO = "@cf/black-forest-labs/flux-2-klein-4b"
ESTILO = ("Panel of a modern European graphic novel: flat limited colour palette of cream, ochre, crimson red, "
          "dark navy blue and black; bold black ink shadows; clean confident ink outlines; cinematic composition. "
          "Absolutely no text, no letters, no numbers, no speech bubbles, no captions, no logos, no signs with writing.")
PERSONA = ("Redraw the person from image 0 as a character in this graphic novel panel, keeping his or her face, hair "
           "and features clearly recognizable and drawn with respect, with a calm, serious, professional expression. ")
SOBRIO = " Muted, desaturated colours, quiet and respectful mood, no dramatic effects."


def _claves():
    env = {}
    for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in l and not l.strip().startswith("#"):
            k, v = l.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]


def ilustra(escena, retrato: Path | None = None, sobrio=False, ancho=1024, alto=592, semilla=None):
    """escena: descripcion en ingles de lo que se ve (sin texto). retrato: foto real de la persona, si la hay.
    Devuelve una imagen RGB o lanza RuntimeError con el motivo (sin claves)."""
    prompt = (PERSONA if retrato else "") + escena.strip().rstrip(".") + ". " + ESTILO + (SOBRIO if sobrio else "")
    foto = b""
    if retrato:
        im = Image.open(retrato).convert("RGB")
        im.thumbnail((500, 500))                      # el modelo pide imagenes de menos de 512x512
        b = io.BytesIO()
        im.save(b, "JPEG", quality=92)
        foto = b.getvalue()
    clave = hashlib.sha1((MODELO + prompt + str(ancho) + str(alto) + str(semilla)).encode() + foto).hexdigest()[:20]
    f = CACHE / f"{clave}.jpg"
    if f.exists():
        return Image.open(f).convert("RGB")
    acc, tok = _claves()
    campos = {"prompt": (None, prompt), "width": (None, str(ancho)), "height": (None, str(alto))}
    if semilla is not None:
        campos["seed"] = (None, str(semilla))
    if foto:
        campos["input_image_0"] = ("retrato.jpg", foto, "image/jpeg")
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{MODELO}",
                      headers={"Authorization": f"Bearer {tok}"}, files=campos, timeout=180)
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
