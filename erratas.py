"""FE DE ERRATAS con Gemini (decisión del usuario del 4-nov-2026): compara lo que dijo el último episodio con las
noticias de hoy y propone correcciones si algo resultó falso o incompleto. La propuesta va después a la mesa de
control de Claude (verificador), así que un error de Gemini no llega al vídeo.
Uso: python erratas.py AAAA-MM-DD     -> dia/<fecha>/correcciones.md   (salida 2 si Gemini no responde)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import gem

RAIZ = Path(__file__).parent

PROMPT = """Eres la fe de erratas de un informativo de política española que promete que todo lo que cuenta es real.
Abajo están las frases que dijimos en el episodio anterior y las noticias de hoy (con fragmentos de artículos).
Busca SOLO contradicciones reales e importantes: una cifra que cambió de forma relevante porque era errónea, un hecho
desmentido por la parte afectada o por una fuente oficial, una cita mal atribuida, o una versión importante que no
dimos y que ya existía ese día. Una cifra que simplemente avanza (más identificados, más detenidos) NO es corrección.
Cada corrección tiene que apoyarse en un texto de abajo, citado literalmente. Ante la duda, NO hay corrección.
Un hecho POSTERIOR que no contradice lo que dijimos (hoy pasó otra cosa, alguien cambió de postura, un debate fue distinto)
NO es una corrección: lo que dijimos sigue siendo verdad. Solo es corrección si lo que dijimos era FALSO cuando lo dijimos.
Responde SOLO con JSON: {"correcciones": [{"bloque": n, "dijimos": "frase exacta del episodio",
"ahora_sabemos": "hecho nuevo", "medio": "...", "enlace": "...", "prueba": "fragmento literal del artículo",
"propuesta": "1-2 frases neutrales para leer"}]}  (lista vacía si no hay ninguna)."""


def _n(t):
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", "".join(c for c in t if not unicodedata.combining(c)))).strip()


def _se_sostiene(c, dia, dia_prev):
    """23-nov-2026 (fallo real: Gemini propuso que Bono no dijo «no hagas el tonto» y que lo de las llaves de la Moncloa
    era de Colau; las dos frases estaban, con su autor, en las fuentes del día anterior, y la corrección llegó al guion
    porque el verificador revisa las piezas, no la corrección): 1) la prueba tiene que estar LITERAL en los artículos de
    hoy; 2) si lo que dijimos es una cita «…» y aparece en las fuentes del episodio anterior junto al nombre (o el cargo) al
    que se la atribuimos, se descarta."""
    import re
    hoy = " ".join(_n(f.read_text(encoding="utf-8")) for f in (dia / "articulos").glob("*.txt"))
    try:                                                 # también los titulares y resúmenes que vio Gemini
        hoy += " " + " ".join(_n(f"{n.get('titular', '')} {n.get('resumen') or ''}")
                              for n in json.loads((dia / "noticias.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    prueba = _n(c.get("prueba", ""))
    if len(prueba) < 20 or prueba[:120] not in hoy:
        print(f"  descartada (la prueba no está literal en las noticias de hoy): {c.get('dijimos', '')[:70]}")
        return False
    dijimos = c.get("dijimos", "")
    citas = [_n(x) for x in re.findall(r"«([^»]+)»", dijimos) if len(x.split()) >= 4]
    fuera = re.sub(r"«[^»]*»", " ", dijimos)
    nombres = {_n(w) for w in re.findall(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b", fuera)}
    nombres |= {_n(w) for w in re.findall(r"\b(vicepresident\w+|ministr\w+|president\w+|portavoz|alcald\w+)\b", fuera, re.I)}
    antes = [_n(f.read_text(encoding="utf-8")) for f in (dia_prev / "articulos").glob("*.txt")]
    try:                                                 # 24-nov-2026: y los titulares de ese día (fallo real: la cita solo
        antes += [_n(f"{n.get('titular', '')} {n.get('resumen') or ''}")   # estaba en un titular de RTVE)
                  for n in json.loads((dia_prev / "noticias.json").read_text(encoding="utf-8"))]
    except (OSError, ValueError):
        pass
    for cita in citas:
        trozo = " ".join(cita.split()[:6])
        for t in antes:
            i = t.find(trozo)
            if i >= 0 and any(nm and nm in t[max(0, i - 700):i + 300] for nm in nombres):
                print(f"  descartada (la fuente original confirma la cita y su autor): {dijimos[:70]}")
                return False
    return True


def main(fecha):
    dia = RAIZ / "dia" / fecha
    previos = sorted(d for d in (RAIZ / "dia").iterdir()
                     if d.is_dir() and d.name[:10] < fecha and len(d.name) == 10 and (d / "episodio.json").exists())
    if not previos:
        (dia / "correcciones.md").write_text("SIN CORRECCIONES\n", encoding="utf-8")
        print("sin episodio anterior: SIN CORRECCIONES")
        return
    G = json.loads((previos[-1] / "episodio.json").read_text(encoding="utf-8"))
    dijimos = "\n".join(f"[bloque {i}] {p['di']}" for i, s in enumerate(G["secciones"]) for p in s["pasos"] if p.get("di"))
    noticias = json.loads((dia / "noticias.json").read_text(encoding="utf-8"))
    lista = "\n".join(f"- {n['medio']}: {n['titular']}. {n.get('resumen') or ''} ({n['enlace']})" for n in noticias)
    r = gem.pide(f"{PROMPT}\n\nEPISODIO ANTERIOR ({previos[-1].name}):\n{dijimos}\n\nNOTICIAS DE HOY:\n{lista}", como_json=True)
    if not isinstance(r, dict):
        print("Gemini no responde: usa el agente fe-de-erratas")
        sys.exit(2)
    cs = [c for c in (r.get("correcciones") or []) if _se_sostiene(c, dia, previos[-1])]
    if not cs:
        (dia / "correcciones.md").write_text("SIN CORRECCIONES\n", encoding="utf-8")
        print("SIN CORRECCIONES")
        return
    md = []
    for k, c in enumerate(cs, 1):
        md += [f"## Corrección {k}", f"Dijimos (episodio {previos[-1].name}, bloque {c.get('bloque')}): \"{c.get('dijimos')}\"",
               f"Ahora sabemos: {c.get('ahora_sabemos')} — Fuente: {c.get('medio')}, {c.get('enlace')}",
               f"Prueba: «{c.get('prueba')}»", f"Propuesta de texto: \"{c.get('propuesta')}\"", ""]
    md.append("_Propuesta de Gemini (erratas.py): ya pasó el filtro de erratas._se_sostiene (prueba literal hoy; la fuente original no confirma lo que dijimos)._")
    (dia / "correcciones.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(cs)} corrección(es) propuesta(s): pasan por el verificador")


if __name__ == "__main__":
    main(sys.argv[1])
