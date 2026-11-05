"""TEXTO COMPLETO de las noticias de temas.json, para que la redaccion contraste contra el articulo entero y no solo
contra el titular (norma del canal). Los agentes no pueden descargarlas solos (la herramienta web da error con varios
medios), asi que esta herramienta las baja desde el servidor antes de la investigacion.
Uso: python articulos.py AAAA-MM-DD  ->  dia/<fecha>/articulos/NNN.txt + articulos/indice.json {enlace: fichero}
Cada .txt empieza con medio, titular, enlace y fecha, y luego el texto. Los enlaces de Google News (RTVE, La Razon,
Publico) y El Confidencial (bloquea con 403) se quedan sin texto: para esos medios solo hay titular y resumen."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
import re

import trafilatura

RAIZ = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}


TUITS = set()                                          # (cuenta, id, medio) de los tuits que incrustan los medios


def baja(noticia):
    u = noticia["enlace"]
    if "news.google.com" in u:
        return None, "Google News (sin texto)"
    try:
        r = requests.get(u, headers=UA, timeout=25)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        TUITS.update((u_, i_, noticia["medio"]) for u_, i_ in
                     re.findall(r"https?://(?:twitter|x)\.com/([A-Za-z0-9_]+)/status(?:es)?/(\d+)", r.text))   # tuits incrustados (5-nov)
        txt = trafilatura.extract(r.text, include_comments=False, include_tables=False, favor_precision=True)
        if not txt or len(txt) < 300:
            return None, "sin texto extraible"
        return txt, "ok"
    except requests.RequestException as e:
        return None, type(e).__name__


def main(dia_txt):
    dia = RAIZ / "dia" / dia_txt
    temas = json.loads((dia / "temas.json").read_text(encoding="utf-8"))
    vistas, noticias = set(), []
    for t in temas:
        for n in t["noticias"]:
            if n["enlace"] not in vistas:
                vistas.add(n["enlace"])
                noticias.append(n)
    sal = dia / "articulos"
    sal.mkdir(exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(baja, noticias))
    indice, ok, fallos = {}, 0, {}
    for k, (n, (txt, estado)) in enumerate(zip(noticias, res)):
        if txt:
            f = sal / f"{k:03d}.txt"
            f.write_text(f"MEDIO: {n['medio']}\nTITULAR: {n['titular']}\nENLACE: {n['enlace']}\n\n{txt}\n", encoding="utf-8")
            indice[n["enlace"]] = f"articulos/{f.name}"
            ok += 1
        else:
            fallos[n["medio"]] = fallos.get(n["medio"], 0) + 1
    (sal / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    (sal / "tuits.json").write_text(json.dumps(sorted(TUITS), ensure_ascii=False, indent=1), encoding="utf-8")
    # cada noticia de temas.json apunta a su texto, para que el investigador lo encuentre sin buscar
    for t in temas:
        for n in t["noticias"]:
            if n["enlace"] in indice:
                n["texto"] = indice[n["enlace"]]
    (dia / "temas.json").write_text(json.dumps(temas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{ok}/{len(noticias)} articulos con texto completo -> {sal}")
    if fallos:
        print("sin texto:", ", ".join(f"{m} {c}" for m, c in sorted(fallos.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main(sys.argv[1])
