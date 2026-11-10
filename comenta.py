"""COMENTARIO DEL CANAL EN LOS SHORTS (10-nov-2026, petición del usuario). Cuando el usuario publica un Short (se suben
privados y los privados no admiten comentarios), el canal comenta en él con el enlace al vídeo largo del día y la
pregunta del Short: «🎬 El vídeo completo de hoy: <enlace> · ¿Tiene razón Ayuso? 👇». Va cada hora por cron; mira los
Shorts de los últimos 3 días y comenta una sola vez en cada uno (lo apunta en shorts/youtube.json, "comentado").
La API no permite fijar el comentario: si se quiere fijado, se hace a mano. Uso: python comenta.py"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from googleapiclient.discovery import build

import subir

RAIZ = Path(__file__).parent


def main():
    yt = None
    for k in range(3):
        fecha = str(date.today() - timedelta(days=k))
        for dia in sorted((RAIZ / "dia").glob(f"{fecha}*")):
            reg, largo_f = dia / "shorts" / "youtube.json", dia / "youtube.json"
            if not reg.exists():
                continue
            if not largo_f.exists():                    # carpetas aparte (…-extra): el largo es el del día
                largo_f = RAIZ / "dia" / fecha / "youtube.json"
            if not largo_f.exists():
                continue
            largo = json.loads(largo_f.read_text(encoding="utf-8"))
            hechos = json.loads(reg.read_text(encoding="utf-8"))
            cambio = False
            for h in hechos:
                if h.get("comentado"):
                    continue
                yt = yt or build("youtube", "v3", credentials=subir.credenciales())
                st = yt.videos().list(part="status", id=h["id"]).execute().get("items", [])
                if not st or st[0]["status"]["privacyStatus"] != "public":
                    continue
                pregunta = ""
                n = h.get("short_json")
                for f in (dia / "shorts").glob("short_*.json"):
                    try:
                        S = json.loads(f.read_text(encoding="utf-8"))
                    except ValueError:
                        continue
                    if S.get("titulo", "")[:30] and S["titulo"][:30] in h.get("titulo", ""):
                        pregunta = S.get("pregunta", "")
                        break
                txt = f"🎬 El vídeo completo de hoy, con todos los cruces: {largo['url']}" + (f"\n\n{pregunta} 👇" if pregunta else "")
                try:
                    yt.commentThreads().insert(part="snippet", body={"snippet": {"videoId": h["id"], "topLevelComment": {
                        "snippet": {"textOriginal": txt}}}}).execute()
                    h["comentado"] = True
                    cambio = True
                    print(f"comentado {h['id']}: {h.get('titulo', '')[:50]}")
                except Exception as e:
                    print(f"no se pudo comentar {h['id']}: {type(e).__name__}: {str(e)[:120]}")
            if cambio:
                reg.write_text(json.dumps(hechos, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
