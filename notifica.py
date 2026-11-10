"""Aviso al DIRECTOR por Telegram cuando hay un video listo para revisar: el parte del dia resumido, la miniatura y la
copia ligera del episodio; o un video suelto (un corto) con --video.
Usa el canal KRAKEN del proyecto anterior (TELEGRAM_KRAKEN_TOKEN y TELEGRAM_KRAKEN_CHAT_ID), elegido por el usuario el
1-nov-2026. Lo busca en el .env de este proyecto o en el del proyecto Kraken (en el PC, ../kraken-futures-bot; en el
servidor, ../kraken_bot/allweather_bot). Nunca imprime las claves.
Uso: python notifica.py AAAA-MM-DD [--error "texto"] [--video ruta.mp4 ["texto"]]"""
from __future__ import annotations
import json

import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).parent
ENVS = (RAIZ / ".env", RAIZ.parent / "kraken-futures-bot" / ".env", RAIZ.parent / "kraken_bot" / "allweather_bot" / ".env",
        RAIZ.parent / "kraken_bot" / ".env")
MAX_TG = 49 * 1024 * 1024                  # los bots de Telegram no pueden mandar ficheros de mas de 50 MB


def credenciales():
    for env in ENVS:
        if env.exists():
            kv = dict(l.split("=", 1) for l in env.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))
            tok = kv.get("TELEGRAM_KRAKEN_TOKEN", "").strip().strip('"')
            chat = kv.get("TELEGRAM_KRAKEN_CHAT_ID", "").strip().strip('"')
            if tok and chat:
                return tok, chat
    raise SystemExit("sin credenciales de Telegram")


def envia(api, metodo, **kw):
    """Llama a la API y comprueba que Telegram lo acepta; si no, dice por que sin mostrar la URL (lleva la clave)."""
    r = requests.post(f"{api}/{metodo}", **kw)
    if not r.ok:
        raise SystemExit(f"Telegram rechazo {metodo}: {r.status_code} {r.json().get('description', '') if r.content else ''}")


def aviso_subida(info):
    """Aviso corto en cuanto hay un video subido a YouTube esperando a que el director lo publique (norma del 1-nov)."""
    tok, chat = credenciales()
    api = f"https://api.telegram.org/bot{tok}"
    txt = (f"▶️ El Hoyformativo: vídeo subido a YouTube como PRIVADO, listo para que lo revises y lo publiques.\n"
           f"{info['titulo']}\n{info['studio']}")
    if info.get("sustituye_a"):
        txt += "\n(Sustituye a la versión anterior de ese día, que se ha borrado.)"
    if info.get("avisos"):
        txt += "\nAvisos: " + "; ".join(info["avisos"])
    envia(api, "sendMessage", data={"chat_id": chat, "text": txt[:4000]}, timeout=30)


def manda_video(api, chat, v, texto):
    if v.stat().st_size < MAX_TG:
        with open(v, "rb") as fh:
            envia(api, "sendVideo", data={"chat_id": chat, "caption": texto, "supports_streaming": "true"},
                  files={"video": fh}, timeout=600)
    else:
        envia(api, "sendMessage", timeout=30, data={"chat_id": chat, "text":
              f"{texto}: ocupa {v.stat().st_size / 2**20:.0f} MB, demasiado para Telegram. Está en {v}"})


