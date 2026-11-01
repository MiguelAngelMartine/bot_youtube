"""Aviso al DIRECTOR por Telegram: el parte del dia resumido, la miniatura y la copia ligera del video.
Lee TELEGRAM_TOKEN y TELEGRAM_CHAT_ID del .env de este proyecto o, si no existe, del de kraken-futures-bot. Nunca los imprime.
Uso: python notifica.py AAAA-MM-DD [--error "texto"]"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).parent


def credenciales():
    for env in (RAIZ / ".env", RAIZ.parent / "kraken-futures-bot" / ".env"):
        if env.exists():
            kv = dict(l.split("=", 1) for l in env.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
            tok, chat = kv.get("TELEGRAM_TOKEN", "").strip().strip('"'), kv.get("TELEGRAM_CHAT_ID", "").strip().strip('"')
            if tok and chat:
                return tok, chat
    raise SystemExit("sin credenciales de Telegram")


def main(dia_txt, error=None):
    tok, chat = credenciales()
    api = f"https://api.telegram.org/bot{tok}"
    dia = RAIZ / "dia" / dia_txt
    if error:
        requests.post(f"{api}/sendMessage", data={"chat_id": chat, "text": f"⚠️ Política en Claro {dia_txt}: {error}"}, timeout=30)
        print("aviso de error enviado")
        return
    parte = (dia / "parte_del_dia.md").read_text(encoding="utf-8") if (dia / "parte_del_dia.md").exists() else "(sin parte)"
    titulo = ""
    pub = dia / "publicacion.md"
    if pub.exists():
        for l in pub.read_text(encoding="utf-8").splitlines():
            if l.strip() and not l.startswith("#"):
                titulo = l.strip("*# ").strip()
                break
    texto = f"🗳️ Política en Claro · {dia_txt}\nListo para revisar.\n{titulo}\n\n{parte[-3000:]}"
    requests.post(f"{api}/sendMessage", data={"chat_id": chat, "text": texto[:4000]}, timeout=30)
    if (dia / "miniatura.png").exists():
        with open(dia / "miniatura.png", "rb") as fh:
            requests.post(f"{api}/sendPhoto", data={"chat_id": chat, "caption": "Miniatura"}, files={"photo": fh}, timeout=60)
    v = dia / "episodio_720p.mp4"
    if v.exists() and v.stat().st_size < 49 * 1024 * 1024:
        with open(v, "rb") as fh:
            requests.post(f"{api}/sendVideo", data={"chat_id": chat, "caption": "Episodio (copia 720p)"}, files={"video": fh}, timeout=600)
    print("aviso enviado")


if __name__ == "__main__":
    err = sys.argv[sys.argv.index("--error") + 1] if "--error" in sys.argv else None
    main(sys.argv[1], err)
