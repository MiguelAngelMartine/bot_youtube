"""DOCUMENTALISTA (contexto del día) con Gemini (decisión del usuario del 4-nov-2026): prepara contexto.md con las
historias en curso que tocan los temas de hoy y los cargos de las personas, a partir del archivo verificado
(archivo/historias.json y archivo/personas.json). Solo resume lo que ya está en el archivo: no añade nada nuevo.
Uso: python contexto.py AAAA-MM-DD     -> dia/<fecha>/contexto.md   (salida 2 si Gemini no responde)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import gem

RAIZ = Path(__file__).parent

PROMPT = """Eres el documentalista de un informativo de política española. Con el ARCHIVO VERIFICADO de abajo, prepara
el contexto para la redacción de hoy:
## Historias en curso
Para cada historia del archivo relacionada con algún tema de hoy: qué se sabía hasta ahora, con fechas, y qué dijimos.
## Personas
Cada persona del archivo que pueda salir hoy, con su cargo y partido TAL CUAL figuran en el archivo (y su fecha).
Marca «SIN VERIFICAR» si el archivo lo indica.
Reglas: usa SOLO lo que está en el archivo; no añadas nada de tu memoria (los cargos cambian y el archivo es la fuente).
Escribe en Markdown, en español, conciso."""


def main(fecha):
    dia = RAIZ / "dia" / fecha
    arch = RAIZ / "archivo"
    historias = (arch / "historias.json").read_text(encoding="utf-8") if (arch / "historias.json").exists() else "{}"
    personas = (arch / "personas.json").read_text(encoding="utf-8") if (arch / "personas.json").exists() else "{}"
    temas = json.loads((dia / "temas.json").read_text(encoding="utf-8")) if (dia / "temas.json").exists() else []
    hoy = "\n".join(f"- {t['tema']}: {t.get('resumen', '')}" for t in temas)
    md = gem.pide(f"{PROMPT}\n\nTEMAS DE HOY:\n{hoy}\n\nARCHIVO · historias.json:\n{historias}\n\nARCHIVO · personas.json:\n{personas}")
    if not md:
        print("Gemini no responde: usa el agente documentalista")
        sys.exit(2)
    (dia / "contexto.md").write_text(md.strip() + "\n\n_Contexto preparado con Gemini (contexto.py) a partir del archivo verificado._\n",
                                     encoding="utf-8")
    print(f"contexto.md listo ({len(md.split())} palabras)")


if __name__ == "__main__":
    main(sys.argv[1])
