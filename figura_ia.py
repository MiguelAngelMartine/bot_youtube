"""FIGURA DE UN PERSONAJE QUE FALTA, CON IA (28-nov-2026). El usuario: «para recrear al personaje puedes usar cualquier
foto, no hace falta que sea libre. Y puedes usar ChatGPT»; y tras la prueba con Alfredo Duro: «perfecto. Cuando falte una
imagen haz lo mismo y la guardas».

Cuando una cita es de alguien sin figura en el catálogo (Imagenes/Políticos o futbol/imagenes/Personajes):
  1) busca fotos reales de la persona (Bing Imágenes; cualquier foto vale, solo sirve para el parecido) y se queda con las
     que traen el apellido en el título y UNA cara clara y grande (OpenCV);
  2) pide a OpenAI (gpt-image-2, /images/edits) una figura de cuerpo entero con esas fotos + 2 figuras del catálogo como
     modelo de estilo (encuadre, luz, fondo negro);
  3) le quita el fondo (rembg, isnet-general-use) y la guarda en <catálogo>/IA/NombreApellido.png (el original con fondo en
     <catálogo>/IA/_originales/), y la manda por Telegram para que el usuario la vea (si no le gusta, se borra y ya).
Solo con nombre y apellido (con un apellido suelto se podría dibujar a otra persona). Lo que falla se apunta en
archivo/figuras_ia.json y no se reintenta el mismo día. EH_SIN_FIGURA_IA=1 lo desactiva.
Gemini 2.5 Flash Image no sirve sin facturación (cuota 0) y FLUX.2 klein de Cloudflare bloquea a personas reales.
Uso: python figura_ia.py "Nombre Apellido" [catálogo]              (catálogo: Imagenes/Políticos por defecto)
     python figura_ia.py "Nombre" destino_dir foto1 [foto2] --estilo fig1.png fig2.png   (a mano, con fotos dadas)"""
from __future__ import annotations

import base64
import html
import io
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image

RAIZ = Path(__file__).parent
REGISTRO = RAIZ / "archivo" / "figuras_ia.json"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}
# modelos de estilo por catálogo (un hombre y una mujer si se puede); si no existen, las dos figuras más grandes
ESTILO = {"Políticos": ["Nuevas/a/PedroSanchez.png", "Nuevas/a/recortadas/IsabelDiazAyuso.png"],
          "Personajes": ["JosepPedrerol.png", "JoseAlvarez.png"]}
PROMPT = ("The first {nf} image(s) are photos of the same real person, {nombre}. The last {ne} images are STYLE references: "
          "full-body figures of other public figures on a plain black background. Create a full-body image of the person from "
          "the photos, standing, head to shoes, with exactly the same look, realism, framing, soft studio lighting and plain "
          "pure black background as the style references. Keep the face faithful to the photos (features, hair, beard, "
          "glasses, age). Outfit: {ropa}. Natural relaxed pose, one hand slightly raised as if speaking, confident expression. "
          "Do not copy the faces of the style references. No text, no logos.")
ROPA = "the kind of clothes this person usually wears in public, as in the photos, without logos"


def _n(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def _png(im_o_ruta, w=1024):
    im = Image.open(im_o_ruta) if not isinstance(im_o_ruta, Image.Image) else im_o_ruta
    im.thumbnail((w, w))
    if im.mode == "RGBA":
        f = Image.new("RGB", im.size, (0, 0, 0))
        f.paste(im, mask=im.getchannel("A"))
        im = f
    b = io.BytesIO()
    im.convert("RGB").save(b, "PNG")
    return b.getvalue()


def _cara(im):
    """Tamaño relativo de la cara si hay UNA sola cara clara; None si no hay o hay varias."""
    import cv2
    import numpy as np
    from miniatura import YUNET, YUNET_URL               # YuNet (OpenCV 5 ya no trae los Haar)
    if not YUNET.exists():
        YUNET.parent.mkdir(parents=True, exist_ok=True)
        YUNET.write_bytes(requests.get(YUNET_URL, timeout=60).content)
    im = im.convert("RGB")
    im.thumbnail((1024, 1024))
    bgr = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (bgr.shape[1], bgr.shape[0]), 0.8)
    _, caras = det.detect(bgr)
    if caras is None:
        return None
    grandes = [c for c in caras if c[2] / bgr.shape[1] >= 0.04]   # las caras diminutas del fondo no cuentan
    if len(grandes) != 1:
        return None
    return grandes[0][2] / bgr.shape[1]


def busca_fotos(nombre, n=2, contexto=""):
    """Fotos reales de la persona (PIL), las de cara más grande primero."""
    ape = _n(nombre.split()[-1])
    vistos, buenas = set(), []
    for q in (nombre, f"{nombre} {contexto}".strip()):
        try:
            r = requests.get("https://www.bing.com/images/search", params={"q": q}, headers=UA, timeout=25)
        except requests.RequestException:
            continue
        t = html.unescape(r.text)
        for url, tit in zip(re.findall(r'"murl":"(.*?)"', t), re.findall(r'"t":"(.*?)"', t)):
            if url in vistos or ape not in _n(tit):
                continue
            vistos.add(url)
            try:
                d = requests.get(url, headers=UA, timeout=20)
                im = Image.open(io.BytesIO(d.content)).convert("RGB")
            except Exception:
                continue
            if min(im.size) < 300:
                continue
            c = _cara(im)
            if c and c >= 0.08:
                buenas.append((c, url, im))
            if len(buenas) >= n + 3 or len(vistos) >= 25:
                break
        if len(buenas) >= n:
            break
    buenas.sort(key=lambda x: -x[0])
    return [(u, im) for _, u, im in buenas[:n]]


