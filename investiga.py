"""INVESTIGADOR externo con Gemini (plan gratuito; decisión del usuario del 4-nov-2026) para ahorrar uso del plan de
Claude sin perder calidad: Gemini lee los artículos completos y escribe el dossier; el servidor comprueba después que
CADA cita entre «» está literal en algún artículo descargado y marca las que no (el redactor no puede usarlas).
Luego la mesa de control de Claude verifica el vídeo como siempre.

Uso: python investiga.py AAAA-MM-DD <id_tema>      -> dia/<fecha>/dossier/<id>.md   (salida 0 = bien)
     python investiga.py AAAA-MM-DD frases         -> dossier/frases.md: las frases del día de todos los partidos
Si Gemini no responde (saturado, límite diario), sale con código 2 y la jornada usa el investigador de Claude.
La clave está en .env (GEMINI_API_KEY) y nunca se imprime."""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

RAIZ = Path(__file__).parent
MODELOS = ["gemini-3-flash-preview", "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]
MAX_ART, MAX_CHARS = 10, 14000                         # por tema: artículos y caracteres por artículo
PARTIDOS = "PSOE, PP, Vox, Sumar, Podemos, ERC, Junts, PNV, EH Bildu, BNG, Coalición Canaria, UPN, Compromís, SALF"


def _clave():
    kv = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines()
              if "=" in l and not l.startswith("#"))
    return kv["GEMINI_API_KEY"].strip().strip("\"'")


def gemini(prompt, temperatura=0.2):
    """Via gem.pide: modelos gratuitos por orden, espera limitada; None si Gemini esta saturado."""
    import gem
    return gem.pide(prompt, temperatura=temperatura)


