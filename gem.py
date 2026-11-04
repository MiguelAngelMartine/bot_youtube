"""Acceso común a Gemini (plan gratuito) para los trabajos externalizados de la redacción (decisión del usuario del
4-nov-2026: «externaliza todo lo que se pueda para ahorrar el máximo de tokens sin perder calidad»).
Prueba los modelos gratuitos por orden con reintentos; si ninguno responde devuelve None y quien llama usa a Claude.
La clave está en .env (GEMINI_API_KEY) y nunca se imprime."""
from __future__ import annotations

import base64
import io
import json
import sys
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).parent
MODELOS = ["gemini-3-flash-preview", "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]
LIMITE_S = 180                                         # espera maxima por trabajo antes de pasarlo a Claude


def _clave():
    kv = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines()
              if "=" in l and not l.startswith("#"))
    return kv["GEMINI_API_KEY"].strip().strip("\"'")


def imagen(im, ancho=None):
    """Parte de imagen para Gemini a partir de una imagen PIL (opcionalmente reducida)."""
    from PIL import Image
    if ancho and im.width > ancho:
        im = im.resize((ancho, int(ancho * im.height / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", quality=88)
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}


def pide(partes, como_json=False, temperatura=0.2):
    """partes: texto o lista de partes (textos y imágenes). Devuelve texto, dict/list si como_json, o None."""
    if isinstance(partes, str):
        partes = [{"text": partes}]
    partes = [{"text": p} if isinstance(p, str) else p for p in partes]
    conf = {"temperature": temperatura}
    if como_json:
        conf["responseMimeType"] = "application/json"
    k = _clave()
    limite = time.time() + LIMITE_S
    for modelo in MODELOS:
        cfg = dict(conf, thinkingConfig={"thinkingLevel": "low"}) if modelo.startswith("gemini-3") else conf   # mas rapido
        for intento in range(3):
            if time.time() > limite:                    # saturado: mejor que lo haga Claude que esperar
                print("  (Gemini saturado: se pasa el trabajo a Claude)", file=sys.stderr)
                return None
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
                                  headers={"x-goog-api-key": k}, timeout=max(20, limite - time.time()),
                                  json={"contents": [{"parts": partes}], "generationConfig": cfg})
            except requests.RequestException:
                time.sleep(10)
                continue
            if r.ok:
                txt = "".join(p.get("text", "") for p in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []))
                if txt.strip():
                    print(f"  (Gemini: {modelo})", file=sys.stderr)
                    if not como_json:
                        return txt.strip()
                    try:
                        return json.loads(txt)
                    except ValueError:
                        break                           # JSON roto: prueba otro modelo
            if r.status_code in (429, 500, 503):
                time.sleep(10 * (intento + 1))
                continue
            if r.status_code == 400 and "thinking" in r.text.lower():
                cfg = conf                              # este modelo no admite el ajuste: sin el
                continue
            break
    return None