def _estilo(cat):
    rutas = [cat / r for r in ESTILO.get(cat.name, []) if (cat / r).exists()]
    if len(rutas) < 2:
        todas = [p for p in cat.rglob("*.png") if "IA" not in p.relative_to(cat).parts]
        todas = [p for p in todas if Image.open(p).mode == "RGBA"]
        rutas = sorted(todas, key=lambda p: -Image.open(p).size[1])[:2]
    return rutas


def genera(nombre, fotos, estilo, n=1, ropa=ROPA):
    """Llama a gpt-image-2 con las fotos (rutas o PIL) y los modelos de estilo. Devuelve imágenes PIL."""
    import imagen_fondo
    key = imagen_fondo.clave_openai()
    if not key:
        raise RuntimeError("sin clave de OpenAI")
    prompt = PROMPT.format(nf=len(fotos), ne=len(estilo), nombre=nombre, ropa=ropa)
    r = requests.post("https://api.openai.com/v1/images/edits", headers={"Authorization": f"Bearer {key}"}, timeout=500,
                      data={"model": "gpt-image-2", "prompt": prompt, "size": "1024x1536", "quality": "high", "n": str(n)},
                      files=[("image[]", (f"r{i}.png", _png(p), "image/png")) for i, p in enumerate([*fotos, *estilo])])
    if not r.ok:
        raise RuntimeError(f"OpenAI no la genera: HTTP {r.status_code} "
                           f"{(r.json().get('error') or {}).get('message', '')[:160] if r.content else ''}")
    return [Image.open(io.BytesIO(base64.b64decode(d["b64_json"]))) for d in r.json()["data"]]


def _registro():
    try:
        return json.loads(REGISTRO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def crea(nombre, cat=None, fecha=None, contexto=""):
    """Crea, recorta, guarda y avisa. Devuelve la ruta de la figura o None (y por qué, en el registro)."""
    if os.environ.get("EH_SIN_FIGURA_IA") == "1":
        return None
    cat = Path(cat or RAIZ / "Imagenes" / "Políticos")
    nombre = " ".join(nombre.split())
    if len(nombre.split()) < 2:
        return None                                     # apellido suelto: podría ser otra persona
    reg = _registro()
    hoy = time.strftime("%Y-%m-%d")
    previo = reg.get(nombre, {})
    if previo.get("estado") != "hecha" and previo.get("fecha") == hoy:
        return None                                     # ya falló hoy
    base = re.sub(r"[^\wÁÉÍÓÚÑáéíóúñü]", "", nombre.title().replace(" ", ""))
    destino = cat / "IA" / f"{base}.png"
    if destino.exists():
        return destino
    entrada = {"fecha": hoy, "catalogo": str(cat.relative_to(RAIZ)) if cat.is_relative_to(RAIZ) else str(cat)}
    try:
        fotos = busca_fotos(nombre, 2, contexto)
        entrada["fotos"] = [u for u, _ in fotos]
        if not fotos:
            raise RuntimeError("no encuentro fotos con su cara clara")
        im = genera(nombre, [f for _, f in fotos], _estilo(cat))[0]
        (cat / "IA" / "_originales").mkdir(parents=True, exist_ok=True)
        im.save(cat / "IA" / "_originales" / f"{base}.png")
        from rembg import new_session, remove
        remove(im.convert("RGB"), session=new_session("isnet-general-use")).save(destino)
        entrada.update(estado="hecha", figura=str(destino.relative_to(RAIZ)) if destino.is_relative_to(RAIZ) else str(destino))
        print(f"figura IA: {nombre} -> {destino}")
    except Exception as e:
        entrada.update(estado="fallida", motivo=str(e)[:200])
        print(f"figura IA de {nombre}: {e}")
        destino = None
    reg[nombre] = entrada
    REGISTRO.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        import notifica
        if destino:
            notifica.manda_foto(fecha or hoy, cat / "IA" / "_originales" / f"{base}.png",
                                f"🖼️ Faltaba la imagen de {nombre}: la he hecho con ChatGPT a partir de sus fotos y la he "
                                f"guardado en {destino.relative_to(RAIZ) if destino.is_relative_to(RAIZ) else destino}. "
                                f"Si no se parece, dímelo y la quito.")
        else:
            notifica.aviso(fecha or hoy, f"🖼️ Falta la imagen de {nombre} y no he podido hacerla con IA "
                                         f"({entrada.get('motivo', '')[:120]}). Su cita la lee el presentador.")
    except (SystemExit, Exception) as e:
        print(f"(Telegram: {e})")
    return destino


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--estilo" in a:                                 # a mano: nombre destino fotos... --estilo f1 f2
        i = a.index("--estilo")
        nombre, dest, fotos, est = a[0], Path(a[1]), a[2:i], a[i + 1:i + 3]
        dest.mkdir(parents=True, exist_ok=True)
        for k, im in enumerate(genera(nombre, fotos, est, n=2), 1):
            f = dest / f"{nombre.replace(' ', '')}_ia_{k}.png"
            im.save(f)
            print(f"hecha: {f}")
    else:
        print(crea(a[0], a[1] if len(a) > 1 else None))
