"""VIÑETAS ANIMADAS CON IA (11-nov-2026, pedido para el Short de Jordi Wild): convierte una viñeta en un clip de 4 s con
LTX-Video (espacio gratuito de Hugging Face; el de Wan 2.1 falla o no tiene cuota). Si no responde, None: la viñeta
sale con su movimiento de siempre. Uso: from animar_ia import clip; clip(ruta_jpg, "movimiento en inglés")"""
from __future__ import annotations

import shutil
from pathlib import Path

RAIZ = Path(__file__).parent


def clip(ruta, movimiento="camera slowly pushes in, subtle natural motion"):
    ruta = Path(ruta)
    dest = ruta.with_suffix(".mp4")
    if dest.exists():
        return dest
    try:
        from gradio_client import Client, handle_file
        env = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
        c = Client("Lightricks/ltx-video-distilled", token=env["HF_TOKEN"].strip().strip('"'), verbose=False)
        r = c.predict("comic illustration animation, " + movimiento + ", smooth natural motion",
                      "static, text, letters, deformed faces, flicker", handle_file(str(ruta)), None, 512, 896,
                      "image-to-video", 4, 9, 42, False, 1, False, api_name="/image_to_video")
        v = r[0]["video"] if isinstance(r[0], dict) else r[0]
        shutil.copy(v, dest)
        return dest
    except Exception as e:
        print(f"  (sin clip animado para {ruta.name}: {type(e).__name__})")
        return None
