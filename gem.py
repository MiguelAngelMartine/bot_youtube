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


def _claves():
    """Todas las claves de Gemini (7-nov-2026: la segunda es otro proyecto, con su propia cuota gratuita)."""
    kv = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines()
              if "=" in l and not l.startswith("#"))
    return [kv[n].strip().strip("\"'") for n in ("GEMINI_API_KEY", "GEMINI_IMAGEN_API_KEY") if kv.get(n, "").strip()]


def imagen(im, ancho=None):
    """Parte de imagen para Gemini a partir de una imagen PIL (opcionalmente reducida)."""
    from PIL import Image
    if ancho and im.width > ancho:
        im = im.resize((ancho, int(ancho * im.height / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", quality=88)
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}


def pide(partes, como_json=False, temperatura=0.2, pensar="low", limite_s=None, modelos=None):
    """partes: texto o lista de partes (textos y imágenes). Devuelve texto, dict/list si como_json, o None."""
    if isinstance(partes, str):
        partes = [{"text": partes}]
    partes = [{"text": p} if isinstance(p, str) else p for p in partes]
    conf = {"temperature": temperatura}
    if como_json:
        conf["responseMimeType"] = "application/json"
    claves = _claves()
    limite = time.time() + (limite_s or LIMITE_S)
    agotados = set()                                    # cuota diaria gastada: ese modelo con esa clave, fuera hasta mañana
    for modelo, k in [(m, c) for m in (modelos or MODELOS) for c in claves] * 3:   # vueltas por modelos y claves mientras quede tiempo
        if (modelo, k) in agotados:
            continue
        cfg = dict(conf, thinkingConfig={"thinkingLevel": pensar}) if modelo.startswith("gemini-3") else conf   # mas rapido
        for intento in range(3):
            if time.time() > limite:                    # saturado: antes que Claude, los modelos gratuitos (10-nov)
                return _pool(partes, como_json, temperatura)
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
            if r.status_code == 429 and "quota" in r.text.lower():
                agotados.add((modelo, k))               # sin cuota hoy: al siguiente modelo o clave, sin esperar
                break
            if r.status_code in (429, 500, 503):
                if intento:                             # saturado dos veces: prueba otro modelo y vuelve luego
                    break
                time.sleep(8)
                continue
            if r.status_code == 400 and "thinking" in r.text.lower():
                cfg = conf                              # este modelo no admite el ajuste: sin el
                continue
            break
    return _pool(partes, como_json, temperatura)


POOL = Path.home() / ".local" / "bin" / "freellmpool"


def _pool(partes, como_json, temperatura):
    """10-nov-2026 (petición del usuario: ahorrar créditos de Claude): si Gemini no responde, el trabajo de texto pasa
    a freellmpool (proveedores gratuitos con relevo automático, routing «quality»; instalado con `uv tool install`
    porque pide Python ≥ 3.11). Solo texto: con imágenes no (sus modelos gratuitos no las ven bien). Si tampoco
    responde, None y lo hace el agente de Claude, como antes. El material es público (noticias), sin secretos."""
    import subprocess
    if not POOL.exists() or any("text" not in p for p in partes):
        print("  (Gemini saturado: se pasa el trabajo a Claude)", file=sys.stderr)
        return None
    texto = "\n\n".join(p["text"] for p in partes)
    if como_json:
        texto += "\n\nResponde SOLO con JSON válido, sin texto antes ni después."
    try:
        r = subprocess.run([str(POOL), "ask", "--routing", "quality", "--max-tokens", "8000", "--timeout", "120",
                            "--temperature", str(temperatura)] + (["--json"] if como_json else []),
                           input=texto, capture_output=True, text=True, timeout=400)
        out = r.stdout.strip()
        if r.returncode == 0 and out:
            print("  (freellmpool: modelo gratuito)", file=sys.stderr)
            if not como_json:
                return out
            import re
            m = re.search(r"[\[{].*[\]}]", out, re.S)
            return json.loads(m.group(0)) if m else None
    except (subprocess.SubprocessError, ValueError, OSError):
        pass
    print("  (Gemini y freellmpool sin respuesta: se pasa el trabajo a Claude)", file=sys.stderr)
    return None
