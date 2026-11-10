"""ESTADÍSTICAS DEL CANAL (10-nov-2026, petición del usuario: saber por qué los Shorts y los vídeos no se ven).
Lee YouTube Analytics (solo lectura): por vídeo, visualizaciones, duración media vista, % visto, me gusta, comentarios,
compartidos y suscriptores; la curva de retención (cuánta gente sigue al 10 %, 25 %, 50 %... del vídeo); y de dónde
llegan las visitas. Escribe archivo/analitica_<fecha>.md.  Uso: python analitica.py [días=28]"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from googleapiclient.discovery import build

import subir

RAIZ = Path(__file__).parent


def main(dias=28):
    cred = subir.credenciales()
    yt = build("youtube", "v3", credentials=cred)
    ya = build("youtubeAnalytics", "v2", credentials=cred)
    fin, ini = date.today(), date.today() - timedelta(days=dias)
    canal = yt.channels().list(part="contentDetails,statistics,snippet", mine=True).execute()["items"][0]
    subidas = canal["contentDetails"]["relatedPlaylists"]["uploads"]
    videos, tok = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails,snippet", playlistId=subidas, maxResults=50, pageToken=tok).execute()
        videos += [(i["contentDetails"]["videoId"], i["snippet"]["title"]) for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok:
            break
    info = {}
    for k in range(0, len(videos), 50):
        ids = ",".join(v for v, _ in videos[k:k + 50])
        for it in yt.videos().list(part="status,contentDetails,snippet", id=ids).execute()["items"]:
            info[it["id"]] = it
    publicos = [(v, t) for v, t in videos if info.get(v, {}).get("status", {}).get("privacyStatus") == "public"]
    met = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained"
    filas = []
    for v, t in publicos:
        r = ya.reports().query(ids="channel==MINE", startDate=str(ini), endDate=str(fin), metrics=met,
                               filters=f"video=={v}").execute()
        val = (r.get("rows") or [[0] * 8])[0]
        dur = info[v]["contentDetails"]["duration"]
        es_short = "#shorts" in t.lower() or "shorts" in info[v]["snippet"].get("title", "").lower()
        ret = {}
        try:
            rr = ya.reports().query(ids="channel==MINE", startDate=str(ini), endDate=str(fin), metrics="audienceWatchRatio",
                                    dimensions="elapsedVideoTimeRatio", filters=f"video=={v}").execute()
            for x, y in rr.get("rows") or []:
                for p in (0.1, 0.25, 0.5, 0.75, 1.0):
                    if abs(x - p) < 0.006:
                        ret[p] = y
        except Exception:
            pass
        filas.append((v, t, es_short, dur, info[v]["snippet"]["publishedAt"][:10], val, ret))
    fuentes = ya.reports().query(ids="channel==MINE", startDate=str(ini), endDate=str(fin), metrics="views",
                                 dimensions="insightTrafficSourceType", sort="-views").execute().get("rows") or []
    tipo = []
    try:
        tipo = ya.reports().query(ids="channel==MINE", startDate=str(ini), endDate=str(fin), metrics="views,averageViewPercentage",
                                  dimensions="creatorContentType").execute().get("rows") or []
    except Exception:
        pass
    md = [f"# Estadísticas de «{canal['snippet']['title']}» ({ini} a {fin})", "",
          f"Suscriptores: {canal['statistics'].get('subscriberCount')} · vídeos subidos: {len(videos)} · públicos: {len(publicos)}", "",
          "## Por vídeo", "", "| Publicado | Tipo | Título | Vistas | Vista media (s) | % visto | Siguen al 25 % / 50 % | Me gusta | Coment. | Compart. | Subs. |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v, t, sh, dur, pub, val, ret in sorted(filas, key=lambda f: f[4]):
        vistas, minutos, media, pct, likes, com, comp, subs = val
        r25 = f"{ret[0.25] * 100:.0f} %" if 0.25 in ret else "-"
        r50 = f"{ret[0.5] * 100:.0f} %" if 0.5 in ret else "-"
        md.append(f"| {pub} | {'Short' if sh else 'Largo'} | {t[:60]} | {vistas} | {media} | {pct:.0f} % | {r25} / {r50} | {likes} | {com} | {comp} | {subs} |")
    md += ["", "## De dónde llegan las visitas", ""] + [f"- {s}: {n}" for s, n in fuentes]
    if tipo:
        md += ["", "## Por formato", ""] + [f"- {t}: {n} vistas, {p:.0f} % visto de media" for t, n, p in tipo]
    out = RAIZ / "archivo" / f"analitica_{fin}.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return out


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 28)
