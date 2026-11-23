"""RETENCIÓN SEGUNDO A SEGUNDO (23-nov-2026, el usuario aprueba la mejora 2: medir dónde se va la gente para convertir los
patrones en normas del guion). Para cada Short publicado con vistas suficientes, la curva de YouTube Analytics
(audienceWatchRatio por elapsedVideoTimeRatio) y:
  - para todos: cuánto queda a los 3 s (el gancho), a la mitad y al final, y si se repite (> 100 %);
  - si el montaje guardó sus tramos (shorts/short_N_tramos.json, desde el 23-nov; antes, la línea «SHORT N (presentador)»
    de shorts.log), cuánto se pierde por SEGUNDO en cada tipo de tramo (gancho, cita, presentador, puente, cierre) y los
    tramos concretos donde más gente se va.
Escribe archivo/retencion_<fecha>.md y lo resume por Telegram. Lo llama informe_semanal.py.
Uso: python retencion.py [días=14] [mínimo de vistas=80]"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).parent


def _tramos(dia, short):
    """[(tipo, t0, t1, texto)] del Short, o []."""
    j = dia / "shorts" / f"{short}_tramos.json"
    if j.exists():
        d = json.loads(j.read_text(encoding="utf-8"))
        return [(x["clase"], x["t0"], x["t1"], x.get("di", "")) for x in d["tramos"]], d.get("total")
    n = re.sub(r"\D", "", short)
    log = dia / "shorts.log"
    if not log.exists():
        return [], None
    lineas = [l for l in log.read_text(encoding="utf-8", errors="ignore").splitlines() if f"SHORT {n} (presentador)" in l]
    if not lineas:
        return [], None
    l = lineas[-1]
    total = float(re.search(r"\):\s*([\d.]+) s", l).group(1))
    items = re.findall(r"(Q|P)(?:·\S+)?\s+([\d.]+)", l.split(" · ", 1)[1])
    out = []
    for k, (tp, t0) in enumerate(items):
        t0 = float(t0)
        t1 = float(items[k + 1][1]) if k + 1 < len(items) else total
        clase = "gancho" if k == 0 and tp == "Q" else ("cita" if tp == "Q" else
                ("cierre" if k == len(items) - 1 else ("puente" if t1 - t0 < 3 and 0 < k else "presentador")))
        out.append((clase, t0, t1, ""))
    return out, total


def _curva(ya, vid, ini, fin):
    r = ya.reports().query(ids="channel==MINE", startDate=str(ini), endDate=str(fin), metrics="audienceWatchRatio",
                           dimensions="elapsedVideoTimeRatio", filters=f"video=={vid}").execute()
    return sorted((float(x), float(y)) for x, y in (r.get("rows") or []))


def _en(curva, ratio):
    if not curva:
        return None
    return min(curva, key=lambda p: abs(p[0] - ratio))[1]


def main(dias=14, minimo=80):
    import subir
    from googleapiclient.discovery import build
    cred = subir.credenciales()
    yt = build("youtube", "v3", credentials=cred)
    ya = build("youtubeAnalytics", "v2", credentials=cred)
    fin, ini = date.today(), date.today() - timedelta(days=60)
    shorts = []
    for d in range(dias + 1):
        dia = RAIZ / "dia" / str(fin - timedelta(days=d))
        reg = dia / "shorts" / "youtube.json"
        if reg.exists():
            for v in json.loads(reg.read_text(encoding="utf-8")):
                if v.get("id"):
                    shorts.append((dia, v.get("short", ""), v["id"], v.get("titulo", "")))
    if not shorts:
        print("sin Shorts")
        return ""
    datos = {}
    for k in range(0, len(shorts), 50):
        for it in yt.videos().list(part="statistics,status,contentDetails",
                                   id=",".join(s[2] for s in shorts[k:k + 50])).execute()["items"]:
            datos[it["id"]] = it
    filas, por_clase, peores = [], defaultdict(list), []
    for dia, short, vid, titulo in shorts:
        it = datos.get(vid)
        if not it or it["status"]["privacyStatus"] != "public" or int(it["statistics"].get("viewCount", 0)) < minimo:
            continue
        m = re.match(r"PT(?:(\d+)M)?(?:(\d+)S)?", it["contentDetails"]["duration"])
        dur = int(m.group(1) or 0) * 60 + int(m.group(2) or 0) if m else 0
        try:
            curva = _curva(ya, vid, ini, fin)
        except Exception as e:
            print(f"  {vid}: sin curva ({type(e).__name__})")
            continue
        if not curva or not dur:
            continue
        a3 = _en(curva, min(1.0, 3 / dur))
        filas.append((titulo[:60], int(it["statistics"]["viewCount"]), dur, a3, _en(curva, 0.5), _en(curva, 0.99),
                      max(y for _, y in curva)))
        tr, total = _tramos(dia, short)
        if tr and total:
            for clase, t0, t1, txt in tr:
                if t1 - t0 < 0.8:
                    continue
                r0, r1 = _en(curva, min(1, t0 / total)), _en(curva, min(1, t1 / total))
                perd = (r0 - r1) / (t1 - t0) * 100            # puntos de audiencia perdidos por segundo
                por_clase[clase].append(perd)
                peores.append((perd, titulo[:45], clase, t0, txt[:70]))
    md = [f"# Retención de los Shorts ({fin}, últimos {dias} días, ≥ {minimo} vistas)", ""]
    if filas:
        md += ["| Short | Vistas | Dur. | A los 3 s | A la mitad | Al final | Máx. |", "|---|---|---|---|---|---|---|"]
        for t, vw, du, a3, mi, fi, mx in sorted(filas, key=lambda f: -f[1]):
            md.append(f"| {t} | {vw} | {du} s | {a3:.0%} | {mi:.0%} | {fi:.0%} | {mx:.0%} |")
        media3 = sum(f[3] for f in filas) / len(filas)
        md += ["", f"Media a los 3 s (el gancho): {media3:.0%}. Se repiten (final > 100 %): "
                   f"{sum(1 for f in filas if f[5] > 1)} de {len(filas)}."]
    if por_clase:
        md += ["", "## Pérdida por segundo según el tramo (puntos de audiencia/s; más alto = peor)", ""]
        for c, xs in sorted(por_clase.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
            md.append(f"- {c}: {sum(xs) / len(xs):.1f} ({len(xs)} tramos)")
        md += ["", "## Los tramos donde más gente se va", ""]
        for perd, t, c, t0, txt in sorted(peores, reverse=True)[:8]:
            md.append(f"- {perd:.1f}/s · {t} · {c} en el segundo {t0:.0f}" + (f" · «{txt}»" if txt else ""))
    else:
        md += ["", "_Aún no hay Shorts publicados con los tramos guardados (empiezan con los del formato presentador)._"]
    out = RAIZ / "archivo" / f"retencion_{fin}.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return "\n".join(md)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else 14, int(a[1]) if len(a) > 1 else 80)
