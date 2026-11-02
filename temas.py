"""Herramienta del RECOPILADOR para ahorrar tokens sin perder calidad (2-nov-2026).

El agente solo hace lo que pide criterio: decidir qué noticias forman cada tema. Lo mecánico lo hace el servidor:
  python temas.py lista AAAA-MM-DD     -> dia/<fecha>/noticias_lista.txt: una línea por noticia (número | medio | titular
                                          | resumen corto), sin las secciones que nunca son política (deportes, loterías...)
  python temas.py arma AAAA-MM-DD      -> lee dia/<fecha>/temas_borrador.json (lo escribe el agente, solo con números)
                                          y escribe temas.json completo (medios, n_medios, noticias con titular y enlace),
                                          ordenado de más a menos medios, máximo 15 temas.
Formato del borrador: [{"id": "urda", "tema": "Accidente de Urda: investigación", "resumen": "2-3 frases",
                        "noticias": [3, 17, 42]}]"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
# secciones que nunca son política española (por la dirección de la noticia); ante la duda, la noticia se queda
FUERA = re.compile(r"/(deportes?|futbol|baloncesto|motor|loterias?|horoscopo|gente|famosos|television|series|"
                   r"gastronomia|recetas|viajes|moda|estilo|tecnologia|videojuegos|el-tiempo|tiempo)/", re.I)


def lista(fecha):
    dia = RAIZ / "dia" / fecha
    noticias = json.loads((dia / "noticias.json").read_text(encoding="utf-8"))
    lineas, fuera = [], 0
    for i, n in enumerate(noticias):
        if FUERA.search(n.get("enlace", "")):
            fuera += 1
            continue
        resumen = re.sub(r"\s+", " ", n.get("resumen") or "")[:140]
        lineas.append(f"{i} | {n['medio']} | {n['titular']}" + (f" | {resumen}" if resumen else ""))
    (dia / "noticias_lista.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"{len(lineas)} noticias en noticias_lista.txt ({fuera} descartadas por sección: deportes, loterías...)")


def arma(fecha):
    dia = RAIZ / "dia" / fecha
    noticias = json.loads((dia / "noticias.json").read_text(encoding="utf-8"))
    borrador = json.loads((dia / "temas_borrador.json").read_text(encoding="utf-8"))
    temas, avisos = [], []
    for t in borrador:
        ns = []
        for k in t.get("noticias", []):
            if not isinstance(k, int) or not 0 <= k < len(noticias):
                avisos.append(f"{t.get('id')}: la noticia {k} no existe")
                continue
            n = noticias[k]
            ns.append({"medio": n["medio"], "titular": n["titular"], "enlace": n["enlace"]})
        medios = sorted({n["medio"] for n in ns})
        if not ns:
            avisos.append(f"{t.get('id')}: sin noticias, se descarta")
            continue
        temas.append({"id": t["id"], "tema": t["tema"], "resumen": t.get("resumen", ""), "medios": medios,
                      "n_medios": len(medios), "noticias": ns})
    temas.sort(key=lambda t: -t["n_medios"])
    temas = temas[:15]
    (dia / "temas.json").write_text(json.dumps(temas, ensure_ascii=False, indent=1), encoding="utf-8")
    for a in avisos:
        print("AVISO:", a)
    print(f"temas.json: {len(temas)} temas")
    for t in temas[:8]:
        print(f"  {t['id']}: {t['n_medios']} medios, {len(t['noticias'])} noticias")


if __name__ == "__main__":
    {"lista": lista, "arma": arma}[sys.argv[1]](sys.argv[2])
