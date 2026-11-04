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
Responde SOLO con JSON: {"correcciones": [{"bloque": n, "dijimos": "frase exacta del episodio",
"ahora_sabemos": "hecho nuevo", "medio": "...", "enlace": "...", "prueba": "fragmento literal del artículo",
"propuesta": "1-2 frases neutrales para leer"}]}  (lista vacía si no hay ninguna)."""


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
    cs = r.get("correcciones") or []
    if not cs:
        (dia / "correcciones.md").write_text("SIN CORRECCIONES\n", encoding="utf-8")
        print("SIN CORRECCIONES")
        return
    md = []
    for k, c in enumerate(cs, 1):
        md += [f"## Corrección {k}", f"Dijimos (episodio {previos[-1].name}, bloque {c.get('bloque')}): \"{c.get('dijimos')}\"",
               f"Ahora sabemos: {c.get('ahora_sabemos')} — Fuente: {c.get('medio')}, {c.get('enlace')}",
               f"Prueba: «{c.get('prueba')}»", f"Propuesta de texto: \"{c.get('propuesta')}\"", ""]
    md.append("_Propuesta de Gemini (erratas.py): el verificador la comprueba antes de que entre en el vídeo._")
    (dia / "correcciones.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(cs)} corrección(es) propuesta(s): pasan por el verificador")


if __name__ == "__main__":
    main(sys.argv[1])