def main(dia_txt, error=None, video=None, texto_video=None):
    tok, chat = credenciales()
    api = f"https://api.telegram.org/bot{tok}"
    dia = RAIZ / "dia" / dia_txt
    if error:
        envia(api, "sendMessage", data={"chat_id": chat, "text": f"⚠️ El Hoyformativo {dia_txt}: {error}"}, timeout=30)
        print("aviso de error enviado")
        return
    if video:
        v = Path(video) if Path(video).is_absolute() else RAIZ / video
        manda_video(api, chat, v, f"🗳️ El Hoyformativo · {dia_txt}\nListo para revisar: {texto_video or v.name}")
        print("aviso de video enviado")
        return
    parte = (dia / "parte_del_dia.md").read_text(encoding="utf-8") if (dia / "parte_del_dia.md").exists() else "(sin parte)"
    titulo = ""
    pub = dia / "publicacion.md"
    if pub.exists():
        for l in pub.read_text(encoding="utf-8").splitlines():
            if l.strip() and not l.startswith("#"):
                titulo = l.strip("*# ").strip()
                break
    yt = json.loads((dia / "youtube.json").read_text(encoding="utf-8")) if (dia / "youtube.json").exists() else None
    enlace = (f"\n\n▶️ Subido a YouTube como PRIVADO. Revísalo y publícalo tú:\n{yt['studio']}"
              + (f"\nAvisos: {'; '.join(yt['avisos'])}" if yt.get("avisos") else "")) if yt else ""
    texto = f"🗳️ El Hoyformativo · {dia_txt}\nListo para revisar.\n{titulo}{enlace}\n\n{parte[-2800:]}"
    envia(api, "sendMessage", data={"chat_id": chat, "text": texto[:4000]}, timeout=30)
    if (dia / "miniatura.png").exists():
        with open(dia / "miniatura.png", "rb") as fh:
            envia(api, "sendPhoto", data={"chat_id": chat, "caption": "Miniatura"}, files={"photo": fh}, timeout=60)
    v = dia / "episodio_720p.mp4"
    if v.exists():
        manda_video(api, chat, v, "Episodio (copia 720p)")
    for c in sorted(dia.glob("corto_s*.mp4")):
        manda_video(api, chat, c, f"Corto vertical ({c.stem})")
    print("aviso enviado")


def aviso_shorts(dia_txt, hechos):
    """Shorts subidos como privados (5-nov-2026): enlaces de Studio y, de cada uno, el vídeo y su portada."""
    from pathlib import Path
    tok, chat = credenciales()
    api = f"https://api.telegram.org/bot{tok}"
    txt = [f"📱 El Hoyformativo · {dia_txt}: {len(hechos)} Shorts subidos a YouTube como PRIVADOS, para revisar y publicar:"]
    txt += [f"{k}. {h['titulo']}\n{h['studio']}" + (f"\n({h['aviso']})" if h.get("aviso") else "")
            for k, h in enumerate(hechos, 1)]
    import json as _j                                  # 10-nov: el largo del día, para el «Vídeo relacionado»
    yl = Path(__file__).parent / "dia" / dia_txt[:10] / "youtube.json"
    if yl.exists():
        largo = _j.loads(yl.read_text(encoding="utf-8"))
        txt.append(f"🔗 Al publicar cada Short, en «Vídeo relacionado» elige el vídeo largo del día (publícalo antes):\n"
                   f"«{largo.get('titulo', '')}»\n{largo.get('url', '')}\n"
                   f"El comentario del canal con el enlace se pone solo cuando el Short esté público.")
    envia(api, "sendMessage", data={"chat_id": chat, "text": "\n\n".join(txt)[:4000]}, timeout=30)
    for k, h in enumerate(hechos, 1):
        portada = Path(h["portada"])
        if portada.exists():
            with open(portada, "rb") as fh:
                envia(api, "sendPhoto", data={"chat_id": chat, "caption": f"Short {k} · portada"}, files={"photo": fh},
                      timeout=60)
        v = portada.with_name(portada.name.replace("_portada.png", ".mp4"))
        if v.exists():
            manda_video(api, chat, v, f"Short {k}: {h['titulo']}")


def aviso(dia_txt, texto):
    """Mensaje corto informativo (por ejemplo, que empieza la jornada)."""
    tok, chat = credenciales()
    envia(f"https://api.telegram.org/bot{tok}", "sendMessage", data={"chat_id": chat, "text": f"🎬 El Hoyformativo · {dia_txt}: {texto}"},
          timeout=30)
    print("aviso enviado")


if __name__ == "__main__":
    a = sys.argv
    if "--aviso" in a:
        aviso(a[1], a[a.index("--aviso") + 1])
        sys.exit()
    err = a[a.index("--error") + 1] if "--error" in a else None
    vid = a[a.index("--video") + 1] if "--video" in a else None
    txt = a[a.index("--video") + 2] if vid and len(a) > a.index("--video") + 2 and not a[a.index("--video") + 2].startswith("--") else None
    main(a[1], err, vid, txt)
