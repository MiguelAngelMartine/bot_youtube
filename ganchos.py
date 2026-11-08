"""GANCHOS DEL DÍA (método del director, 8-nov-2026): frases literales con impacto (ataques, zascas, descalificaciones
políticas) que los medios nacionales ponen entre comillas en sus titulares y tuits, y las de las cuentas oficiales de
partidos y políticos. Son el gancho de los primeros segundos, de la miniatura y de los Shorts; luego se cuenta la noticia.

- Lee los titulares y entradillas del día (noticias.json, los mismos medios que tuitean: Europa Press, ABC, El Mundo,
  El País, La Vanguardia...) y se queda con los que llevan una cita entre comillas.
- Gemini elige las de más gancho, dice quién la dice y a quién, y empareja la respuesta si otro titular la trae
  (canal plural: acusación con respuesta si la hay).
- El programa comprueba que cada frase está LITERAL en el titular o la entradilla; si no, fuera.
- Si existe dia/<fecha>/ganchos_director.md (ganchos que pasa el usuario, ya comprobados), van los primeros.
Escribe dia/<fecha>/ganchos.md y lo pone al principio de redes.md (lo leen el jefe de edición, el dossier de frases,
el diseñador y shorts_guion.py). Uso: python ganchos.py AAAA-MM-DD  (después de redes.py). Salida 2 = Gemini no responde."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import gem

RAIZ = Path(__file__).parent
EJEMPLOS = (RAIZ / "oficina" / "EJEMPLOS_GANCHOS.md").read_text(encoding="utf-8") if (RAIZ / "oficina" / "EJEMPLOS_GANCHOS.md").exists() else ""   # EJEMPLOS_GANCHOS: aprende del director
MARCA = "<!-- ganchos -->"
COMILLAS = re.compile(r"[«\"“]([^«»\"“”]{12,220})[»\"”]")

PROMPT = """Eres el editor de redes de un canal de YouTube de política española con tono desenfadado e impactante, pero
riguroso y plural. De estos titulares del día (cada uno con su medio y su enlace), elige hasta {n} GANCHOS: frases
literales entre comillas con impacto (ataque, zasca, réplica, descalificación política, promesa llamativa), como en los ejemplos del director; si la frase es larga, quédate con su trozo literal de más impacto en "gancho" dichas por
un político o partido. No valen frases de periodistas ni de expertos, ni tacos o insultos vejatorios.
Para cada una: quién la dice (nombre y partido), a quién va dirigida (si se ve en el titular), la frase COPIADA LETRA A
LETRA tal como va entre comillas, el medio y el enlace. Si otro titular trae la respuesta del aludido, ponla en
"replica" (también literal). Reparte entre partidos: que no sean todas del mismo.
Responde solo JSON: {{"ganchos": [{{"quien": "...", "partido": "...", "a_quien": "...", "frase": "...", "gancho": "...", "medio": "...",
"enlace": "...", "titular": "...", "replica": {{"quien": "...", "frase": "...", "enlace": "..."}} o null}}]}}

TITULARES:
{titulares}"""


def _n(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[«»“”\"'‘’]", "", s)
    return re.sub(r"\s+", " ", s).strip(" .")


def main(fecha, n=12):
    dia = RAIZ / "dia" / fecha
    noticias = json.loads((dia / "noticias.json").read_text(encoding="utf-8")) if (dia / "noticias.json").exists() else []
    cands = [x for x in noticias if COMILLAS.search(x.get("titular", "") + " " + x.get("resumen", ""))]
    texto = {x["enlace"]: x.get("titular", "") + " " + x.get("resumen", "") for x in cands}
    lineas = [f"- [{x['medio']}] {x['titular']} | {x.get('resumen', '')[:260]} ({x['enlace']})" for x in cands[:220]]
    md = [MARCA, "# GANCHOS DEL DÍA (frases literales con impacto: abren el vídeo, la miniatura y los Shorts)", ""]
    dirf = dia / "ganchos_director.md"
    if dirf.exists():
        md += ["## Del director (comprobados a mano; tienen prioridad)", dirf.read_text(encoding="utf-8").strip(), ""]
    buenos = []
    if lineas:
        r = gem.pide("ASÍ ELIGE LOS GANCHOS EL DIRECTOR (imítalo):\n" + EJEMPLOS[:6000] + "\n\n" + PROMPT.format(n=n, titulares="\n".join(lineas)), como_json=True)
        if isinstance(r, list):
            r = {"ganchos": r}
        if not isinstance(r, dict):
            print("Gemini no responde: solo los ganchos del director")
            r = {"ganchos": []}
            codigo = 2
        else:
            codigo = 0
        todo = _n(" ".join(texto.values()))
        for g in r.get("ganchos", []):
            fuente = _n(texto.get(g.get("enlace", ""), "")) or todo
            if len(g.get("frase", "").split()) < 3 or _n(g["frase"]) not in fuente:
                print(f"  fuera (no literal): «{g.get('frase', '')[:60]}»")
                continue
            rp = g.get("replica")
            if rp and _n(rp.get("frase")) not in _n(texto.get(rp.get("enlace", ""), "")) and _n(rp.get("frase")) not in todo:
                g["replica"] = rp = None
            buenos.append(g)
            l = (f"- **{g['quien']}** ({g.get('partido', '')}){' a ' + g['a_quien'] if g.get('a_quien') else ''}: "
                 f"«{g['frase']}» — {g.get('medio', '')}: {g.get('titular', '')} ({g.get('enlace', '')})")
            if rp:
                l += f"\n  - Responde **{rp['quien']}**: «{rp['frase']}» ({rp.get('enlace', '')})"
            md.append(l)
    else:
        codigo = 0
    md += ["", "(Cada frase está literal en el titular o la entradilla del medio citado. Se atribuye: «según X» en pantalla.)",
           MARCA, ""]
    bloque = "\n".join(md)
    (dia / "ganchos.md").write_text(bloque, encoding="utf-8")
    redes = dia / "redes.md"
    viejo = redes.read_text(encoding="utf-8") if redes.exists() else ""
    if MARCA in viejo:                                   # una vuelta anterior: se sustituye
        partes = viejo.split(MARCA)
        viejo = partes[0] + (partes[2] if len(partes) > 2 else "")
    redes.write_text(bloque + "\n" + viejo.lstrip(), encoding="utf-8")
    print(f"{len(buenos)} ganchos de los titulares" + (" + los del director" if dirf.exists() else "") + f" -> {dia / 'ganchos.md'}")
    return codigo


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
