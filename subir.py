"""SUBIDA A YOUTUBE como PRIVADO (decision del usuario del 1-nov-2026: la oficina sube, el usuario revisa y publica).

Uso:
  python subir.py autorizar            una sola vez: espera en el puerto 8765 la autorizacion del navegador
                                       (desde el PC: ssh -L 8765:localhost:8765 miguel@192.168.1.129 y abrir el enlace)
  python subir.py AAAA-MM-DD shorts   sube los Shorts del día (dia/<fecha>/shorts/short_N.mp4), privados, con portada
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
    tramo = re.search(r"^##\s*" + re.escape(seccion) + r"[^\n]*\n(.*?)(?=^##\s|\Z)", md, re.S | re.M)
    if not tramo:
        return ""
    m = re.search(r"^```[^\n]*\n(.*?)^```", tramo.group(1), re.S | re.M)
    return (m.group(1) if m else tramo.group(1)).strip()      # sin bloque ```: el texto de la seccion (2-nov)


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


def personas_dibujadas(dia):
    """Personas reales dibujadas por IA que salen en el video (viñetas aceptadas con retrato, vinetas/origen.json)."""
    o = dia / "vinetas" / "origen.json"
    if not o.exists():
        return []
    return sorted({d["persona"] for k, d in json.loads(o.read_text(encoding="utf-8")).items()
                   if d.get("persona") and (dia / "vinetas" / f"{k}.jpg").exists()})


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
    if personas_dibujadas(dia):                         # persona real dibujada por IA: se declara (no afecta a ingresos)
        try:
            yt.videos().update(part="status", body={"id": vid, "status": {
                "privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True,
                "containsSyntheticMedia": True}}).execute()
            print("declarado como contenido alterado o sintético (personas reales dibujadas por IA)")
        except Exception as e:
            avisos.append(f"no se pudo marcar «contenido alterado o sintético» ({type(e).__name__}): márcalo en "
                          "YouTube Studio antes de publicar, porque el vídeo dibuja con IA a personas reales")
    srt = dia / "episodio.srt"
    # Decision del usuario (3-nov-2026): los subtitulos ya van incrustados en la imagen, asi que no se sube pista de
    # subtitulos a YouTube (si no, se podrian activar encima de los nuestros). SUBIR_SRT=1 solo para probar.
    import os
    if srt.exists() and os.environ.get("SUBIR_SRT") == "1":
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
    try:                                                   # norma: con cada video subido, aviso por Telegram
        import notifica
        notifica.aviso_subida(info)
        print("aviso por Telegram enviado")
    except (SystemExit, Exception) as e:
        print(f"AVISO: no se pudo avisar por Telegram ({e})")


def _sube(yt, ruta, cuerpo):
    from googleapiclient.http import MediaFileUpload
    pet = yt.videos().insert(part="snippet,status", body=cuerpo,
                             media_body=MediaFileUpload(str(ruta), mimetype="video/mp4", chunksize=8 * 1024 * 1024,
                                                        resumable=True))
    resp = None
    while resp is None:
        _, resp = pet.next_chunk()
    return resp["id"]


MAX_SHORTS = 3        # cuota de la API: ~6 subidas al día; el vídeo largo y sus repeticiones van primero


def subir_shorts(dia_txt):
    """Shorts del día (decisión del usuario del 5-nov-2026), PRIVADOS como el vídeo largo: el usuario los revisa y
    publica. De cada día queda solo la última tanda: los anteriores que sigan privados se borran."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    dia = RAIZ / "dia" / dia_txt
    carpeta = dia / "shorts"
    shorts = sorted(carpeta.glob("short_*.json"), key=lambda f: int(re.sub(r"\D", "", f.stem)))[:MAX_SHORTS]
    shorts = [f for f in shorts if f.with_suffix(".mp4").exists()]
    if not shorts:
        raise SystemExit("no hay Shorts renderizados")
    yt = build("youtube", "v3", credentials=credenciales())
    reg = carpeta / "youtube.json"
    for v in (json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else []):
        r = yt.videos().list(part="status", id=v["id"]).execute().get("items", [])
        if r and r[0]["status"]["privacyStatus"] == "private":
            yt.videos().delete(id=v["id"]).execute()
            print(f"short anterior {v['id']} (privado) borrado")
    largo = json.loads((dia / "youtube.json").read_text(encoding="utf-8")) if (dia / "youtube.json").exists() else {}
    hechos = []
    for f in shorts:
        S = json.loads(f.read_text(encoding="utf-8"))
        titulo = S["titulo"].strip()
        if "#shorts" not in titulo.lower():
            titulo = f"{titulo} #Shorts"
        cita = f"«{S['cita'].strip().rstrip('.')}», {S['quien']}"
        if S.get("replica"):
            cita += f"\n«{S['replica']['cita'].strip().rstrip('.')}», responde {S['replica']['quien']}"
        partes = ([f"▶ Más información en el vídeo de hoy: {largo['url']}", ""] if largo.get("url") else []) + \
                 [cita, "", S["contexto"].strip(), "",
                  "Más información en el vídeo de hoy" + (f": {largo['url']}" if largo.get("url") else "."),
                  "¿Qué opinas? Te leo en comentarios.",
                  "", f"Fuente: {S.get('fuente', '')}" + (f" {S['enlace']}" if S.get("enlace") else "")]
        cr = S.get("creditos") or []
        if cr:
            partes += ["", "Imágenes: " + "; ".join(cr)]
        if any("sin foto libre" in c for c in cr):
            partes += ["Ilustración generada con IA en lugar de una foto (no había foto libre de la persona); "
                       "no representa a nadie en concreto."]
        if any("viñetas del tema" in c for c in cr):
            partes += ["Las viñetas son ilustraciones generadas con IA a partir de los hechos contados; las personas "
                       "dibujadas salen de fotos con licencia libre."]
        hs, vistos = [], set()                          # 7-nov: más hashtags (máx. 15: con más, YouTube los ignora)
        for h in ["#Shorts"] + list(S.get("hashtags") or []) + ["#PolíticaEspañola", "#NoticiasDeHoy", "#ElHoyformativo"]:
            h = "#" + re.sub(r"[\s#]+", "", str(h))
            if len(h) > 1 and h.lower() not in vistos:
                vistos.add(h.lower())
                hs.append(h)
        partes += ["", " ".join(hs[:15])]
        tags = list(dict.fromkeys([t.strip() for t in (S.get("etiquetas") or []) if str(t).strip()] +
                                  [S["quien"], (S.get("replica") or {}).get("quien", ""), S.get("partido", ""),
                                   "política española", "noticias de hoy", "Shorts", "El Hoyformativo"]))
        tags = [t for t in tags if t]
        while len(", ".join(tags)) > 480:
            tags.pop(-2)
        cuerpo = {"snippet": {"title": titulo[:100], "description": "\n".join(partes)[:5000], "categoryId": "25",
                              "tags": tags,
                              "defaultLanguage": "es", "defaultAudioLanguage": "es"},
                  "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True}}
        if S.get("sintetico"):                          # persona real dibujada por IA: se declara (no afecta a ingresos)
            cuerpo["status"]["containsSyntheticMedia"] = True
        vid = _sube(yt, f.with_suffix(".mp4"), cuerpo)
        print(f"short {f.stem} -> {vid} (PRIVADO)")
        aviso = ""
        portada = carpeta / f"{f.stem}_portada.png"
        if portada.exists():                                # YouTube no siempre la muestra en los Shorts; se intenta
            try:
                yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(portada), mimetype="image/png")).execute()
            except Exception as e:
                aviso = f"miniatura no puesta ({type(e).__name__})"
        hechos.append({"id": vid, "url": f"https://youtube.com/shorts/{vid}", "titulo": titulo,
                       "studio": f"https://studio.youtube.com/video/{vid}/edit", "aviso": aviso, "portada": str(portada)})
        reg.write_text(json.dumps(hechos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(hechos, ensure_ascii=False, indent=1))
    try:
        import notifica
        notifica.aviso_shorts(dia_txt, hechos)
        print("aviso por Telegram enviado")
    except (SystemExit, Exception) as e:
        print(f"AVISO: no se pudo avisar por Telegram ({e})")


if __name__ == "__main__":
    if sys.argv[1:2] == ["autorizar"]:
        autorizar()
    elif sys.argv[2:3] == ["shorts"]:
        subir_shorts(sys.argv[1])
    else:
        subir(sys.argv[1])
