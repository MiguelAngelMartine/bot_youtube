"""Agente 6, IMAGENES: busca fotos de LICENCIA LIBRE en Wikimedia Commons para cada busqueda del guion y guarda
autor y licencia para el credito en pantalla. Nada de fotos de periodicos ni agencias (derechos de autor).
Uso: python imagenes.py AAAA-MM-DD   (lee "imagenes" de cada seccion de guion.json; escribe imagenes/ y creditos.json)"""
from __future__ import annotations

import html
import json
import re
import sys
import time
from pathlib import Path

import requests

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "ElHoyformativo/0.2 (https://github.com/MiguelAngelMartine/bot_youtube) python-requests"}   # Wikimedia exige un contacto; sin el, responde 429
LIBRES = ("cc0", "cc by", "cc-by", "public domain", "dominio público", "pd")


def limpia(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(t or ""))).strip()


def busca(q, n=8, ancho=1920):
    p = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
         "gsrnamespace": 6, "gsrlimit": n, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": ancho}
    for intento in range(5):                      # Commons corta si se pregunta muy seguido: esperar y repetir
        resp = requests.get(API, params=p, headers=UA, timeout=30)
        if resp.ok and resp.headers.get("content-type", "").startswith("application/json"):
            break
        time.sleep(3 * (intento + 1))
    r = resp.json()
    out = []
    for pg in sorted(r.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99)):
        ii = pg["imageinfo"][0]
        md = ii.get("extmetadata", {})
        lic = limpia(md.get("LicenseShortName", {}).get("value", ""))
        if ii["width"] < 1000 or not any(l in lic.lower() for l in LIBRES):
            continue
        out.append({"titulo": pg["title"], "url": ii.get("thumburl") or ii["url"], "ancho": ii["width"], "alto": ii["height"],
                    "autor": limpia(md.get("Artist", {}).get("value", ""))[:60] or "Wikimedia Commons", "licencia": lic,
                    "pagina": ii.get("descriptionurl")})
    return out


def main(dia_txt, elegir=None):
    dia = Path(__file__).parent / "dia" / dia_txt
    G = json.loads((dia / "guion.json").read_text(encoding="utf-8"))
    carpeta = dia / "imagenes"
    carpeta.mkdir(exist_ok=True)
    creditos = {}
    for i, s in enumerate(G["secciones"]):
        for j, q in enumerate(s.get("imagenes", [])):
            # "busqueda#k" elige el k-esimo resultado (por defecto el primero)
            q, k = (q.split("#") + ["0"])[:2]
            res = busca(q)
            if not res:
                print(f"  s{i}.{j} SIN RESULTADO: {q}")
                continue
            c = res[min(int(k), len(res) - 1)]
            ruta = carpeta / f"s{i}_{j}.jpg"
            if not (ruta.exists() and ruta.read_bytes()[:2] == b"\xff\xd8"):
                for intento in range(6):            # 429 de Wikimedia: esperar y repetir; solo vale si es una imagen
                    r = requests.get(c["url"], headers=UA, timeout=60)
                    if r.ok and r.headers.get("content-type", "").startswith("image/"):
                        ruta.write_bytes(r.content)
                        break
                    time.sleep(5 * (intento + 1))
                else:
                    print(f"  s{i}.{j} NO SE PUDO BAJAR: {c['titulo']}")
                    continue
                time.sleep(2)
            creditos[ruta.name] = c
            print(f"  s{i}.{j} {q!r} -> {c['titulo'][:70]} | {c['autor'][:30]} | {c['licencia']}")
    (dia / "creditos.json").write_text(json.dumps(creditos, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
