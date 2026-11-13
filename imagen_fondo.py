"""FONDO FOTOGRÁFICO PARA LA MINIATURA TEMÁTICA (11-nov-2026, el usuario: «para ganar calidad en las miniaturas, que
las haga Gemini»). Genera la imagen de fondo de la miniatura temática, como la de la referencia del director (una mano
votando, una silueta con pancarta...): fotográfica, SIN personas reales reconocibles y SIN texto (el titular lo pone
miniatura.py, literal y sin faltas).
1) Gemini (gemini-2.5-flash-image) si la cuenta tiene facturación activada (la cuota gratuita de imágenes es 0);
2) si no, FLUX.1 schnell en Cloudflare (gratis), en estilo fotográfico.
Uso: from imagen_fondo import genera; genera(descripcion_en_ingles, destino)"""
from __future__ import annotations

import base64
from pathlib import Path

import requests

RAIZ = Path(__file__).parent
REGLAS = ("photorealistic editorial news photograph, dramatic cinematic lighting, shallow depth of field, high detail, "
          "16:9; no identifiable real people (only hands, silhouettes, people from behind or out of focus), "
          "no text, no letters, no logos, no flags with text. Scene: ")


def _openai(prompt, destino):
    import base64
    key = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text().splitlines()
               if "=" in l and not l.strip().startswith("#")).get("OPENAI_API_KEY", "").strip().strip('"')
    if not key:
        return False
    r = requests.post("https://api.openai.com/v1/images/generations", headers={"Authorization": f"Bearer {key}"}, timeout=180,
                      json={"model": "gpt-image-2", "prompt": prompt, "size": "1536x1024", "quality": "medium", "n": 1})
    if not r.ok:                                        # p. ej. safety_violations=[political]: lo coge FLUX
        print(f"  (OpenAI no genera: {r.json().get('error', {}).get('message', r.status_code)[:90]})")
        return False
    Path(destino).write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))
    return True


def _gemini(prompt, destino):
    import gem
    for k in gem._claves():
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent",
                          headers={"x-goog-api-key": k}, timeout=120,
                          json={"contents": [{"parts": [{"text": "Generate an image. " + prompt}]}],
                                "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}})
        if not r.ok:
            continue
        for c in r.json().get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                if "inlineData" in p:
                    Path(destino).write_bytes(base64.b64decode(p["inlineData"]["data"]))
                    return True
    return False


def _flux(prompt, destino):
    import ia_vinetas as IA
    acc, tok = IA._claves()
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{IA.ESCENAS}",
                      headers={"Authorization": f"Bearer {tok}"}, json={"prompt": prompt, "steps": 8}, timeout=180)
    img = ((r.json() if r.ok else {}).get("result") or {}).get("image")
    if img:
        Path(destino).write_bytes(base64.b64decode(img))
        return True
    return False


def solo_ia(descripcion, destino):
    """13-nov-2026: para la miniatura del vídeo largo, solo OpenAI (y Gemini de reserva), SIN FLUX: si no sale un fondo
    generado, el que llama usa una imagen real del tema. Devuelve "openai", "gemini" o None."""
    prompt = REGLAS + descripcion
    for motor, fn in (("openai", _openai), ("gemini", _gemini)):
        try:
            if fn(prompt, destino):
                return motor
        except Exception:
            pass
    return None


def genera(descripcion, destino):
    """Devuelve "gemini", "flux" o None."""
    prompt = REGLAS + descripcion
    for motor, fn in (("openai", _openai), ("gemini", _gemini)):   # 12-nov: OpenAI primero (lo no político), luego Gemini
        try:
            if fn(prompt, destino):
                return motor
        except Exception:
            pass
    try:
        if _flux(prompt, destino):
            return "flux"
    except Exception:
        pass
    return None
