"""SUBIDA A YOUTUBE como PRIVADO (decision del usuario del 1-nov-2026: la oficina sube, el usuario revisa y publica).

Uso:
  python subir.py autorizar            una sola vez: espera en el puerto 8765 la autorizacion del navegador
                                       (desde el PC: ssh -L 8765:localhost:8765 miguel@192.168.1.129 y abrir el enlace)
  python subir.py AAAA-MM-DD [--publico-no]   sube dia/<fecha>/episodio.mp4 con los datos de publicacion.md,
                                       la miniatura y los subtitulos; escribe dia/<fecha>/youtube.json con el enlace

Lo que pone: titulo, descripcion (con capitulos, fuentes, creditos y hashtags), etiquetas, categoria Noticias y
politica, idioma espanol, «no es para ninos», PRIVADO. Lo que NO se puede por la API: pantalla final y tarjetas.
Nunca publica: el estado es siempre privado. De cada dia queda solo la ultima version: al subir otra, se borra la
anterior si sigue privada (si ya es publica, no se toca y no se sube nada). Las claves (client_secret.json, token_youtube.json) no van a git."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
SECRETO = RAIZ / "client_secret.json"
TOKEN = RAIZ / "token_youtube.json"
PERMISOS = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
PUERTO = 8765


def credenciales():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    if not TOKEN.exists():
        raise SystemExit("Falta la autorizacion: ejecuta `python subir.py autorizar` una vez.")
    c = Credentials.from_authorized_user_file(str(TOKEN), PERMISOS)
    if not c.valid:
        c.refresh(Request())
        TOKEN.write_text(c.to_json(), encoding="utf-8")
        TOKEN.chmod(0o600)
    return c


def autorizar():
    from google_auth_oauthlib.flow import InstalledAppFlow
    flujo = InstalledAppFlow.from_client_secrets_file(str(SECRETO), PERMISOS)
    c = flujo.run_local_server(host="localhost", port=PUERTO, open_browser=False, bind_addr="127.0.0.1",
                               authorization_prompt_message="ENLACE: {url}",
                               success_message="Autorizado. Ya puedes cerrar esta pestana.")
    TOKEN.write_text(c.to_json(), encoding="utf-8")
    TOKEN.chmod(0o600)
    print("Autorizacion guardada en token_youtube.json")


def bloque(md, seccion):
    """El primer bloque ``` que sigue al encabezado '## <seccion>'."""
    m = re.search(r"^##\s*" + re.escape(seccion) + r".*?^```[^\n]*\n(.*?)^```", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def borra_anterior(yt, dia):
    """Regla del usuario (1-nov-2026): de cada dia se queda solo la ultima version. Si ya se subio una antes y sigue
    PRIVADA, se borra. Si el usuario ya la hizo publica u oculta, no se toca nunca."""
    f = dia / "youtube.json"
    if not f.exists():
        return None
    vid = json.loads(f.read_text(encoding="utf-8")).get("id")
    if not vid:
        return None
    r = yt.videos().list(part="status", id=vid).execute().get("items", [])
    if not r:
        return None                                       # ya no existe (borrado a mano)
    estado = r[0]["status"]["privacyStatus"]
    if estado != "private":
        raise SystemExit(f"La version anterior ({vid}) esta {estado}: no se borra ni se sube otra. Decide tu.")
    yt.videos().delete(id=vid).execute()
    print(f"version anterior {vid} (privada) borrada")
    return vid


def subir(dia_txt):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    dia = RAIZ / "dia" / dia_txt
    md = (dia / "publicacion.md").read_text(encoding="utf-8")
    titulo = bloque(md, "Título")[:100]
    descripcion = bloque(md, "Descripción")
    hashtags = bloque(md, "Hashtags")
    if hashtags:
        descripcion = f"{descripcion}\n\n{hashtags}"
    etiquetas = [e.strip() for e in bloque(md, "Etiquetas").split(",") if e.strip()]
    while len(", ".join(etiquetas)) > 480:                  # limite de YouTube: 500 caracteres en total
        etiquetas.pop()
    if not titulo or not descripcion:
        raise SystemExit("publicacion.md no tiene titulo o descripcion en el formato esperado")
    yt = build("youtube", "v3", credentials=credenciales())
    anterior = borra_anterior(yt, dia)
    cuerpo = {"snippet": {"title": titulo, "description": descripcion[:5000], "tags": etiquetas, "categoryId": "25",
                          "defaultLanguage": "es", "defaultAudioLanguage": "es"},
              "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True}}
    video = MediaFileUpload(str(dia / "episodio.mp4"), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    peticion = yt.videos().insert(part="snippet,status", body=cuerpo, media_body=video)
    respuesta = None
    while respuesta is None:
        estado, respuesta = peticion.next_chunk()
        if estado:
            print(f"  subido {int(estado.progress() * 100)} %", flush=True)
    vid = respuesta["id"]
    print(f"video {vid} subido como PRIVADO")
    avisos = []
    mini = dia / "miniatura.png"
    if mini.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(mini), mimetype="image/png")).execute()
        except Exception as e:                              # sin verificar el canal con el telefono no se permite
            avisos.append(f"miniatura no puesta ({type(e).__name__}): verifica el canal en youtube.com/verify")
    srt = dia / "episodio.srt"
    if srt.exists():
        try:
            yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "es", "name": "Español",
                                                                    "isDraft": False}},
                                 media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream")).execute()
        except Exception as e:
            avisos.append(f"subtitulos no puestos ({type(e).__name__})")
    info = {"id": vid, "url": f"https://youtu.be/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
            "estado": "privado", "titulo": titulo, "avisos": avisos, "sustituye_a": anterior}
    (dia / "youtube.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["autorizar"]:
        autorizar()
    else:
        subir(sys.argv[1])