def _norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[«»“”\"'‘’]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def articulos(dia, enlaces):
    """Textos completos descargados de esos enlaces (los que tienen texto)."""
    idx = json.loads((dia / "articulos" / "indice.json").read_text(encoding="utf-8"))
    out = []
    for e in enlaces:
        f = idx.get(e)
        if f and (dia / f).exists():
            out.append((dia / f).read_text(encoding="utf-8")[:MAX_CHARS])
    return out


REGLAS = """REGLAS OBLIGATORIAS (si incumples una, el dossier no vale):
- Solo hechos, cifras y citas que estén en los TEXTOS de abajo. Nada de tu memoria ni de suposiciones. Si algo no está, no existe.
- Las citas entre «» se copian LETRA A LETRA del texto de un artículo (un programa lo comprueba después; si no está literal, se descarta). No las resumas ni las corrijas.
- Cada hecho lleva [CONTRASTADO: medio1, medio2] si lo cuentan dos o más medios, o [ATRIBUIDO: medio] si solo uno, y el enlace del artículo.
- Si dos medios cuentan algo distinto (cifras, horas, frases), ponlo en «Dudas y contradicciones» con cada versión y su medio.
- Neutralidad: recoge las versiones de todas las partes (Gobierno, oposición, socios y otros) que aparezcan en los textos; si una parte no habla en los textos, dilo en el dossier.
- Escribe en español. Formato Markdown con exactamente estas secciones:
# Tema
## Hechos
## Versiones
## Cruce de declaraciones   (ataque -> respuesta, con las frases literales con más gancho de cada parte; quién, cargo, fecha y medio)
## Cifras
## Contexto
## Qué pasa ahora
## Dudas y contradicciones"""


def dossier_tema(fecha, tid):
    dia = RAIZ / "dia" / fecha
    temas = json.loads((dia / "temas.json").read_text(encoding="utf-8"))
    tema = next((t for t in temas if t["id"] == tid), None)
    if not tema:
        sys.exit(f"no existe el tema {tid}")
    # primero los artículos de medios distintos (pluralidad de líneas editoriales)
    vistos, orden = set(), []
    for n in tema["noticias"]:
        if n["medio"] not in vistos:
            vistos.add(n["medio"])
            orden.append(n)
    orden += [n for n in tema["noticias"] if n not in orden]
    textos = articulos(dia, [n["enlace"] for n in orden])[:MAX_ART]
    titulares = "\n".join(f"- {n['medio']}: {n['titular']} ({n['enlace']})" for n in tema["noticias"])
    contexto = (dia / "contexto.md").read_text(encoding="utf-8")[:6000] if (dia / "contexto.md").exists() else ""
    prompt = (f"Eres investigador de un informativo de política española neutral. Escribe el dossier del tema "
              f"«{tema['tema']}» del {fecha}.\n\n{REGLAS}\n\nCONTEXTO VERIFICADO DE DÍAS ANTERIORES:\n{contexto}\n\n"
              f"TITULARES DEL TEMA (todos los medios):\n{titulares}\n\nTEXTOS COMPLETOS DE LOS ARTÍCULOS:\n\n"
              + "\n\n=====\n\n".join(textos))
    return gemini(prompt), textos + [titulares]


def dossier_frases(fecha):
    dia = RAIZ / "dia" / fecha
    idx = json.loads((dia / "articulos" / "indice.json").read_text(encoding="utf-8"))
    parrafos = []                                       # solo los párrafos con citas: la entrada es mucho menor
    for f in idx.values():
        if not (dia / f).exists():
            continue
        txt = (dia / f).read_text(encoding="utf-8")
        cab = "\n".join(txt.splitlines()[:3])
        citas = [p for p in txt.split("\n") if re.search(r"[«“\"].{12,}[»”\"]", p)]
        if citas:
            parrafos.append(cab + "\n" + "\n".join(citas[:12]))
    prompt = (f"Eres investigador de un informativo de política española neutral. Del {fecha}, en campaña electoral, "
              f"recoge LAS FRASES DEL DÍA CON MÁS GANCHO de todos los partidos (sobre todo de sus redes oficiales: las publicaciones de abajo; y de Isabel Díaz Ayuso si ha dicho algo) ({PARTIDOS}): mítines, entrevistas, "
              f"ruedas de prensa y mensajes en X o redes que recogen los medios. Para cada ataque, la respuesta del "
              f"aludido si está en los textos. Busca el mismo número de frases por partido; si de alguno no hay, dilo.\n\n"
              f"{REGLAS}\n(En este dossier la sección «Cruce de declaraciones» es la principal; añade «## Frases sueltas» "
              f"con las que no tienen respuesta.)\n\nPÁRRAFOS CON DECLARACIONES (cada bloque empieza por medio, titular y "
              f"enlace):\n\n" + "\n\n=====\n\n".join(parrafos[:120]))
    redes = dia / "redes.md"                            # publicaciones oficiales de los partidos (redes.py, 4-nov-2026)
    if redes.exists():
        r = redes.read_text(encoding="utf-8")[:40000]
        prompt += ("\n\n=====\n\nPUBLICACIONES OFICIALES DE LOS PARTIDOS Y SUS LÍDERES (webs, Telegram, Bluesky; cada una "
                   "con su enlace; cítalas como «<quién>, en <canal>»):\n" + r)
        parrafos = parrafos + [r]
    return gemini(prompt), parrafos


def comprueba_citas(md, textos):
    """Marca las citas «...» que no están literales en ningún texto. Devuelve (md marcado, n_ok, n_mal)."""
    base = _norm("\n".join(textos))
    ok = mal = 0

    def revisa(m):
        nonlocal ok, mal
        cita = m.group(1)
        if len(cita.split()) < 3 or _norm(cita) in base:
            ok += 1
            return m.group(0)
        mal += 1
        return m.group(0) + " ⚠️[CITA NO LITERAL EN LAS FUENTES: NO USAR]"
    md = re.sub(r"«([^»]{3,600})»", revisa, md)
    return md, ok, mal


def main(fecha, tid):
    dia = RAIZ / "dia" / fecha
    md, textos = dossier_frases(fecha) if tid == "frases" else dossier_tema(fecha, tid)
    if not md:
        print(f"{tid}: Gemini no responde; usa el investigador de Claude")
        sys.exit(2)
    md = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", md.strip())
    md, ok, mal = comprueba_citas(md, textos)
    md += (f"\n\n## Comprobación automática de citas\n{ok} citas literales comprobadas en los artículos; {mal} no "
           f"encontradas literalmente (marcadas con ⚠️: el redactor no puede usarlas).\n"
           f"_Dossier hecho con Gemini (investiga.py) a partir de los artículos descargados._\n")
    (dia / "dossier").mkdir(exist_ok=True)
    (dia / "dossier" / f"{tid}.md").write_text(md, encoding="utf-8")
    print(f"{tid}: dossier listo ({len(md.split())} palabras; citas {ok} bien, {mal} marcadas)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
