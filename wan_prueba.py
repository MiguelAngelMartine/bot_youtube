"""PRUEBA DE VÍDEO CON IA (Wan 2.1, Apache 2.0) desde una viñeta, con la cuota gratuita de Hugging Face (ZeroGPU).
Genera un clip de ~4 s por imagen y los manda por Telegram, con el tiempo que ha tardado cada uno (para calcular cuántos
clips daría Hugging Face PRO). Uso: python wan_prueba.py imagen1.jpg "movimiento en inglés" [imagen2.jpg "..." ...]"""
import shutil
import sys
import time
from pathlib import Path

from gradio_client import Client, handle_file

import notifica as N

RAIZ = Path(__file__).parent
env = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
c = Client("multimodalart/wan2-1-fast", token=env["HF_TOKEN"].strip().strip('"'), verbose=False)
tok, chat = N.credenciales()
api = f"https://api.telegram.org/bot{tok}"
args = sys.argv[1:]
for img, mov in zip(args[::2], args[1::2]):
    t = time.time()
    try:
        r = c.predict(handle_file(img), "ligne claire comic animation, " + mov + ", smooth natural motion, camera slowly moves",
                      480, 832, "static, deformed faces, extra limbs, text, letters, blurry, flicker", 4, 1, 4, 42, False,
                      api_name="/generate_video")
        v = r[0]["video"] if isinstance(r[0], dict) else r[0]
        out = RAIZ / "cache" / f"wan_{Path(img).stem}.mp4"
        shutil.copy(v, out)
        N.manda_video(api, chat, out, f"Prueba Wan 2.1 · {Path(img).stem} · {time.time() - t:.0f} s en generarse")
        print("ok", img, round(time.time() - t))
    except Exception as e:
        print("fallo", img, type(e).__name__, str(e)[:200])
        N.aviso("prueba", f"la prueba de Wan falló: {str(e)[:200]}")
